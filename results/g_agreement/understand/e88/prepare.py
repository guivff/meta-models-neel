"""E88 source binding and frozen inventories; no rate/bootstrap/leakage analysis."""
import ast,hashlib,importlib,json,math,os,sys
from pathlib import Path
import numpy as np
from audit import HERE,ROOT,CACHE,read as rawread,sha,write,SEED,signed
WT=ROOT.parent;U=ROOT/'results/g_agreement/understand';M=WT/'wt-wmech';I=WT/'wt-i2';N=WT/'wt-blindspot-internals'
sources={}
def bind(p,h=None):
 p=Path(p).resolve();actual=sha(p)
 if h is not None and actual!=h:raise ValueError('input hash: '+str(p))
 if str(p) in sources and sources[str(p)]!=actual:raise ValueError('source changed')
 sources[str(p)]=actual;return p
def read(p):return rawread(bind(p))
def seal(p,name='ANALYSIS_SEAL.json'):
 p=Path(p);s=read(p/name)
 for n,h in s['files'].items():bind(p/n,h['sha256']if isinstance(h,dict)else h)
 return s
def main():
 sys.dont_write_bytecode=True;CACHE.mkdir(parents=True,exist_ok=True,mode=0o700)
 sys.path.insert(0,str(ROOT/'results/g_agreement/discovery2'))
 import evidence_native as en,evidence_e54 as e54,evidence_positions as ep,evidence_e67 as e67
 for mod in [en,e54,ep,e67]:bind(mod.__file__);mod.read=read
 native={b:en.load_native(b,True)for b in ['E49','E56','E57','E59','E62']}
 native['E54']=e54.load_e54(True);native['E73']=ep.load_e73_records()
 items={};tokens=[];coverage={};probes=[];records=[]
 # Full original dev/test banks, independent of native sampling.
 s=read(M/'results/g_agreement/understand/e49/job/INPUT_BINDING.json');items['E49']=rawread(bind(s['private_items_path'],s['private_items_sha256']))
 s54=N/'cache/g_agreement/understand/e5354/bound_inputs_21a39c48';seal(s54,'INPUT_SEAL.json');items['E54']=read(s54/'e54_items.json')
 y54=read(N/'results/g_agreement/understand/e5354/E54_CPU_LABELS.json')
 pair54={hashlib.sha256(('E54|'+x['id']).encode()).hexdigest()[:24]:x for x in items['E54']}
 for b in ['E56','E57','E59','E62']:
  spec=read(M/('results/g_agreement/understand/'+('analysis5968'if b=='E59'else'analysis402')+'/'+b+'_SPEC.json'))
  items[b]=rawread(bind(spec['private_items'],spec['private_items_sha256']))
 plan73=read(I/'results/g_agreement/i2/E73_ONCE_ANALYSIS_INPUT_PLAN.json');items['E73']=[]
 for bank in plan73['banks']:
  s=read(bank['builder_spec']);ip=bind(s['items'],plan73['input_bindings'][s['items']]);lp=bind(s['labels'],plan73['input_bindings'][s['labels']]);labels={x['id']:x for x in map(json.loads,lp.read_text().splitlines())}
  for x in map(json.loads,ip.read_text().splitlines()):
   l=labels[x['id']];ids=x['input_ids'];items['E73'].append(dict(id=x['id'],feature=l['state'],split=l['split'],ids=ids,text=None))
 # Decoder supplies exact capture-prefix text for E73 token audit/leakage.
 from tokenizers import Tokenizer
 pin=read(U/'e52/BASIS_INPUTS_2026-10-27.json')['files']['tokenizer'];tok=Tokenizer.from_file(str(bind(pin['path'],pin['sha256'])))
 for x in items['E73']:x['text']=tok.decode(x['ids'],skip_special_tokens=False)
 # Signed scores are derived in the separate once-only audit, not here.
 for b,xs in native.items():
  skipped=0
  for x in xs:
   j=x['judge'];truth=x.get('_truth');row=x.get('feature',x.get('row'))
   if b=='E49':continue # exact frozen regex categories bound separately below
   if b=='E54':
    it=pair54[x['pair_id']];v=y54[it['id']];truth='A' if (v['label']if isinstance(v,dict)else v)==1 else 'B'
   if b=='E73':truth='AB'[truth];j=j['code']if j['status']=='KEPT'else dict(category='UNPARSEABLE',values=[])
   if truth not in ('A','B') or not j or 'category'not in j:skipped+=1;continue
   records.append(dict(bank=b,reader=x['reader'],row=row,item_id=x['pair_id'],label=1 if truth=='A'else 0,judgment=j))
  coverage[b]=dict(native_readouts=len(xs),excluded_nonbinary_or_unbound=skipped)
 # Regex detector is the original E49 source, with immutable label orientation.
 path=M/'results/g_agreement/understand/e49/job/statements49.py';bind(path)
 sys.path.insert(0,str(path.parent));import statements49
 for x in native['E49']:
  label=1 if x['_truth']=='A'else 0
  # Freeze raw records and definition, evaluate only inside the audit invocation.
  records.append(dict(bank='E49',reader=x['reader'],row=x['feature'],item_id=x['pair_id'],regex=True,text=x['text'],label=label))
 for b in items:
  xs=sorted(items[b],key=lambda x:x['id']);assert len({x['id']for x in xs})==len(xs)
  rng=np.random.default_rng(SEED);sample=sorted(rng.choice(len(xs),size=math.ceil(.05*len(xs)),replace=False))
  for i in sample:
   x=xs[i];ids=x['ids'];idx=x.get('read_index',len(ids)-1)
   tokens.append(dict(bank=b,item_id=x['id'],ids=ids,text=x['text'],registered_index=idx,capture_index=None))
  coverage[b].update(full_items=len(xs),dev=sum(x['split']=='dev'for x in xs),test=sum(x['split']=='test'for x in xs),token_sample=len(sample))
 # Bind capture order + the frozen index-selection implementation, not merely
 # a fresh re-tokenisation of a prompt. No activation recomputation.
 capture_ids={};index_maps={};proof={}
 spec49=read(M/'results/g_agreement/understand/e49/job/ANALYSIS_SPEC.json')
 for b,folder in [('E49',Path(spec49['verified_output'])/'capture'),('E54',N/'cache/g_agreement/understand/e5354/verified_output_d8z2quqdxth285/e54_capture')]:
  cap=read(folder/'CAPTURE_SEAL.json')
  for n in ['CAPTURE_METADATA.json','items.order.json']:bind(folder/n,cap['files'][n])
  meta=read(folder/'CAPTURE_METADATA.json');assert meta['read_position']=='last raw-prefix token'
  capture_ids[b]=set(read(folder/'items.order.json'));proof[b]='sealed capture metadata and exact item order: last raw-prefix token'
 backend=bind(M/'results/g_agreement/understand/e49/job/vendor/e36_worker.py')
 assert '[[len(x["ids"]) - 1] for x in items]'in backend.read_text()
 for b in ['E56','E57']:
  s=read(U/'analysis402'/f'{b}_SPEC.json');capture_ids[b]=set()
  for folder in s['outputs']:
   folder=Path(folder)/'capture';cap=read(folder/'CAPTURE_SEAL.json');bind(folder/'items.order.json',cap['files']['items.order.json']);capture_ids[b].update(read(folder/'items.order.json'))
  proof[b]='sealed capture order; frozen E49 NativeBackend capture inherited by worker56/joint_worker, len(ids)-1'
 for b,sp in [('E59',M/'results/g_agreement/understand/e59/job/ANALYSIS_SPEC.json'),('E62',U/'analysis402/E62_SPEC.json')]:
  s=read(sp)
  if b=='E59':s=read(M/'cache/g_agreement/understand/analysis5968_verified/E59/RECEIPT.json')
  folder=Path(s['output'])/'capture';cap=read(folder/'CAPTURE_SEAL.json');bind(folder/'items.order.json',cap['files']['items.order.json']);capture_ids[b]=set(read(folder/'items.order.json'))
  if b=='E62':
   bind(folder/'POSITIONS.json',cap['files']['POSITIONS.json']);index_maps[b]={x['id']:x['read_index']for x in read(folder/'POSITIONS.json')};proof[b]='sealed POSITIONS.json read_index'
  else:proof[b]='sealed capture order; frozen inherited NativeBackend last raw-prefix token'
 cp=bind(I/'cache/g_agreement/i2/e73_analysis_once_candidate/frozen/projects/g_agreement/e73/capture.py')
 assert 'read token 255'in cp.read_text();capture_ids['E73']=set();proof['E73']='hash-bound capture implementation block42 read token255; operator provenance row union'
 for folder in [I/'cache/g_agreement/i2/operator_c_attempt2/capture_pull',I/'cache/g_agreement/i2/operator_c_controls_20261027_a2/capture_pull']:
  op=read(folder/'OPERATOR_PROVENANCE.json');assert sha(cp)==op['source_files']['projects/g_agreement/e73/capture.py']
  capture_ids['E73'].update(x['id']for shard in op['shards']for x in shard['rows'])
 for x in tokens:
  assert x['item_id']in capture_ids[x['bank']]
  x['capture_index']=index_maps.get(x['bank'],{}).get(x['item_id'],255 if x['bank']=='E73'else len(x['ids'])-1)
  x['capture_index_proof']=proof[x['bank']]
 # Aggregate probe values only. Each source analysis must already be sealed.
 gates=read(M/'results/g_agreement/understand/e49/job/analysis/GATES.json')
 for row,x in gates['rows'].items():probes.append(dict(bank='E49',row=row,AUROC=x['probe'],source='E49 sealed GATES.json',orientation='label1=A; test score for class1',resolution='No automatic inversion; audit code/labels before interpretation'))
 agg=read(N/'results/g_agreement/understand/e5354/analysis_c9076571_541b23b1/E54_RESULTS.json')
 for x in agg['rows']:probes.append(dict(bank='E54',row=x['row'],AUROC=x['probe'],source='E54 sealed RESULTS',orientation='frozen E54 CPU labels',resolution='No refit or inversion'))
 pre=read(U/'e75/QWEN_PREFLIGHT_2026-10-28.json')
 for b,a in pre['analysis_bindings'].items():
  ap=Path(a['analysis_seal']);bind(ap,a['analysis_seal_sha256']);seal(ap.parent)
  res=read(a['results']);p=ap.parent/'PROBE.json'
  if b=='E73':probe={x['state']:x['test_auroc']for x in res['primary']['probe_rows']}
  else:probe=read(p)if p.exists()else res.get('probe',{})
  for row,v in probe.items():
   if isinstance(v,(float,int)):probes.append(dict(bank=b,row=row,AUROC=v,source=str(p if p.exists()else a['results']),orientation='E73 label0=A/1=B; others label1=A/0=B; score class1',resolution='No automatic inversion; low score needs source-code trace'))
 counts67=[]
 for wave in (1,2):
  for x in e67.load_e67(wave):counts67.append(dict(wave=wave,reader=x['reader'],bank=x['bank'],row=x['row'],condition=x['condition'],status=x['status']))
 coverage['E67']=dict(status='DERIVED_READOUT_JUDGING_BANK',lineage='Both waves sampled source-bank native readouts; inherited dev/test and read-token findings; native S not its registered claim metric')
 coverage['E75']=dict(status='DERIVED_FORECAST_ANALYSIS',lineage='No own prompts/captures/probe fits; inherits included original banks; no invented native S')
 # Uniform item5 sample; no condition/quality filters.
 pool=[x for b in ['E49','E57','E73']for x in native[b]];pool.sort(key=lambda x:(x['bank'],x['reader'],x['opaque_id']))
 rng=np.random.default_rng(SEED);selected=[pool[i]for i in sorted(rng.choice(len(pool),300,replace=False))]
 key=[];packet=[]
 for n,x in enumerate(selected):
  opaque=hashlib.sha256(('E88-5|'+str(n)+'|'+x['opaque_id']).encode()).hexdigest()[:32]
  key.append(dict(id=opaque,bank=x['bank'],reader=x['reader'],row=x.get('feature',x.get('row')),source_opaque_id=x['opaque_id'],pair_id=x['pair_id']))
  packet.append(dict(id=opaque,readout=x['text'],property=x.get('property'),values=x.get('values',x.get('value_descriptions')),original_judgment=x['judge']))
 # Original judgments in this private inventory must be stripped from blind wire.
 write(CACHE/'ITEM5_SAMPLE_v2.PRIVATE.json',dict(key=key,records=packet,seed=SEED,n=300,blind_wire_required=True))
 write(CACHE/'ITEM6_INVENTORY_v2.PRIVATE.json',[dict(x,bank=b)for b in ['E49','E54']for x in native[b]])
 data=dict(items=items,raw_signed_records=records,probes=probes,token_sample=tokens,coverage=coverage,e67_terminal_status=counts67,judging_pending={'5':'300-record sample frozen; route/dispatch through authorised judging owner; no API call from W-lens','6':'Full E49/E54 detector inventory frozen; Track Q supplies §172+§202 judgments'})
 write(CACHE/'CPU_INPUTS_v2.PRIVATE.json',data)
 for f in CACHE.glob('*.PRIVATE.json'):os.chmod(f,0o600)
 # Source code and manifest are frozen before invoking analysis.
 code={f:sha(HERE/f)for f in ['audit.py','near_duplicate.cpp','prepare.py','BRIEF_E88.md']}
 write(HERE/'CPU_PLAN_v2.json',dict(experiment='E88',scope='CPU items1-4; judging inventory5-6',sources=sources,code=code,data={'path':str(CACHE/'CPU_INPUTS_v2.PRIVATE.json'),'sha256':sha(CACHE/'CPU_INPUTS_v2.PRIVATE.json')},seed=SEED,source_verdicts_unchanged=True))
 print('E88 source/input inventory frozen; no audit statistics computed')
if __name__=='__main__':main()
