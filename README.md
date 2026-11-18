# Tetherfi multilingual streaming ASR

A local speech-to-text application for English, Mandarin Chinese, and Indonesian. The browser sends audio as it arrives; a FastAPI backend runs Qwen3-ASR-0.6B on the CPU and returns one live transcript. Recent words may change as more speech provides context.

## What you need

This project was tested on an Apple M2 MacBook Air with 8 GB RAM. Install Python 3.11+, Node.js 20.19+ or 22.12+, npm, Git, curl, and the macOS command-line tools (`xcode-select --install`). Allow several GB of free disk space for the model and build files.

The setup script downloads and builds the pinned [antirez/qwen-asr C runtime](https://github.com/antirez/qwen-asr) and downloads the official [Qwen3-ASR-0.6B model](https://huggingface.co/Qwen/Qwen3-ASR-0.6B). It applies this project's [streaming-output patch](runtime_patches/early-commit.patch) to the runtime. The macOS build uses Apple Accelerate for CPU inference; no GPU backend is enabled.

## Install

From the project folder, run:

```sh
bash scripts/setup.sh
```

This creates `.venv`, builds the CPU runtime, downloads approximately 1.88 GB of model weights, checks their SHA-256, and installs the frontend packages. The runtime, weights, and dependencies stay in local ignored folders and are not stored in Git.

## Run

Open two terminals in the project folder. Start the backend in the first:

```sh
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --ws-max-size 32768 --ws-max-queue 4
```

Start the web page in the second:

```sh
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173/** in your browser.

## Use

- **WAV file:** Drop or choose a 16 kHz, mono, uncompressed PCM16 WAV, then press **Start streaming**. The recording plays aloud while 500 ms audio chunks are sent at real-time pace. Keep the tab active.
- **Microphone:** Select **Microphone**, press **Start microphone**, allow browser access, speak, then press **Finish recording** to receive the final transcript.
- The page detects the language automatically. It shows the current transcript, time to first text, and time from the end of audio to the final result. A recording can be up to five minutes long.

Sample WAV files: English at `.runtime/qwen-asr/samples/jfk.wav` after setup; Mandarin and Indonesian in [`samples/`](samples/). To convert another recording to the required WAV format, use [FFmpeg](https://ffmpeg.org/) if installed:

```sh
ffmpeg -i original.wav -ac 1 -ar 16000 -c:a pcm_s16le prepared.wav
```

## Check the installation

```sh
.venv/bin/python -m pytest -q
(cd frontend && npm test && npm run build)
```

These are code checks. To check real speech recognition, run the app with a sample WAV. The [60-clip benchmark](evidence/fleurs-60-500ms/REPORT.md) and [English concurrency measurements](evidence/concurrency-en/REPORT.md) record measured results and limits.

## How it works

`React page → WebSocket → FastAPI → one native CPU worker per stream → transcript back to the page`

The browser sends 16 kHz mono PCM16 in 500 ms chunks. Each connection has its own native worker. The worker processes audio in roughly two-second inference steps; 500 ms delivery does **not** mean text appears every 500 ms. The backend reports timing and replaces the displayed transcript when the model revises recent words. See the [WebSocket protocol](docs/protocol.md) for message details.

This is a local prototype. The server listens on `127.0.0.1`; public hosting is not configured.
