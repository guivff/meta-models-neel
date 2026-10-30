"""Create an integrator-only E22 request from committed CPU-validated sources."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from projects.g_agreement.blindspot import protocol as P
from .inputs import load
from .run import CAP, SETUP, LAYERS, POSITIONS, ARMS, PROMPTS, schedule, source_hashes


def create(inputs,tests,out):
    inputs,tests,out=map(Path,(inputs,tests,out))
    if out.exists():raise FileExistsError('request already exists')
    sources=source_hashes()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P.ROOT,text=True).strip()
    for name,digest in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=P.ROOT)).hexdigest()!=digest:
            raise ValueError('uncommitted source: '+name)
    data=load(inputs)
    if data['provenance']['registration_sha256']!=P.sha(P.ROOT/'results/g_agreement/understand/e22/REGISTRATION.md'):
        raise ValueError('input registration differs from pinned E22 registration')
    validation=json.loads(tests.read_text())
    if validation.get('status')!='PASS' or validation.get('gpu_hours')!=0:
        raise ValueError('passing CPU receipt required')
    if validation.get('layer0_full_swap_check')!='PASS':raise ValueError('CPU full-swap equivalence required')
    binding={'input_seal_sha256':P.sha(inputs/'INPUT_SEAL.json')}
    receipt={'experiment':'E22','owner':'W-internals','branch':'r/blindspot-internals',
        'status':'LAUNCH_REQUESTED_PENDING_INTEGRATOR_ASSIGNMENT_AND_WARMED_GATE',
        'registration_commit':'e71d1eeb',
        'registration_snapshot_sha256':P.sha(P.ROOT/'results/g_agreement/understand/e22/REGISTRATION.md'),
        'source_commit':commit,'source_files':sources,'input_directory':str(inputs.resolve()),**binding,
        'scope':{'items':len(data['items']),'test_items_per_row':84,'row_prompts':PROMPTS,
                 'layers':LAYERS,'layer_convention':'zero-based decoder block INPUT; block0 precedes mixing',
                 'positions':POSITIONS,'arms':ARMS,'patch_units':len(list(schedule(data))),
                 'patch_records':sum(len(s[-1]) for s in schedule(data)),
                 'baseline_row_prompt_captures':3*len(PROMPTS),'donor_seed':20261025},
        'controls':'Seeded opposite-value and same-value nonself donors; layer0 injection patch equals full activation swap. Retain original scores and candidate-pair scores.',
        'cpu_tests_receipt':str(tests),'cpu_tests_sha256':P.sha(tests),
        'model_environment':'/weights/venv-kernels','resources':{'gpu_count':1,'gpu_memory_gib_at_least':80},
        'memory':'One Oracle model/adapter load. Inference-only16activations/32candidates. One row/prompt recipient+two donor-arm capture bundle in CPU RAM at a time; no generation/backprop/cache state reuse.',
        'cap_rule':'min(1.5F+360,7200) seconds continuously from first warm-up; setup1500 seconds',
        'warmed_gate':'Nine row/prompt forecasts; one discarded warm-up then three timed bundles of three full84-item captures (recipient/opposite/same in matching recipient order) and three timed16-item patches per row/prompt. F sums one three-capture bundle plus every patch unit per row/prompt, with transfer/serialization/fsync/hash. No subset if gate fails.',
        'layer0_parity_gate':'Before production, exact per-pair score equality on first four frozen-stage recipients in every row/prompt and both donor arms, same candidate layout; retained in calibration receipts. Every production layer0 injection unit also must equal its matching-layout full-swap baseline exactly. Failure seals INCOMPLETE, no repair/retry.',
        'assignment_required':{'experiment':'E22','pod_id':'INTEGRATOR_MUST_FILL','gpu_count':1,
            'max_science_seconds':CAP,'setup_allowance_seconds':SETUP,'source_files':sources,**binding,
            'external_hard_stop_verified':True,'hard_deadline_utc':'INTEGRATOR_MUST_FILL_TIMEZONE_AWARE'},
        'launch_argv':['/weights/venv-kernels/bin/python','-m','projects.g_agreement.understand.e22.run',
            '--inputs','STAGED_E22_INPUTS','--assets','PINNED_ASSETS_JSON','--assignment','ASSIGNMENT_JSON','--out','NEW_E22_OUTPUT'],
        'analysis':'Per-item fractions, no clipping/epsilon; undefined denominators explicit and complete-population mean not evaluable. Raw donor-signed asked changes plus all baselines. 2000 template-cluster bootstrap draws, seed20261025. Undefined early/mid/late and control-percentile comparison rules remain descriptive, no invented pass/fail criterion.',
        'operations':'Integrator pushes and operates pods. Stage only sealed E22 worker package, never private labels sidecar. E19 and all prior outputs untouched. Seal before analysis; no implicit retry.',
        'production_scoring_performed':False}
    P.dump(out,receipt);return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','tests','out'):p.add_argument('--'+name,type=Path,required=True)
    receipt=create(**vars(p.parse_args()))
    print(json.dumps({'status':receipt['status'],'source_commit':receipt['source_commit']}))

if __name__=='__main__':main()
