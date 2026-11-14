"""One CPU-only process per call. No shell and no shared audio/context."""
import asyncio
import codecs
import json
import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    binary: str = os.environ.get('ASR_BINARY', str(ROOT / '.runtime/qwen-asr/qwen_asr'))
    model: str = os.environ.get('ASR_MODEL', str(ROOT / '.runtime/models/qwen3-asr-0.6b'))
    threads: int = int(os.environ.get('ASR_THREADS', '4'))
    max_sessions: int = int(os.environ.get('ASR_MAX_SESSIONS', '0'))
    hypotheses: bool = os.environ.get('ASR_HYPOTHESES', '1') == '1'
    stream_step_sec: float = float(os.environ.get('ASR_STREAM_STEP_SEC', '2.0'))
    unfixed_chunks: int = int(os.environ.get('ASR_UNFIXED_CHUNKS', '2'))
    idle_timeout: float = 30
    finish_timeout: float = 120
    session_timeout: float = 600
    max_audio_seconds: int = 300
    queue_chunks: int = 16

    def command(self, language):
        args = [self.binary, '-d', self.model, '--stdin', '--stream', '-t', str(self.threads)]
        if self.hypotheses:
            args += ['--hypotheses', '--stream-chunk-sec', str(self.stream_step_sec),
                     '--stream-unfixed-chunks', str(self.unfixed_chunks)]
        if language != 'auto':
            args += ['--language', {'en': 'English', 'zh': 'Chinese', 'id': 'Indonesian'}[language]]
        return args

class Runtime:
    def __init__(self, command):
        self.command = command
        self.hypotheses = '--hypotheses' in command
        self.process = None
        self.stderr_tail = b''
        self.stderr_task = None

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            *self.command, stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE, limit=65536)
        self.stderr_task = asyncio.create_task(self._stderr())

    async def _stderr(self):
        while data := await self.process.stderr.read(4096):
            self.stderr_tail = (self.stderr_tail + data)[-16384:]

    async def write(self, data):
        self.process.stdin.write(data)
        await asyncio.wait_for(self.process.stdin.drain(), 15)

    async def end(self):
        self.process.stdin.close()
        await self.process.stdin.wait_closed()

    async def pieces(self):
        if self.hypotheses:
            while line := await self.process.stdout.readline():
                event = json.loads(line.decode('utf-8'))
                if not isinstance(event, dict) or not isinstance(event.get('text'), str):
                    raise ValueError('Invalid hypothesis event')
                yield event['text']
            return
        # Legacy committed text flushes tokens without newlines.
        decoder = codecs.getincrementaldecoder('utf-8')('strict')
        while data := await self.process.stdout.read(4096):
            piece = decoder.decode(data)
            if piece: yield piece
        tail = decoder.decode(b'', final=True)
        if tail: yield tail

    async def wait(self):
        code = await self.process.wait()
        await asyncio.shield(self.stderr_task)
        return code

    async def close(self):
        if self.process and self.process.returncode is None:
            try: self.process.terminate()
            except ProcessLookupError: pass
            try: await asyncio.wait_for(self.process.wait(), 3)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
        if self.stderr_task:
            await asyncio.gather(self.stderr_task, return_exceptions=True)
