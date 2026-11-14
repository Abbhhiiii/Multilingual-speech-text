# Mandarin Mc1–Mc10: manual and automated comparison

**Selected result:** the latest Mc7 repeat (`mc7-repeat-2/`) is used in the main table and ten-clip averages, as requested. The original Mc7 run and first repeat remain recorded below and in the raw files.

Run date: 14 November 2026 (Asia/Kolkata). Ten renamed 16 kHz mono PCM16 WAVs were verified against the original FLEURS manifest by SHA-256. The automated tests used FastAPI WebSocket, Qwen3-ASR-0.6B CPU worker, Auto detect, 500 ms real-time-paced chunks, and one session at a time. No concurrency test was run. All sessions completed.

## Selected per-clip latency and CPU

First text is measured from the first PCM audio received by FastAPI. Final latency is measured from end-of-audio received by FastAPI to completion. Manual CPU values are one Activity Monitor snapshot per clip. Automated worker CPU was sampled about every 0.2 s.

| Clip | Length (s) | Manual first (s) | Auto first (s) | Manual final (s) | Auto final (s) | Manual CPU snapshot | Auto mean worker CPU | Auto sampled peak CPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mc1 | 6.96 | 5.79 | 5.94 | 3.29 | 3.06 | 154.70% | 82.8% | 294.2% |
| Mc2 | 10.38 | 5.61 | 3.73 | 1.20 | 1.85 | 48.30% | 76.9% | 271.8% |
| Mc3 | 8.28 | 5.10 | 4.39 | 1.69 | 1.80 | 94.06% | 82.7% | 284.6% |
| Mc4 | 13.86 | 5.44 | 5.83 | 0.97 | 1.24 | 90.20% | 89.6% | 295.8% |
| Mc5 | 15.42 | 4.96 | 4.21 | 1.81 | 2.65 | 90.90% | 97.3% | 308.4% |
| Mc6 | 12.90 | 6.42 | 5.61 | 1.23 | 2.94 | 88.98% | 81.2% | 279.8% |
| Mc7 (latest repeat) | 13.74 | 7.61 | 8.14 | 1.93 | 2.88 | 78.00% | 83.4% | 289.0% |
| Mc8 | 15.18 | 6.43 | 9.75 | 2.53 | 3.14 | 87.00% | 97.6% | 276.9% |
| Mc9 | 15.46 | 6.58 | 5.67 | 1.30 | 1.61 | 125.60% | 92.4% | 305.7% |
| Mc10 | 7.62 | 4.87 | 5.05 | 1.71 | 1.95 | 192.87% | 89.1% | 292.9% |
| **Mean of selected 10** | — | **5.88** | **5.83** | **1.77** | **2.31** | **105.1%** | **87.3%** | **289.9%** |

The selected automated mean first-text delay is 0.05 s lower than the manual mean; selected final delay is 0.55 s higher than the manual mean. These are one-pass observations for nine clips and the latest run for Mc7, so they do not isolate a frontend effect. All ten selected runs produced text before audio transmission ended.

## Mc7 run history

| Run | First text (s) | Final delay (s) | Observed worker CPU Time (s) |
|---|---:|---:|---:|
| Original | 18.44 | 115.58 | 64.03 |
| First repeat | 6.35 | 1.30 | 11.62 |
| Latest repeat, selected | 8.14 | 2.88 | 13.89 |

The original Mc7 run completed, but text did not appear before audio ended and the worker produced slow partial hypotheses for almost two minutes. Its cause is not established. The latest repeat is the selected comparison value, but the original remains an observed tail-latency risk. If the original run were included instead, the original ten-clip mean would be 6.86 s to first text and 13.58 s final delay.

The manual CPU average is an average of ten single-moment observations, not a per-clip time average; it is not directly comparable to the selected automated mean of per-clip worker means. Sampled CPU peaks are not guaranteed instantaneous maxima. The automated client did not play audio or render the React page, but both latency fields are the same server-side metrics shown by the UI.

Files: `selected-summary.csv` is the selected ten-clip comparison data; `manifest.json` maps filenames to sources; `runs/` retains the original ten raw runs; `mc7-repeat/` and `mc7-repeat-2/` retain both repeats and their resource samples.
