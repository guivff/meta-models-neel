"""CPU imports only: no engine construction, CUDA calls, or plugin registration."""
import importlib.metadata as metadata
import json
import os
import subprocess
import sys
import time

CHECKS = {
    "torch": "import torch; assert torch.version.cuda == '13.0'",
    "transformers": "import transformers",
    "peft": "import peft",
    "vllm": "import vllm",
    "lens_plugin_entrypoint_load": "import importlib.metadata as m; e = [e for e in m.distribution('vllm-lens').entry_points if e.group == 'vllm.general_plugins' and e.name == 'activations']; assert len(e) == 1; f = e[0].load(); assert callable(f) and f.__module__ == 'vllm_lens._activations_plugin' and f.__name__ == 'register'",
    "author_module": "import runpy; m = runpy.run_path('/recipe/vendor/olens_glm53_usage.py', run_name='e74_cpu_import'); assert callable(m['GlmOlensEngine'])",
}

def main():
    env = dict(os.environ, CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', PYTHONDONTWRITEBYTECODE='1', HOME='/tmp')
    rows = {}
    for name, code in CHECKS.items():
        start = time.monotonic()
        try:
            proc = subprocess.run([sys.executable, '-c', code], env=env, capture_output=True, text=True, timeout=180)
            rows[name] = dict(status='PASS' if proc.returncode == 0 else 'FAIL', returncode=proc.returncode, stdout=proc.stdout[-4000:], stderr=proc.stderr[-6000:])
        except subprocess.TimeoutExpired as exc:
            rows[name] = dict(status='TIMEOUT', timeout_seconds=180)
        rows[name]['wall_seconds'] = time.monotonic() - start
    result = dict(status='PASS_CPU_IMPORTS_ONLY' if all(r['status']=='PASS' for r in rows.values()) else 'CPU_IMPORT_CHECKS_INCOMPLETE_OR_FAILED', checks=rows, gpu_used=False, model_weights_downloaded_bytes=0, plugin_registration_executed=False, worker_hooks_verified=False, gpu_engine_verified=False)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result['status']=='PASS_CPU_IMPORTS_ONLY' else 1

if __name__ == '__main__':
    raise SystemExit(main())
