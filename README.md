# Multilingual Streaming Speech-to-Text

A local CPU-only app that transcribes English, Mandarin Chinese, and Indonesian speech from a WAV file or microphone. The web page streams audio to a FastAPI backend, which runs [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) through the [antirez/qwen-asr runtime](https://github.com/antirez/qwen-asr) and updates the transcript as speech arrives.

## Run locally

On an Apple Silicon Mac, install Python 3.11+, Node.js and npm, Git, curl, and the Xcode command-line tools (`xcode-select --install`). Then run:

```sh
git clone https://github.com/Abbhhiiii/Multilingual-speech-text.git
cd Multilingual-speech-text
bash scripts/setup.sh
```

Start the backend in one terminal from the project folder:

```sh
source .venv/bin/activate
uvicorn backend.app:app --host 127.0.0.1 --port 8000 --ws-max-size 32768 --ws-max-queue 4
```

Start the web page in another terminal from the project folder:

```sh
cd frontend
npm run dev
```

Open **http://127.0.0.1:5173/**.
