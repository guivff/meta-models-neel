"""§79 worker. Reader scoring is exclusively the pinned vendored mats interface."""
from __future__ import annotations
import argparse,gc,json,math,time,importlib.metadata
from collections import defaultdict
from pathlib import Path
import numpy as np
from . import protocol as P,corpus as C

CAPTURE_BATCH=4;SCORE_POINTS_PER_CHUNK=16;SMOKE_PAIRS=8
OUTPUTS=['positions.s79.json','acts42.s79.npy','acts44.s79.npy','scores.s79.jsonl','smoke.s79.jsonl','gate.s79.json','environment.s79.json','progress.s79.json','stage_complete.s79.json','kernel_preflight.s79.json','warmup.s79.json','status.s79.json','prediction_seal.s79.json']

def output_paths(out):return {n:Path(out)/n for n in OUTPUTS}
def assert_output_paths(out):
 extra={x.name for x in Path(out).iterdir()}-set(OUTPUTS)
 if extra:raise ValueError('extra worker output '+repr(sorted(extra)))

def smoke_assignments(assign):
 pairs=defaultdict(dict)
 for r in assign:pairs[r['feature']][tuple(sorted([r['id'],r['donor_id']]))]=True
 chosen={(f,p) for f,ps in pairs.items() for p in sorted(ps,key=lambda p:C.rank('smoke',f,p))[:SMOKE_PAIRS]}
 return [r for r in assign if (r['feature'],tuple(sorted([r['id'],r['donor_id']]))) in chosen]

def capture_union(ol,docs,positions,check=lambda:None,progress=lambda **kw:None):
 import common
 import torch
 from mats.capture import capture
 bydoc=defaultdict(list);dmap={r['id']:r for r in docs};out={42:{},44:{}}
 for r in positions:bydoc[r['document_id']].append(r)
 groups=defaultdict(list)
 for doc,ps in bydoc.items():groups[len(ps)].append((doc,sorted(ps,key=lambda x:x['position'])))
 with ol.base():
  for count,group in sorted(groups.items()):
   group.sort(key=lambda x:(len(dmap[x[0]]['ids']),x[0]))
   for start in range(0,len(group),CAPTURE_BATCH):
    check();chunk=group[start:start+CAPTURE_BATCH];seqs=[dmap[d]['ids'] for d,ps in chunk];at=[[r['position'] for r in ps] for d,ps in chunk]
    h=capture(ol.model,seqs,[42,44],at,batch_size=CAPTURE_BATCH,pad_id=ol.tok.pad_token_id or 0)
    for site in [42,44]:
     if h[site].shape[:2]!=(len(chunk),count) or not torch.isfinite(h[site]).all():raise ValueError('capture shape/nonfinite')
     for row,(_,ps) in enumerate(chunk):
      for j,r in enumerate(ps):out[site][r['id']]=h[site][row,j]
    progress(phase='capture',documents_done=start+len(chunk),group_positions=count)
 order=[r['id'] for r in positions]
 return {site:torch.stack([out[site][i] for i in order]) for site in [42,44]}

def asked(reader_name,reader,h,pair):
 import common
 if reader_name=='olens':return reader.paired_logodds_templates(h,44,[pair],prefix='- ')
 if reader_name=='nla':
  from mats.readers.nla import paired_logodds_templates
  return paired_logodds_templates(reader,h,[pair],batch=32)
 raise ValueError('unknown reader '+reader_name)

def score_all(readers,states,positions,assign,templates,kind,check=lambda:None,progress=lambda **kw:None):
 import torch
 index={r['id']:i for i,r in enumerate(positions)};groups=defaultdict(list);scores=[];timings={}
 for r in assign:groups[r['feature']].append(r)
 for feature,rr in sorted(groups.items()):
  rr=sorted(rr,key=lambda r:r['id']);pair=templates[feature]
  if len(pair)!=1 or len(pair[0])!=2:raise ValueError('single frozen pair required')
  for name,reader in readers.items():
   start=time.monotonic();site=P.SITES[name];values={}
   for offset in range(0,len(rr),SCORE_POINTS_PER_CHUNK):
    check();chunk=rr[offset:offset+SCORE_POINTS_PER_CHUNK];h=states[site][[index[r['id']] for r in chunk]];v=asked(name,reader,h,pair[0])
    if tuple(v.shape)!=(1,len(chunk)) or not torch.isfinite(v).all():raise ValueError('native score shape/nonfinite')
    values.update({r['id']:float(v[0,i]) for i,r in enumerate(chunk)})
    progress(phase='score',reader=name,feature=feature,done=offset+len(chunk))
   timings[feature,name]={'seconds':time.monotonic()-start,'n':len(rr)}
   # Identical teacher-forced donor requests are aliases of their TRUE evaluation.
   for r in rr:
    for arm,key in [('true',r['id']),('mismatched',r['donor_id'])]:scores.append(dict(P.stamp(kind),feature=feature,id=r['id'],reader=name,site=site,arm=arm,score=values[key],source_state_id=key))
 return scores,timings

def warmup(ol,nla,tok,check=lambda:None,progress=lambda **kw:None,synchronize=None):
 """Fixed synthetic setup forwards; discard all reader outputs, no outcome rows."""
 import torch
 from mats.capture import capture
 from contextlib import nullcontext
 synchronize=torch.cuda.synchronize if synchronize is None else synchronize
 started=time.time();check();pieces=tok('Neutral setup warmup text.',add_special_tokens=False)['input_ids']
 if not pieces:raise ValueError('empty warmup tokenization')
 lengths=[512,384,256,128][:CAPTURE_BATCH];seqs=[(pieces*((n+len(pieces)-1)//len(pieces)))[:n] for n in lengths]
 completed=[];pair=['This is setup text.','This is warmup text.']
 devices=[torch.cuda.current_device()] if torch.cuda.is_available() else []
 with torch.random.fork_rng(devices=devices):
  for iteration in range(P.WARMUP_ITERATIONS):
   check()
   with ol.base():h=capture(ol.model,seqs,[42,44],[[len(x)-1] for x in seqs],batch_size=CAPTURE_BATCH,pad_id=tok.pad_token_id or 0)
   check();completed.append('target');progress(phase='warmup',iteration=iteration+1,path='target',outcome_rows=0)
   for name,reader,context in [('olens-active',ol,nullcontext),('olens-base',ol,ol.base),('nla-active',nla,nullcontext),('nla-base',nla,nla.no_adapter)]:
    check();reader_name='olens' if name.startswith('olens') else 'nla';site=P.SITES[reader_name]
    states=h[site][:,0];states=states.repeat((SCORE_POINTS_PER_CHUNK+len(states)-1)//len(states),1)[:SCORE_POINTS_PER_CHUNK]
    with context():discard=asked(reader_name,reader,states,pair)
    del discard;check();completed.append(name);progress(phase='warmup',iteration=iteration+1,path=name,outcome_rows=0)
   synchronize();check();del h
 check();finished=time.time()
 return {'setup_only':True,'unscored':True,'outcome_rows':0,'iterations':P.WARMUP_ITERATIONS,'completed_paths':completed,'started_at':started,'completed_at':finished,'seconds':finished-started,'synthetic_lengths':lengths,'synthetic_input_sha256':C.digest(C.canonical(seqs)),'reader_state_batch':SCORE_POINTS_PER_CHUNK,'no_kernel_shape_exhaustiveness_or_speed_claim':True}

def projection(first_science,now,capture_seconds,smoke_docs,full_docs,smoke_timings,assign,absolute_cutoff=None):
 counts=defaultdict(int)
 for r in assign:counts[r['feature']]+=1
 seconds=capture_seconds*full_docs/max(1,smoke_docs)
 for (feature,reader),m in smoke_timings.items():seconds+=m['seconds']*counts[feature]/m['n']
 projected=1.5*seconds
 remaining=min(P.SCIENCE_SECONDS-(now-first_science),float('inf') if absolute_cutoff is None else absolute_cutoff-now)
 return {'elapsed_science_seconds':now-first_science,'full_projected_1p5_seconds':projected,'reserve_seconds':P.RETRIEVAL_SECONDS,'science_cap_seconds':P.SCIENCE_SECONDS,'remaining_science_seconds':remaining,'staging_excluded':True,'pass':projected<=remaining}

def assets(path):
 path=Path(path);P.verify(path.parent,'assets_seal.s79.json');a=json.loads(path.read_text());covered=set()
 for r in a['files']:
  p=Path(r['path'])
  if str(p.resolve())!=r['resolved_path'] or p.stat().st_size!=r['file_bytes'] or p.stat().st_mtime_ns!=r['file_mtime_ns']:raise ValueError('read-only asset changed after full stage hash '+str(p))
  covered.add(str(p.resolve()))
 for name in ['model','olens','nla']:
  root=Path(a[name])
  if not root.is_dir() or not {str(p.resolve()) for p in root.rglob('*') if p.is_file()}<=covered:raise ValueError('missing local asset coverage '+name)
 return a

def worker(bank,out,assignment,asset_path):
 import common
 import torch
 from transformers import AutoModelForCausalLM,AutoTokenizer
 from mats.readers.olens import load_olens
 from mats.readers.nla import load_nla
 torch.manual_seed(C.SEED)
 P.verify_freeze();a=P.admit(assignment);docs,positions,assign,registry=P.inputs(bank);aweights=assets(asset_path);out=Path(out);out.mkdir(parents=True,exist_ok=False);paths=output_paths(out)
 if torch.cuda.device_count()!=1 or 'H200' not in torch.cuda.get_device_name(0):raise ValueError('requires assigned single H200141GB')
 active_deadline=a['setup_deadline_epoch']
 def check():
  if time.time()>=active_deadline:raise TimeoutError('setup/science cutoff: reserve verified pull')
 def progress(**kw):C.save(paths['progress.s79.json'],dict(P.stamp('real'),at=time.time(),**kw))
 try:
  check();pins=json.loads((C.OUT/'RUNTIME_PINS.json').read_text());actual={k:importlib.metadata.version(k) for k in pins}
  if actual!=pins:raise ValueError('runtime pin mismatch')
  from . import kernel_preflight as K
  kernel_proof=K.check(a['pod_id']);C.save(paths['kernel_preflight.s79.json'],dict(P.stamp('real'),**kernel_proof))
  C.save(paths['environment.s79.json'],dict(P.stamp('real'),packages=actual,pod_id=a['pod_id'],device=torch.cuda.get_device_name(0),asset_manifest_sha256=C.sha(asset_path),runtime_environment=a.get('runtime_environment',{'mode':'current'})))
  start=time.time();model=AutoModelForCausalLM.from_pretrained(aweights['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval();tok=AutoTokenizer.from_pretrained(aweights['model'],local_files_only=True);ol=load_olens(model,tok,lora_dir=aweights['olens']);nla=load_nla(root=aweights['nla'],load_ar=False,enable_thinking=False)
  check();loaded_at=time.time();warmup_proof=warmup(ol,nla,tok,check,progress)
  C.save(paths['warmup.s79.json'],dict(P.stamp('real'),**warmup_proof))
  check();first_science=time.time();P.validate_warmup(warmup_proof,first_science);active_deadline=P.science_deadline(a,first_science)
  C.save(paths['stage_complete.s79.json'],{'at':first_science,'model_load_seconds':loaded_at-start,'warmup_seconds':warmup_proof['seconds'],'science_deadline_epoch':active_deadline,'science_cap_seconds':P.SCIENCE_SECONDS,'setup_seconds':first_science-a['provider_created_epoch'],'checkpoint_files':aweights})
  smoke_assign=smoke_assignments(assign);smoke_ids={r['id'] for r in smoke_assign};smoke_pos=[r for r in positions if r['id'] in smoke_ids];smoke_doc_ids={r['document_id'] for r in smoke_pos}
  start=time.monotonic();smoke_states=capture_union(ol,docs,smoke_pos,check,progress);dt=time.monotonic()-start
  smoke,timing=score_all({'olens':ol,'nla':nla},smoke_states,smoke_pos,smoke_assign,registry['templates'],'smoke',check,progress);P.score_coverage(smoke,smoke_assign,'smoke');C.jsonl(paths['smoke.s79.jsonl'],smoke)
  # Adapter liveness, using the same frozen vendored scoring path, not a new score.
  first=smoke_assign[0]['feature'];pair=registry['templates'][first][0];effects={}
  for name,reader in [('olens',ol),('nla',nla)]:
   h=smoke_states[P.SITES[name]][:2];active=asked(name,reader,h,pair)
   with (reader.base() if name=='olens' else reader.no_adapter()):base=asked(name,reader,h,pair)
   effects[name]=float((active-base).abs().max())
   if effects[name]<=1e-4:raise ValueError('adapter liveness failed '+name)
  full_doc_ids={r['document_id'] for r in positions}
  work=lambda ids:sum(len(d['ids']) for d in docs if d['id'] in ids)
  gate=projection(first_science,time.time(),dt,work(smoke_doc_ids),work(full_doc_ids),timing,assign,active_deadline);gate['adapter_liveness_max_logodds_delta']=effects;C.save(paths['gate.s79.json'],gate)
  if not gate['pass']:raise RuntimeError('INCOMPLETE_SMOKE_PROJECTION_EXCEEDS_CAP')
  del smoke_states;gc.collect();check();states=capture_union(ol,docs,positions,check,progress);C.save(paths['positions.s79.json'],positions)
  for site in [42,44]:np.save(paths[f'acts{site}.s79.npy'],states[site].numpy(),allow_pickle=False)
  scores,_=score_all({'olens':ol,'nla':nla},states,positions,assign,registry['templates'],'real',check,progress);P.score_coverage(scores,assign,'real');C.jsonl(paths['scores.s79.jsonl'],scores);assert_output_paths(out);check()
  P.seal(out,['positions.s79.json','acts42.s79.npy','acts44.s79.npy','scores.s79.jsonl','smoke.s79.jsonl','gate.s79.json','stage_complete.s79.json','environment.s79.json','kernel_preflight.s79.json','warmup.s79.json'],'prediction_seal.s79.json',**P.stamp('real'),input_seal_sha256=C.sha(Path(bank)/'INPUT_SEAL.json'),freeze_sha256=C.sha(C.OUT/'FREEZE.json'),assignment_sha256=C.sha(assignment))
  C.save(paths['status.s79.json'],{'status':'SEALED_BEFORE_LABEL_JOIN','at':time.time()})
 except BaseException as error:
  C.save(paths['status.s79.json'],{'status':'INCOMPLETE','reason':str(error),'at':time.time()});raise

def main():
 p=argparse.ArgumentParser()
 for key in ['bank','out','assignment','assets']:p.add_argument('--'+key,required=True,type=Path)
 a=p.parse_args();worker(a.bank,a.out,a.assignment,a.assets)
if __name__=='__main__':main()
