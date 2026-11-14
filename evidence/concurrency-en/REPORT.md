# English concurrent CPU and memory: En1+En2, then En1+En2+En3

Run date: 14 November 2026 (Asia/Kolkata). These are two **sequential batches**, one with two simultaneous WebSocket calls and one with three. Every call used Auto detect and 500 ms real-time-paced PCM16 audio, through the FastAPI backend and native CPU worker with four native threads per call. The automated client did not play browser audio. The backend had no configured call-count limit.

## Call outcomes

| Batch | Clip | Audio length | First text | Final delay after audio end | Result |
|---|---|---:|---:|---:|---|
| 2 calls | en1 | 10.56 s | 13.03 s | 27.36 s | Complete |
| 2 calls | en2 | 9.90 s | 15.98 s | 26.87 s | Complete |
| 3 calls | en1 | 10.56 s | 12.42 s | 119.78 s | Complete |
| 3 calls | en2 | 9.90 s | — | — | ASR finalization exceeded the time limit. |
| 3 calls | en3 | 4.80 s | — | — | ASR finalization exceeded the time limit. |

The two-call batch completed both streams. In the three-call batch, En1 completed only 0.22 s before the 120 s finalization limit; En2 and En3 hit that limit. The worker processes were cleaned up afterward; the backend returned to zero active sessions. These outcomes are one run per batch under the Mac state at that time.

## Resource samples during full worker overlap

“Full overlap” means all workers in that batch existed simultaneously, including time spent finalizing after audio transmission ended. Process CPU on macOS can exceed 100% when multiple cores are used. Worker RSS/USS values are summed at the same sample time, so the table does not add separate process peaks.

| Measure | 2 calls | 3 calls |
|---|---:|---:|
| Peak workers simultaneously observed | 2 | 3 |
| Mean combined worker CPU during full overlap | 144.3% | 144.0% |
| Highest sampled combined worker CPU | 349.7% | 518.4% |
| Highest sampled combined worker RSS | 3.82 GiB | 3.38 GiB |
| Highest sampled combined worker USS | 2.21 GiB | 2.18 GiB |
| Highest sampled FastAPI RSS | 22.4 MiB | 24.6 MiB |
| Lowest whole-Mac available memory | 1.13 GiB | 1.16 GiB |
| Whole-Mac swap before batch | 3.21 GiB | 4.64 GiB |
| Highest whole-Mac swap during batch | 4.75 GiB | 6.01 GiB |
| Observed total worker CPU Time | 54.3 s | 185.6 s |
| Batch wall time | 38.0 s | 130.5 s |

## Interpretation and limits

- The combined workers averaged about 144% CPU in both batches despite the third worker. The whole-Mac CPU load averaged about 62% and 70% respectively during full overlap. This is consistent with substantial contention, but the data do not isolate CPU scheduling from memory stalls or unrelated system work.
- Whole-Mac swap was already in use before either batch. It rose from 3.21 GiB to a 4.75 GiB peak in the two-call run and from 4.64 GiB to a 6.01 GiB peak in the three-call run. These are system-wide observations and cannot be assigned solely to ASR. The lower three-worker peak *resident* memory than the two-worker value does not imply three calls needed less memory: macOS may reclaim, compress or swap pages.
- The monitor requested a 0.2 s interval. Actual median sample gaps were 0.27 s (two calls) and 0.34 s (three calls) because collecting process memory takes time under load. Samples may miss shorter peaks, and monitoring itself can perturb performance.
- These clips are not identical in duration, and this automated run began with different system memory/swap conditions from the user’s manual tests. Their latency values should not be interpreted as controlled differences caused by the measurement client.
- At the current four-threads-per-worker setting, the three-call run did not meet the 120 s finalization bound for two of three streams. Raising the timeout would change the failure threshold but not make transcription real time.

Raw data: `concurrent-en1-en2.json` and `concurrent-en1-en2-en3.json` include every timestamped resource sample and per-call WebSocket event.
