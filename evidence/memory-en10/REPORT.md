# English En1–En10 memory benchmark

Run date: 14 November 2026 (Asia/Kolkata). A fresh sequential run of the ten verified renamed English WAV clips used Auto detect, 500 ms real-time-paced audio, FastAPI WebSocket and Qwen3-ASR-0.6B on the Apple M2 CPU. All 10 completed. The benchmark sampled operating-system process memory and whole-Mac memory about every 0.2 seconds while each clip streamed. No concurrency test was run.

## Per-clip measurements

RSS is resident memory mapped into a process; USS estimates memory private to the worker. The peak values below are the highest **sampled** values, not guaranteed instantaneous maxima. Backend and worker are measured separately. Available memory and swap belong to the whole Mac.

| Clip | Worker peak RSS (GiB) | Worker peak USS (GiB) | Backend peak RSS (MiB) | Lowest Mac available (GiB) | Mac Swap Used start → end (GiB) |
|---|---:|---:|---:|---:|---:|
| En1 | 2.00 | 1.12 | 20.4 | 1.24 | 2.66 → 3.23 |
| En2 | 1.94 | 1.13 | 21.5 | 1.28 | 3.23 → 3.21 |
| En3 | 2.16 | 1.09 | 21.3 | 1.24 | 3.21 → 3.38 |
| En4 | 1.96 | 1.09 | 21.5 | 1.27 | 3.38 → 3.36 |
| En5 | 2.19 | 1.14 | 21.5 | 1.25 | 3.36 → 3.42 |
| En6 | 2.03 | 1.11 | 22.4 | 1.27 | 3.42 → 3.41 |
| En7 | 2.03 | 1.11 | 21.5 | 1.39 | 3.41 → 3.41 |
| En8 | 1.93 | 1.09 | 22.1 | 1.25 | 3.41 → 3.45 |
| En9 | 2.04 | 1.09 | 21.4 | 1.29 | 3.45 → 3.45 |
| En10 | 2.04 | 1.27 | 21.5 | 1.27 | 3.45 → 3.45 |

**Across ten clips:** mean worker peak RSS **2.03 GiB**; highest worker peak RSS **2.19 GiB** (En5). Mean worker peak USS **1.12 GiB**; highest **1.27 GiB** (En10). Mean backend peak RSS **21.5 MiB**; highest **22.4 MiB**. The lowest sampled whole-Mac available memory was **1.24 GiB**.

Whole-Mac Swap Used was **2.66 GiB** before the first clip and **3.45 GiB** at the last sample of the final clip. It rose by about **808 MiB** across the batch. The largest per-clip increase was **585 MiB** on En1; some clips showed no increase or a decrease. These are system-wide figures and cannot be attributed solely to ASR, Safari, or the backend.

## Interpretation

- The worker is the main visible process-memory cost. Its RSS includes shared mappings, while USS estimates private memory; adding separate RSS peaks together would overstate unique physical RAM. `combined_peak_rss_bytes` in the CSV is a simultaneous worker-plus-backend RSS sum, useful as an approximate process footprint but still includes shared pages.
- FastAPI stayed near 20–22 MiB RSS in these runs. Browser/Safari process memory was not isolated by this sampler. The whole-Mac available-memory and swap figures include it along with every other app.
- Swap Used was already nonzero before the benchmark. Increasing Swap Used can indicate memory pressure, but without per-process swap attribution or a contemporaneous Activity Monitor Memory Pressure trace, this run does not establish whether swapping caused any latency change.
- Memory sampling can miss a spike shorter than about 0.2 seconds. All numbers describe this Mac and this run, with one ASR session at a time.

Files: `runs/summary.csv` has per-clip summaries; `runs/enN-500-1.json` contains timestamped resource samples and transcript events.
