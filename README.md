# Multilingual Streaming Speech-to-Text

A local CPU-only app that transcribes English, Mandarin Chinese, and Indonesian speech from a WAV file or microphone. The web page streams audio to a FastAPI backend, which runs [Qwen3-ASR-0.6B](https://huggingface.co/Qwen/Qwen3-ASR-0.6B) through the [antirez/qwen-asr runtime](https://github.com/antirez/qwen-asr) and updates the transcript as speech arrives.

## Run on macOS, Windows, or Linux

Install and start [Docker Desktop](https://docs.docker.com/desktop/) on macOS or Windows, or [Docker Engine with Compose](https://docs.docker.com/engine/install/) on Linux. On Windows, use Linux containers. Give Docker at least 4 GB of memory and several GB of free disk space; the first build downloads the model.

```sh
git clone https://github.com/Abbhhiiii/Multilingual-speech-text.git
cd Multilingual-speech-text
docker compose up --build
```

Open **http://127.0.0.1:8080/**. Stop the app with **Ctrl+C** in the terminal.
