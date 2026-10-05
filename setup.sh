#!/bin/bash
# One-time setup for Booth. Safe to run again: it skips anything already done.
set -e
cd "$(dirname "$0")"

say() { printf "\n\033[1m%s\033[0m\n" "$1"; }

if [ "$(uname -m)" != "arm64" ]; then
  echo "Voice cloning needs an Apple Silicon Mac (M1 or newer). Built-in voices will still work."
fi

if ! command -v uv >/dev/null 2>&1; then
  say "Installing uv (free Python installer)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

if [ ! -x .venv/bin/python ]; then
  say "Creating the Python environment..."
  uv venv -p 3.11 .venv
fi
say "Installing packages..."
uv pip install -p .venv/bin/python -r requirements.txt
# phonemizer (not the fork) breaks espeak data paths, make sure it is gone
uv pip uninstall -p .venv/bin/python phonemizer >/dev/null 2>&1 || true
uv pip install -p .venv/bin/python --reinstall-package phonemizer-fork phonemizer-fork==3.3.2 >/dev/null

mkdir -p models
BASE=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
if [ ! -s models/kokoro-v1.0.onnx ]; then
  say "Downloading the built-in voice model (310 MB)..."
  curl -L --fail -o models/kokoro-v1.0.onnx.part "$BASE/kokoro-v1.0.onnx" && mv models/kokoro-v1.0.onnx.part models/kokoro-v1.0.onnx
fi
if [ ! -s models/voices-v1.0.bin ]; then
  say "Downloading the built-in voices (27 MB)..."
  curl -L --fail -o models/voices-v1.0.bin.part "$BASE/voices-v1.0.bin" && mv models/voices-v1.0.bin.part models/voices-v1.0.bin
fi

if [ "$(uname -m)" = "arm64" ] && [ ! -e models/qwen3-tts-0.6b/speech_tokenizer/model.safetensors ]; then
  say "Downloading the voice cloning model (about 2 GB, one time only)..."
  .venv/bin/python - <<'PY'
from huggingface_hub import snapshot_download
snapshot_download("mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit", local_dir="models/qwen3-tts-0.6b")
PY
fi

say "Done. Double-click 'Start Booth.command' to open the studio."
