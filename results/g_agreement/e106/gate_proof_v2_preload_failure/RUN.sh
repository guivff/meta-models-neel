#!/bin/bash
set -e
cd /workspace/e106-run
export PYTHONPATH=/workspace/e106-run:/workspace/e106-run/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e106-run/cuda_cache
echo $$ > job.pid
finish() { rc=$?; trap - EXIT; /weights/venv-kernels/bin/python -c 'import json,pathlib,sys;pathlib.Path("WORKER_EXIT.json").write_text(json.dumps({"exit_code":int(sys.argv[1])}))' "$rc"; exit "$rc"; }
trap finish EXIT
export TILELANG_CACHE_DIR=/workspace/e106-tilelang-final/tilelang-cache TVM_FFI_CACHE_DIR=/workspace/e106-tilelang-final/ffi-cache TORCH_EXTENSIONS_DIR=/workspace/e106-tilelang-final/torch-cache TRITON_CACHE_DIR=/workspace/e106-tilelang-final/triton-cache TORCHINDUCTOR_CACHE_DIR=/workspace/e106-tilelang-final/inductor-cache PYTHONPYCACHEPREFIX=/workspace/e106-tilelang-final/pycache PIP_CACHE_DIR=/workspace/e106-tilelang-final/pip-cache FLA_CACHE_RESULTS=0
unset FLA_TILELANG FLA_DISABLE_BACKEND_DISPATCH
mkdir operational_backend
/weights/venv-kernels/bin/python projects/g_agreement/e106/backend_install.py --manifest results/g_agreement/e106/backend_fix/DEPENDENCIES.json --wheelhouse cache/g_agreement/e106/backend_fix/wheels_linux --root /workspace/e106-tilelang-final --base-python /weights/venv-kernels/bin/python
cp /workspace/e106-tilelang-final/INSTALL_RECEIPT.json /workspace/e106-tilelang-final/INSTALL.log operational_backend/
export PYTHONPATH=/workspace/e106-tilelang-final/site:$PYTHONPATH
/weights/venv-kernels/bin/python projects/g_agreement/e106/backend_smoke.py --manifest results/g_agreement/e106/backend_fix/DEPENDENCIES.json --overlay /workspace/e106-tilelang-final/site --out GPU_SMOKE.json
/weights/venv-kernels/bin/python -c 'import pathlib,json,time;p=pathlib.Path('"'"'ADMISSION.json'"'"');a=json.loads(p.read_text());a['"'"'measured_e106_staging_seconds'"'"']=[time.time()-a['"'"'created_epoch'"'"']];p.write_text(json.dumps(a,indent=2)+'"'"'\n'"'"')'
/weights/venv-kernels/bin/python -u -m projects.g_agreement.e106.worker --phase gate --inputs cache/g_agreement/e106/inputs_v1 --assets ASSETS.json --admission ADMISSION.json --out out
