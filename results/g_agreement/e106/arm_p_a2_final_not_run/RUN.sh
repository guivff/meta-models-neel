#!/bin/bash
set -e
cd /workspace/e106-run
export PYTHONPATH=/workspace/e106-run:/workspace/e106-run/external/mats-nla-workspace/src OMP_NUM_THREADS=8 MKL_NUM_THREADS=8 OPENBLAS_NUM_THREADS=8 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 CUDA_CACHE_PATH=/workspace/e106-run/cuda_cache
echo $$ > job.pid
finish() { rc=$?; trap - EXIT; /weights/venv-kernels/bin/python -c 'import json,pathlib,sys;pathlib.Path("WORKER_EXIT.json").write_text(json.dumps({"exit_code":int(sys.argv[1])}))' "$rc"; exit "$rc"; }
trap finish EXIT
/weights/venv-kernels/bin/python -c 'import pathlib,json,time;p=pathlib.Path('"'"'ADMISSION.json'"'"');a=json.loads(p.read_text());a['"'"'measured_e106_staging_seconds'"'"']=[time.time()-a['"'"'created_epoch'"'"']];p.write_text(json.dumps(a,indent=2)+'"'"'\n'"'"')'
/weights/venv-kernels/bin/python -u -m projects.g_agreement.e106.p_retime --inputs cache/g_agreement/e106/inputs_v1 --assets ASSETS.json --admission ADMISSION.json --out out
