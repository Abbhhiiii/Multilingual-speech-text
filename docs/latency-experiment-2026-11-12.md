# Early text and revisable transcript experiment — 12 November 2026

The repository was pushed before this change at commit `93b64842963ec5098ef5019cac5676d7f758aa72`. This experiment changes the native runtime through the tracked `runtime_patches/early-commit.patch`; no GPU backend is used. All audio was sent at real-time pace on the same Apple M2 (8 GB) using the Qwen3-ASR-0.6B CPU build. These are individual trials, not a statistically reliable benchmark.

| Native mode | First nonblank direct stdout on 15 s English WAV | Final output |
|---|---:|---|
| Upstream: 2 s step, first 2 windows withheld | 8.67 s | Reference baseline text, with Tommy/Johnny error |
| 2 s step, immediate committed text | 6.45 s | Same English final text |
| 1 s step, immediate committed text | 5.31 s | Same English final text |
| 0.5 s step, immediate committed text | not selected | Duplicated English words and took 22.12 s total |

The 1 s immediate-commit mode failed the multilingual check: Indonesian audio was transcribed in Thai; Mandarin duplicated “告别”. It is **not** the application default. These failures show why simply displaying unstable text as irrevocable commits is unsafe.

The chosen mode keeps the native 2 s step, 5-token rollback and two holdback windows, but emits a **complete revisable text hypothesis** after each native inference step. The backend and UI replace one transcript snapshot; the latest uncommitted tail may change. Direct paced tests ended with the same final English, Indonesian and Mandarin text as the original stable path. A Mandarin example changed the first snapshot “这。” to “这并不是告别。” on the next step. The final result is still only declared on `done`.

End-to-end WebSocket smoke checks with this mode returned first text in 6.20 s (English), 5.75 s (Indonesian) and 2.89 s (Mandarin) measured from first audio received by the backend. Their final transcripts matched the previous stable runs. Recorded events: `evidence/revisable-english-websocket.json`, `evidence/revisable-indonesian-websocket.json`, `evidence/revisable-mandarin-websocket.json`.

A separate 45 s English clip completed without repeated final text. Its first visible text was 20.57 s after first audio, with a long low-energy stretch in the recording; that is not a general startup-latency measurement. Raw event data: `evidence/revisable-english-45s-websocket.json`.

**Limit:** This does not guarantee text at the 2 s mark. CPU encoding/decoding and the model's ability to form a useful hypothesis still take time. A visible hypothesis may be wrong and revised later. Longer recordings and more speakers need evaluation before claiming improved accuracy or sustained real-time performance.
