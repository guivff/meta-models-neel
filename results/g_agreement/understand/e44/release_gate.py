"""Read-only release evidence: E39 reached sealed step0/25, never an E39 analysis."""
from pathlib import Path
import math
import contract as C
from e39_gate_frozen import validate_operational_gates

def verify_progress(root,row,bound_input):
    root,bound_input=Path(root),Path(bound_input)
    a=C.read(root/'assignment.json')
    if (a.get('experiment')!='E39' or not a.get('pod_id')
            or [row,'L'] not in a['runs']
            or a.get('source_manifest_sha256')!='7988652a885bc68dff170a6df568f8a8a35c3d1ea829d6c01f88c514b1968014'
            or a.get('input_seal_sha256')!=C.plan()['e39_bound_input_seal_sha256']
            or C.sha(bound_input/'INPUT_SEAL.json')!=a['input_seal_sha256']):
        raise ValueError('original E39 assigned input/source required')
    C.verify(bound_input)
    fields={'TRAINING_ENVIRONMENT.json':'environment_manifest_sha256','ENVIRONMENT_RUNTIME_RESULT.json':'environment_runtime_result_sha256','PARITY_RESULT.json':'parity_result_sha256','PARITY_SCORES.jsonl':'parity_scores_sha256'}
    receipt={k:C.sha(root/n) for n,k in fields.items()}|{'parity_input_seal_sha256':a['parity_input_seal_sha256']}
    validate_operational_gates(root,receipt,a)
    expected={r['id'] for r in C.rows(bound_input/'test.jsonl') if r['feature']==row}
    if len(expected)!=84:raise ValueError('complete release reference row required')
    files={n:C.sha(root/n) for n in [*fields,'PARITY_REFERENCE.json','assignment.json']}
    for step in (0,25):
        folder=root/(row+'__L');C.verify(folder,f'CHECKPOINT_{step}.json')
        records=C.rows(folder/f'asked.{step}.jsonl')
        if (len(records)!=84 or {r['id'] for r in records}!=expected
                or any(len(r['scores'])!=2 or not all(math.isfinite(v) for v in r['scores']) for r in records)):
            raise ValueError('finite complete step0 and step25 checkpoints required')
        for n in (f'CHECKPOINT_{step}.json',f'asked.{step}.jsonl'):files[row+'__L/'+n]=C.sha(folder/n)
    return {'status':'E39_STEP25_VERIFIED','experiment':'E44','prerequisite':'E39','pod_id':a['pod_id'],
        'row':row,'steps':[0,25],'files':files,'e39_input_seal_sha256':a['input_seal_sha256'],
        'e39_source_manifest_sha256':a['source_manifest_sha256'],'scores_interpreted':False,'e39_analysis_invocations':0}

def verify_release_receipt(path):
    r=C.read(path);frozen=C.read(C.HERE/'E39_RELEASE_GATE_2026-10-26.json')
    if r!=frozen or r.get('status')!='E39_STEP25_VERIFIED':raise ValueError('bound verified E39 step25 release required')
    return r
