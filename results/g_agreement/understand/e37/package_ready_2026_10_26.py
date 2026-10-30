"""Freeze clarification-3 operational handoff; no model call or launch."""
from pathlib import Path
import importlib.util
import json
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
PREFIX='results/g_agreement/understand/e37/'
CACHE=ROOT/'cache/g_agreement/understand'
spec=importlib.util.spec_from_file_location('e37_package_old',HERE/'package.py')
P=importlib.util.module_from_spec(spec);spec.loader.exec_module(P)
read,sha,dump=P.read,P.sha,P.dump

def main():
    old=read(HERE/'SOURCE_MANIFEST.json')
    pins=dict(old['source_files']);pins.pop('results/g_agreement/understand/e33/runtime.py',None)
    for n,h in pins.items():
        if not n.startswith(PREFIX) and sha(ROOT/n)!=h:raise ValueError('non-E37 frozen dependency drift: '+n)
    names=set(pins)|{str(p.relative_to(ROOT)) for p in HERE.glob('*.py')}
    names|={PREFIX+n for n in ('CHECKPOINT_MANIFEST_2026-10-26.json','ANALYSIS_REQUEST_2026-10-26.json',
        'OWNER_READING_2026-10-26.md','HANDOFF_2026-10-26.md','CPU_VALIDATION_2026-10-26.json','CPU_IDENTITY_EVIDENCE_2026-10-26.json')}
    names|={'results/g_agreement/understand/e33/analysis_2026-10-26/'+n for n in ('ANALYSIS_SEAL.json','metrics.json','RESULTS.md')}
    names.add('results/g_agreement/understand/e28/analysis_2026-10-26/METRICS.json')
    pins={n:sha(ROOT/n) for n in sorted(names)}
    archive=CACHE/'e37-source-v2.tar.gz';P.archive(archive,{n:ROOT/n for n in pins})
    manifest={**old,'source_files':pins,'source_archive':str(archive.relative_to(ROOT)),'source_archive_sha256':sha(archive)}
    dump(HERE/'SOURCE_MANIFEST.json',manifest)
    assignment=read(HERE/'ASSIGNMENT.template.json');assignment['source_files']=pins
    dump(HERE/'ASSIGNMENT.template.json',assignment)
    request=read(HERE/'LAUNCH_REQUEST.json')
    command=('python results/g_agreement/understand/e37/runtime.py run --inputs cache/g_agreement/understand/e37-inputs-v1 '
        '--assets VERIFIED_ASSETS.json --checkpoint-receipt CHECKPOINT_RECEIPT.json --predecessors PREDECESSORS.json '
        '--parity-gate results/g_agreement/understand/e37/PARITY_GATE.json --assignment ASSIGNMENT.json '
        '--out cache/g_agreement/understand/e37-run-v2')
    request.update(manifest);request.update(schema='E37_LAUNCH_REQUEST_v2',date='2026-10-26',status='READY',
        checkpoint_clarification_commit='be450eb9',source_manifest_sha256=sha(HERE/'SOURCE_MANIFEST.json'),
        checkpoint_manifest=PREFIX+'CHECKPOINT_MANIFEST_2026-10-26.json',
        checkpoint_manifest_sha256=sha(HERE/'CHECKPOINT_MANIFEST_2026-10-26.json'),
        checkpoint_manifest_key='olens_s3d_student_step251',
        cpu_checkpoint_command='python results/g_agreement/understand/e37/checkpoint_cpu.py --hf-dir STAGED_STEP251_PATH --out cache/g_agreement/understand/e37-checkpoint-v2 --received-epoch ACTUAL_CHECKPOINT_RECEIVED_EPOCH',
        staged_checkpoint_path='Integrator supplies --hf-dir at launch; selected local_path and exact file hashes are bound by CHECKPOINT_RECEIPT.json and assignment',
        cpu_tensor_check='REQUIRED before any model forward; match => lora_hf, differ => original lora tensors, anonymous download unavailable => lora_hf_UNVERIFIED; corrupt bytes STOP',
        local_cpu_result=read(HERE/'CPU_IDENTITY_EVIDENCE_2026-10-26.json'),
        optional_descriptive_arm='omitted',worker_command=command,
        validate_command=command.replace('runtime.py run','runtime.py validate').split(' --out ')[0],
        analysis_command='python results/g_agreement/understand/e37/analysis_once_2026_10_26.py',
        analysis_request=PREFIX+'ANALYSIS_REQUEST_2026-10-26.json',
        validation=read(HERE/'CPU_VALIDATION_2026-10-26.json'),
        limitations=['Anonymous original lora download returned HTTP 401; README tensor identity remains unverified',
                     'No real GPU parity or warmed forecast has run; these remain launch gates'])
    request['global_operations']['programme_deadline_utc']='2026-10-29T22:59:00Z'
    request['release_gate']=[
        'Pinned HF checkpoint staged; anonymous single-file CPU comparison receipt and selected bytes frozen before any forward',
        'E33 and E28 complete or closed with verified predecessor receipts',
        'Published source hashes, bound assignment and external hardstop verified',
        'RL600 three-row W1 AUROC parity first, then RL and SFT smoke; any parity failure stops without retry',
        'All eight warmed paths admit the complete original scope within 5400 provider seconds']
    dump(HERE/'LAUNCH_REQUEST.json',request)
    # Seal all analysis/runtime sources plus exact request and source manifest.
    sealed={**pins,**{PREFIX+n:sha(HERE/n) for n in ('SOURCE_MANIFEST.json','LAUNCH_REQUEST.json','ASSIGNMENT.template.json')}}
    dump(HERE/'ANALYSIS_CODE_SEAL_2026-10-26.json',{'schema':'E37_ANALYSIS_CODE_SEAL_v1','files':sealed})
    print(json.dumps({'status':'READY','source_archive_sha256':sha(archive),'file_count':len(pins)}))

if __name__=='__main__':main()
