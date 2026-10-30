"""All production paths on tiny CPU models, including retained pilots and clean NO_FIT."""
import time,copy
from pathlib import Path
from contextlib import nullcontext
import numpy as np
from production_joint import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel

def smoke_joint(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=False)
 TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb
 # Different lengths deliberately exercise capture packet indexing without production weights.
 def unit(k,split):return dict(id=k,feature='category_switch',split=split,text='stub',ids=[1])
 xs=[unit('d0','dev'),unit('d1','dev'),unit('t0','test'),unit('t1','test')]
 plan={'native_ids':{'category_switch':['t0','t1']},'rows':{'category_switch':{'continuation_pairs':[[' a',' b']]}},'donors':{'t0':'t1','t1':'t0'},'count_metadata':{k:{'mention_policy':'word_exact_casefold','animal_lexicon':{'cat':['cat']},'last_animal_id':None} for k in ('t0','t1')}}
 states={}
 for e in ('E56','E57'):
  states[e]={'source':'s','input_sha':'i','items':copy.deepcopy(xs),'capture_items':copy.deepcopy(xs),'rows':['category_switch'],'samples':plan['native_ids'],'plan':copy.deepcopy(plan)}
 s=states['E56'];s.update(cont={'category_switch':{'pairs':[[' a',' b']]}},donors=plan['donors'],vectors=np.ones((1,5120),np.float32),injection=[{'id':'inj','row':'category_switch','index':0,'variant':'a','arm':'full'}]);s['plan']['injection_rows']={'0':['category_switch']}
 a=dict(id='D3',ids=[1],text='stub',display='D3',arm='decline',pair_id='pair',instruction_end_index=0,pre_answer_index=0)
 b=dict(id='D4',ids=[1],text='stub',display='D4',arm='think',pair_id='pair',read_index=0,completion_ids=[1],completion_text='stub',answer_text='stub',answer_token_id=1,concept='birds')
 states['E61']={'source':'s','input_sha':'i','items':[a,b],'capture_items':position_jobs([a,b])}
 items=[{'id':f'{r}:{i}','feature':r} for r in parity_gate.ROWS for i in range(84)];labels={x['id']:i%2 for i,x in enumerate(items)};h=np.zeros((252,5120),np.float32);h[:,0]=list(labels.values())
 parity=(items,labels,{r:{'olens':[[' a',' b'],[' a',' b']]} for r in parity_gate.ROWS},h,{'reference_auc':dict.fromkeys(parity_gate.ROWS,1.)})
 caps={'E56':5000,'E57':3600,'E61':3600};now=time.time();ass={'slot':0,'pod_id':'CPU','pod_created_epoch':now,'absolute_deadline_epoch':now+sum(caps.values()),'gpu_count':1,'allocation_by_slot':{'E56':{'0':5000,'1':5000,'2':5000},'E57':{'0':3600,'1':3600,'2':3600},'E61':{'0':3600}},'prior_custody_seconds':{'E56':1000,'E57':0,'E61':0}}
 validate_allocation(ass);backend=TinyBackend();budget=Budget(out,caps,ass['absolute_deadline_epoch'],{'oracle_setup':445.5,'oracle_native_8_items':11.36})
 ready=capture_states(states,backend,budget,out,ass,parity)
 require(backend.old_oracle.native_calls==0 and backend.nla is None,'no reader output before GO')
 go={'reader_launch_authorized':True,'pod_id':'CPU','capture_seals':ready['capture_seals'],'input_seals':ready['input_seals'],'issued_epoch':time.time(),'forecast_seals':dict.fromkeys(states,'a'*64),'forecast_commits':dict.fromkeys(states,'b'*40)};validate_go(go,ready)
 bad=dict(go,capture_seals={})
 try:validate_go(bad,ready)
 except ValueError:pass
 else:raise AssertionError('invalid GO accepted')
 (out/'jobs').mkdir();jobs=make_jobs(states,0);results=admit_and_run(jobs,backend,budget,lambda j:execute_job(j,backend,out));finish(states,jobs,results,budget,ass,go)
 require(len(list((out/'jobs').glob('*.json')))==len(jobs),'each pilot/full job emitted exactly once')
 require(any(j['kind']=='base' for j in jobs) and any(j['kind']=='injection' for j in jobs),'base and injection covered')
 for e,s in states.items():verify(s['out'],'OUTPUT_SEAL.json')
 # Force a forecast failure after pilot calls; no remaining jobs may execute.
 fail=out/'rejection';fail.mkdir();fb=Budget(fail,{'E56':1},time.time()+1e4,{'oracle_setup':445.5,'oracle_native_8_items':11.36});dummy=TinyBackend();dummy.load_oracle();calls=[]
 js=[dict(exp='E56',reader=r,phase=r+'_native',number=i) for i,r in enumerate(['oracle']*3+['nla']*3)]
 try:admit_and_run(js,dummy,fb,lambda j:calls.append(j['number']) or [])
 except NoFit:pass
 else:raise AssertionError('over-budget admitted')
 require(len(calls)==4 and read(fail/'FORECAST.json')['status']=='NO_FIT','stop after retained pilot jobs')
 dump(out/'SMOKE_RESULT.json',{'status':'PASS','jobs_once':len(jobs),'all_experiments':['E56','E57','E61'],'stages':['parity','capture','GO','Oracle native','Oracle continuation','NLA native','NLA continuation','injection','E61 base probabilities','counts','seals','NO_FIT'],'production_model_calls':0})
