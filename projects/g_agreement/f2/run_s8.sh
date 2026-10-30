#!/bin/bash
# S8 pod chain: phase A (J-lens + Oracle on the target) then phase B (NLA). Resumable (scores.jsonl is keyed).
set -e
source /workspace/.env
cd "$(dirname "$0")/../../.."  # repo root (pod: /workspace/activation-readers)
nvidia-smi --query-gpu=memory.used,utilization.gpu --format=csv
python -m projects.g_agreement.f2.s8_rescore --phase A 2>&1 | tee -a /workspace/s8_A.log
python -m projects.g_agreement.f2.s8_rescore --phase B 2>&1 | tee -a /workspace/s8_B.log
echo S8_CHAIN_DONE
