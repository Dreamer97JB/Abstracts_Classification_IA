#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${VENV_DIR:-$HOME/.venvs/abstracts-rocm}"
REQ_FILE="${ROOT_DIR}/requirements/wsl-rocm-7.2.txt"
KERNEL_NAME="${KERNEL_NAME:-abstracts-rocm}"
KERNEL_DISPLAY_NAME="${KERNEL_DISPLAY_NAME:-Python (abstracts-rocm)}"

if ! command -v python3.12 >/dev/null 2>&1; then
  echo "[X] python3.12 no esta disponible en WSL." >&2
  exit 1
fi

if ! command -v rocminfo >/dev/null 2>&1; then
  echo "[X] rocminfo no esta disponible. Instala ROCm para WSL antes de continuar." >&2
  exit 1
fi

mkdir -p "$(dirname "$VENV_DIR")"
python3.12 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"

python -m pip install --upgrade pip wheel setuptools
python -m pip install -r "$REQ_FILE"

TORCH_LIB="$(
python - <<'PY'
import site
from pathlib import Path

for path in site.getsitepackages():
    candidate = Path(path) / "torch" / "lib"
    if candidate.exists():
        print(candidate)
        break
PY
)"

if [ -n "$TORCH_LIB" ]; then
  rm -f "$TORCH_LIB"/libhsa-runtime64.so*
fi

python -m ipykernel install --user --name "$KERNEL_NAME" --display-name "$KERNEL_DISPLAY_NAME"
python - <<'PY'
import nltk

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
PY

python - <<'PY'
import torch

print("torch", torch.__version__)
print("cuda_available", torch.cuda.is_available())
print("device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device_0", torch.cuda.get_device_name(0))
PY

echo
echo "[OK] Entorno ROCm listo en: $VENV_DIR"
echo "[OK] Kernel Jupyter: $KERNEL_NAME"
echo "[i] Activa con: source \"$VENV_DIR/bin/activate\""
