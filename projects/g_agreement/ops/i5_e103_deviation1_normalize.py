"""§221 E103 deviation1 exact sealed pointers; no parsing, calls or analysis."""
from pathlib import Path
import argparse,datetime,json,os,subprocess,sys,hashlib
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.ops.i5_e103_normalize import build,read,write,sha
AUTHORITY='f60fd54fe3400d58d1c07257ad565e8567b23488'
STRICT='413a790896a2a09acf4a2353939b4463be734fc41d4d52fc0d4320a2fba55343'
LABEL='validator-corrected (E103 deviation 1)'

def unchanged_raw(strict,corrected):
    if len(strict)!=1564 or len(corrected)!=1564:raise ValueError('All1564 original terminal responses')
    for a,b in zip(strict,corrected):
        for key in set(a)|set(b):
            if key not in {'status','reason','response'}and a.get(key)!=b.get(key):raise ValueError('Original response metadata/bytes/order changed')
        if a['status']=='KEPT' or a['reason']!='FROZEN_YES_NO_PARSE':
            if a!=b:raise ValueError('Non-parser terminal disposition changed')
        if b['response'] not in ('yes','no','unparseable'):raise ValueError('Sealed exact normalized response')
    return True

def main():
    p=argparse.ArgumentParser();p.add_argument('--judgment-seal',type=Path,required=True);a=p.parse_args()
    root=Path.cwd();base=root/'results/g_agreement/understand/e103';dest=root/'cache/g_agreement/understand/e103/deviation1_normalization_v1'
    assert not dest.exists(),'Never rebuild corrected normalization; inspect partial publication manually'
    # Source and this correction must already be committed before normalization.
    own=Path(__file__).resolve();blob=subprocess.check_output(['git','show','HEAD:'+str(own.relative_to(root))]);assert hashlib.sha256(blob).hexdigest()==sha(own)
    subprocess.check_output(['git','cat-file','-e',AUTHORITY+'^{commit}'])
    strictdir=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E103/judgments')
    assert sha(strictdir/'JUDGMENT_SEAL.json')==STRICT
    s=read(a.judgment_seal);folder=a.judgment_seal.parent
    assert s['bank']=='E103'and s['status']=='COMPLETE_VALIDATOR_CORRECTED_ONCE'and s['label']==LABEL
    assert s['strict_judgment_seal_sha256']==STRICT and s['new_calls']==0
    assert s['route_verified']and s['redaction_audit_complete']and s['all_prompts_unchanged']
    for n,h in s['files'].items():assert sha(folder/n)==h
    correction=read(folder/'CORRECTION_RECEIPT.json');assert correction['new_calls']==correction['new_cost_usd']==0 and correction['strict_analyses_unchanged']and correction['all_other_missing_preserved']
    corrected=read(folder/'RESPONSES.json');unchanged_raw(read(strictdir/'RESPONSES.json'),corrected)
    invpath=base/'analysis/private_inventory/INVENTORY_SEAL.json';inv=read(invpath)
    for n,h in inv['files'].items():assert sha(invpath.parent/n)==h
    inventory=read(invpath.parent/'INVENTORY.json');assert len(inventory)==584
    mapping=read(root/'cache/g_agreement/understand/e103/judge_packet_v1/MAPPING.PRIVATE.json')
    records,used=build(inventory,mapping,corrected);assert len(used)==1168
    extras=[dict(id=x['id'],owner_call_id=x['owner_call_id'],readout_uid=x['readout_uid'],claim_index=x['claim_index'],arm=x['arm'],response_pointer=dict(seal_index=0,member='RESPONSES.json',keys=[i,'response']))for i,v in enumerate(corrected)for x in mapping if x['id']==v['id']and x['id']not in used];assert len(extras)==396
    original_guard=root.parent/'wt-wmech/cache/g_agreement/understand/e103/ANALYSIS_ONCE.json';strict_analysis=base/'analysis/strict_registered_once/ANALYSIS_SEAL.json';before={str(p):sha(p)for p in [original_guard,strict_analysis]}
    dest.mkdir(parents=True);os.chmod(dest,0o700);write(dest/'RECORDS.json',records);write(dest/'EXTRA_RESPONSES.PRIVATE.json',extras)
    write(dest/'DATA_SEAL.json',dict(experiment='E103',status='COMPLETE',label=LABEL,authority_commit=AUTHORITY,inventory_sha256=sha(invpath),route_verified=True,redaction_audit_complete=True,source_seals=[dict(seal=str(a.judgment_seal.resolve()),sha256=sha(a.judgment_seal))],files={n:sha(dest/n)for n in ['RECORDS.json','EXTRA_RESPONSES.PRIVATE.json']},strict_artifacts_unchanged=before))
    invcommit=subprocess.check_output(['git','rev-parse','7a666ced'],text=True).strip()
    spec=dict(experiment='E103',label=LABEL,deviation='E103 deviation 1',authority_commit=AUTHORITY,analysis=str(base/'analysis/validator_corrected_deviation1_once'),inventory=dict(seal=str(invpath),sha256=sha(invpath)),inventory_commit=invcommit,data=dict(seal=str(dest/'DATA_SEAL.json'),sha256=sha(dest/'DATA_SEAL.json')),strict_analysis_seal=dict(path=str(strict_analysis),sha256=sha(strict_analysis)),strict_guard=dict(path=str(original_guard),sha256=sha(original_guard)))
    write(dest/'SPEC.json',spec)
    for q in dest.iterdir():os.chmod(q,0o600)
    assert all(sha(Path(n))==h for n,h in before.items())
    receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),label=LABEL,status='EXACT_CORRECTED_POINTER_NORMALIZATION_READY_NO_ANALYSIS',authority_commit=AUTHORITY,source_judgment_seal=str(a.judgment_seal.resolve()),source_judgment_seal_sha256=sha(a.judgment_seal),validator_fix_commit=s['validator_fix_commit'],inventory_commit=invcommit,primary_claims=584,primary_pointers=1168,all_claims=782,all_calls=1564,extra_pointers_retained=396,DATA_SEAL_sha256=sha(dest/'DATA_SEAL.json'),SPEC_sha256=sha(dest/'SPEC.json'),private_directory=str(dest),strict_artifacts_unchanged=before,source_code_sha256=sha(own),new_paid_calls=0,parser_runs_by_normalizer=0,analysis_runs=0)
    write(base/'I5_DEVIATION1_NORMALIZATION_RECEIPT.json',receipt);print('Corrected sealed pointers normalized once; no parser/calls/statistics/guard touched')
if __name__=='__main__':main()
