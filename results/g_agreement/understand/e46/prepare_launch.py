"""Bind E46 frozen bank and create a label-free acquisition archive."""
from io46 import *
import tarfile

def prepare():
    verify(HERE,'BANK_SEAL.json')
    names=['worker46.py','io46.py','states.py','check_long.py','persistence_once.py','prepare_launch.py','test_author.py','test_runtime.py','BANK_SEAL.json','BANK_SOURCE_SEAL.json','ROW_DEFINITIONS.json','CANDIDATES.json','STATE_FUNCTION_SEAL.json','VALIDATION.json']
    source_files={str((HERE/n).relative_to(ROOT)):sha(HERE/n) for n in names}
    plan={'experiment':'E46','stage':'GREEDY_CONTINUATION_BEFORE_READER_SCORES','items':336,'split':'test','tokens_per_item':32,'seed':20261026,'aggregate_experiment_cap_seconds':10800,'acquisition_cap_seconds':1800,'input_seal_sha256':sha(HERE/'cache/prepared/INPUT_SEAL.json'),'state_seal_sha256':sha(HERE/'STATE_FUNCTION_SEAL.json'),'bank_seal_sha256':sha(HERE/'BANK_SEAL.json'),'source_files':source_files,'cold_batch_forecast':'charged but excluded from warmed mean','following_text_source':'model-expected continuation; not authored suffix'}
    dump(HERE/'RUN_PLAN.json',plan)
    dump(HERE/'CODE_SEAL.json',{'complete':True,'files':{n:sha(HERE/n) for n in names+['RUN_PLAN.json']}})
    archive=HERE/'cache/E46_ACQUISITION.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:
        for name in names+['RUN_PLAN.json','CODE_SEAL.json']:
            tar.add(HERE/name,arcname=str((HERE/name).relative_to(ROOT)))
        for name in ['prefixes.jsonl','INPUT_SEAL.json']:
            tar.add(HERE/'cache/prepared'/name,arcname='e46_stage/'+name)
    dump(HERE/'STAGING_ARCHIVE.json',{'path':str(archive),'sha256':sha(archive),'private_labels_in_archive':False,'contents':'operational code, public seals, label-free test token IDs; no private item/source-suffix file'})
    request={'experiment':'E46','status':'READY_CONTINUATION_ACQUISITION_ONLY_READERS_HELD','plan_sha256':sha(HERE/'RUN_PLAN.json'),'bank_seal_sha256':sha(HERE/'BANK_SEAL.json'),'state_seal_sha256':sha(HERE/'STATE_FUNCTION_SEAL.json'),'aggregate_cap_seconds':10800,'acquisition_cap_seconds':1800,'previous_E46_gpu_seconds_required':0,'items':336,'tokens_per_item':32,'reader_channels':['probe','Oracle asked','NLA asked'],'readers_held_until':['PERSISTENCE_SEAL.json verified and row eligibility published','full 252-item E36 W1 parity gate passed at |delta AUROC|<=0.02','reader plan binds exact bank, candidates, persistence and cumulative GPU budget'],'worker_argv':['python','results/g_agreement/understand/e46/worker46.py','--plan','results/g_agreement/understand/e46/RUN_PLAN.json','--stage','e46_stage','--assignment','INTEGRATOR_ASSIGNMENT.json','--assets','VERIFIED_BASE_ASSETS.json','--out','NEW_OUTPUT_DIRECTORY'],'assignment_required':['issuer=integrator','experiment=E46','pod_id=RUNPOD_POD_ID','plan_sha256','assets_manifest_sha256','previous_gpu_seconds=0','external_hardstop_verified=true','state_functions_committed=true','source_published=true','provider_created_epoch','deadline_epoch <= provider_created_epoch + 1800'],'no_push_or_GPU_by_worker_chat':True}
    # Replaces the explicit unlaunched preparation hold, never a scientific seal.
    (HERE/'LAUNCH_REQUEST.json').write_text(json.dumps(request,indent=2,sort_keys=True)+'\n')
    print('Ready acquisition plan',sha(HERE/'RUN_PLAN.json'))
if __name__=='__main__':prepare()
