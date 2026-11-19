FROM node:22-bookworm-slim AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential ca-certificates curl git libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY runtime_patches/early-commit.patch ./runtime_patches/early-commit.patch
COPY scripts/download_model.py ./scripts/download_model.py
RUN mkdir -p .runtime \
    && git clone https://github.com/antirez/qwen-asr.git .runtime/qwen-asr \
    && git -C .runtime/qwen-asr checkout 924694251d9e0f18e5d86bbd06aa3ab5f870002d \
    && git -C .runtime/qwen-asr apply ../../runtime_patches/early-commit.patch \
    && make -C .runtime/qwen-asr blas \
    && python scripts/download_model.py \
    && rm -rf .runtime/qwen-asr/.git

COPY backend/ ./backend/
COPY samples/ ./samples/
COPY --from=frontend-build /build/frontend/dist/ ./frontend/dist/

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000", "--ws-max-size", "32768", "--ws-max-queue", "4"]
