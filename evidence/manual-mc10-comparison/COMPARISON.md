# Mandarin Mc1–Mc10: manual and automated comparison

Run date: 14 November 2026 (Asia/Kolkata). Ten renamed 16 kHz mono PCM16 WAVs were verified against the original FLEURS source manifest by SHA-256. The automated run used FastAPI WebSocket, Qwen3-ASR-0.6B CPU worker, Auto detect, 500 ms real-time-paced chunks, and one session at a time. No concurrency test was run. All ten sessions completed. Mc7 was repeated once because its original run was an extreme outlier.

## Per-clip latency and CPU

First text is measured from the first PCM audio received by FastAPI. Final latency is measured from end-of-audio received by FastAPI to completion. Manual CPU values are one Activity Monitor snapshot per clip. Automated worker CPU was sampled about every 0.2 s.

| Clip | Length (s) | Manual first (s) | Auto first (s) | Manual final (s) | Auto final (s) | Manual CPU snapshot | Auto mean worker CPU | Auto sampled peak CPU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Mc1 | 6.96 | 5.79 | 5.94 | 3.29 | 3.06 | 154.70% | 82.8% | 294.2% |
| Mc2 | 10.38 | 5.61 | 3.73 | 1.20 | 1.85 | 48.30% | 76.9% | 271.8% |
| Mc3 | 8.28 | 5.10 | 4.39 | 1.69 | 1.80 | 94.06% | 82.7% | 284.6% |
| Mc4 | 13.86 | 5.44 | 5.83 | 0.97 | 1.24 | 90.20% | 89.6% | 295.8% |
| Mc5 | 15.42 | 4.96 | 4.21 | 1.81 | 2.65 | 90.90% | 97.3% | 308.4% |
| Mc6 | 12.90 | 6.42 | 5.61 | 1.23 | 2.94 | 88.98% | 81.2% | 279.8% |
| Mc7 | 13.74 | 7.61 | 18.44 | 1.93 | 115.58 | 78.00% | 55.0% | 205.8% |
| Mc8 | 15.18 | 6.43 | 9.75 | 2.53 | 3.14 | 87.00% | 97.6% | 276.9% |
| Mc9 | 15.46 | 6.58 | 5.67 | 1.30 | 1.61 | 125.60% | 92.4% | 305.7% |
| Mc10 | 7.62 | 4.87 | 5.05 | 1.71 | 1.95 | 192.87% | 89.1% | 292.9% |
| **Mean of original 10** | — | **5.88** | **6.86** | **1.77** | **13.58** | **105.1%** | **84.5%** | **281.6%** |

## Mc7 outlier and repeat

- Original Mc7: first text 18.44 s; final delay 115.58 s; observed worker CPU Time 64.03 CPU-s. The stream completed without an error, but text did not appear before the audio ended. The worker kept producing partial hypotheses for almost two minutes.
- Repeat Mc7: first text 6.35 s; final delay 1.30 s; observed worker CPU Time 11.62 CPU-s. It produced text before the audio ended.
- Second repeat Mc7 (requested separately): first text 8.14 s; final delay 2.88 s; observed worker CPU Time 13.89 CPU-s. It produced text before the audio ended. This repeat also did not reproduce the original 115.58 s final delay.
- Median of the original ten: first text 5.64 s; final delay 2.30 s. If the repeat is used *only as a sensitivity calculation* in place of the first Mc7 run, ten-clip means become 5.65 s and 2.15 s. The original result is retained in the raw data.

The cause of the original Mc7 delay is not established. Recorded events show repeated slow model hypotheses; the repeat of the same bytes did not reproduce the delay. It should be treated as an observed tail-latency risk, not silently removed or assumed to be a language effect.

Mean manual first text was 5.88 s and manual final delay was 1.77 s. The original automated means are dominated by Mc7 and are not representative of the other nine. The mean of ten manual single-moment CPU observations (105.1%) is not directly comparable to the automated mean of per-clip worker means (84.5%). CPU peaks are sampled maxima, not guaranteed instantaneous maxima.

The automated client did not play audio or render the React page, but both reported latency fields are the same server-side metrics shown by the UI. The mean per-clip character error rate against the reference is 10.4% for the original ten; this is an unweighted average for these clips, not a language-wide estimate.

Files: `manifest.json` records source mapping; `runs/summary.csv` and `runs/mcN-500-1.json` contain the original run; `mc7-repeat/` and `mc7-repeat-2/` contain the two targeted repeats and their resource samples.
