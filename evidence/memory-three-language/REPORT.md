# Sequential memory benchmark: English, Mandarin, Bahasa Indonesia

Run date: 14 November 2026 (Asia/Kolkata). The same Apple M2 8 GB Mac and FastAPI/Qwen3-ASR-0.6B CPU setup were used for 30 sequential sessions: ten renamed clips per language, Auto detect, 500 ms real-time-paced chunks, one session at a time. All 30 sessions completed. Process memory, available memory, and whole-Mac swap were sampled about every 0.2 seconds. These are **separate fresh memory runs** from the earlier latency comparisons.

## Language summary

The mean columns average each clip’s sampled peak. GiB/MiB use powers of 1024.

| Language | Mean worker peak RSS | Highest worker RSS | Mean worker peak USS | Highest worker USS | Mean backend peak RSS | Lowest Mac available | Mac Swap Used before → after batch |
|---|---:|---:|---:|---:|---:|---:|---:|
| English | 2.03 GiB | 2.19 GiB | 1.12 GiB | 1.27 GiB | 21.5 MiB | 1.24 GiB | 2.66 → 3.45 GiB |
| Mandarin Chinese | 2.09 GiB | 2.29 GiB | 1.12 GiB | 1.15 GiB | 21.9 MiB | 1.24 GiB | 3.26 → 3.38 GiB |
| Bahasa Indonesia | 2.09 GiB | 2.35 GiB | 1.11 GiB | 1.15 GiB | 21.9 MiB | 1.29 GiB | 3.38 → 3.34 GiB |

Across these clips, the worker peak RSS means were close: English 2.03 GiB, Mandarin 2.09 GiB, Bahasa Indonesia 2.09 GiB. The worker USS means were 1.12, 1.12 and 1.11 GiB respectively. These small differences do not establish a language-specific memory cost; RSS also includes shared mappings and system conditions differed between runs. The largest sampled worker RSS was 2.35 GiB on Id8.

## Per-clip peaks

| Language | Clip | Worker peak RSS (GiB) | Worker peak USS (GiB) | Backend peak RSS (MiB) | Lowest Mac available (GiB) |
|---|---|---:|---:|---:|---:|
| English | en1 | 2.00 | 1.12 | 20.4 | 1.24 |
| English | en2 | 1.94 | 1.13 | 21.5 | 1.28 |
| English | en3 | 2.16 | 1.09 | 21.3 | 1.24 |
| English | en4 | 1.96 | 1.09 | 21.5 | 1.27 |
| English | en5 | 2.19 | 1.14 | 21.5 | 1.25 |
| English | en6 | 2.03 | 1.11 | 22.4 | 1.27 |
| English | en7 | 2.03 | 1.11 | 21.5 | 1.39 |
| English | en8 | 1.93 | 1.09 | 22.1 | 1.25 |
| English | en9 | 2.04 | 1.09 | 21.4 | 1.29 |
| English | en10 | 2.04 | 1.27 | 21.5 | 1.27 |
| Mandarin Chinese | mc1 | 1.95 | 1.12 | 21.7 | 1.30 |
| Mandarin Chinese | mc2 | 2.01 | 1.10 | 21.8 | 1.27 |
| Mandarin Chinese | mc3 | 1.95 | 1.09 | 21.3 | 1.24 |
| Mandarin Chinese | mc4 | 2.10 | 1.13 | 22.0 | 1.27 |
| Mandarin Chinese | mc5 | 2.15 | 1.15 | 22.2 | 1.34 |
| Mandarin Chinese | mc6 | 2.11 | 1.11 | 21.9 | 1.29 |
| Mandarin Chinese | mc7 | 2.29 | 1.12 | 22.1 | 1.38 |
| Mandarin Chinese | mc8 | 2.01 | 1.13 | 22.0 | 1.28 |
| Mandarin Chinese | mc9 | 2.08 | 1.14 | 22.2 | 1.29 |
| Mandarin Chinese | mc10 | 2.25 | 1.09 | 22.1 | 1.29 |
| Bahasa Indonesia | id1 | 2.07 | 1.10 | 22.0 | 1.32 |
| Bahasa Indonesia | id2 | 1.90 | 1.09 | 21.7 | 1.31 |
| Bahasa Indonesia | id3 | 1.94 | 1.10 | 21.5 | 1.31 |
| Bahasa Indonesia | id4 | 1.95 | 1.10 | 21.5 | 1.29 |
| Bahasa Indonesia | id5 | 1.94 | 1.11 | 21.6 | 1.34 |
| Bahasa Indonesia | id6 | 2.05 | 1.12 | 21.8 | 1.31 |
| Bahasa Indonesia | id7 | 2.22 | 1.14 | 22.1 | 1.31 |
| Bahasa Indonesia | id8 | 2.35 | 1.13 | 22.3 | 1.29 |
| Bahasa Indonesia | id9 | 2.26 | 1.12 | 22.2 | 1.29 |
| Bahasa Indonesia | id10 | 2.25 | 1.15 | 22.0 | 1.29 |

## How to read these values

- RSS is the memory mapped into a process and can count shared pages in more than one process. USS estimates private memory. FastAPI and worker peaks are reported separately; do not add independent peaks as exact RAM use. The CSV also contains a simultaneous approximate `combined_peak_rss_bytes` value.
- Swap Used and available memory are for the **whole Mac**, including Safari and other apps. They are context, not ASR memory. Safari process memory and Activity Monitor Memory Pressure were not isolated or recorded.
- The Mac already had swap in use before the English batch. Swap changed by +0.79 GiB during English, +0.12 GiB during Mandarin, and -0.03 GiB during Bahasa Indonesia; these changes cannot be attributed to the ASR worker alone. Swap occupancy is not the same as a measured swap I/O rate.
- Peaks are sampled values and may miss spikes shorter than the sampling interval. No concurrent sessions were tested.

Raw files: `../memory-en10/runs/`, `../memory-mc10/runs/`, `../memory-id10/runs/`. Each run JSON includes timestamped resource samples; each `summary.csv` contains per-clip peaks.
