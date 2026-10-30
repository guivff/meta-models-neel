"""CPU execution of every second-wave stage, using tiny reader models."""
from contextlib import nullcontext
from unittest.mock import patch
import torch
from second_worker import *
from smoke_profile import TinyBackend,TinyOracle,TinyModel,Tok

def smoke(out,experiments=None):
 out=Path(out);out.mkdir(parents=True,exist_ok=False);TinyOracle.base=lambda self:nullcontext();TinyModel.get_input_embeddings=lambda self:self.emb
 def unit(k,split='test'):return dict(id=k,feature='format_plan',split=split,ids=[1],text='stub')
 e62=[dict(unit('ladder'),feature='S1_L4',state='S1',rung='L4',base_item_id='base',first_content_index=0,read_index=0,alpha_token_id=1,beta_token_id=2),dict(unit('eval'),feature='S6_C0',state='S6',rung='C0',base_item_id='task',first_content_index=0,read_index=0)]
 e59=[unit('a'),unit('b'),unit('d','dev')];real=[unit(f'shuffled:{i:03d}') for i in range(200)]
 states={'E62':dict(items=e62),'E59':dict(items=e59,plan={'continuation_pairs':{'format_plan':[[' a',' b']]},'donors':{'a':'b','b':'a'}}),'E63':dict(items=real,random=np.random.default_rng(20261027).standard_normal((200,5120)).astype(np.float32))}
 states['E62P']=dict(items=[dict(e62[0],id='placebo',feature='S1_L4p',rung='L4p')])
 states['D4A']=dict(items=[dict(unit('d4dev','dev'),concept='planets',arm='think',pair_id='dev',read_index=0),dict(unit('d4test'),concept='planets',arm='mention',pair_id='test',read_index=0,completion_ids=[1],completion_text='stub',answer_text='stub',answer_token_id=1)])
 states={e:states[e] for e in REGISTERED if experiments is None or e in experiments}
 for s in states.values():s.update(source='s',input_sha='i')
 caps={'E62':14000,'E62P':4200,'E59':7000,'E63':2800,'D4A':1000};caps={e:c for e,c in caps.items() if e in states};now=time.time();ass=dict(fresh_dedicated_pod=True,gpu_count=1,pod_created_epoch=now,custody_start_epoch=now,absolute_deadline_epoch=now+sum(caps.values()),provider_deadline_epoch=now+sum(caps.values()),caps=caps,prior_custody_seconds=dict.fromkeys(caps,0),pod_id='CPU',cohort_id='CPU_COHORT',parent_request_sha256='a'*64)
 if 'E62' not in states:ass.update(fresh_dedicated_pod=False,existing_pod=True)
 allocation(ass);b=TinyBackend();budget=Budget(out,caps,ass['absolute_deadline_epoch'],{'oracle_setup':445.5,'oracle_native_8_items':11.36})
 xs=[dict(id=f'{r}:{i}',feature=r) for r in parity_gate.ROWS for i in range(84)];labels={x['id']:i%2 for i,x in enumerate(xs)};h=np.zeros((252,5120),np.float32);h[:,0]=list(labels.values());parity=(xs,labels,{r:{'olens':[[' a',' b'],[' a',' b']]} for r in parity_gate.ROWS},h,{'reference_auc':dict.fromkeys(parity_gate.ROWS,1.)})
 def tiny_capture(model,seqs,layers,positions,**kw):
  model(input_ids=torch.tensor(seqs));return {l:torch.tensor(positions,dtype=torch.float32)[:,:,None].repeat(1,1,5120)+l for l in layers}
 original=Tok.encode
 def encode(self,text,**kw):return [2] if text==' beta' else original(self,text,**kw)
 with patch('mats.capture.capture',tiny_capture),patch.object(Tok,'encode',encode):
  ready=capture_all(states,b,budget,out,ass,parity);assert b.old_oracle.native_calls==0 and b.nla is None
  if 'E62' in states:
   cap=states['E62']['cap'];assert np.load(cap/'all_positions44.npy').dtype==np.float16 and np.load(cap/'offsets.npy').tolist()==[0,1,2]
  go=dict(reader_launch_authorized=True,pod_id='CPU',cohort_id='CPU_COHORT',issued_epoch=time.time(),capture_seals=ready['capture_seals'],input_seals=ready['input_seals'],forecast_seals=dict.fromkeys(states,'b'*64),forecast_commits=dict.fromkeys(states,'c'*40));validate_go(go,ready)
  (out/'jobs').mkdir();jobs=jobs_for(states);results=admit_and_run(jobs,b,budget,lambda j:execute(j,b,out));finish(states,jobs,results,out,budget,ass,go)
 assert len(list((out/'jobs').glob('*.json')))==len(jobs)
 for e,s in states.items():verify(s['out'],'OUTPUT_SEAL.json')
 if 'E63' in states:assert len((out/'e63/oracle.jsonl').read_text().splitlines())==400
 expected={'native'} | ({'behaviour'} if 'E62' in states else set()) | ({'pool','continuation','d4base'} if 'E63' in states else set())
 assert {j['kind'] for j in jobs}==expected
 dump(out/'SMOKE_RESULT.json',{'status':'PASS','all_stage_jobs_once':len(jobs),'all_positions':'fp16+offsets+order','capture_before_GO':True,'production_model_calls':0})
