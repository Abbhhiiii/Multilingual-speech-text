"""Pinned official model download with atomic files and weight checksum verification."""
import hashlib
from pathlib import Path
import subprocess

REVISION = '5eb144179a02acc5e5ba31e748d22b0cf3e303b0'
WEIGHT_SHA256 = '79d6cbd4c98c7bbffe9db2edac07f56cd6637d0d5944b27f6c2b8353840323ea'
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    model = ROOT / '.runtime/models/qwen3-asr-0.6b'
    model.mkdir(parents=True, exist_ok=True)
    for name in ('config.json','generation_config.json','vocab.json','merges.txt','model.safetensors'):
        target = model / name
        if target.exists() and (name != 'model.safetensors' or digest(target) == WEIGHT_SHA256):
            print('Already present:', name)
            continue
        partial = target.with_suffix(target.suffix + '.part')
        print('Downloading:', name, flush=True)
        subprocess.run(['curl', '-fL', '--retry', '3', '-o', str(partial),
                        f'https://huggingface.co/Qwen/Qwen3-ASR-0.6B/resolve/{REVISION}/{name}'], check=True)
        if name == 'model.safetensors' and digest(partial) != WEIGHT_SHA256:
            raise RuntimeError('Weight checksum mismatch; partial file retained, not installed.')
        partial.replace(target)
    (model/'REVISION').write_text(REVISION+'\n')

if __name__ == '__main__': main()
