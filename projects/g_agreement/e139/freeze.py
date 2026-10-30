"""Freeze original E139 sources and public strings, CPU only; never score them."""
import json,hashlib,random,tarfile,shutil,datetime
from pathlib import Path
from collections import Counter
import numpy as np
from tokenizers import Tokenizer
from .selection import STATES,select,graft
from .prepare_intake import read,member,checked_array,PINS,B
from .analyze_once import verify

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def pack_rows(stage,dev,e85):
 if len(stage)!=120 or Counter(r['state']for r in stage)!=Counter({s:20 for s in STATES}):raise ValueError('full120 six-state census')
 if len(dev)!=100 or Counter(r['state']for r in dev)!=Counter({s:20 for s in STATES if s!='evaluation_cue'}):raise ValueError('100 other-state DEV spans')
 if len(e85)!=200 or Counter(r['label']for r in e85)!={0:100,1:100}:raise ValueError('all200 E85 DEV class balance')
 public=[];rows=[];directions=[]
 def add(text):
  if not isinstance(text,str):raise ValueError('exact text string')
  id_='E139-%06d'%len(public);public.append(dict(id=id_,text=text));return id_
 for s in STATES:
  for label in (0,1):
   if sum(r['state']==s and r['label']==label for r in stage)!=10:raise ValueError('10 TEST/class/state')
 for i,r in enumerate(stage):
  if set(r['strings'])!={'original','true','false','neutral'}:raise ValueError('four whole strings')
  if any(r['strings'][k]!=r['strings']['original']+'\n'+r['statements'][k]for k in ('true','false','neutral')):raise ValueError('exact append after unmodified original')
  if r['statements']['tokens']['true']!=r['statements']['tokens']['neutral']:raise ValueError('token matched true/neutral')
  rows.append(dict(id='E139-R%03d'%i,state=r['state'],variants={k:add(r['strings'][k])for k in ('original','true','false','neutral')}))
 for r in dev:directions.append(dict(state=r['state'],label=r['label'],source='acquired',id=add(r['text'])))
 for i,r in enumerate(e85):directions.append(dict(state='evaluation_cue',label=r['label'],source='E130',index=i))
 for s in STATES:
  ds=[r for r in directions if r['state']==s];n=100 if s=='evaluation_cue'else 10
  if Counter(r['label']for r in ds)!={0:n,1:n}:raise ValueError('DEV class balance')
 random.Random(20261030).shuffle(public)
 return public,rows,directions

def native_sample_zero(native):
 texts={}
 for r in native:
  if r['reader']=='olens'and r['layer']==44 and r['sample']==0:
   if r['id']in texts or r['status']!='COMPLETE':raise ValueError('one sealed native Oracle44 sample0 per item')
   texts[r['id']]=r['raw']
 return texts

def main(out):
 out=Path(out)
 if out.exists():raise FileExistsError('freeze destination must be new')
 partial=B/'outputs/e139-intake-partial-v4'
 ps=verify(partial,'INTAKE_STATUS.json','b714150600469fd6e87b1ca29f2b6829fe442de14a0e4b97c7ac9928a27d0152')
 stage=read(partial/'READOUTS.PRIVATE.json');dev=read(partial/'DEV_SPANS.PRIVATE.json');pins=read(partial/'SOURCE_PINS.json')
 for p,h in pins.items():
  if sha(p)!=h:raise ValueError('original prepared source changed')
 targets=np.load(partial/'h44.PRIVATE.npy',allow_pickle=False)
 if targets.shape!=(100,5120)or len(stage)!=100 or len(dev)!=80:raise ValueError('immutable five-state intake')
 root=B/'blindspot-worktree/cache/g_agreement/blindspot'
 manifest=read(root/'w1-bank-v2/manifest.json','6e38ba7e5a5998082489ece5ab63a8a720bc039df6f32874b37481523f9f8f17')
 xs=read(root/'w1-bank-v2/items.DO_NOT_STAGE.jsonl','48497c10082f18a5e80034c34e97e7139ee9783de8a8b28440e2e30535dfa07b',True)
 templates=read(root/'w1-bank-v2/templates.json','57cad0d1bce20de00026cab2515b3c43a2925d50b2944e0d0556376e88833172')
 if templates['table_column']['values']!=['first','later']or templates['table_column']['score_orientation']!='value_A_positive':raise ValueError('frozen W1 A-positive class binding')
 tab=[r for r in xs if r['feature']=='table_column'];rs=[dict(id=r['id'],split=r['split'],label={'first':1,'later':0}[r['value']])for r in tab];meta={r['id']:r for r in tab}
 if any(r['meta']['level']!=({'first':1,'later':5}[r['value']])or r['meta']['read_position']!=len(r['ids'])-1 for r in tab):raise ValueError('original column values and read token')
 ar=root/'w1-assembled/target';ss=read(ar/'SCORE_SEAL.json','d6f12937d5f85b2c44c98a71b7b0cc5fb8eb1fa7c6e92c42b1c0876f534d938a');order=member(ar,ss,'items.order.json');arr=checked_array(ar/'acts44.npy',ss['files']['acts44.npy'])
 if arr.shape!=(7296,5120)or arr.dtype!=np.float32 or len(order)!=7296 or len(set(order))!=7296:raise ValueError('full original7296 source order, no subset indexing')
 acts={id_:arr[i]for i,id_ in enumerate(order)}
 nr=root/'w1-units/priority/target';ns=read(nr/'FREE_SEAL.json','1f8881f513d6d94658c32871b47dc2cfd6aeeeff7603684346910f4d6a47426c');native=member(nr,ns,'unasked.target.jsonl');texts=native_sample_zero(native)
 tokfile=B/'outputs/e139-evidence-v1/tokenizer.json';tok=Tokenizer.from_file(str(tokfile));encode=lambda t:tok.encode(t,add_special_tokens=False).ids
 if manifest['tokenizer_sha256']!=sha(tokfile):raise ValueError('identical original Qwen tokenizer')
 tabtargets=[]
 for r in select([r for r in rs if r['id']in texts and r['id']in acts],'table_column','test'):
  strings,statements=graft(texts[r['id']],'table_column',r['label'],encode)
  stage.append(dict(state='table_column',original_id=r['id'],label=r['label'],strings=strings,statements=statements,vector_index=len(stage)))
  tabtargets.append(acts[r['id']].copy())
 for r in select(rs,'table_column','dev'):
  ids=meta[r['id']]['ids'][-32:];text=tok.decode(ids,skip_special_tokens=False)
  if encode(text)!=ids:raise ValueError('lossless original table DEV span')
  dev.append(dict(state='table_column',original_id=r['id'],label=r['label'],text=text,input_ids=ids))
 e85=read(partial/'E85_DEV_ORDER.PRIVATE.json');public,rows,directions=pack_rows(stage,dev,e85)
 pub=out/'public';cpu=out/'cpu_only';pub.mkdir(parents=True);cpu.mkdir()
 write(pub/'items.json',public)
 write(pub/'MANIFEST.json',dict(experiment='E139',status='COMPLETE',prompts=580,labels_on_pod=False,tokenizer_revision='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9',tokenization=dict(add_special_tokens=False,truncation=False,strip=False,tag_added_by='original OLensAR.reconstruct tag44')))
 write(pub/'INPUT_SEAL.json',dict(experiment='E139',status='COMPLETE',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()if p.is_file()}))
 write(cpu/'PLAN.PRIVATE.json',dict(experiment='E139',rows=rows,directions=directions,acquire_ids=[r['id']for r in public],moments_path=str(B/'wt-i4/cache/g_agreement/e96/operator/whitener.pt')))
 write(cpu/'ROSTER.PRIVATE.json',stage);write(cpu/'DEV_SPANS.PRIVATE.json',dev);write(cpu/'E85_DEV_ORDER.PRIVATE.json',e85)
 np.save(cpu/'h44.PRIVATE.npy',np.concatenate([targets,np.stack(tabtargets)]),allow_pickle=False)
 shutil.copyfile(partial/'E85_DEV_REBUILDS.PRIVATE.npy',cpu/'E85_DEV_REBUILDS.PRIVATE.npy')
 pins.update(PINS);write(cpu/'SOURCE_PINS.PRIVATE.json',pins)
 write(cpu/'CPU_INPUT_SEAL.json',dict(experiment='E139',status='COMPLETE',items=120,acquisition_inputs=580,labels_cpu_only=True,public_input_sha256=sha(pub/'INPUT_SEAL.json'),files={p.name:sha(p)for p in cpu.iterdir()if p.is_file()}))
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz')as t:
  for n in ('items.json','MANIFEST.json','INPUT_SEAL.json'):t.add(pub/n,arcname=n)
 write(out/'FREEZE_RECEIPT.json',dict(experiment='E139',status='COMPLETE_INPUT_FREEZE',frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),public_input_root=str(pub),public_input_sha256=sha(pub/'INPUT_SEAL.json'),public_archive=str(out/'PUBLIC_INPUTS.tar.gz'),public_archive_sha256=sha(out/'PUBLIC_INPUTS.tar.gz'),cpu_root=str(cpu),cpu_input_sha256=sha(cpu/'CPU_INPUT_SEAL.json'),original_readouts=120,states=list(STATES),TEST_readouts_per_state=20,DEV_new_spans_per_other_state=20,existing_E85_DEV_rebuilds=200,public_strings=580,token_matching='TRUE and neutral exactly equal Qwen tokens; false length reported in private roster',source_W1_table_authority='direct human answer Use sealed W1 table_column',source_selection='pre-output SELECTION_PLAN.json',real_scoring=False,GPU_calls=0))
 print('E139 FROZEN',sha(pub/'INPUT_SEAL.json'),sha(cpu/'CPU_INPUT_SEAL.json'))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
