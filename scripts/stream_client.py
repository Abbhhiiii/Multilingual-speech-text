"""Real-time WebSocket smoke client; records actual events, not fabricated results."""
import argparse
import asyncio
import json
import time
import wave
from pathlib import Path
import websockets

async def run(args):
    with wave.open(args.wav, 'rb') as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getcomptype()) != (16000,1,2,'NONE'):
            raise ValueError('Expected 16 kHz mono PCM16 WAV')
        pcm=w.readframes(w.getnframes())
    events=[]
    async with websockets.connect(args.url, max_size=2**20) as ws:
        start=time.monotonic()
        await ws.send(json.dumps(dict(type='start',sample_rate=16000,channels=1,encoding='pcm_s16le',chunk_ms=args.chunk_ms,language=args.language)))
        ready=json.loads(await ws.recv())
        if ready['type']!='ready': raise RuntimeError(ready)
        end_sent=None
        async def send():
            nonlocal end_sent
            origin=time.monotonic()
            for offset in range(0,len(pcm),args.chunk_ms*32):
                end=min(offset+args.chunk_ms*32,len(pcm))
                await asyncio.sleep(max(0,origin+end/32000-time.monotonic()))
                await ws.send(pcm[offset:end])
            await ws.send(json.dumps({'type':'end'}))
            end_sent=time.monotonic()-start
        sender=asyncio.create_task(send())
        try:
            while True:
                event=json.loads(await asyncio.wait_for(ws.recv(),180))
                event['client_elapsed_seconds']=time.monotonic()-start
                event['before_client_end']=end_sent is None
                events.append(event)
                if event['type'] in ('done','error'): break
            if events[-1]['type'] == 'error': sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)
        finally:
            sender.cancel()
            await asyncio.gather(sender,return_exceptions=True)
    report={'wav':args.wav,'language':args.language,'chunk_ms':args.chunk_ms,'audio_seconds':len(pcm)/32000,
            'client_end_seconds':end_sent,'incremental_verified':any(e['type']=='transcript' and e.get('text','').strip() and e['before_client_end'] for e in events),
            'events':events}
    Path(args.output).write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'incremental_verified':report['incremental_verified'],'final':events[-1]},ensure_ascii=False,indent=2))
    return events[-1]['type']=='done' and (not args.require_incremental or report['incremental_verified'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('wav');p.add_argument('--url',default='ws://127.0.0.1:8000/ws/transcribe')
    p.add_argument('--language',choices=['auto','en','zh','id'],default='auto')
    p.add_argument('--chunk-ms',type=int,choices=[250,500,1000],default=500)
    p.add_argument('--output',default='evidence/websocket.json');p.add_argument('--require-incremental',action='store_true')
    raise SystemExit(0 if asyncio.run(run(p.parse_args())) else 1)
