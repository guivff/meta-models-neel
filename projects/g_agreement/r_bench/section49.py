"""§49 donor-minus-recipient bridge split. CPU prepare/analyze; assigned-pod stages only."""
from __future__ import annotations
import argparse, hashlib, json, math, os, re, signal, subprocess, sys, time
from pathlib import Path
import numpy as np

REG=Path(__file__).resolve().parents[1]/'registrations/section49'
BASIS_SHA='372946128c4b303070d5926a91a34694b11d5307049d18c410377501cbda0f33'
JPP=('koayon/jpp-lenses','237dab6ea0e611d964bf407f13ba1655f1a6ae43','qwen3.6-27b/lens.pt','adc103d4e724d04e721b019ecafa1388ff376541db3ecb78f693e60ed1d8609d')
CAP_SECONDS=9000
ANSWER_TOKENS=64
ALPHAS=(1.,1.5,2.)
ARMS=('full','J','perp','random0','random1')
READERS=('olens','nla','skip_a','rlens','jpp','jlens')
CELLS=[('natural',0.)]+[(a,v) for a in ARMS for v in ALPHAS]

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix('.tmp');t.write_text(json.dumps(x,indent=2,allow_nan=False)+'\n');t.replace(p)
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines()] if Path(p).exists() else []
def append(p,x):
 with Path(p).open('a') as f:f.write(json.dumps(x,allow_nan=False)+'\n');f.flush()
def wilson(k,n=196):
 z=1.959963984540054;p=k/n;v=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n));return ((p+z*z/(2*n)-v)/(1+z*z/n),(p+z*z/(2*n)+v)/(1+z*z/n))

def prepare():
 from projects.g_agreement.core import config as C
 ids=read(REG/'bank_inventory.json')['item_ids'];allitems=read(C.DATASET_DIR/'items_re.json')['items'];bank={r['item_id']:r for r in allitems if r['item_id'] in ids}
 if len(bank)!=196:raise ValueError('Not exactly 196 frozen items')
 rec=[]
 for iid in ids:
  r=bank[iid];c=r['construction'];options=[t for t in bank.values() if t['construction']['template']==c['template'] and t['construction']['bridge']!=c['bridge'] and t['construction']['answer']!=c['answer']]
  if not options:raise ValueError('No donor: '+iid)
  donor=min(options,key=lambda t:digest([20261021,iid,t['item_id']]))
  rec.append({'id':iid,'donor':donor['item_id'],'text':r['prompt_text'],'position':r['read_position'],'bridge':c['bridge'],'answer':c['answer'],'template':c['template'],'bridge_jlens':c.get('bridge_jlens') or c['bridge']})
 plan={'section':49,'n':196,'records':rec,'smoke_ids':[r['id'] for r in sorted(rec,key=lambda r:(-len(r['text']),r['id']))[:4]],'edit_layer':38,'read_layers':[42,44],'basis_sha256':BASIS_SHA,'alphas':ALPHAS,'arms':ARMS,'seed':20261021,'source_bank_sha256':sha(C.DATASET_DIR/'items_re.json')}
 save(REG/'plan.json',plan);return plan

def split_edit(delta,Q,seed):
 d=np.asarray(delta,dtype=np.float64);q=np.asarray(Q,dtype=np.float64);n=np.linalg.norm(d,axis=-1,keepdims=True)
 if not np.isfinite(d).all() or not np.isfinite(q).all():raise ValueError('Nonfinite geometry')
 j=(d@q)@q.T;p=d-j
 def scale(v):
  norm=np.linalg.norm(v,axis=-1,keepdims=True)
  if np.any((n>1e-6)&(norm<=1e-6)):raise ValueError('Degenerate nonzero component; no replacement or exclusion')
  return np.divide(v*n,norm,out=np.zeros_like(v),where=norm>1e-6).astype(np.float32)
 rng=np.random.default_rng(seed)
 return {'full':d.astype(np.float32),'J':scale(j),'perp':scale(p),'random0':scale(rng.normal(size=d.shape)),'random1':scale(rng.normal(size=d.shape))}

def shard_plan(shard_id):
 plan=read(REG/'plan.json');spec=read(REG/'shards.json')
 if spec['plan_sha256']!=sha(REG/'plan.json'):raise ValueError('Shard plan hash mismatch')
 if type(shard_id) is not int or shard_id not in range(4):raise ValueError('Invalid shard ID')
 all_ids=[r['id'] for r in plan['records']];ranked=sorted(all_ids,key=lambda i:(hashlib.sha256(i.encode()).hexdigest(),i))
 if len(spec['shards'])!=4:raise ValueError('Require four shard definitions')
 for k,entry in enumerate(spec['shards']):
  expected=[i for i in all_ids if i in set(ranked[k::4])]
  smoke=[r['id'] for r in sorted((r for r in plan['records'] if r['id'] in expected),key=lambda r:(-len(r['text']),r['id']))[:4]]
  if entry['item_ids']!=expected or entry['smoke_ids']!=smoke or entry['shard_id']!=k or entry['cap_seconds']!=9000:raise ValueError('Frozen hash shard mismatch')
 shard=spec['shards'][shard_id]
 ids=shard['item_ids']
 if len(ids)!=49 or len(set(ids))!=49:raise ValueError('Invalid shard coverage')
 # Keep the full donor bank and answer vocabulary; only recipients are sharded.
 return dict(plan,recipient_ids=ids,smoke_ids=shard['smoke_ids'],shard_id=shard_id)

def chosen_records(plan,smoke):
 allowed=set(plan.get('recipient_ids',[r['id'] for r in plan['records']]))
 return [r for r in plan['records'] if r['id'] in allowed and (r['id'] in plan['smoke_ids'])==smoke]

def reader_candidates(name,recipient,donor):
 key='bridge_jlens' if name in ('jlens','rlens','jpp') else 'bridge'
 return recipient[key],donor[key]

class Guard:
 def __init__(self,run):
  self.run=Path(run);self.booking=read(self.run/'booking.json');self.plan=shard_plan(self.booking['shard_id']);b=self.booking
  if b['cap_seconds']!=CAP_SECONDS or b['gpu_count']!=1 or b['deadline']>b['created_epoch']+CAP_SECONDS:raise ValueError('Invalid budget booking')
  if b.get('shards_sha256')!=sha(REG/'shards.json'):raise ValueError('Shard assignment mismatch')
  if b['plan_sha256']!=sha(REG/'plan.json'):raise ValueError('Plan mismatch')
  native=dict(x.split('=',1) for x in Path('/proc/1/environ').read_text().split('\0') if '=' in x).get('RUNPOD_POD_ID')
  if b['pod_id']!=native or b['pod_id']!=os.environ.get('RUNPOD_POD_ID'):raise ValueError('Native pod identity mismatch')
  speed=b.get('verified_pull_bytes_per_second',0)
  if not math.isfinite(speed) or speed<=0:raise ValueError('Missing measured pull bandwidth')
  self.reserve=max(600,math.ceil(2*512*1024**2/speed))
  if not b.get('custody_acknowledged') or not b.get('own_account_http200'):raise ValueError('Missing custody/account proof')
  if not b.get('mac_hardstop_pid') or not b.get('mac_watchdog_pid'):raise ValueError('Missing detached guard proof')
  for path,h in read(REG/'source_manifest_shards.json').items():
   if sha(REG.parents[3]/path)!=h:raise ValueError('Frozen source mismatch '+path)
  self()
 def __call__(self):
  if time.time()>=self.booking['deadline']-self.reserve:raise TimeoutError('Science cutoff; preserve pull reserve')
  if os.environ.get('RUNPOD_POD_ID')!=self.booking['pod_id']:raise ValueError('Pod identity changed')
  (self.run/'progress.txt').write_text(str(time.time()))

def answer_label(text, vocabulary):
 normalized=' '.join(text.strip().lower().split())
 hits=[]
 for v in vocabulary:
  match=re.search(r'(?<!\w)'+re.escape(v.lower())+r'(?!\w)',normalized)
  if match:hits.append((match.start(),-len(v),v))
 return min(hits)[2] if hits else None

def answer_measure(text, natural, vocabulary):
 label=answer_label(text,vocabulary);base=answer_label(natural,vocabulary)
 return {'answer_label':label,'natural_label':base,'unparseable':label is None or base is None,
         'flip':None if label is None or base is None else label!=base}

def parse_report(records):
 ids={r['item'] for r in records};bad={r['item'] for r in records if r.get('unparseable',False)}
 return {'items':len(ids),'unparseable_items':len(bad),'unparseable_item_ids':sorted(bad),
         'unparseable_cells':sum(r.get('unparseable',False) for r in records),'rate':len(bad)/len(ids) if ids else 1.}

def smoke_parse_gate(records):
 report=parse_report(records)
 if report['rate']>.05:raise ValueError('More than 5% smoke items unparseable; preserve all rows')
 return report

def encode(target,plan):
 from projects.g_agreement.r_bench import collect as C,swap as S
 out={}
 for r in plan['records']:
  ids=C.render_ids(target.tokenizer,r['text'],'chat');p=r['position'];span=S.char_span_tokens(target.tokenizer,ids,r['text'],p['char_start'],p['char_end'],None)
  if span is None or not 0<=span[1]-1<len(ids)-1:raise ValueError('Bridge span failure '+r['id'])
  out[r['id']]={'ids':ids,'pos':span[1]-1}
 return out

def require_admission(run):
 p=read(Path(run)/'projection.json')
 if not p.get('admitted'):raise ValueError('Full phase not admitted')
 for name,h in p['smoke_files'].items():
  if sha(Path(run)/'smoke'/name)!=h:raise ValueError('Smoke evidence changed')

def target_stage(run,smoke):
 import torch
 from projects.g_agreement.core import model as M,readers as R,scoring_lo as LO,config as C
 from projects.g_agreement.r_bench.remainder_x1b_collect import forward
 from projects.g_agreement.w_pod.common import prefill_generate
 g=Guard(run);run=Path(run)
 if not smoke:require_admission(run)
 plan=g.plan;bank={r['id']:r for r in plan['records']};start=time.monotonic();target=M.load_target();g();
 if torch.cuda.device_count()!=1:raise ValueError('Requires exactly one GPU')
 encoded=encode(target,plan)
 basis=run/'inputs/jspace_L38_r384.pt'
 if sha(basis)!=BASIS_SHA:raise ValueError('Basis hash mismatch')
 q=torch.load(basis,map_location='cpu',weights_only=False)['Q'].float().numpy()[:,:384]
 if q.shape!=(C.D_MODEL,384) or not np.allclose(q.T@q,np.eye(384),atol=2e-4):raise ValueError('Basis shape/orthogonality')
 natpath=run/'natural.npz'
 if smoke:
  natural={}
  for r in plan['records']:
   g();e=encoded[r['id']];_,s=forward(target,[e['ids']],[e['pos']],(38,));natural[r['id']]=s[38][0]
  np.savez(natpath,**natural);save(run/'natural_hash.json',{'sha256':sha(natpath)})
 else:
  if sha(natpath)!=read(run/'natural_hash.json')['sha256']:raise ValueError('Natural hash mismatch')
  with np.load(natpath,allow_pickle=False) as z:natural={k:z[k] for k in z.files}
 setup=time.monotonic()-start
 chosen=chosen_records(plan,smoke);phase='smoke' if smoke else 'full';out=run/phase;out.mkdir(exist_ok=True)
 if (out/'model.jsonl').exists():raise ValueError('No automatic rerun')
 t=time.monotonic()
 for r in chosen:
  g();iid=r['id'];e=encoded[iid];h=natural[iid];delta=natural[r['donor']]-h;parts=split_edit(delta,q,int(digest([20261021,iid])[:16],16));states={}
  base=prefill_generate(target,e['ids'],read_layers=(42,44),max_new_tokens=ANSWER_TOKENS)[0]
  # Zero replacement must preserve the generated answer and downstream vectors.
  if smoke:
   zero=prefill_generate(target,e['ids'],edit_layer=38,row_positions=[[e['pos']]],row_vectors=[h],read_layers=(42,44),max_new_tokens=ANSWER_TOKENS)[0]
   if zero['answer_text']!=base['answer_text'] or any(not torch.allclose(zero['read'][L],base['read'][L],rtol=.003,atol=.03) for L in (42,44)):raise ValueError('Zero-edit invariance failed')
  for arm,alpha in CELLS:
   g();res=base if arm=='natural' else prefill_generate(target,e['ids'],edit_layer=38,row_positions=[[e['pos']]],row_vectors=[h+alpha*parts[arm]],read_layers=(42,44),max_new_tokens=ANSWER_TOKENS)[0]
   key=f'{iid}|{arm}|{alpha}';states.update({f'{arm}_{alpha}_L{L}':res['read'][L].numpy() for L in (42,44)})
   append(out/'model.jsonl',{'key':key,'item':iid,'donor':r['donor'],'arm':arm,'alpha':alpha,'answer_text':res['answer_text'],'natural_answer':base['answer_text'],**answer_measure(res['answer_text'],base['answer_text'],sorted({v['answer'] for v in bank.values()})),'delta_norm':float(np.linalg.norm(delta))})
  np.savez(out/(iid+'.npz'),**states)
 save(out/'parse_report.json',parse_report(rows(out/'model.jsonl')))
 # The standing rule gates pooled smoke missingness after every reader has run.
 capture_s=time.monotonic()-t
 # Read one lens at a time; Oracle first, then skip A on the same target.
 score_times={};LO.NLA_TEMPLATES['section49']=['The country is {X}.']
 for name in ('jlens','rlens','jpp','olens','skip_a'):
  g();t=time.monotonic()
  if name in ('jlens','rlens'):
   reader=(R.JLensReader() if name=='jlens' else R.RLensReader()).bind(target,layers_keep=[44])
   expected=C.JLENS_FILE_SHA256 if name=='jlens' else C.RLENS_FILE_SHA256
   if sha(reader.lens_path)!=expected or 44 not in reader.J:raise ValueError('Lens asset/layer mismatch')
  elif name=='jpp':reader=bind_jpp(target)
  elif name=='olens':reader=R.OLensReader().bind(target)
  else:reader=R.SkipLensReader('a').bind(target)
  score(reader,name,chosen,out,bank,g)
  score_times[name]=time.monotonic()-t
  del reader;torch.cuda.empty_cache()
 save(out/'target_timing.json',{'setup_s':setup,'capture_s':capture_s,'reader_s':score_times,'n':len(chosen)})

def bind_jpp(target):
 import torch
 from huggingface_hub import hf_hub_download
 from projects.g_agreement.core import readers as R,model as M
 p=hf_hub_download(JPP[0],JPP[2],revision=JPP[1])
 if sha(p)!=JPP[3]:raise ValueError('J++ hash mismatch')
 obj=torch.load(p,map_location='cpu',weights_only=True,mmap=True);jac=obj.get('J',obj.get('jacobians',obj.get('parameters',{}).get('jacobians')))
 if jac is None:raise ValueError('Unknown J++ layout')
 if isinstance(jac,dict):v=jac[44] if 44 in jac else jac['44']
 else:v=jac[list(map(int,obj.get('source_layers',range(len(jac))))).index(44)]
 d=M.unembed_weight(target.model).shape[1]
 if tuple(v.shape)!=(d,d):raise ValueError('J++ shape')
 reader=R.JLensReader();reader.name='jpp';reader.J={44:v.float().to(target.device)};reader.w_u=M.unembed_weight(target.model).float();reader.tokenizer=target.tokenizer;reader.device=target.device
 return reader

def score(reader,name,chosen,out,bank,guard):
 import torch
 from projects.g_agreement.core import scoring_lo as LO
 LO.NLA_TEMPLATES['section49']=['The country is {X}.'];L=42 if name=='nla' else 44
 path=out/(name+'.jsonl')
 if path.exists():raise ValueError('No automatic reader rerun')
 for r in chosen:
  with np.load(out/(r['id']+'.npz'),allow_pickle=False) as z:
   for arm,alpha in CELLS:
    guard();a,b=reader_candidates(name,r,bank[r['donor']]);h=torch.from_numpy(z[f'{arm}_{alpha}_L{L}'])[None]
    try:result=LO.score_lo(reader,h,[(a,b)],'section49',layer=L,batch=2)[0]
    except (ValueError,RuntimeError) as exc:
     if isinstance(exc,torch.cuda.OutOfMemoryError):raise
     result={'unscorable':True,'lo':None,'reason':type(exc).__name__+': '+str(exc)}
    append(path,reader_cell(r['id'],r['donor'],arm,alpha,name,L,result))

def reader_cell(item,donor,arm,alpha,name,layer,result):
 # Preserve native payload; JSON has no NaN/Infinity, so encode those explicitly as strings.
 def safe(v):
  if isinstance(v,float) and not math.isfinite(v):return str(v)
  if isinstance(v,dict):return {k:safe(x) for k,x in v.items()}
  if isinstance(v,list):return [safe(x) for x in v]
  return v
 value=result.get('lo');missing=bool(result.get('unscorable')) or value is None or not math.isfinite(value)
 return {'item':item,'donor':donor,'arm':arm,'alpha':alpha,'reader':name,'layer':layer,
         'status':'MISSING' if missing else 'OK','missing_reason':result.get('reason','null/nonfinite native score') if missing else None,
         'lo_original_minus_donor':None if missing else value,'native':safe(result)}

def follow_bounds(d,ids,arm,alpha):
 low=[];high=[]
 for i in ids:
  cell=d[i,arm,alpha];base=d[i,'natural',0.]
  if cell is None or base is None:low.append(0.);high.append(1.)
  else:
   value=float(cell<base);low.append(value);high.append(value)
 return np.array(low),np.array(high)

def nla_stage(run,smoke):
 from projects.g_agreement.core.readers import NLAReader
 g=Guard(run);run=Path(run)
 if not smoke:require_admission(run)
 plan=g.plan;start=time.monotonic();reader=NLAReader().bind();setup=time.monotonic()-start
 chosen=chosen_records(plan,smoke);out=run/('smoke' if smoke else 'full');start=time.monotonic();score(reader,'nla',chosen,out,{r['id']:r for r in plan['records']},g)
 save(out/'nla_timing.json',{'setup_s':setup,'score_s':time.monotonic()-start,'n':len(chosen)})

def missing_summary(tables):
 arms={};total=bad=0
 for name,rr in tables.items():
  for r in rr:
   key=f"{name}/{r['arm']}/{r['alpha']}";v=arms.setdefault(key,{'n':0,'missing':0})
   missing=r.get('status')=='MISSING' or r.get('unparseable',False)
   v['n']+=1;v['missing']+=int(missing);total+=1;bad+=int(missing)
 for v in arms.values():v.update(rate=v['missing']/v['n'],format_limited=v['missing']/v['n']>.05)
 return {'n':total,'missing':bad,'rate':bad/total if total else 1.,'arms':arms}

def missing_gate(report):
 if report['rate']>.20:raise ValueError('More than20% pooled smoke cells MISSING')

def projection(run):
 g=Guard(run);run=Path(run);a=read(run/'smoke/target_timing.json');b=read(run/'smoke/nla_timing.json')
 expected={(i,arm,v) for i in g.plan['smoke_ids'] for arm,v in CELLS}
 for name in ('model',)+READERS:
  rr=rows(run/'smoke'/(name+'.jsonl'))
  if len(rr)!=len(expected) or {(r['item'],r['arm'],r['alpha']) for r in rr}!=expected:raise ValueError('Incomplete smoke '+name)
 missing=missing_summary({name:rows(run/'smoke'/(name+'.jsonl')) for name in ('model',)+READERS});save(run/'smoke/missing_summary.json',missing);missing_gate(missing)
 rate=(a['capture_s']+sum(a['reader_s'].values())+b['score_s'])/len(g.plan['smoke_ids'])
 # Includes repeated target/NLA loading, capture setup conservatively repeated, 25% execution margin.
 estimate=1.25*(len(chosen_records(g.plan,False))*rate+a['setup_s']+b['setup_s']);remaining=g.booking['deadline']-time.time()-g.reserve
 report={'shard_id':g.plan['shard_id'],'remaining_items':len(chosen_records(g.plan,False)),'projected_science_s':estimate,'remaining_science_s':remaining,'pull_reserve_s':g.reserve,'admitted':estimate<remaining,'smoke_files':{p.name:sha(p) for p in (run/'smoke').iterdir() if p.is_file()}}
 save(run/'projection.json',report)
 if not report['admitted']:raise RuntimeError('Timing gate failed; preserve partial, no retry or scope reduction')
 return report

def paired_ci(values,groups=None):
 x=np.asarray(values,float);rng=np.random.default_rng(0);means=[]
 if groups is None:
  for _ in range(2000):means.append(x[rng.integers(0,len(x),len(x))].mean())
 else:
  unique=sorted(set(groups));indices=[np.where(np.asarray(groups)==v)[0] for v in unique]
  for _ in range(2000):means.append(x[np.concatenate([indices[j] for j in rng.integers(0,len(indices),len(indices))])].mean())
 return [float(v) for v in np.quantile(means,[.025,.975])]

def analyze(run):
 run=Path(run)
 if (run/'booking.json').exists() and 'shard_id' in read(run/'booking.json'):return analyze_shard(run)
 plan=read(REG/'plan.json');ids=[r['id'] for r in plan['records']];bank={r['id']:r for r in plan['records']};models=rows(run/'smoke/model.jsonl')+rows(run/'full/model.jsonl');expected={(i,a,v) for i in ids for a,v in CELLS}
 m={(r['item'],r['arm'],r['alpha']):r for r in models}
 if len(models)!=len(expected) or set(m)!=expected:raise ValueError('Model coverage/duplicates')
 flips={}
 for arm in ARMS:
  for alpha in ALPHAS:
   k=sum(m[i,arm,alpha]['flip'] is True for i in ids);u=sum(m[i,arm,alpha]['flip'] is None for i in ids)
   flips[f'{arm}/{alpha}']={'k':k,'unresolved':u,'n':196,'rate_bounds':[k/196,(k+u)/196],'wilson95':wilson(k+u),'wilson_observed':wilson(k),'bound_policy':'all unresolved count as flips for confirmatory upper bound'}
 output={}
 for reader in READERS:
  rr=rows(run/f'smoke/{reader}.jsonl')+rows(run/f'full/{reader}.jsonl');d={(r['item'],r['arm'],r['alpha']):r['lo_original_minus_donor'] for r in rr}
  if len(rr)!=len(expected) or set(d)!=expected:raise ValueError('Reader coverage/duplicates '+reader)
  table={}
  for alpha in ALPHAS:
   # Native follow: positive movement toward donor relative to the same item's natural margin.
   bounds={a:follow_bounds(d,ids,a,alpha) for a in ARMS}
   low={a:v[0] for a,v in bounds.items()};high={a:v[1] for a,v in bounds.items()}
   contrast_low=low['J']-(high['random0']+high['random1'])/2
   contrast_high=high['J']-(low['random0']+low['random1'])/2
   groups=[None,[bank[i]['bridge'] for i in ids],[bank[bank[i]['donor']]['bridge'] for i in ids]]
   lower=[paired_ci(contrast_low,g)[0] for g in groups];upper=[paired_ci(contrast_high,g)[1] for g in groups]
   ci=[min(lower),max(upper)];j=float(low['J'].mean());p=float(high['perp'].mean())
   passed=alpha==1 and flips['J/1.0']['wilson95'][1]<=.05 and ci[0]>0 and j>=.8*p
   table[str(alpha)]={'follow_rate_bounds':{a:[float(low[a].mean()),float(high[a].mean())] for a in ARMS},
     'unresolved_follow_items':{a:int((high[a]-low[a]).sum()) for a in ARMS},'denominator':196,
     'J_minus_random_bounds':[float(contrast_low.mean()),float(contrast_high.mean())],'ci95_envelope':ci,
     'J_at_least_0.8_perp':j>=.8*p,'missing_native_cells':sum(d[i,a,alpha] is None for i in ids for a in ARMS),
     'missing_cells_by_arm':{a:sum(d[i,a,alpha] is None for i in ids) for a in ARMS},
     'missing_natural_cells':sum(d[i,'natural',0.] is None for i in ids),
     'verdict':('CIRCULAR_DESCRIPTIVE' if reader=='jlens' else 'SENSITIVITY WITHOUT USE' if passed else 'CRITERION NOT MET' if alpha==1 else 'DESCRIPTIVE')}
  output[reader]=table
 report={'section':49,'n':196,'flip_definition':'greedy up to 64 tokens; first registered whole-phrase entity, longest at same offset; compare natural; unresolved retained with conservative flip upper bound','missing_summary':missing_summary({name:rows(run/f'smoke/{name}.jsonl')+rows(run/f'full/{name}.jsonl') for name in ('model',)+READERS}),'parse_report':parse_report(models),'flips':flips,'readers':output};save(run/'RESULTS.json',report);return report

def analyze_shard(run,write=True):
 run=Path(run);booking=read(run/'booking.json');plan=shard_plan(booking['shard_id'])
 if booking['shards_sha256']!=sha(REG/'shards.json'):raise ValueError('Shard assignment mismatch')
 expected={(i,a,v) for i in plan['recipient_ids'] for a,v in CELLS};tables={}
 for name in ('model',)+READERS:
  rr=rows(run/f'smoke/{name}.jsonl')+rows(run/f'full/{name}.jsonl')
  if len(rr)!=len(expected) or {(r['item'],r['arm'],r['alpha']) for r in rr}!=expected:raise ValueError('Shard coverage/duplicates '+name)
  tables[name]=rr
 result={'section':49,'shard_id':plan['shard_id'],'n':49,'status':'SHARD_COMPLETE_NO_CONFIRMATORY_VERDICT','item_ids':plan['recipient_ids'],'missing_summary':missing_summary(tables),'shards_sha256':sha(REG/'shards.json')}
 if write:save(run/'SHARD_RESULTS.json',result)
 return result

def merge_shards(inputs,out):
 inputs=list(map(Path,inputs));out=Path(out)
 if len(inputs)!=4:raise ValueError('Require all four verified shards')
 seen=set();source_commits=set();tables={name:[] for name in ('model',)+READERS};sources=[]
 for run in inputs:
  manifest=read(run/'manifest.json');receipt=read(run/'mac_receipt.json');released=read(run/'release.json')
  if receipt['manifest_sha256']!=sha(run/'manifest.json') or receipt['files']!=manifest or released['manifest_sha256']!=sha(run/'manifest.json') or released['status']!='VERIFIED_READY_TO_STOP':raise ValueError('Unverified shard')
  for rel,h in manifest.items():
   path=(run/rel).resolve()
   if not path.is_relative_to(run.resolve()) or sha(path)!=h:raise ValueError('Shard pull hash mismatch')
  required={'booking.json','chain_result.json','SHARD_RESULTS.json'}|{f'{phase}/{name}.jsonl' for phase in ('smoke','full') for name in ('model',)+READERS}
  if not required<=set(manifest):raise ValueError('Required files absent from manifest')
  booking=read(run/'booking.json');stop=read(run.parent/'stop.json')
  if stop['status']!='EXITED' or stop['pod']!=booking['pod_id']:raise ValueError('Shard pod closure unverified')
  source_commits.add(booking['source_commit'])
  result=analyze_shard(run,write=False);sid=result['shard_id']
  if read(run/'SHARD_RESULTS.json')!=result:raise ValueError('Shard result mismatch')
  if sid in seen:raise ValueError('Duplicate shard')
  if read(run/'chain_result.json')['status']!='COMPLETE':raise ValueError('Incomplete shard')
  seen.add(sid);sources.append({'shard_id':sid,'manifest_sha256':sha(run/'manifest.json')})
  for name in tables:tables[name]+=rows(run/f'smoke/{name}.jsonl')+rows(run/f'full/{name}.jsonl')
 if seen!=set(range(4)):raise ValueError('Missing shard')
 if len(source_commits)!=1:raise ValueError('Mixed shard sources')
 out.mkdir(parents=True,exist_ok=False);(out/'full').mkdir()
 for name,rr in tables.items():
  for r in rr:append(out/'full'/f'{name}.jsonl',r)
 save(out/'merged_sources.json',sources)
 return analyze(out)

def package(run):
 run=Path(run);manifest={}
 for p in sorted(run.rglob('*')):
  if p.is_file() and p.name not in ('manifest.json','mac_receipt.json','release.json','progress.txt') and 'inputs' not in p.relative_to(run).parts:
   manifest[str(p.relative_to(run))]=sha(p)
 save(run/'manifest.json',manifest);return manifest

def mac_receipt(local):
 local=Path(local);manifest=read(local/'manifest.json')
 for rel,h in manifest.items():
  if sha(local/rel)!=h:raise ValueError('Local pull mismatch '+rel)
 result={'manifest_sha256':sha(local/'manifest.json'),'files':manifest,'verified_at':time.time()};save(local/'mac_receipt.json',result);return result

def release(run,local):
 run=Path(run);receipt=read(local);manifest=read(run/'manifest.json')
 if receipt['manifest_sha256']!=sha(run/'manifest.json') or receipt['files']!=manifest:raise ValueError('Manifest differs')
 for rel,h in manifest.items():
  if sha(run/rel)!=h:raise ValueError('Retained hash mismatch '+rel)
 result={'status':'VERIFIED_READY_TO_STOP','manifest_sha256':sha(run/'manifest.json'),'files':len(manifest)};save(run/'release.json',result);return result

def pipeline(run):
 run=Path(run);g=Guard(run);save(run/'controller.json',{'pid':os.getpid(),'started':time.time()})
 code=0
 try:
  for phase in ['target-smoke','nla-smoke','projection','target-full','nla-full','analyze']:
   g();left=g.booking['deadline']-time.time()-g.reserve
   with (run/(phase+'.log')).open('w') as log:
    child=subprocess.Popen([sys.executable,'-m','projects.g_agreement.r_bench.section49',phase,'--run',str(run)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:rc=child.wait(timeout=max(.1,left))
    except subprocess.TimeoutExpired:
     os.killpg(child.pid,signal.SIGTERM)
     try:child.wait(timeout=10)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait()
     raise TimeoutError('Science subprocess deadline reached')
    if rc:raise RuntimeError('Stage failed: '+phase+' exit '+str(rc))
 except Exception as exc:
  code=1;save(run/'failure.json',{'error':str(exc),'time':time.time()})
 finally:
  save(run/'science_exit.json',{'code':code,'time':time.time()});package(run)
 return {'exit':code,'manifest_sha256':sha(run/'manifest.json')}

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','target-smoke','nla-smoke','projection','target-full','nla-full','analyze','package','release','mac-receipt','pipeline','merge-shards']);p.add_argument('--shard-inputs',nargs=4,type=Path);p.add_argument('--run',type=Path);p.add_argument('--local',type=Path);a=p.parse_args()
 if a.action=='merge-shards':print(json.dumps(merge_shards(a.shard_inputs,a.run)))
 elif a.action=='prepare':prepare()
 elif a.action=='mac-receipt':print(json.dumps(mac_receipt(a.local)))
 elif a.action=='pipeline':print(json.dumps(pipeline(a.run)))
 elif a.action.startswith('target-'):target_stage(a.run,a.action.endswith('smoke'))
 elif a.action.startswith('nla-'):nla_stage(a.run,a.action.endswith('smoke'))
 else:print(json.dumps({'projection':projection,'analyze':analyze,'package':package,'release':lambda r:release(r,a.local)}[a.action](a.run)))
if __name__=='__main__':main()
