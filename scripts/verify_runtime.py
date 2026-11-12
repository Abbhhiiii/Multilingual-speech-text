"""Real, paced stdin test. Success requires nonblank output before stdin closes."""
import argparse
import asyncio
import codecs
import json
import time
import wave
from pathlib import Path
import psutil

async def verify(args):
    with wave.open(args.wav, 'rb') as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getcomptype()) == (16000, 1, 2, 'NONE')
        pcm = w.readframes(w.getnframes())
    command = [args.binary, '-d', args.model, '--stdin', '--stream', '-t', '4']
    started = time.monotonic()
    proc = await asyncio.create_subprocess_exec(*command, stdin=-1, stdout=-1, stderr=-1)
    events, diagnostics, samples = [], bytearray(), []
    eof_at = None
    async def send():
        nonlocal eof_at
        for offset in range(0, len(pcm), 16000):
            end = min(offset + 16000, len(pcm))
            await asyncio.sleep(max(0, started + end / 32000 - time.monotonic()))
            proc.stdin.write(pcm[offset:end])
            await proc.stdin.drain()
        eof_at = time.monotonic() - started
        proc.stdin.close()
        await proc.stdin.wait_closed()
    async def read():
        decoder = codecs.getincrementaldecoder('utf-8')()
        while data := await proc.stdout.read(1024):
            text = decoder.decode(data)
            if text:
                events.append({'seconds': time.monotonic() - started, 'text': text, 'before_eof': eof_at is None})
        tail = decoder.decode(b'', final=True)
        if tail: events.append({'seconds': time.monotonic() - started, 'text': tail, 'before_eof': eof_at is None})
    async def stderr():
        while data := await proc.stderr.read(4096): diagnostics.extend(data)
    async def monitor():
        p = psutil.Process(proc.pid)
        while proc.returncode is None:
            try: samples.append({'seconds': time.monotonic() - started, 'rss_bytes': p.memory_info().rss, 'cpu_percent': p.cpu_percent()})
            except psutil.NoSuchProcess: break
            await asyncio.sleep(.2)
    monitoring = asyncio.create_task(monitor())
    try:
        await asyncio.wait_for(asyncio.gather(send(), read(), stderr(), proc.wait()), 240)
    finally:
        if proc.returncode is None: proc.kill(); await proc.wait()
        await monitoring
    result = {'command': command, 'audio_seconds': len(pcm)/32000, 'stdin_closed_seconds': eof_at,
              'elapsed_seconds': time.monotonic()-started, 'exit_code': proc.returncode,
              'incremental_verified': proc.returncode == 0 and any(e['before_eof'] and e['text'].strip() for e in events),
              'transcript': ''.join(e['text'] for e in events).strip(), 'events': events,
              'peak_sampled_rss_bytes': max((s['rss_bytes'] for s in samples), default=0),
              'resource_samples': samples, 'stderr': diagnostics.decode('utf-8', 'replace')}
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('resource_samples','stderr','events')}, indent=2))
    return result['incremental_verified']

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    for name in ('binary','model','wav','output'): p.add_argument('--'+name, required=True)
    raise SystemExit(0 if asyncio.run(verify(p.parse_args())) else 1)
