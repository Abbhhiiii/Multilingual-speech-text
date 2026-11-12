# Four-day execution plan

Day 1: CPU runtime feasibility, paced stdin/stdout proof, asynchronous backend, isolated sessions, errors and timing. Day 2: React UI, pacing validation and real English/Mandarin/Indonesian recordings. Day 3: chunk-size comparison, accuracy/performance and conservative concurrency ramp. Day 4: sizing estimates, alternative comparison, report and personally narrated demonstration.

## Reproducible experiment design (not completed measurements)

Use Google FLEURS `en_us`, `cmn_hans_cn`, `id_id` with reference transcripts. Pin dataset revision and sample IDs, retain license/provenance and split. Begin with 10 recordings per language across speakers/durations. Separate tuning and evaluation samples. Convert once to 16 kHz mono PCM16 using FFmpeg; retain originals and conversion command. Dataset has not yet been downloaded.

1. Compare 250, 500, 1000 ms network chunks on identical recordings/order. Hold runtime defaults fixed: 2 s native steps, 8 s encoder windows, 5-token rollback, 32 new tokens/step; 4 configured CPU threads. Record warm/cold conditions and repeat trials. Do not select a winner before measuring.
2. Score English/Indonesian WER, Mandarin CER with explicit shared normalization (Unicode, case, punctuation and whitespace policy). Preserve raw predictions. Use jiwer in a separate benchmark environment when this phase starts.
3. Record first-text latency, end-to-done latency, total session wall time, runtime inference time from stderr where valid, CPU time/utilization, sampled peak RSS, errors and audio timing. Paced elapsed/audio duration is NOT inference RTF. The application queue is NOT the runtime's inference backlog; instrument native processed sample positions before claiming backlog measurements.
4. Sample process CPU and RSS with psutil (include child workers and backend). Percent CPU can exceed 100% across cores. Sum RSS overcounts shared mapped pages; distinguish RSS from physical/system memory pressure. Report sampling interval and warmup.
5. Concurrency 1 then 2 then 3 only while measured memory pressure and latency allow. Raise ASR_MAX_SESSIONS explicitly for each controlled test; do not treat successful socket connection counts as inference capacity. Keep one Uvicorn process so admission is global to this prototype. Stop at sustained slowdown, unacceptable latency, errors or unsafe memory pressure.
6. Estimate 50/100/200/500/1000 call legs from measured sustainable calls per comparable host, resource budgets and explicit headroom. Label all extrapolations; do not equate M2 cores directly to arbitrary cloud vCPUs.
7. Research and run a controlled CPU comparison with whisper.cpp if time permits. Same audio, normalization, hardware and concurrency. Separate research-only claims from executed measurements.

## Remaining assignment deliverables

Three-language real demo, full accuracy/resource/concurrency results, capacity estimates, alternative-model comparison, final technical report, and candidate's own spoken explanation/video. The implementation does not generate or impersonate that personal explanation.
