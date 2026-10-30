#!/bin/bash
# S1 pod chain: smoke (2 pairs per family, one layer; discarded) then the full run. Usage: bash run_s1.sh <pod start epoch>
set -e
source /workspace/.env
cd "$(dirname "$0")/../../.."  # repo root (pod: /workspace/activation-readers)
export S1_T0="$1"
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
rm -rf cache/g_agreement/s1
python -m projects.g_agreement.f2.s1_cells --smoke --budget-min 200 2>&1 | tee /workspace/s1_smoke.log
mkdir -p cache/g_agreement/s1_smoke_discarded && mv cache/g_agreement/s1/* cache/g_agreement/s1_smoke_discarded/
python -m projects.g_agreement.f2.s1_cells --budget-min 115 2>&1 | tee /workspace/s1_full.log
echo S1_CHAIN_DONE
