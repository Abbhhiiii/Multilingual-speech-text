# English En1–En10: manual and automated comparison

Run date: 13 November 2026 (Asia/Kolkata). The automated test used the exact renamed WAV files `benchmark_audio/en/en1.wav` through `en10.wav`; their SHA-256 hashes match the earlier FLEURS test clips identified in `manifest.json`. All files are 16 kHz mono PCM16. The WebSocket request used **Auto detect**, 500 ms real-time-paced chunks, one session at a time, one pass per clip, Qwen3-ASR-0.6B on the Apple M2 CPU, four worker threads, a two-second native inference step, and revisable transcript snapshots. All **10/10** automated sessions completed. No concurrent calls were run.

## Latency, seconds

Both manual UI values and automated values use the same FastAPI timestamps: first text is measured from first PCM received; final latency is measured from `end` received to `done`. The automated client does not play audio or render the React page.

| Clip | Audio length | Manual first text | Automated first text | Manual final | Automated final |
|---|---:|---:|---:|---:|---:|
| En1 | 10.56 | 3.33 | 4.68 | 0.99 | 0.99 |
| En2 | 9.90 | 4.76 | 3.00 | 0.50 | 0.54 |
| En3 | 4.80 | 5.18 | 3.02 | 2.48 | 1.25 |
| En4 | 5.72 | 2.69 | 2.93 | 0.66 | 0.67 |
| En5 | 15.56 | 4.38 | 2.83 | 0.80 | 0.81 |
| En6 | 8.76 | 3.57 | 2.92 | 1.00 | 1.09 |
| En7 | 11.46 | 4.49 | 3.98 | 0.61 | 0.64 |
| En8 | 5.76 | 2.97 | 3.56 | 0.68 | 0.69 |
| En9 | 4.32 | 3.47 | 3.21 | 1.76 | 1.34 |
| En10 | 11.42 | 3.36 | 2.91 | 0.58 | 0.56 |
| **Mean of 10** | — | **3.82** | **3.30** | **1.01** | **0.86** |

The automated pass averaged **0.52 s less first-text delay** and **0.15 s less final delay** than the ten manual notes. Individual clips varied in both directions: automated En1 was 1.35 s slower to first text, while En3 was 2.16 s faster. One manual and one automated run per clip cannot establish that automation caused the mean difference. Machine load, model loading/cache state, and other run-to-run effects were not controlled closely enough for causal attribution.

## CPU use

The manual values supplied by the tester are **one Activity Monitor reading per clip**. The automated client sampled the native worker approximately every 0.2 s. Its per-clip mean is the mean of worker CPU-percent samples while the worker existed; its peak is the highest sampled reading, not a guaranteed instantaneous maximum. On macOS, 100% process CPU is about one logical core's worth of activity. `CPU Time` is the last observed cumulative user-plus-system CPU seconds for the worker and may miss the final fraction of a second before exit.

| Clip | Manual one-shot CPU % | Automated worker mean % | Automated sampled peak % | Observed worker CPU Time, s |
|---|---:|---:|---:|---:|
| En1 | 50.6 | 71.0 | 320.1 | 8.22 |
| En2 | 81.2 | 78.2 | 346.0 | 8.08 |
| En3 | 56.9 | 93.6 | 350.9 | 5.80 |
| En4 | 58.3 | 59.5 | 345.3 | 3.83 |
| En5 | 79.0 | 70.0 | 355.4 | 11.21 |
| En6 | 92.2 | 74.4 | 357.1 | 7.30 |
| En7 | 99.7 | 83.9 | 367.6 | 10.21 |
| En8 | 51.35 | 77.3 | 345.0 | 5.15 |
| En9 | 115.6 | 78.0 | 346.3 | 4.44 |
| En10 | 35.7 | 65.0 | 319.3 | 7.64 |
| **Mean of 10** | **72.1** | **75.1** | **345.3** | **7.19** |

**75.1%** is the mean of ten per-clip worker means and is the suitable language-level summary for this set. **72.1%** is only the mean of ten manual single-moment observations; their numerical closeness does not validate the one-shot method. Sampled peaks reached **367.6%**, showing short multi-core bursts that Activity Monitor's sparse manual readings did not capture. The ten workers accumulated approximately **71.88 observed CPU-seconds** in total; this is CPU work, not wall-clock latency. Backend CPU and memory, worker memory, transcript events and every resource sample remain in the individual run JSON files and `runs/summary.csv`.

## Interpretation and limits

- This is a **sequential** CPU benchmark, matching the user's request to leave concurrency for later. The backend's admission limit was one session.
- The automated WebSocket client exercised FastAPI and the same native worker, but did not exercise browser playback, rendering or human-visible delay. The app's displayed first/final metrics are server-side, so those two fields are directly comparable with the manual notes.
- All ten automated clips produced text before audio transmission ended, according to the recorded WebSocket events.
- Because each clip was run only once in each set, the comparison describes these specific runs. Repeated passes would be needed to estimate run-to-run variance more reliably.
- CPU Time and peak CPU are approximate sampled values. Peaks from separate clips must not be added to estimate concurrent demand; concurrent aggregate CPU must be sampled at common timestamps when that test is run.

Files: `manifest.json` preserves the renamed-file mapping and reference text; `runs/summary.csv` contains per-clip results; `runs/<clip>-500-1.json` contains timestamped transcript events and approximately 0.2-second resource samples.
