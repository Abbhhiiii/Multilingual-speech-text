# Indonesian Id1–Id10: manual and automated comparison

Run date: 14 November 2026 (Asia/Kolkata). Ten renamed 16 kHz mono PCM16 WAVs were verified against the original FLEURS manifest by SHA-256. The automated run used the FastAPI WebSocket, Qwen3-ASR-0.6B CPU worker, Auto detect, 500 ms real-time-paced chunks, and one session at a time. No concurrency test was run. All ten sessions completed.

## Latency and CPU

First text is measured from the first PCM audio received by FastAPI. Final latency is measured from end-of-audio received by FastAPI to completion. Manual CPU values are one Activity Monitor snapshot per clip. Automated worker CPU was sampled approximately every 0.2 s.

| Clip | Length (s) | Manual first (s) | Auto first (s) | Manual final (s) | Auto final (s) | Manual CPU snapshot | Auto mean worker CPU | Auto sampled peak CPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Id1 | 7.32 | 4.40 | 5.99 | 1.54 | 3.40 | 92.50% | 90.3% | 295.1% |
| Id2 | 5.22 | 5.33 | 3.45 | 2.74 | 1.63 | 88.90% | 76.8% | 296.3% |
| Id3 | 8.58 | 5.45 | 4.19 | 2.26 | 1.97 | 141.00% | 85.3% | 295.2% |
| Id4 | 7.68 | 5.56 | 5.04 | 1.99 | 1.54 | 56.80% | 82.7% | 261.5% |
| Id5 | 9.48 | 5.49 | 4.04 | 1.08 | 1.03 | 59.20% | 89.2% | 277.2% |
| Id6 | 9.48 | 5.48 | 3.57 | 1.09 | 0.69 | 120.10% | 73.4% | 325.8% |
| Id7 | 12.30 | 5.24 | 3.67 | 1.89 | 1.81 | 131.04% | 91.8% | 308.3% |
| Id8 | 13.92 | 5.62 | 3.11 | 1.12 | 0.93 | 121.00% | 73.6% | 306.6% |
| Id9 | 7.98 | 6.05 | 3.81 | 2.60 | 1.20 | 48.67% | 86.2% | 285.7% |
| Id10 | 15.96 | 5.24 | 5.48 | 4.24 | 1.54 | 146.24% | 101.2% | 289.2% |
| **Mean of 10** | — | **5.39** | **4.23** | **2.06** | **1.57** | **100.5%** | **85.1%** | **294.1%** |

The automated pass averaged 1.15 s less first-text delay and 0.48 s less final delay than the manual notes. These are one-pass observations, not evidence that the automated client made the worker faster. Id1 automated first text was 1.59 s slower than the manual result; Id10 automated final delay was 2.70 s shorter. Run-to-run load and model/cache state were not controlled closely enough to explain those differences.

The mean of the ten manual one-shot CPU observations (100.5%) is not a per-clip time average and should not be treated as equivalent to the 85.1% mean of automated worker means. The highest sampled worker CPU reading was 325.8%, a brief multi-core burst. Peaks are sampled maxima, not guaranteed instantaneous maxima. The mean of observed worker CPU Time values was 9.80 CPU-seconds per clip; this is accumulated processor work, not latency. The benchmark also sampled backend CPU and memory separately in the raw JSON.

## Additional checks

All 10 runs produced text before audio finished and ended without error. The mean per-clip word error rate against the FLEURS reference was 9.9%; this is an unweighted average across these ten clips, not a language-wide accuracy estimate. The automated WebSocket client did not play audio or render the React page; the two reported latency fields are the same server-side metrics shown by the UI.

Files: `manifest.json` records renamed-file source mapping; `runs/summary.csv` contains the per-clip summary; `runs/<clip>-500-1.json` contains timestamped transcript events and resource samples.
