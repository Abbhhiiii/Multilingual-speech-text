# WebSocket protocol v1

Connect `/ws/transcribe`. One connection is one call leg; one start/end lifecycle per connection. Send:

```json
{"type":"start","sample_rate":16000,"channels":1,"encoding":"pcm_s16le","chunk_ms":500,"language":"auto"}
```

`language`: auto/en/zh/id. `chunk_ms`: 250/500/1000. Unknown metadata keys and wrong scalar types are rejected. Await `ready`, then send binary messages containing only raw signed little-endian PCM16 (no WAV header). Each message contains at most the configured chunk duration; all except the last must be full-sized. Send the first chunk after its duration elapses and pace subsequent chunks from a monotonic origin.

After the final binary message, send `{"type":"end"}`. This closes native stdin after queued audio is written, flushes the native final text, and awaits a successful worker exit. `{"type":"cancel"}` stops the worker immediately, including while finalizing. Disconnect also cleans up.

Server events:

- `ready`: session ID, accepted chunk size. Means process spawned, not that model loading has finished.
- `transcript`: session ID, monotonically increasing sequence, full `text` snapshot, `metrics`. Replace displayed text with the snapshot; do not append snapshots. There is only one transcript.
- `done`: final full text, final metrics; the server closes the connection.
- `error`: machine-readable `code`, human-readable `message`, session ID when admitted. The server closes the connection. Capacity rejections have no session allocation.

Error codes: metadata, audio, protocol, duration, pacing, backpressure, runtime, timeout, cancelled, capacity. Stderr remains in backend diagnostics rather than being mixed into recognized text.

At the recommended Uvicorn launch, incoming messages are limited to 32,768 bytes and the server WebSocket receive queue to four messages. Application controls are limited to 4096 characters. Native stdin writing and stdout/stderr reading run concurrently; a slow worker does not block FastAPI's event loop.
