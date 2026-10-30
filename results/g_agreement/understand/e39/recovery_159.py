"""Validate50 original runs +4 authorised B reruns without rewriting source receipts."""
from pathlib import Path
import math
import contract as C
import rerun_159 as R
from analyze import validate_operational_gates

def original_runs(slot):return C.assigned_runs(slot,6)
def retained_runs(slot):return [r for r in original_runs(slot) if r not in R.scope()['rerun_runs']]

def verify_selected_pull(directory,digest,excluded=()):
    directory=Path(directory).resolve();manifest=directory/'PULL_SUMS'
    if C.sha(manifest)!=digest:raise ValueError('transfer manifest digest differs')
    excluded={str(row)+'__'+str(arm) for row,arm in excluded}
    def ignored(n):return len(Path(n).parts)>=2 and Path(n).parts[0]=='out' and Path(n).parts[1] in excluded
    files={}
    for line in manifest.read_text().splitlines():
        h,n=line.split(maxsplit=1);n=n.removeprefix('*').removeprefix('./');path=(directory/n).resolve()
        if (len(h)!=64 or any(c not in '0123456789abcdef' for c in h) or n in files or not path.is_relative_to(directory)):
            raise ValueError('invalid transfer record')
        files[n]=h
        if not ignored(n) and (not path.is_file() or C.sha(path)!=h):raise ValueError('retained transfer file missing or altered')
    actual={p.relative_to(directory).as_posix() for p in (directory/'out').rglob('*') if p.is_file() and not ignored(p.relative_to(directory).as_posix())}
    expected={n for n in files if n.startswith('out/') and not ignored(n)}
    if not expected or actual!=expected:raise ValueError('transfer does not cover all retained outputs')
    return {'pull_sums_sha256':digest,'verified_retained_files':len(expected),'excluded_partial_runs':sorted(excluded)}

def collect(input_dir,outputs):
    if len(outputs)!=7:raise ValueError('six original pulls and one rerun pull required')
    input_dir=Path(input_dir);outputs=list(map(Path,outputs));R.check_sources();C.verify(input_dir)
    if C.sha(input_dir/'INPUT_SEAL.json')!=R.scope()['input_seal_sha256']:raise ValueError('exact bound-v2 input required')
    reroot=outputs[-1];ra=C.read(reroot/'assignment.json');ledger=R.bind_ledger(ra,reroot/'PRIOR_CUSTODY_159.json',now=ra['provider_created_epoch'])
    context=C.read(reroot/'RERUN_CONTEXT_159.json')
    if (context.get('scope_sha256')!=C.sha(R.SCOPE) or context.get('rerun_source_manifest_sha256')!=C.sha(R.MANIFEST)
            or context.get('prior_custody_sha256')!=C.sha(reroot/'PRIOR_CUSTODY_159.json')
            or context.get('runs')!=R.scope()['rerun_runs'] or context.get('original_worker_unchanged') is not True):
        raise ValueError('rerun authority/source/custody context mismatch')
    directories={}
    for i,root in enumerate(outputs):
        a=C.read(root/'assignment.json');r=C.read(root/'RUN_RECEIPT.json')
        if i<6:
            old=R.scope()['original_pods'][i]
            if (C.sha(root/'assignment.json')!=old['assignment_sha256'] or C.sha(root/'RUN_RECEIPT.json')!=old['run_receipt_sha256']
                    or a['slot']!=i or a['pod_id']!=old['pod_id'] or a['pod_count']!=6):raise ValueError('original receipts must remain byte-identical')
            C.assignment(a,now=a['provider_created_epoch']);runs=retained_runs(i)
            if r['runs']!=original_runs(i):raise ValueError('original full assignment receipt changed')
            for lost in R.scope()['rerun_runs']:
                if (root/('__'.join(lost))/'SCORE_SEAL.json').exists():raise ValueError('lost run became recoverable; stop and reconcile, never choose by score')
        else:
            runs=R.scope()['rerun_runs']
            if r['runs']!=runs:raise ValueError('rerun must cover exactly four lost B runs')
        if (a.get('source_manifest_sha256')!=R.scope()['original_source_manifest_sha256']
                or a.get('input_seal_sha256')!=C.sha(input_dir/'INPUT_SEAL.json')
                or r.get('status')!='COMPLETE_FULL_ASSIGNED_GRID' or r.get('plan_sha256')!=C.sha(C.HERE/'PLAN.json')
                or r.get('previous_gpu_seconds')!=a['previous_gpu_seconds']
                or type(r.get('gpu_seconds_provider')) not in (int,float) or not math.isfinite(r['gpu_seconds_provider'])
                or not 0<=r['gpu_seconds_provider']<=a['allocated_gpu_seconds']):raise ValueError('complete same-science run and custody required')
        validate_operational_gates(root,r,a)
        if r.get('item_execution_audit_sha256')!=C.sha(root/'ITEM_EXECUTION_AUDIT.jsonl'):raise ValueError('execution audit changed')
        for row,arm in runs:
            key=(row,arm);folder=root/(row+'__'+arm)
            if key in directories:raise ValueError('duplicate run source')
            C.verify(folder,'SCORE_SEAL.json');directories[key]=folder
    if set(directories)!=set(C.RUNS) or ledger['total_gpu_seconds']+ra['allocated_gpu_seconds']>C.CAP:
        raise ValueError('complete unique54run grid within cumulative cap required')
    return directories

def receipt_preflight(request,receipt):
    if (receipt.get('issuer')!='integrator' or receipt.get('experiment')!='E39'
            or receipt.get('schema')!='E39_VERIFIED_RECOVERY_PULLS_159_v1'
            or receipt.get('status')!='VERIFIED_COMPLETE' or receipt.get('production_complete') is not True
            or receipt.get('original_pod_count')!=6 or receipt.get('rerun_pod_count')!=1
            or receipt.get('input_seal_sha256')!=R.scope()['input_seal_sha256']):raise ValueError('truthful full-grid verified recovery receipt required')
    entries=receipt.get('pulls',[])
    if len(entries)!=7 or [x['pull_id'] for x in entries]!=[f'original_slot{i}' for i in range(6)]+['rerun_159']:
        raise ValueError('exact original and rerun pull references required')
    roots=[];proofs=[];expected_map={}
    for i,entry in enumerate(entries):
        relative=request['pull_directories'][i]
        runs=retained_runs(i) if i<6 else R.scope()['rerun_runs']
        excluded=[r for r in original_runs(i) if r not in runs] if i<6 else []
        if entry.get('directory')!=relative or entry.get('selected_runs')!=runs:raise ValueError('fixed provenance selection differs')
        directory=C.ROOT/relative
        proofs.append({'pull_id':entry['pull_id'],**verify_selected_pull(directory,entry['pull_sums_sha256'],excluded)})
        root=directory/'out';roots.append(root)
        if C.read(root/'assignment.json')['pod_id']!=entry.get('pod_id'):raise ValueError('pull pod identity differs')
        for row,arm in runs:
            expected_map[row+'__'+arm]={'pull_id':entry['pull_id'],'score_seal_sha256':C.sha(root/(row+'__'+arm)/'SCORE_SEAL.json')}
    if receipt.get('run_sources')!=expected_map:raise ValueError('every one of54runs needs its unique source pull and seal hash')
    return roots,proofs
