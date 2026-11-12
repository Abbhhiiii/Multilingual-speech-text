# Tetherfi sequential multilingual ASR benchmark

Run date: 12 November 2026 (Asia/Kolkata). Project: `/Users/abhinavshetty/Documents/Codex/2026-11-11/referenced-chatgpt-conversation-this-is-an/outputs/tetherfi`.

## Result at a glance

All **60 of 60** real-time-paced sessions completed: 20 English, then 20 Mandarin, then 20 Indonesian. There were no failed benchmark sessions and no simultaneous inference streams. The results show usable recognition on this clean read-speech set, but inconsistent live responsiveness: median first text arrived 4.0–5.2 seconds after the backend received audio, and a Mandarin outlier took 28.7 seconds. Finalization after the last audio chunk ranged from under a second to 28.2 seconds. This baseline does **not** establish a two-second live-text guarantee.

Before this recorded run, one preliminary smoke attempt on the first English clip returned a stream timeout with no text; its immediate repeat completed. That attempt is **outside** the 60-clip dataset and its cause was not established. It remains a reliability warning despite the 60/60 completed recorded run.

| Language | Clips | Audio total | Corpus accuracy measure | First text after first audio, median / p90 / max | Final result after end, median / p90 / max | Text before audio ended |
|---|---:|---:|---:|---:|---:|---:|
| English | 20/20 | 187.60 s | 5.15% WER | 5.21 / 6.70 / 11.30 s | 4.76 / 8.25 / 23.45 s | 14/20 |
| Mandarin | 20/20 | 204.56 s | 8.88% CER | 4.24 / 7.15 / 28.74 s | 1.46 / 16.41 / 28.24 s | 17/20 |
| Indonesian | 20/20 | 214.26 s | 8.58% WER | 4.01 / 5.49 / 7.39 s | 1.36 / 5.17 / 7.87 s | 20/20 |

WER is word error rate; CER is character error rate. Lower is better. Corpus rates pool all reference words or characters within each language; per-clip scores are in `summary.csv`.

## Setup and method

- Hardware verified with `system_profiler`: **Apple M2, 8 cores (4 performance + 4 efficiency), 8 GB RAM**. The native worker linked to Apple's Accelerate framework and not Metal or CoreML (`otool -L`). This supports that these runs used the CPU path; it is not a power or GPU utilization measurement.
- App version: project Git commit `a8c0ed6` plus local benchmark script changes; native `antirez/qwen-asr` checkout `924694251d9e0f18e5d86bbd06aa3ab5f870002d`; Qwen3-ASR-0.6B local weights. Python 3.14.6. Backend: FastAPI WebSocket; one new native worker per clip; four worker threads; English, Chinese, or Indonesian language explicitly selected. Revisable hypothesis mode: two-second inference step and two held context windows.
- Audio: [Google FLEURS](https://huggingface.co/datasets/google/fleurs) **test** split, dataset revision `70bb2e84b976b7e960aa89f1c648e09c59f894dd`, CC BY 4.0. The selection is deterministic archive order, 4–16 seconds: 10 labeled male and 10 labeled female English; the same for Mandarin; first 20 Indonesian records because the source test metadata for this configuration was all labeled male. Source references and SHA-256 hashes are saved in `benchmark_audio/manifest-60.json`. All 60 converted WAV hashes and result IDs were checked after the run.
- Each file was converted to **16 kHz mono PCM16** and sent through the same WebSocket as the application in **500 ms chunks paced by wall clock**. Trials ran sequentially, in the manifest's language order. The browser UI and speaker playback were not part of this measurement.
- CPU and memory were sampled approximately every 200 ms using `psutil`. First text is measured on the backend from its first received PCM chunk to its first nonempty text output. Final delay is from receipt of `end` to `done`. The client-visible metric starts when its WebSocket session opens, so it includes the approximately 500 ms before the first chunk is sent.
- Accuracy normalization applies Unicode NFKC, case folding, punctuation removal and whitespace collapsing. Chinese CER also removes spaces. It does **not** normalize written numbers into spoken words, transliterate names, or resolve alternative word order.

## Responsiveness and transcript behavior

| Language | First text seen by WebSocket client, median / p90 / max | Session start to `done`, median / p90 / max | Final delay >5 s | Final delay >10 s | Non-prefix transcript revisions |
|---|---:|---:|---:|---:|---:|
| English | 5.74 / 7.23 / 11.83 s | 12.43 / 19.98 / 34.96 s | 10/20 | 2/20 | 66 across 20 clips |
| Mandarin | 4.79 / 7.70 / 29.32 s | 14.59 / 25.43 / 35.83 s | 5/20 | 4/20 | 67 across 20 clips |
| Indonesian | 4.55 / 6.03 / 7.94 s | 13.30 / 16.98 / 23.87 s | 3/20 | 0/20 | 62 across 20 clips |

For 6 English and 3 Mandarin clips, the first visible transcript arrived after audio ended. All Indonesian clips showed text before their audio ended. A non-prefix revision means a later full-text snapshot did not start with the previous snapshot verbatim; this includes punctuation and formatting changes as well as word corrections. It is **not** a count of semantic mistakes. Revisions occurred in 20/20 English, 20/20 Mandarin, and 19/20 Indonesian clips.

The most delayed first text was Mandarin clip `zh-10279011772105822622`: 7.56 seconds of audio, first text at 28.74 seconds after first PCM, and final result 28.24 seconds after `end`. The slowest English finalization was `en-10167324587744183095`: 23.45 seconds after `end` for an 11.46-second clip. These are real completed trials, not discarded failures. The Mandarin outlier had elevated whole-machine CPU activity; that observation does not establish its cause.

### Follow-up on the two worst outliers

Each outlier was repeated once, sequentially, with the same audio and settings. The repeats are **not included** in the 60-clip aggregate.

| Clip | First text, original → repeat | Final delay, original → repeat | Whole-machine CPU mean, original → repeat |
|---|---:|---:|---:|
| English `en-10167324587744183095` | 6.46 → 6.54 s | 23.45 → 5.10 s | 47.6% → 37.9% |
| Mandarin `zh-10279011772105822622` | 28.74 → 6.20 s | 28.24 → 3.57 s | 44.8% → 38.2% |

In the original English run, a transcript arrived at 10.94 seconds after connection, then the next one did not arrive until 30.75 seconds. In the original Mandarin run, the 7.56-second clip had finished sending before any text arrived at 29.32 seconds. At those points the backend reported zero bytes in its application queue and all audio forwarded to native stdin; the native worker remained active. This locates the wait beyond the WebSocket input queue, within or around native processing. The original outliers also had higher whole-machine CPU use and lower average worker CPU than their repeats. Transient competition for CPU, memory pressure or file-cache behavior are plausible, but per-window inference time, page faults, thermal state and other processes were not recorded well enough to distinguish them. The two repeats show the severe delays were **not reproducible on demand from clip content alone**. Raw repeat events and resource samples are in `../outlier-repeats/`.

## CPU and memory

| Language | Worker CPU mean across a clip, median / p90 | Worker peak CPU, median / max | Worker peak RSS, median / max | Worker peak unique memory, median / max | Whole-machine CPU mean, median |
|---|---:|---:|---:|---:|---:|
| English | 74% / 84% | 311% / 351% | 1.92 / 2.08 GiB | 1.10 / 1.13 GiB | 33% |
| Mandarin | 69% / 80% | 311% / 360% | 2.11 / 2.35 GiB | 1.11 / 1.13 GiB | 25% |
| Indonesian | 78% / 90% | 334% / 363% | 2.10 / 2.35 GiB | 1.11 / 1.14 GiB | 26% |

Worker CPU percentages use the usual process convention: **100% is one fully used logical CPU**, so peaks near 350% represent roughly 3.5 logical CPUs during sampled bursts. The mean includes quieter periods while audio is paced or the worker waits. Backend Python CPU was small (median per-clip mean about 0.24%); the native worker dominated application compute. RSS includes shared mapped pages; unique memory is the worker's USS estimate. The smallest sampled whole-machine “available” memory was approximately **1.19 GiB**. This is an OS estimate, not a macOS memory-pressure reading. The machine was not isolated from Activity Monitor, browser, WindowServer, and other desktop activity.

## Accuracy observations

| Language | Corpus error | Median clip error | Worst clip error | Exact normalized clips |
|---|---:|---:|---:|---:|
| English | 5.15% WER | 5.66% WER | 20.0% WER | 6/20 |
| Mandarin | 8.88% CER | 4.95% CER | 32.43% CER | 9/20 |
| Indonesian | 8.58% WER | 7.49% WER | 23.53% WER | 7/20 |

Examples show why these scores need interpretation. English clip `en-10550734868852131138` had the worst per-clip WER, but much of the difference is “15 August 1940” versus “August 15, 1940,” plus an added conjunction. Mandarin clip `zh-10048525650290665384` had the worst CER largely because the reference uses `15`, `2011`, and `2017` while the output writes those numbers in Chinese characters. Indonesian clip `id-10108741791199111381` misrecognized the spoken organization name or acronym at the end. These examples do not erase the lexical errors elsewhere; they show that raw WER/CER mixes meaning changes with formatting conventions.

## What the results suggest

1. **The present UI can show provisional text, but cannot promise it at the two-second mark.** A two-second inference step is not a two-second end-to-end latency target. Model startup, compute, held context, and revisable output all add delay. The short clips that showed no text until after playback ended make this especially visible.
2. **Finalization is a material part of perceived delay.** Median post-end delay was 4.76 seconds in English, 1.46 seconds in Mandarin, and 1.36 seconds in Indonesian, with much larger worst cases. The user can finish hearing audio while the native decoder is still working.
3. **The native worker, rather than FastAPI, is the main compute and memory cost.** Worker CPU briefly occupied several logical cores and RSS reached 2.35 GiB on an 8 GB machine. A new worker per clip also reloads model state. The measurements do not isolate loading time from first-window inference.
4. **Language quality should be judged with examples as well as error rates.** Numeral formatting and names materially affect the reported scores. The Indonesian selection cannot support conclusions across speaker genders.

The next optimization experiment should change **one variable at a time**: held-context windows or inference step first, then compare the same 60 clips for first-text delay, post-end delay, transcript revisions, and WER/CER. A shorter context may show text sooner but increase corrections or errors. Reusing a warm worker might reduce startup cost, but requires explicit session-state reset validation before it can be trusted. These are proposed experiments, **not measured improvements**.

## Scope and files

This run covers clean, read FLEURS speech of 4–16 seconds, the three explicitly selected languages, 500 ms chunks, one stream at a time, and the backend WebSocket path. It does **not** measure browser audio scheduling or audible playback synchronization, microphone noise, overlapping speakers, code switching, long continuous recordings, other chunk sizes, thermal throttling, battery drain, or concurrency. No causal attribution is claimed for latency outliers.

- `summary.csv`: all 60 per-clip metrics, references, final predictions, and status.
- `aggregate.json`: reproducible language-level counts and distributions.
- `<clip-id>-500-1.json`: timestamped transcript events and approximately 200 ms CPU/memory samples for each clip.
- `../../benchmark_audio/manifest-60.json` and `../../benchmark_audio/source.json`: clip provenance, source revision, and conversion details.
- On a fresh clone, first download and convert the pinned source clips with `.venv/bin/python scripts/prepare_fleurs.py en zh id` (this downloads three source archives). Then re-run the baseline from the project root with `.venv/bin/python scripts/benchmark.py benchmark_audio/manifest-60.json --chunks 500 --backend-pid <running-backend-pid> --output evidence/new-run`, and summarize it with `.venv/bin/python scripts/summarize_benchmark.py evidence/new-run/summary.csv --output evidence/new-run/aggregate.json`.
