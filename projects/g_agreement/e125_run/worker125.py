"""E125 pod worker (Integrator Q; §234/§236 E125; W-lens source 7d2a4df9 / archive 1747e8d5 / CODE_SEAL d7f6eba4, input seal 6235fa58,
C loader compatibility b4036f01a). Outer custody only: verify code/input seals and the pinned AR heads/LoRA bytes on the weights volume, check one H200
and the assignment (created before 10:00Z, deadline <= 12:50Z), then run W-lens's once-only entrypoint unchanged as a subprocess:
python run_rebuild.py --input <packet> --out <fresh> --batch 4 --device cuda (offline HF cache on /weights), killed at deadline - 60 s.
run_rebuild.py itself applies the frozen label-blind SPACE_PROOF (8e7b77506) and stops as NOT_RUN_OPERATIONAL_SPACE_MISMATCH if it fails.
No labels, probes or alignment. The outer OUTPUT_SEAL lists every file written; outputs sealed unopened."""
import argparse, hashlib, json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path
CODE_SEAL = 'd7f6eba4fa669b202d81fa922265c9aa8814999ec8d89b85db411f14b17925b0'; INPUT_SEAL = '6235fa58c1e0e003ed13998d3fc42b7e5590ac390a9e423c80b53f26ca2333ad'
AR = '/weights/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc/ar_ptag_pooled'
BASE = '/weights/hf_cache/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
ARROOT = '/weights/hf_cache/hub/models--agu18dec--olens_and_ar/snapshots/c95215d5d2f6250f20c305ae55c6e4d7569f92dc'
# Loader routing only (pre-load failure rf67jx0qjlaai7: offline snapshot_download still issued an API tree call). run_rebuild.py is run unchanged
# via runpy; huggingface_hub.snapshot_download is routed to the two pinned volume snapshots for exact (repo, revision) pairs and refuses anything else.
WRAP = '''import sys, runpy, huggingface_hub
P = {('Qwen/Qwen3.6-27B', '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'): %r, ('agu18dec/olens_and_ar', 'c95215d5d2f6250f20c305ae55c6e4d7569f92dc'): %r}
def routed(repo_id, revision=None, **kw):
    if (repo_id, revision) not in P: raise ValueError('unpinned snapshot request %%s@%%s' %% (repo_id, revision))
    return P[(repo_id, revision)]
huggingface_hub.snapshot_download = routed
sys.argv = ['run_rebuild.py'] + sys.argv[1:]
runpy.run_path('run_rebuild.py', run_name='__main__')
''' % (BASE, ARROOT)
PINS = {'heads.pt': '9f4cb6d193679c8683d7b49c8d2821c71567b3fc720baa73d7dbddb95f4c2179', 'lora/adapter_model.safetensors': 'd90bb9df02c352ef19f28536374e4a333e6dae8a103ba37d9e1c4e5183654e8a'}
def read(p): return json.loads(Path(p).read_text())
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()
def write(p, x): p = Path(p);p.parent.mkdir(parents=True, exist_ok=True);p.write_text(json.dumps(x, indent=2)+'\n')
def verify(root, name, digest):
    p = Path(root)/name;assert sha(p) == digest, 'seal '+name
    for n, h in read(p)['files'].items(): assert sha(Path(root)/n) == h, 'member '+n
def main():
    p = argparse.ArgumentParser()
    for n in ('src', 'inputs', 'assignment', 'out'): p.add_argument('--'+n, type=Path, required=True)
    p.add_argument('--validate-only', action='store_true');a = p.parse_args()
    verify(a.src, 'CODE_SEAL.json', CODE_SEAL);verify(a.inputs, 'INPUT_SEAL.json', INPUT_SEAL);assert read(a.inputs/'INPUT_SEAL.json')['labels_included'] is False
    assert set(read(a.inputs/'INPUT_SEAL.json')['files']) == {'READOUTS.json', 'test_true_raw.npy', 'whitener.pt'} and set(os.listdir(a.inputs)) == {'READOUTS.json', 'test_true_raw.npy', 'whitener.pt', 'INPUT_SEAL.json'}, 'label-free packet only'
    if a.validate_only: print('VALIDATE_OK E125 code+input seals');return
    for n, h in PINS.items(): assert sha(Path(AR)/n) == h, 'pinned AR '+n
    assert Path(BASE, 'config.json').exists() and Path(ARROOT, 'ar_ptag_pooled', 'heads.pt').exists(), 'pinned volume snapshots'
    ass = read(a.assignment)
    assert ass['experiment'] == 'E125' and ass['pod_id'] == os.environ.get('RUNPOD_POD_ID') and ass['gpu_type'] == 'H200' and ass['allocation_verified'] and ass['daily_budget_verified']
    assert ass['source_sha256'] == CODE_SEAL and ass['input_sha256'] == INPUT_SEAL
    assert ass['absolute_deadline_epoch'] == ass['pod_created_epoch']+ass['cap_seconds'] and ass['pod_created_epoch'] < 1793354400 and ass['absolute_deadline_epoch'] <= 1793364600 and ass['cap_seconds']*5.29/3600 <= 25
    import torch
    assert torch.cuda.is_available() and torch.cuda.device_count() == 1 and 'H200' in torch.cuda.get_device_name(0), 'one H200'
    a.out.mkdir(parents=True, exist_ok=False);write(a.out/'ASSIGNMENT.json', ass);run = a.out/'run'
    env = dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HOME='/weights/hf_cache', HF_HUB_CACHE='/weights/hf_cache/hub')
    budget = ass['absolute_deadline_epoch']-time.time()-60;t0 = time.time();status = 'FAILED';code = None
    try:
        r = subprocess.run(['python', '-B', '-c', WRAP, '--input', str(a.inputs), '--out', str(run), '--batch', '4', '--device', 'cuda'], cwd=a.src, env=env, timeout=max(1, budget),
                           stdout=open(a.out/'run_rebuild.stdout.log', 'w'), stderr=open(a.out/'run_rebuild.stderr.log', 'w'));code = r.returncode
        inner = read(run/'OUTPUT_SEAL.json')['status'] if (run/'OUTPUT_SEAL.json').exists() else None
        status = {'RECONSTRUCTION_AND_SPACE_PROOF_COMPLETE': 'COMPLETE', 'NOT_RUN_OPERATIONAL_SPACE_MISMATCH': 'NOT_RUN_OPERATIONAL_SPACE_MISMATCH'}.get(inner, 'FAILED')
    except subprocess.TimeoutExpired: status = 'NO_FIT'
    finally:
        files = [q for q in a.out.rglob('*') if q.is_file() and q.name != 'OUTPUT_SEAL.json' or (q.is_file() and q.parent != a.out)]
        write(a.out/'OUTPUT_SEAL.json', dict(experiment='E125', status=status, returncode=code, seconds=round(time.time()-t0, 1), code_seal_sha256=CODE_SEAL, input_seal_sha256=INPUT_SEAL,
              labels_read=False, outputs_unopened=True, sealed_utc=datetime.now(timezone.utc).isoformat(), files={str(q.relative_to(a.out)): sha(q) for q in files}))
if __name__ == '__main__': main()
