#!/bin/bash
set -u
cd /workspace/e102-gate
export PYTHONPATH=/workspace/e102-gate:/workspace/e102-gate/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e102-gate/cuda_cache
echo $$ > job.pid
/weights/venv-kernels/bin/python -u -m projects.g_agreement.e102.gate --inputs cache/g_agreement/e102/gate_inputs --out out --model /weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9 --adapter /weights/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/olens_s3d_rl600 --admission ADMISSION.json --asset-manifest ASSETS.json; status=$?; /weights/venv-kernels/bin/python -c 'import sys,json,pathlib; pathlib.Path('"'"'WORKER_EXIT.json'"'"').write_text(json.dumps({'"'"'exit_code'"'"':int(sys.argv[1]),'"'"'production_training'"'"':False}))' "$status"; exit "$status"
