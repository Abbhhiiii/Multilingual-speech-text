# First sizing measurement: two simultaneous English calls

Run date: 15 November 2026 (Asia/Kolkata). En1 and En2 were started together through separate WebSocket sessions and native Qwen3-ASR-0.6B CPU workers on the Apple M2 MacBook Air (8 CPU cores, 8 GB RAM). Both used Auto detect and 500 ms real-time-paced PCM16 chunks. The automated client did not play browser audio. This is **one measured two-call run**, not a 50-call projection or a production capacity claim.

## Call results

| Clip | Audio length | First text from first audio | First text before audio end? | Final delay after audio end | Result | Reference word error rate |
|---|---:|---:|---|---:|---|---:|
| En1 | 10.56 s | 9.29 s | Yes, about 0.71 s before | 12.36 s | Complete | 5.3% |
| En2 | 9.90 s | 9.69 s | No, about 0.35 s after | 12.59 s | Complete | 0.0% |

Both audio streams were paced at their real durations. Total batch wall time was 23.15 s. En2 completed accurately, but its first visible text arrived after its audio ended, so that call did not demonstrate incremental text on this run. The transcripts and events are preserved in the raw JSON.

## CPU and memory during both workers' overlap

| Measurement | Observed value |
|---|---:|
| Combined worker CPU, mean of overlap samples | 125.8% (about 1.26 cores' worth) |
| Combined worker CPU, highest sampled reading | 500.3% (about 5.00 cores' worth) |
| Observed total worker CPU Time | 28.63 CPU-s |
| Combined worker peak RSS, simultaneous sample | 3.86 GiB |
| Combined worker peak USS, simultaneous sample | 2.21 GiB |
| FastAPI peak RSS | 16.8 MiB |
| Whole-Mac available memory, lowest sample | 0.81 GiB |
| Whole-Mac Swap Used before run | 3.49 GiB |
| Whole-Mac Swap Used, highest sample | 5.69 GiB |

RSS includes pages that can be shared; USS estimates the workers' private resident memory. These are **simultaneous aggregate samples**, rather than sums of independent process peaks. Backend memory is separate. Whole-Mac available memory and swap include Safari, macOS and other applications and cannot be attributed solely to ASR. The Mac already had substantial swap in use before the run. The Activity Monitor Memory Pressure graph was not recorded.

The monitor requested a 0.5 s sample interval; its actual median gap was 0.56 s under load. Shorter CPU or memory peaks may have been missed. The workers' average CPU stayed far below the sampled peak, while first-text and final delays were much longer than a single-call baseline. This one run does not establish whether CPU scheduling, memory pressure, model behavior or background work was the main cause. It is a measured input for sizing; a target server still needs its own concurrency test.

Raw samples and per-call events: `two-english-2026-11-15.json`.
