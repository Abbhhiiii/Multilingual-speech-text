import asyncio
import json
import logging
import time
import uuid
import anyio
from contextlib import suppress
from typing import Literal

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, ValidationError
from .runtime import Runtime, Settings

log = logging.getLogger('tetherfi')

class Start(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    type: Literal['start']
    sample_rate: Literal[16000]
    channels: Literal[1]
    encoding: Literal['pcm_s16le']
    chunk_ms: Literal[250, 500, 1000] = 500
    language: Literal['auto', 'en', 'zh', 'id'] = 'auto'

class StreamError(Exception):
    def __init__(self, code, message): self.code, self.message = code, message


def create_app(settings=None, command_factory=None):
    config = settings or Settings()
    app = FastAPI(title='Tetherfi CPU Streaming ASR')
    active = set()
    app.state.active = active

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'active_sessions': len(active), 'max_sessions': config.max_sessions,
                'note': 'Service health only; model readiness is verified by transcription.'}

    @app.websocket('/ws/transcribe')
    async def transcribe(ws: WebSocket):
        # Local development only; disallow cross-site browser requests.
        origin = ws.headers.get('origin')
        if origin and origin not in {'http://localhost:5173', 'http://127.0.0.1:5173',
                                     'http://localhost:8000', 'http://127.0.0.1:8000'}:
            await ws.close(code=1008)
            return
        await ws.accept()
        sid = str(uuid.uuid4())
        if len(active) >= config.max_sessions:
            await ws.send_json({'type': 'error', 'code': 'capacity', 'message': 'All inference slots are busy. Try again after the active stream finishes.'})
            await ws.close(code=1013)
            return
        active.add(sid)  # No await between capacity check and reservation.
        runtime = None
        tasks = []
        lock = asyncio.Lock()
        started = time.monotonic()
        first_audio = first_text = ended = None
        received = forwarded = 0
        transcript = ''
        sequence = 0

        async def send(event):
            async with lock:
                await asyncio.wait_for(ws.send_json({'session_id': sid, **event}), 10)

        def metrics():
            now = time.monotonic()
            return {'elapsed_ms': round((now-started)*1000, 2),
                    'first_text_ms': None if first_text is None else round((first_text-first_audio)*1000, 2),
                    'final_latency_ms': None if ended is None else round((now-ended)*1000, 2),
                    'audio_received_seconds': received/32000,
                    'audio_forwarded_seconds': forwarded/32000,
                    'application_queue_seconds': (received-forwarded)/32000}

        try:
            async with asyncio.timeout(config.session_timeout):
                raw = await asyncio.wait_for(ws.receive_text(), config.idle_timeout)
                if len(raw) > 4096: raise StreamError('metadata', 'Start message is too large.')
                start = Start.model_validate_json(raw)
                runtime = Runtime((command_factory or config.command)(start.language))
                await runtime.start()
                await send({'type': 'ready', 'chunk_ms': start.chunk_ms,
                            'message': 'Worker started; model loading is included in first-text latency.'})
                queue = asyncio.Queue(maxsize=config.queue_chunks)
                input_closed = asyncio.Event()
                short_seen = False

                async def receive():
                    nonlocal received, first_audio, ended, short_seen
                    while True:
                        message = await ws.receive() if ended is not None else await asyncio.wait_for(ws.receive(), config.idle_timeout)
                        if message['type'] == 'websocket.disconnect': raise WebSocketDisconnect()
                        data = message.get('bytes')
                        if data is not None:
                            if ended is not None or short_seen:
                                raise StreamError('protocol', 'Audio is not allowed after the final chunk or end.')
                            if not data or len(data) % 2 or len(data) > start.chunk_ms*32:
                                raise StreamError('audio', 'PCM chunks must contain complete 16-bit samples and fit the selected chunk size.')
                            now = time.monotonic()
                            if first_audio is None: first_audio = now
                            if received + len(data) > config.max_audio_seconds*32000:
                                raise StreamError('duration', 'Audio exceeds the five-minute session limit.')
                            if received + len(data) > (now-first_audio+2)*32000:
                                raise StreamError('pacing', 'Send audio at real-time speed, not as a whole-file upload.')
                            short_seen = len(data) < start.chunk_ms*32
                            received += len(data)
                            try: queue.put_nowait(data)
                            except asyncio.QueueFull: raise StreamError('backpressure', 'Inference input is falling behind. Stream stopped.')
                        else:
                            text = message.get('text') or ''
                            if len(text) > 4096: raise StreamError('protocol', 'Control message too large.')
                            try: control = json.loads(text)
                            except ValueError: raise StreamError('protocol', 'Invalid JSON control message.')
                            if control == {'type': 'cancel'}:
                                raise StreamError('cancelled', 'Stream cancelled.')
                            if control != {'type': 'end'} or ended is not None:
                                raise StreamError('protocol', 'Expected end or cancel.')
                            if not received: raise StreamError('audio', 'No audio received.')
                            ended = time.monotonic()
                            # Await the bounded writer queue while the runtime continues draining.
                            await queue.put(None)
                            input_closed.set()
                            # Continue receiving so cancellation/disconnect also works during finalization.

                async def write():
                    nonlocal forwarded
                    while True:
                        data = await queue.get()
                        if data is None:
                            await runtime.end()
                            return
                        await runtime.write(data)
                        forwarded += len(data)

                async def output():
                    nonlocal transcript, first_text, sequence
                    async for piece in runtime.pieces():
                        transcript += piece
                        if piece.strip() and first_text is None:
                            if first_audio is None: raise StreamError('runtime', 'Worker emitted text before receiving audio.')
                            first_text = time.monotonic()
                        sequence += 1
                        await send({'type': 'transcript', 'text': transcript.rstrip('\n'), 'sequence': sequence,
                                    'metrics': metrics()})
                    code = await runtime.wait()
                    if code != 0:
                        log.error('Worker %s exited %s: %s', sid, code, runtime.stderr_tail.decode('utf-8', 'replace'))
                        raise StreamError('runtime', 'ASR worker failed. Check backend logs and model setup.')
                    if ended is None: raise StreamError('runtime', 'ASR worker ended before the audio stream.')
                    return

                async def finish_watchdog():
                    await input_closed.wait()
                    await asyncio.sleep(config.finish_timeout)
                    raise StreamError('timeout', 'ASR finalization exceeded the time limit.')

                reader = asyncio.create_task(receive())
                writer = asyncio.create_task(write())
                output_task = asyncio.create_task(output())
                watchdog = asyncio.create_task(finish_watchdog())
                tasks = [reader, writer, output_task, watchdog]
                pending = set(tasks)
                while output_task in pending:
                    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                    for task in done: task.result()
                await send({'type': 'done', 'text': transcript.rstrip('\n'), 'metrics': metrics()})
        except WebSocketDisconnect:
            pass
        except (ValidationError, KeyError):
            with suppress(Exception): await send({'type': 'error', 'code': 'metadata', 'message': 'Invalid stream metadata or encoding.'})
        except StreamError as exc:
            with suppress(Exception): await send({'type': 'error', 'code': exc.code, 'message': exc.message})
        except TimeoutError:
            with suppress(Exception): await send({'type': 'error', 'code': 'timeout', 'message': 'Stream timed out.'})
        except (OSError, UnicodeError, RuntimeError) as exc:
            log.exception('Session %s failed', sid)
            with suppress(Exception): await send({'type': 'error', 'code': 'runtime', 'message': 'Could not run the ASR worker. Check backend logs and model setup.'})
        finally:
            # Server shutdown/client cancellation must not interrupt process reaping.
            with anyio.CancelScope(shield=True):
                for task in tasks: task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                try:
                    if runtime: await runtime.close()
                finally:
                    active.discard(sid)
                with suppress(Exception): await ws.close()

    return app

app = create_app()
