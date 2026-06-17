#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${VENV_DIR:-$HOME/.venvs/abstracts-rocm}"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "[X] No existe la venv en $VENV_DIR" >&2
  exit 1
fi

source "$VENV_DIR/bin/activate"

echo "[i] rocminfo"
rocminfo | sed -n '1,80p'

echo
echo "[i] Python stack"
python - <<'PY'
import bertopic
import pandas
import sentence_transformers
import setfit
import sklearn
import torch
import transformers

print("torch", torch.__version__)
print("cuda", torch.cuda.is_available())
print("device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device", torch.cuda.get_device_name(0))
print("pandas", pandas.__version__)
print("sklearn", sklearn.__version__)
print("transformers", transformers.__version__)
print("sentence_transformers", sentence_transformers.__version__)
print("setfit", setfit.__version__)
print("bertopic", bertopic.__version__)
PY
