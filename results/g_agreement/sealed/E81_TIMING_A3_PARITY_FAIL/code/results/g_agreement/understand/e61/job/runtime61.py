"""E61 acquisition extension, pending binding to W-text's frozen token positions."""
import json,sys,time
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'e56/job'))
from worker56 import Backend
from contract56 import read,dump,seal,require


def position_jobs(items):
    jobs=[]
    for item in items:
        ids=item['ids']
        if item['display']=='D3':
            start=item['instruction_end_index'];end=item['pre_answer_index']
            require(type(start) is int and type(end) is int and 0<=start<=end<len(ids),'inclusive D3 position bounds')
            positions=range(start,end+1)
        else:
            require(item['display']=='D4','registered new-compute display')
            require(type(item['read_index']) is int and 0<=item['read_index']<len(ids),'D4 read position')
            positions=[item['read_index']]
        for pos in positions:
            jobs.append({'id':item['id']+':position:'+str(pos),'item_id':item['id'],'display':item['display'],'arm':item['arm'],'pair_id':item['pair_id'],'position':pos,'relative_position':pos-item.get('instruction_end_index',pos),'ids':ids[:pos+1]})
    require(len({x['id'] for x in jobs})==len(jobs),'unique position IDs')
    return jobs


def base_answer_probability(backend,item):
    import torch
    ids=item['completion_ids'];answer=item['answer_token_id']
    require(ids and type(answer) is int and answer>=0,'frozen completion and answer ID')
    device=backend.oracle.model.get_input_embeddings().weight.device
    tokens=torch.tensor([ids],device=device)
    with backend.oracle.base(),torch.no_grad():
        logits=backend.oracle.model(input_ids=tokens,attention_mask=torch.ones_like(tokens),use_cache=False).logits[0,-1].float()
        require(answer<len(logits),'answer token in vocabulary')
        probability=torch.softmax(logits,dim=-1)[answer].item()
    require(np.isfinite(probability) and 0<=probability<=1,'base probability')
    return {'item_id':item['id'],'pair_id':item['pair_id'],'arm':item['arm'],'concept':item['concept'],'answer_token_id':answer,'probability':probability}


def acquire61(items,backend,budget,out,binding):
    out=Path(out);jobs=position_jobs(items)
    budget.call('e61_oracle_setup',backend.load_oracle)
    # Validate complete frozen prompt tokenization, never reconstruct positions from strings.
    backend.validate_tokenization(items)
    for x in items:
        if x['display']=='D4':
            require(backend.oracle.tok.encode(x['completion_text'],add_special_tokens=False)==x['completion_ids'],'completion token seal')
            require(backend.oracle.tok.encode(x['answer_text'],add_special_tokens=False)==[x['answer_token_id']],'one frozen answer token')
    parts={42:[],44:[]}
    for start in range(0,len(jobs),8):
        batch=jobs[start:start+8];values=budget.call('e61_capture',lambda:backend.capture(batch),(len(jobs)-start-1)//8)
        for layer in parts:parts[layer].append(values[layer])
    acts={layer:np.concatenate(v) for layer,v in parts.items()};cap=out/'capture';cap.mkdir()
    for layer,h in acts.items():
        require(h.shape==(len(jobs),5120) and np.isfinite(h).all(),'position capture grid');np.save(cap/f'acts{layer}.npy',h)
    dump(cap/'POSITION_ORDER.json',jobs);seal(cap,'CAPTURE_SEAL.json',dict(binding,experiment='E61'))
    probabilities=[]
    for item in items:
        if item['display']=='D4':probabilities.append(budget.call('e61_base_probability',lambda:base_answer_probability(backend,item)))
    dump(out/'BASE_PROBABILITIES.json',probabilities)
    for reader in ('oracle','nla'):
        if reader=='nla':budget.call('e61_nla_setup',backend.load_nla)
        with (out/(reader+'.native.jsonl')).open('x') as stream:
            for start in range(0,len(jobs),8):
                batch=jobs[start:start+8];layer=44 if reader=='oracle' else 42
                raw=budget.call('e61_'+reader+'_native',lambda:backend.native_one(reader,acts[layer][start:start+8]),(len(jobs)-start-1)//8)
                require(len(raw)==len(batch),'position readout count')
                for job,group in zip(batch,raw):
                    require(len(group)==1,'one greedy readout per position')
                    for repeat,value in enumerate(group):stream.write(json.dumps({k:v for k,v in dict(job,reader=reader,reader_native_layer=layer,repeat=repeat,**value).items() if k!='ids'},allow_nan=False)+'\n')
    from native_nla512 import truncation_summary
    dump(out/'NLA_TRUNCATION.json',truncation_summary([json.loads(line) for line in (out/'nla.native.jsonl').read_text().splitlines()],row_key='display'))
    dump(out/'TIMING.json',{'completed_epoch':time.time(),'deadline_epoch':budget.end,'phase_max_seconds':budget.observed})
    seal(out,'OUTPUT_SEAL.json',dict(binding,experiment='E61',status='COMPLETE'))


class StageBudget:
    def __init__(self,started,created):
        self.end=min(started+1800,created+6600);self.observed={}
    def call(self,phase,fn,remaining_units=0):
        require(time.time()<self.end-60,'E61 reserve');start=time.monotonic();value=fn()
        self.observed[phase]=max(time.monotonic()-start,self.observed.get(phase,0))
        require(time.time()+1.5*self.observed[phase]*remaining_units<self.end-60,'E61 NO_FIT '+phase)
        return value


def verify_dependencies():
    from contract56 import ROOT,sha
    for name,digest in read(HERE/'DEPENDENCIES.json').items():
        require(sha(ROOT/name)==digest,'E61 dependency '+name)
