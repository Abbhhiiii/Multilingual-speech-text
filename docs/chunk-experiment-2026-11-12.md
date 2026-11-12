# One-recording chunk-size experiment — 12 November 2026

## Method

The same 15.0000625-second English WAV from the upstream runtime samples was streamed through the actual FastAPI WebSocket backend into the native CPU Qwen3-ASR-0.6B worker on the Apple M2 MacBook Air (8 GB). Language was forced to English. The test client paced PCM16 at real-time speed and sent `end` after the last sample. Runtime settings, model, backend and reference transcript remained unchanged. Each chunk size was run three times: first in order 250, 250, 500, 500, 1000, 1000 ms, then once in reverse order 1000, 500, 250 ms. The first 250 ms trial may include a colder file/model cache.

Raw events and timing are in `evidence/chunk-experiment-2026-11-12/` and `evidence/chunk-experiment-reverse-2026-11-12/`. These measurements use the test client, not browser speaker playback; both use the same PCM WebSocket path. Three trials on one recording are insufficient to generalize across languages, speakers or sustained load.

| Network chunk | First text after first audio, ms (three runs) | Mean first text | End-to-done, ms (three runs) | Mean end-to-done | Mean session time |
|---|---|---:|---|---:|---:|
| 250 ms | 7372, 6769, 6858 | 6999 ms | 890, 760, 769 | 806 ms | 15.82 s |
| 500 ms | 6789, 6782, 6780 | 6784 ms | 1054, 996, 1071 | 1040 ms | 16.05 s |
| 1000 ms | 6822, 6762, 6778 | 6787 ms | 1491, 1500, 1505 | 1498 ms | 16.51 s |

All nine runs completed without error and delivered nonblank text before the recording ended. All produced exactly the same transcript: “Tommy asked me if I were afraid. And I said, \"I'm not afraid, Johnny.\" And then, this man started walking up the road. He came slowly.” The reference begins “Johnny,” so the normalized WER was 1/27 = 3.7% for every setting. No chunk size corrected that error.

## Interpretation

After the first trial, first-text timing was roughly 6.76–6.86 s for every size. Changing the network chunk size did **not** materially reduce the initial transcription lag. The runtime's roughly 2 s inference cadence and stable-text commitment dominate that delay.

Final completion was consistently fastest with 250 ms chunks. Its mean end-to-done time was about 0.23 s shorter than 500 ms and 0.69 s shorter than 1000 ms. This is an observed effect in this setup, not a guarantee for other audio or machines. 250 ms sends twice as many WebSocket audio messages as 500 ms, while offering little benefit to the user's main concern of first-text delay. The application default remains 500 ms pending multilingual and longer-recording tests; 1000 ms looks worse for final completion on this sample.

The experiment did not establish CPU efficiency, memory savings, concurrency capacity, or a generally optimal chunk size. The resource sampler's CPU percentages were not calibrated for this comparison and are not used to choose a setting. The process RSS observations include shared memory-mapped pages and should not be interpreted as unique physical RAM per call.
