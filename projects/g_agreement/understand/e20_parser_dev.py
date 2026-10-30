"""Base-only parser validation acquisition. No activations or lens calls allowed."""
import argparse,json,os,signal,time,statistics,math
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P,run as W

def run(a):
    import torch
    q=json.loads(a.assignment.read_text());plan=json.loads(a.plan.read_text())
    if (q.get('issuer')!='integrator' or q.get('experiment')!='E20_PARSER_DEV' or q.get('pod_id')!=os.environ.get('RUNPOD_POD_ID')
        or q.get('plan_sha256')!=P.sha(a.plan) or q.get('item_commit')!=plan['item_commit']
        or q.get('external_hardstop_verified') is not True or q.get('items_published') is not True):raise ValueError('bound integrator assignment required')
    import sys
    if sys.prefix!='/weights/venv-kernels':raise ValueError('must use /weights/venv-kernels')
    used=float(q['previous_science_seconds']);setup_used=float(q['previous_setup_seconds'])
    if used<0 or setup_used<0 or used>=7200 or setup_used>=2400:raise ValueError('shared E20 budget exhausted')
    absolute=float(q['deadline_epoch'])-180;end=min(float(q['provider_created_epoch'])+2400-setup_used,absolute)
    def check():
        if time.time()>=end:raise TimeoutError('E20 parser-dev deadline')
        signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    def expired(*_):raise TimeoutError('E20 parser-dev deadline')
    old=signal.signal(signal.SIGALRM,expired);first=None;a.out.mkdir(parents=True,exist_ok=False)
    try:
        check();P.verify(a.bank,'INPUT_SEAL.json');W._labels_absent(a.bank)
        if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('bank mismatch')
        lookup={x['id']:x for x in P.rows(a.bank/'items.input.jsonl')}
        for name,h in plan['source_files'].items():
            if P.sha(P.ROOT/name)!=h:raise ValueError('source mismatch: '+name)
        from transformers import AutoModelForCausalLM,AutoTokenizer
        assets=W._assets(a.assets,names=('model',));W._offline()
        tok=AutoTokenizer.from_pretrained(assets['model'],local_files_only=True)
        model=AutoModelForCausalLM.from_pretrained(assets['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
        def generate(rec):
            check();x=lookup[rec['item_id']]
            if x['split']!='dev':raise ValueError('parser validation must use dev')
            torch.manual_seed(rec['seed']);torch.cuda.manual_seed_all(rec['seed'])
            ids=torch.tensor([x['ids']],device='cuda');mask=torch.ones_like(ids)
            with torch.inference_mode():out=model.generate(input_ids=ids,attention_mask=mask,do_sample=True,temperature=1.,top_p=1.,top_k=0,max_new_tokens=16,pad_token_id=tok.pad_token_id or tok.eos_token_id)
            new=out[0,len(x['ids']):].tolist()
            return {**rec,'generated_ids':new,'text':tok.decode(new,skip_special_tokens=True,clean_up_tokenization_spaces=False)}
        # Unretained setup warmup; all 240 prescribed production records retained once.
        generate(plan['records'][0]);check();first=time.time();end=min(first+7200-used,absolute)
        P.dump(a.out/'CLOCK.json',{'first_science_epoch':first,'previous_science_seconds':used})
        rows=[];times=[]
        for rec in plan['records']:
            check();torch.cuda.synchronize();start=time.perf_counter();rows.append(generate(rec));torch.cuda.synchronize();times.append(time.perf_counter()-start)
            with (a.out/'generations.partial.jsonl').open('a') as f:f.write(json.dumps(rows[-1])+'\n');f.flush()
            if len(rows)==3:
                F=time.time()-first+statistics.median(times)*237
                allocated=min(1.5*F+360,7200-used);end=min(end,first+allocated)
                P.dump(a.out/'FORECAST.json',{'parser_phase_F':F,'phase_allocation':allocated,'full_E20_F':'pending later full worker; these costs must be carried forward','timed_results_retained':True})
                if F>allocated:raise TimeoutError('parser phase NO_FIT; no retries or scope cuts')
        if len(rows)!=240:raise ValueError('incomplete validation sample')
        P.jsonl(a.out/'generations.jsonl',rows)
        P.dump(a.out/'PROVENANCE.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'assignment_sha256':P.sha(a.assignment),'base_only':True,'source_capture':False,'lens_calls':0})
        P.dump(a.out/'GENERATION_SEAL.json',{'status':'E20_BASE_DEV_GENERATIONS_SEALED_BEFORE_HAND_CHECK','files':{n:P.sha(a.out/n) for n in ('generations.jsonl','PROVENANCE.json','CLOCK.json','FORECAST.json')}})
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','error':str(exc),'retry_authorized':False});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        P.dump(a.out/'RECEIPT.json',{'science_seconds':0 if first is None else time.time()-first,'previous_science_seconds':used,'setup_seconds':(first if first is not None else time.time())-float(q['provider_created_epoch']),'carry_forward_required':True,'parser_validated':False})

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('bank','plan','assignment','assets','out'):p.add_argument('--'+name,type=Path,required=True)
    run(p.parse_args())
