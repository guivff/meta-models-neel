"""E103 exact sealed response pointers; never reinterpret or repair a response."""
from pathlib import Path
import json,hashlib,sys,datetime,subprocess,shutil,os

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
def build(inventory,mapping,responses):
    indexes={x['id']:i for i,x in enumerate(responses)}
    if len(indexes)!=len(responses):raise ValueError('Duplicate terminal response')
    calls={}
    for x in mapping:
        k=(x['readout_uid'],x['claim_index'],x['arm'])
        if k in calls or x['id']not in indexes:raise ValueError('Duplicate/missing exact claim arm')
        calls[k]=x
    rows=[];used=set()
    for meta in inventory:
        index=int(meta['claim_id'].rsplit(':',1)[1]);fields={}
        for arm in ('own','mismatched'):
            x=calls[(meta['readout_id'],index,arm)];used.add(x['id'])
            fields[arm+'_response']=dict(seal_index=0,member='RESPONSES.json',keys=[indexes[x['id']],'response'])
        rows.append(dict(id=meta['id'],metadata=meta,measurements=fields))
    return rows,used

def main():
    root=Path.cwd();base=root/'results/g_agreement/understand/e103';private=root/'cache/g_agreement/understand/e103/strict_normalization_v1';assert not(private/'DATA_SEAL.json').exists()
    owner=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/funded_queue/E103/judgments');s=read(owner/'JUDGMENT_SEAL.json')
    assert s['bank']=='E103'and s['route_verified']is True and s['redaction_audit_complete']is True and s['all_prompts_unchanged']is True
    for n,h in s['files'].items():assert sha(owner/n)==h
    responses=read(owner/'RESPONSES.json');assert len(responses)==1564 and all(x['status']=='UNPARSEABLE'and x['response']=='unparseable'for x in responses)
    mapping=read(root/'cache/g_agreement/understand/e103/judge_packet_v1/MAPPING.PRIVATE.json')
    invseal=base/'analysis/private_inventory/INVENTORY_SEAL.json';inv=read(invseal)
    for n,h in inv['files'].items():assert sha(invseal.parent/n)==h
    inventory=read(invseal.parent/'INVENTORY.json');assert len(inventory)==584
    records,used=build(inventory,mapping,responses);assert len(used)==1168
    private.mkdir(parents=True,exist_ok=True);os.chmod(private,0o700);write(private/'RECORDS.json',records)
    extra=[dict(id=x['id'],owner_call_id=x['owner_call_id'],readout_uid=x['readout_uid'],claim_index=x['claim_index'],arm=x['arm'],response_pointer=dict(seal_index=0,member='RESPONSES.json',keys=[i,'response']))for i,v in enumerate(responses)for x in mapping if x['id']==v['id']and x['id']not in used];assert len(extra)==396;write(private/'EXTRA_RESPONSES.PRIVATE.json',extra)
    write(private/'DATA_SEAL.json',dict(experiment='E103',status='COMPLETE',inventory_sha256=sha(invseal),route_verified=True,redaction_audit_complete=True,source_seals=[dict(seal=str(owner/'JUDGMENT_SEAL.json'),sha256=sha(owner/'JUDGMENT_SEAL.json'))],files={'RECORDS.json':sha(private/'RECORDS.json'),'EXTRA_RESPONSES.PRIVATE.json':sha(private/'EXTRA_RESPONSES.PRIVATE.json')},strict_frozen_parser_no_punctuation_repair=True))
    commit=subprocess.check_output(['git','rev-parse','7a666ced'],text=True).strip();spec=dict(experiment='E103',analysis=str(base/'analysis/strict_registered_once'),inventory=dict(seal=str(invseal),sha256=sha(invseal)),inventory_commit=commit,data=dict(seal=str(private/'DATA_SEAL.json'),sha256=sha(private/'DATA_SEAL.json')));write(private/'SPEC.json',spec)
    for p in private.iterdir():os.chmod(p,0o600)
    receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='STRICT_SEALED_POINTER_NORMALIZATION_READY_NO_ANALYSIS',source_judgment_seal_sha256=sha(owner/'JUDGMENT_SEAL.json'),inventory_commit=commit,inventory_sha256=sha(invseal),all_claims=782,all_calls=1564,primary_inventory_claims=584,primary_response_pointers=1168,extra_claim_responses_retained=396,all_unparseable=True,raw_response_values_unchanged=True,punctuation_not_stripped=True,no_paid_retry=True,no_analysis_guard_touched=True,private_directory=str(private),data_seal_sha256=sha(private/'DATA_SEAL.json'),SPEC_sha256=sha(private/'SPEC.json'),source_code_sha256=sha(Path(__file__)))
    write(base/'I5_STRICT_NORMALIZATION_RECEIPT.json',receipt);print('All sealed responses verified; exact pointers normalized, strict punctuation failures preserved; NO analysis run')
if __name__=='__main__':main()
