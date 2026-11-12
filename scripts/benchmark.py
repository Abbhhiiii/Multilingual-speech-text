"""Run paced WebSocket trials from a pinned manifest; no benchmark data is bundled."""
import argparse, asyncio, csv, json, re, time, unicodedata, wave
from pathlib import Path
import psutil, websockets
from jiwer import wer, cer

def normalize(text):
    text=unicodedata.normalize('NFKC', text).casefold()
    return ' '.join(''.join(' ' if unicodedata.category(c).startswith('P') else c for c in text).split())

async def trial(item, chunk_ms, url, backend_pid, run_id):
    path=Path(item['wav'])
    with wave.open(str(path),'rb') as w:
        if (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getcomptype())!=(16000,1,2,'NONE'):
            raise ValueError(f'{path}: expected 16 kHz mono PCM16 WAV')
        pcm=w.readframes(w.getnframes())
    events=[]; resources=[]; done=asyncio.Event(); first_send=None; end_sent=None
    async def monitor():
        parent=psutil.Process(backend_pid) if backend_pid else None
        while not done.is_set():
            if parent:
                try:
                    procs=[parent,*parent.children(recursive=True)]
                    resources.append({'t':time.monotonic()-start,
                        'rss_bytes_sum':sum(p.memory_info().rss for p in procs if p.is_running()),
                        'cpu_percent_sum':sum(p.cpu_percent(interval=None) for p in procs if p.is_running()),
                        'process_count':len(procs)})
                except psutil.Error: pass
            await asyncio.sleep(.2)
    async with websockets.connect(url,max_size=2**20) as ws:
        start=time.monotonic()
        await ws.send(json.dumps({'type':'start','sample_rate':16000,'channels':1,'encoding':'pcm_s16le','chunk_ms':chunk_ms,'language':item['language']}))
        ready=json.loads(await ws.recv())
        if ready['type']!='ready': raise RuntimeError(ready)
        monitor_task=asyncio.create_task(monitor())
        async def send():
            nonlocal first_send,end_sent
            origin=time.monotonic()
            for offset in range(0,len(pcm),chunk_ms*32):
                end=min(offset+chunk_ms*32,len(pcm))
                await asyncio.sleep(max(0,origin+end/32000-time.monotonic()))
                if first_send is None:first_send=time.monotonic()-start
                await ws.send(pcm[offset:end])
            await ws.send(json.dumps({'type':'end'}));end_sent=time.monotonic()-start
        sending=asyncio.create_task(send())
        try:
            while True:
                e=json.loads(await asyncio.wait_for(ws.recv(),180));e['client_elapsed_seconds']=time.monotonic()-start
                e['before_end']=end_sent is None;events.append(e)
                if e['type'] in ('done','error'):break
        finally:
            done.set();sending.cancel()
            await asyncio.gather(sending,monitor_task,return_exceptions=True)
    final=events[-1]; reference=item.get('reference'); prediction=final.get('text','')
    ref=normalize(reference) if reference is not None else None; pred=normalize(prediction)
    result={'run_id':run_id,'id':item['id'],'wav':str(path),'language':item['language'],'chunk_ms':chunk_ms,
        'audio_seconds':len(pcm)/32000,'status':final['type'],'error_code':final.get('code'),
        'first_text_ms':final.get('metrics',{}).get('first_text_ms'),
        'final_latency_ms':final.get('metrics',{}).get('final_latency_ms'),
        'session_elapsed_ms':final.get('metrics',{}).get('elapsed_ms'),
        'incremental':any(e['type']=='transcript' and e.get('text','').strip() and e['before_end'] for e in events),
        'peak_sampled_rss_sum_bytes':max((r['rss_bytes_sum'] for r in resources),default=None),
        'peak_sampled_cpu_percent_sum':max((r['cpu_percent_sum'] for r in resources),default=None),
        'reference':reference,'prediction':prediction,
        'wer':wer(ref,pred) if ref is not None and item['language']!='zh' else None,
        'cer':cer(ref.replace(' ',''),pred.replace(' ','')) if ref is not None and item['language']=='zh' else None,
        'resource_samples':resources,'events':events}
    return result

async def main(args):
    manifest=json.loads(Path(args.manifest).read_text())
    if not isinstance(manifest,list) or not manifest:raise ValueError('Manifest must be a nonempty JSON array')
    required={'id','wav','language'}
    for item in manifest:
        if not required<=item.keys() or item['language'] not in ('en','zh','id'):
            raise ValueError('Each item needs id, wav and language en/zh/id')
    out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    rows=[]
    for item in manifest:
        for chunk_ms in args.chunks:
            for repeat in range(args.repeats):
                run_id=f"{item['id']}-{chunk_ms}-{repeat+1}"
                result=await trial(item,chunk_ms,args.url,args.backend_pid,run_id)
                (out/f'{run_id}.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
                rows.append({k:v for k,v in result.items() if k not in ('resource_samples','events')})
                print(run_id,result['status'],result['first_text_ms'],result['wer'],result['cer'],flush=True)
    with (out/'summary.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=rows[0].keys());writer.writeheader();writer.writerows(rows)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('manifest');p.add_argument('--url',default='ws://127.0.0.1:8000/ws/transcribe')
    p.add_argument('--output',default='evidence/benchmark');p.add_argument('--backend-pid',type=int)
    p.add_argument('--chunks',type=int,nargs='+',choices=[250,500,1000],default=[250,500,1000])
    p.add_argument('--repeats',type=int,default=1)
    asyncio.run(main(p.parse_args()))
