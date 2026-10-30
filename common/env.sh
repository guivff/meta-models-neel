#!/usr/bin/env bash
# Shared environment for the MATS minis. Run once per machine. Reproduces the pod setup of 2026-10-03 exactly:
#   /workspace/venv (python -m venv --system-site-packages), torch 2.13.0+cu129 / torchvision 0.28.0 / torchaudio 2.11.0,
#   vllm 0.30.0 (official cu129 wheel), transformers/peft/trl/datasets/..., bergson, sae-lens, neuronpedia,
#   editable jacobian-lens, NO obvs (it pins torch==2.2.0 and transformers<5; Qwen3.5 needs transformers>=5.2),
#   Node 22 + Claude Code under /workspace/node22, and /workspace/.env (activation + HF_HOME + API keys from the caller's env).
set -euo pipefail

WS=${WS:-/workspace}                       # RunPod network volume; set WS=$HOME/mats-ws elsewhere
VENV=${VENV:-$WS/venv}
REPO=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
export PIP_BREAK_SYSTEM_PACKAGES=1 HF_HOME=${HF_HOME:-$WS/hf_cache}

# --- venv (system site-packages visible, so the image's CUDA libs are reused) --------------------------------------
if [ ! -x "$VENV/bin/python" ]; then python -m venv --system-site-packages "$VENV"; fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
pip install -U pip
pip install transformers peft datasets scikit-learn pandas matplotlib scipy requests accelerate trl sentence-transformers \
  tqdm safetensors huggingface_hub "tiktoken>=0.7" "typer>=0.26.1"
pip install bergson sae-lens neuronpedia        # data attribution; Gemma Scope directions + explanations (P3 benchmark only)
# obvs is deliberately NOT installed (Patchscope is implemented with hooks in projects/p6_bias_term; see BRIEF D4).

# --- reference repositories --------------------------------------------------------------------------------------
mkdir -p "$REPO/third_party"
[ -d "$REPO/third_party/jacobian-lens" ]           || git clone https://github.com/anthropics/jacobian-lens "$REPO/third_party/jacobian-lens"
[ -d "$REPO/third_party/VEA-through-training" ]    || git clone https://github.com/arbdwj/VEA-through-training "$REPO/third_party/VEA-through-training"
[ -d "$REPO/third_party/evaluation-awareness" ]    || git clone https://github.com/evaluation-awareness/evaluation-awareness "$REPO/third_party/evaluation-awareness"
[ -d "$REPO/third_party/diffing-toolkit" ]         || git clone https://github.com/science-of-finetuning/diffing-toolkit "$REPO/third_party/diffing-toolkit"
pip install -e "$REPO/third_party/jacobian-lens"

# --- GPU stack last, pinned. PyPI wheels target CUDA 13 (driver >= 580); CUDA 12.x drivers need the cu129 builds. ---
VLLM=0.30.0; TORCH=2.13.0; TORCHVISION=0.28.0; TORCHAUDIO=2.11.0
if command -v nvidia-smi >/dev/null; then
  DRIVER_CUDA=$(nvidia-smi | sed -n 's/.*CUDA Version: \([0-9]*\)\..*/\1/p' | head -1)
  if [ "${DRIVER_CUDA:-0}" -ge 13 ]; then
    pip install "vllm==$VLLM" "torch==$TORCH" "torchvision==$TORCHVISION" "torchaudio==$TORCHAUDIO"
  else
    pip install "https://github.com/vllm-project/vllm/releases/download/v$VLLM/vllm-$VLLM%2Bcu129-cp38-abi3-manylinux_2_28_x86_64.whl" \
      "torch==$TORCH+cu129" "torchvision==$TORCHVISION+cu129" "torchaudio==$TORCHAUDIO+cu129" --extra-index-url https://download.pytorch.org/whl/cu129
  fi
  python -c "import torch, transformers, vllm; assert torch.cuda.is_available(), 'CUDA init failed'; print('torch', torch.__version__, '| vllm', vllm.__version__)"
fi

# --- Node 22 + Claude Code (persisted on the volume; the container disk is wiped on every pod restart) --------------
if [ ! -x "$WS/node22/bin/node" ]; then
  curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz -o "$WS/node22.tar.xz"
  mkdir -p "$WS/node22" && tar -xJf "$WS/node22.tar.xz" -C "$WS/node22" --strip-components=1 && rm "$WS/node22.tar.xz"
fi
export PATH="$WS/node22/bin:$PATH"
command -v claude >/dev/null || npm install -g @anthropic-ai/claude-code

# --- $WS/.env: source it in every shell / tmux session before running anything ------------------------------------
if [ ! -f "$WS/.env" ]; then
  {
    echo "source $VENV/bin/activate"
    echo "export PIP_BREAK_SYSTEM_PACKAGES=1"
    echo "export HF_HOME=$HF_HOME"
    echo "export PATH=$WS/node22/bin:\$PATH"
    [ -n "${OPENROUTER_API_KEY:-}" ] && echo "export OPENROUTER_API_KEY=$OPENROUTER_API_KEY"
    [ -n "${HF_TOKEN:-}" ] && echo "export HF_TOKEN=$HF_TOKEN"
  } > "$WS/.env"
  chmod 600 "$WS/.env"
fi

mkdir -p "$REPO/cache" "$REPO/results"
echo "env ready: source $WS/.env (keys are copied into it only if set in the calling shell; never print it)."
