#!/bin/bash
# S6 step zero pod chain: smoke (4 items; discarded) then the full 32 items. Downloads go to the container disk.
set -e
source /workspace/.env
export HF_HOME=/root/hf_s6 HF_HUB_DISABLE_XET=1
cd "$(dirname "$0")/../../.."  # repo root (pod: /workspace/activation-readers)
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
rm -rf cache/g_agreement/s6
python -m projects.g_agreement.f2.s6_step0 --smoke 2>&1 | tee /workspace/s6_smoke.log
mkdir -p cache/g_agreement/s6_smoke_discarded && mv cache/g_agreement/s6/* cache/g_agreement/s6_smoke_discarded/
python -m projects.g_agreement.f2.s6_step0 2>&1 | tee /workspace/s6_full.log
echo S6_CHAIN_DONE
