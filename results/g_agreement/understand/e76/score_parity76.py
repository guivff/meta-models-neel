"""Integrator CPU-only W1 parity adjudication; emits PASS release only on unchanged gate."""
import json,time
from common76 import *
from parity76 import ROWS,ORIGINAL_SEAL

THRESHOLD=.02


def adjudicate(records,key):
    labels=key['labels'];reference=key['reference'];items=key['items']
    require(reference['rows']==list(ROWS) and reference['status']=='FROZEN','Original parity reference')
    require(len(records)==len({x['id'] for x in records})==len(labels)==len(items)==252
        and {x['id'] for x in records}==set(labels)=={x['id'] for x in items},'Complete parity grid')
    rows={x['id']:x['feature'] for x in items};cells={}
    require(all(set(x)=={'id','feature','scores'} and x['feature']==rows[x['id']] for x in records),'Exact parity record identity')
    require(all(type(x) is int and x in (0,1) for x in labels.values()),'Binary CPU labels')
    for row in ROWS:
        group=[x for x in records if x['feature']==row]
        require(len(group)==84 and all(len(x['scores'])==2 and all(type(v) in (int,float) and math.isfinite(v) for v in x['scores']) for x in group),'Complete finite parity row')
        positive=[sum(x['scores'])/2 for x in group if labels[x['id']]==1]
        negative=[sum(x['scores'])/2 for x in group if labels[x['id']]==0]
        require(len(positive)==len(negative)==42,'Balanced original parity row')
        auc=sum((a>b)+.5*(a==b) for a in positive for b in negative)/(42*42)
        ref=reference['reference_auc'][row]
        require(type(ref) in (int,float) and math.isfinite(ref) and 0<=ref<=1,'Finite reference AUROC')
        cells[row]={'n':84,'observed':auc,'reference':ref,'absolute_delta':abs(auc-ref),'threshold':THRESHOLD}
    return {'status':'PASS' if all(x['absolute_delta']<=THRESHOLD for x in cells.values()) else 'FAIL',
        'rows':cells,'authority':'BRIEF_UNDERSTAND section137,1721470e','parity_input_seal_sha256':ORIGINAL_SEAL,
        'production_items_scored_before_gate':0,'recipe':'W1 block44 stored activations; original Oracle backend; mean of two raw A-minus-B log-odds',
        'capture_parity_certified':False}


def main():
    require(__import__('os').environ.get('CUDA_VISIBLE_DEVICES')=='','CPU-only invocation required')
    verify(ROOT,read(HERE/'CPU_SOURCE_SEAL.json'));verify(ROOT,read(HERE/'COMMAND_SEAL.json'))
    request=read(HERE/'LAUNCH_REQUEST.json');binding=read(HERE/'PARITY_BINDING.20261027.json')
    key_path=ROOT/binding['CPU_only_key'];require(sha(key_path)==binding['CPU_only_key_sha256'],'CPU key pin');key=read(key_path)
    require(key['CPU_only'] is True and key['pod_staging_forbidden'] is True and key['original_input_seal_sha256']==ORIGINAL_SEAL,'CPU private custody')
    pull=CACHE/'parity-verified-pull';out=pull/'final';receipt=read(pull/'VERIFIED_PULL.json')
    require(receipt.get('issuer')=='integrator' and receipt.get('experiment')=='E76_PARITY' and receipt.get('verified_complete') is True
        and receipt['output_seal_sha256']==sha(out/'OUTPUT_SEAL.json'),'Verified parity pull required')
    seal=read(out/'OUTPUT_SEAL.json');verify(out,seal)
    require(seal['experiment']=='E76_PARITY' and seal['status']=='GENERATED_UNSCORED','Complete unscored generation required')
    c=read(out/'CUSTODY.json');a=c['assignment']
    require(c['request_sha256']==a['request_sha256']==sha(HERE/'LAUNCH_REQUEST.json') and c['source_seal_sha256']==a['source_seal_sha256']==request['source_seal_sha256']
        and c['parity_input_seal_sha256']==key['parity_input_seal_sha256']==request['parity_input_seal_sha256']
        and c['assets_manifest_sha256']==a['assets_manifest_sha256'],'Exact generation pins')
    require(a['pod_id']==receipt['pod_id'] and a['issuer']=='integrator' and a['main_integrator_admitted'] is True
        and a['gpu_count']==1 and a['track']=='Q' and 0<a['allocated_stage_seconds']<=CAP
        and a['stage_started_epoch']<=c['completed_epoch']<=a['absolute_deadline_epoch']
        <=min(a['stage_started_epoch']+a['allocated_stage_seconds'],a['provider_lease_deadline_epoch'],STOP),'Same admitted pod/stage cap')
    expected={str(p.relative_to(HERE)):sha(p) for p in (HERE/'vendor/mats/readers/olens.py',HERE/'vendor/mats/readers/nla.py',HERE/'native_nla512.py')}
    require(c['native_code_sha256']==expected,'Native code correspondence')
    target=CACHE/'parity-cpu-20261027';target.mkdir(exist_ok=False)
    dump(target/'SCORE.RUN_ONCE.json',{'started_epoch':time.time(),'generation_output_seal_sha256':sha(out/'OUTPUT_SEAL.json')})
    records=[json.loads(line) for line in (out/'PARITY_SCORES.jsonl').read_text().splitlines()]
    result=adjudicate(records,key);result['raw_scores_sha256']=sha(out/'PARITY_SCORES.jsonl');dump(target/'PARITY_RESULT.json',result)
    if result['status']=='PASS':
        dump(target/'PARITY_RELEASE.json',{'issuer':'integrator','pod_id':a['pod_id'],'status':'PASS','same_pod_verified':True,
            'native_backend_unchanged':True,'native_code_sha256':expected,'assets_manifest_sha256':a['assets_manifest_sha256'],
            'parity_result_sha256':sha(target/'PARITY_RESULT.json'),'raw_scores_sha256':sha(out/'PARITY_SCORES.jsonl'),
            'parity_generation_output_seal_sha256':sha(out/'OUTPUT_SEAL.json'),'parity_input_seal_sha256':key['parity_input_seal_sha256']})
    dump(target/'CPU_PARITY_SEAL.json',{'experiment':'E76_PARITY','status':result['status'],'files':{p.name:sha(p) for p in sorted(target.iterdir())}})
    require(result['status']=='PASS','W1 parity failed: stop; no retry or production release')
    print('CPU W1 parity PASS; sealed same-pod release ready')


if __name__=='__main__':main()
