"""Run selected WAV clips together and sample aggregate backend/worker resources."""
import argparse
import asyncio
import json
import statistics
import time
import wave
from pathlib import Path

import psutil
import websockets


def read_pcm(item):
    with wave.open(item['wav'], 'rb') as recording:
        if (recording.getframerate(), recording.getnchannels(),
                recording.getsampwidth(), recording.getcomptype()) != (16000, 1, 2, 'NONE'):
            raise ValueError(f"{item['wav']}: expected 16 kHz mono PCM16 WAV")
        return recording.readframes(recording.getnframes())


async def call(item, pcm, ready, go, url, chunk_ms):
    result = {'id': item['id'], 'wav': item['wav'], 'audio_seconds': len(pcm) / 32000,
              'status': 'client_error', 'events': []}
    sender = None
    try:
        async with websockets.connect(url, max_size=2**20) as ws:
            await ws.send(json.dumps({'type': 'start', 'sample_rate': 16000, 'channels': 1,
                                      'encoding': 'pcm_s16le', 'chunk_ms': chunk_ms,
                                      'language': item.get('request_language', item['language'])}))
            response = json.loads(await asyncio.wait_for(ws.recv(), 30))
            if response['type'] != 'ready':
                result.update(status='error', final=response)
                return result
            result['session_id'] = response['session_id']
            ready.set()
            await go.wait()
            origin = time.monotonic()

            async def send_audio():
                for offset in range(0, len(pcm), chunk_ms * 32):
                    end = min(offset + chunk_ms * 32, len(pcm))
                    await asyncio.sleep(max(0, origin + end / 32000 - time.monotonic()))
                    await ws.send(pcm[offset:end])
                await ws.send(json.dumps({'type': 'end'}))
                result['client_audio_end_seconds'] = time.monotonic() - origin

            sender = asyncio.create_task(send_audio())
            while True:
                event = json.loads(await asyncio.wait_for(ws.recv(), 240))
                event['client_elapsed_seconds'] = time.monotonic() - origin
                result['events'].append(event)
                if event['type'] in ('done', 'error'):
                    result.update(status=event['type'], final=event,
                                  client_elapsed_seconds=time.monotonic() - origin)
                    break
    except Exception as exc:
        result['client_exception'] = f'{type(exc).__name__}: {exc}'
    finally:
        ready.set()
        if sender is not None:
            if not sender.done():
                sender.cancel()
            await asyncio.gather(sender, return_exceptions=True)
        result['first_text_ms'] = next(
            (event.get('metrics', {}).get('first_text_ms')
             for event in result['events']
             if event['type'] == 'transcript' and event.get('text', '').strip()), None)
        result['final_latency_ms'] = result.get('final', {}).get('metrics', {}).get('final_latency_ms')
        first_visible = next(
            (event for event in result['events']
             if event['type'] == 'transcript' and event.get('text', '').strip()), None)
        audio_end = result.get('client_audio_end_seconds')
        result['first_text_before_audio_end'] = (
            first_visible['client_elapsed_seconds'] < audio_end
            if first_visible is not None and audio_end is not None else None)
    return result


async def monitor(backend_pid, started, done, samples, cpu_time_by_pid, sample_seconds):
    parent = psutil.Process(backend_pid)
    known = {}
    psutil.cpu_percent(interval=None)
    while not done.is_set():
        swap = psutil.swap_memory()
        sample = {'t': time.monotonic() - started, 'backend_rss_bytes': None,
                  'worker_count': 0, 'workers_rss_bytes': 0, 'workers_uss_bytes': 0,
                  'workers_cpu_percent': None,
                  'system_cpu_percent': psutil.cpu_percent(interval=None),
                  'system_available_bytes': psutil.virtual_memory().available,
                  'system_swap_used_bytes': swap.used,
                  'system_swap_in_bytes': swap.sin,
                  'system_swap_out_bytes': swap.sout}
        try:
            sample['backend_rss_bytes'] = parent.memory_info().rss
            children = parent.children(recursive=True)
        except psutil.Error:
            children = []
        cpu_total = 0.0
        cpu_seen = 0
        uss_seen = 0
        for process in children:
            try:
                if process.name() != 'qwen_asr':
                    continue
                sample['worker_count'] += 1
                sample['workers_rss_bytes'] += process.memory_info().rss
                try:
                    sample['workers_uss_bytes'] += process.memory_full_info().uss
                    uss_seen += 1
                except (AttributeError, psutil.Error):
                    pass
                times = process.cpu_times()
                cpu_time_by_pid[process.pid] = max(
                    cpu_time_by_pid.get(process.pid, 0), times.user + times.system)
                if process.pid not in known:
                    known[process.pid] = process
                    process.cpu_percent(interval=None)
                else:
                    cpu_total += known[process.pid].cpu_percent(interval=None)
                    cpu_seen += 1
            except psutil.Error:
                pass
        if cpu_seen:
            sample['workers_cpu_percent'] = cpu_total
        if uss_seen != sample['worker_count']:
            sample['workers_uss_bytes'] = None
        samples.append(sample)
        await asyncio.sleep(sample_seconds)


async def run(args):
    manifest = json.loads(Path(args.manifest).read_text())
    by_id = {item['id']: item for item in manifest}
    items = [by_id[name] for name in args.ids]
    pcm = [read_pcm(item) for item in items]
    count = len(items)
    ready = [asyncio.Event() for _ in items]
    go = asyncio.Event()
    done = asyncio.Event()
    samples = []
    cpu_time_by_pid = {}
    baseline_available = psutil.virtual_memory().available
    baseline_swap = psutil.swap_memory()
    started = time.monotonic()
    monitor_task = asyncio.create_task(monitor(args.backend_pid, started, done,
                                                  samples, cpu_time_by_pid,
                                                  args.sample_seconds))
    tasks = [asyncio.create_task(call(item, data, event, go, args.url, args.chunk_ms))
             for item, data, event in zip(items, pcm, ready)]
    try:
        await asyncio.wait_for(asyncio.gather(*(event.wait() for event in ready)), 40)
        go.set()
        calls = await asyncio.gather(*tasks)
    finally:
        done.set()
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await monitor_task

    overlap = [sample for sample in samples if sample['worker_count'] == count]
    def peak(rows, key):
        return max((row[key] for row in rows if row.get(key) is not None), default=None)
    def average(rows, key):
        values = [row[key] for row in rows if row.get(key) is not None]
        return statistics.mean(values) if values else None
    report = {'ids': args.ids, 'chunk_ms': args.chunk_ms, 'request_language':
              [item.get('request_language', item['language']) for item in items],
              'baseline_available_bytes': baseline_available,
              'baseline_swap_used_bytes': baseline_swap.used,
              'baseline_swap_in_bytes': baseline_swap.sin,
              'baseline_swap_out_bytes': baseline_swap.sout,
              'sample_requested_seconds': args.sample_seconds,
              'wall_elapsed_seconds': time.monotonic() - started,
              'full_overlap_sample_count': len(overlap),
              'peak_worker_count': peak(samples, 'worker_count'),
              'full_overlap_mean_workers_cpu_percent': average(overlap, 'workers_cpu_percent'),
              'full_overlap_peak_workers_cpu_percent': peak(overlap, 'workers_cpu_percent'),
              'full_overlap_peak_workers_rss_bytes': peak(overlap, 'workers_rss_bytes'),
              'full_overlap_peak_workers_uss_bytes': peak(overlap, 'workers_uss_bytes'),
              'backend_peak_rss_bytes': peak(samples, 'backend_rss_bytes'),
              'system_min_available_bytes': min((row['system_available_bytes'] for row in samples), default=None),
              'system_swap_used_last_bytes': samples[-1]['system_swap_used_bytes'] if samples else None,
              'system_swap_used_peak_bytes': peak(samples, 'system_swap_used_bytes'),
              'system_swap_in_last_bytes': samples[-1]['system_swap_in_bytes'] if samples else None,
              'system_swap_out_last_bytes': samples[-1]['system_swap_out_bytes'] if samples else None,
              'observed_workers_cpu_time_seconds': sum(cpu_time_by_pid.values()),
              'calls': calls, 'resource_samples': samples}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'ids': args.ids, 'calls': [
        {'id': call_result['id'], 'status': call_result['status'],
         'first_text_ms': call_result['first_text_ms'],
         'final_latency_ms': call_result['final_latency_ms']}
        for call_result in calls],
        'full_overlap_mean_workers_cpu_percent': report['full_overlap_mean_workers_cpu_percent'],
        'full_overlap_peak_workers_rss_bytes': report['full_overlap_peak_workers_rss_bytes']},
        ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('--ids', nargs='+', required=True)
    parser.add_argument('--backend-pid', type=int, required=True)
    parser.add_argument('--url', default='ws://127.0.0.1:8000/ws/transcribe')
    parser.add_argument('--chunk-ms', type=int, default=500, choices=[250, 500, 1000])
    parser.add_argument('--sample-seconds', type=float, default=0.5)
    parser.add_argument('--output', required=True)
    arguments = parser.parse_args()
    if arguments.sample_seconds <= 0:
        parser.error('--sample-seconds must be positive')
    asyncio.run(run(arguments))
