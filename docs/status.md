# Implementation status — 11 November 2026

The original five-page Tetherfi assignment and prior Architecture V2/four-day plan were inspected before implementation. Hardware verified locally: MacBook Air Mac14,2, Apple M2, 8 CPU cores (4 performance + 4 efficiency), 8 GB RAM.

## Executed on this machine

- Native `antirez/qwen-asr` pinned at `924694251d9e0f18e5d86bbd06aa3ab5f870002d` built with `make blas`. Link inspection showed Apple Accelerate, with no GPU backend.
- Official Qwen3-ASR-0.6B weights pinned at `5eb144179a02acc5e5ba31e748d22b0cf3e303b0` downloaded; SHA-256 matched `79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea`.
- **Direct native CPU streaming:** 15.000 s English PCM sent at 500 ms pacing. First nonblank stdout at 8.67 s, before stdin closed at 15.00 s. Process exited 0 at 16.50 s; sampled peak RSS 2,099,150,848 bytes. See `evidence/runtime-local.json`. One trial, not a benchmark or memory capacity estimate.
- **Real WebSocket end-to-end:** same 15.000 s recording paced through FastAPI to native CPU worker. First text at 6.84 s from first audio received; final event 1.01 s after `end`; total session 16.02 s. Transcript updates arrived before the stream ended. See `evidence/websocket-local.json`. These values describe this one local trial only.
- **Indonesian WebSocket CPU check:** 8.58 s FLEURS test WAV, incremental text before end, completed at 9.79 s session time. First text 6.74 s after first audio, final latency 1.21 s. Predicted: “Tim tim virtual memiliki standar keunggulan yang sama dengan tim konvensional, tetapi ada sedikit perbedaan.” Reference differs only in hyphen punctuation. See `evidence/indonesian-websocket.json`.
- **Mandarin WebSocket CPU check:** 10.38 s FLEURS test WAV, incremental text before end, completed at 11.22 s session time. First text 6.73 s after first audio, final latency 0.83 s. Predicted: “这并不是告别，这是一个篇章的结束，也是新篇章的开始。” Reference uses different quote and sentence punctuation. See `evidence/mandarin-websocket.json`.
- Both language recordings were extracted from the official FLEURS test audio archives and converted from float WAV to 16 kHz mono PCM16 with macOS `afconvert`; exact source names/references are in `samples/*.json`. FLEURS is CC BY 4.0. These are individual smoke checks, not corpus accuracy results.
- Backend protocol/error suite: 20 passed using a separate fixture subprocess. Includes split UTF-8, isolation, failures, disconnect and timeout. Evidence in `evidence/backend-tests.txt`.
- Browser: selected the 15 s WAV in the React UI, streamed it through the real CPU worker, observed one completed transcript, 100% audio sent and first/final latency values.
- Frontend: TypeScript production build completed; seven WAV validation/pacing tests passed. Evidence in `evidence/frontend-build.txt` and `evidence/frontend-tests.txt`.

## Still needed for the four-day assignment

A personally recorded three-language demonstration, chunk-size selection, sustained CPU/RAM/concurrency measurements, alternative runtime comparison, sizing estimates, assignment submission report and the candidate's personally spoken video. The early English smoke test proves incremental behavior and integration; the later 60-clip FLEURS baseline below supplies the first corpus accuracy and latency measurements.

## 12 November 2026 — revisable transcript update

The native runtime patch in `runtime_patches/early-commit.patch` now emits full hypothesis snapshots. The backend replaces one transcript instead of appending token pieces; React already replaces the same display text. A revised Mandarin prefix was observed across native windows. The 15 s English, 8.58 s Indonesian and 10.38 s Mandarin samples completed through the WebSocket path with the previous final text. Backend tests: 21 passed, including snapshot replacement. See `docs/latency-experiment-2026-11-12.md` and `evidence/revisable-*-websocket.json`. A longer 45 s English run also completed without duplicated final text. All timing figures remain individual trials rather than benchmark estimates.

## 12 November 2026 — 60-clip sequential baseline

Twenty FLEURS test clips each for English, Mandarin and Indonesian completed one at a time through the real CPU WebSocket path at 500 ms network chunks. All 60 sessions completed. Corpus error rates were 5.15% English WER, 8.88% Mandarin CER and 8.58% Indonesian WER. Median first-text delays from first PCM received were 5.21, 4.24 and 4.01 seconds respectively; substantial post-end outliers remained. CPU, memory, per-clip transcripts, outliers, methodology and limitations are in [`evidence/fleurs-60-500ms/REPORT.md`](../evidence/fleurs-60-500ms/REPORT.md).
