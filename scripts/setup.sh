#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p .runtime
if [ ! -d .runtime/qwen-asr/.git ]; then
  git clone https://github.com/antirez/qwen-asr.git .runtime/qwen-asr
fi
git -C .runtime/qwen-asr checkout 924694251d9e0f18e5d86bbd06aa3ab5f870002d
if git -C .runtime/qwen-asr apply --reverse --check ../../runtime_patches/early-commit.patch 2>/dev/null; then
  echo "Runtime patch already applied"
else
  git -C .runtime/qwen-asr apply ../../runtime_patches/early-commit.patch
fi
make -C .runtime/qwen-asr blas
.venv/bin/python scripts/download_model.py
(cd frontend && npm ci)
