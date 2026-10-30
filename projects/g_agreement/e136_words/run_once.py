"""Integrator-only §247 words once command; no source discovery/model calls."""
import argparse,json,hashlib,os
from pathlib import Path
import joblib
from .words import analyze
from projects.g_agreement.e136.bank import TASKS
ROOT=Path(__file__).resolve().parents[3]
CUES=('sycophancy_pressure','misuse_intent')

def active_scope(xs):
 result=[x for x in xs if x['cue'] in CUES]
 if len(result)!=400 or len({x['id'] for x in result})!=400:raise ValueError('exact400 original active prompts')
 for c in CUES:
  for split,n in [('dev',40),('test',160)]:
   rs=[x for x in result if x['cue']==c and x['split']==split]
   if len(rs)!=n or sum(x['label'] for x in rs)!=n//2:raise ValueError('original balanced20DEV/80TESTpairs percue')
 return result
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def verify(root,name,h):
 root=Path(root).resolve()
 if sha(root/name)!=h:raise ValueError('seal identity')
 s=read(root/name)
 for n,d in s['files'].items():
  p=(root/n).resolve()
  if not p.is_relative_to(root) or sha(p)!=d:raise ValueError('sealed member identity')
 return s

def labels():
 b=read(ROOT/'results/g_agreement/understand/e136/INPUT_BINDING.json');root=Path(b['CPU_only_root']);verify(root,'LABEL_SEAL.json',b['CPU_label_seal_sha256'])
 xs=read(root/'LABELS.PRIVATE.json')
 if len(xs)!=800 or len({x['id'] for x in xs})!=800:raise ValueError('original800labels')
 for x in xs:
  task=TASKS[x['base_task']]
  if (x['correct'],x['wrong'])!=(task[1],task[2]):raise ValueError('frozen task answer binding')
  x['fact_sentence']=task[3]
 return b,{x['id']:x for x in active_scope(xs) if x['split']=='test'}

def load_readouts(spec,key):
 # SPEC entries are source pointers, never copied readout text. Identity checks are
 # literal raw-record fields (e.g. unit_id, reader, block), frozen by producer.
 entries=spec['entries'];expected={(i,b) for i in key for b in (44,)}
 if len(entries)!=len(expected) or {(x['item_id'],x['block']) for x in entries}!=expected:raise ValueError('exact320TEST id/layer source pointers')
 result={};seen=set();cache={};seals={}
 for e in entries:
  root=Path(e['root']).resolve();sk=(str(root),e['seal_name'],e['seal_sha256'])
  if sk not in seals:seals[sk]=verify(root,e['seal_name'],e['seal_sha256'])
  s=seals[sk]
  if e['member'] not in s['files']:raise ValueError('unsealed readout member')
  loc=(str(root),e['member']);slot=(loc,tuple(e['record_path']))
  if slot in seen:raise ValueError('reused physical readout')
  seen.add(slot)
  if loc not in cache:cache[loc]=read(root/e['member'])
  r=cache[loc]
  for k in e['record_path']:r=r[k]
  if not e['identity'] or any(r.get(k)!=v for k,v in e['identity'].items()):raise ValueError('literal original record identity')
  if e['item_id'] not in e['identity'].values():raise ValueError('raw identity must bind original publicitemID')
  # Layer has to occur literally in record identity or in the frozen source member name.
  if e['block'] not in e['identity'].values() and str(e['block']) not in e['member']:raise ValueError('source layer identity')
  text=r[e['text_field']]
  if not isinstance(text,str):raise ValueError('native text missing, never impute')
  label=key[e['item_id']]
  result[e['item_id'],e['block']]=dict(id=e['item_id'],text=text,base_task=label['base_task'],pair_id=label['pair_id'],split=label['split'],label=label['label'],cue=label['cue'],correct=label['correct'],wrong=label['wrong'],fact_sentence=label['fact_sentence'])
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path);p.add_argument('--out',type=Path);p.add_argument('--validate-inputs-only',action='store_true');a=p.parse_args()
 seal=read(Path(__file__).with_name('CODE_SEAL.json'))
 for n,h in seal['files'].items():
  if sha(ROOT/n)!=h:raise ValueError('frozen words code')
 binding,key=labels()
 if a.validate_inputs_only:
  if a.spec or a.out:raise ValueError('inputs-only cannot open outputs')
  print('PASS800originalCPUlabels/400activeprompts/320TESTids, no readout opened');return
 if not a.spec or not a.out:raise ValueError('explicit sealed source SPEC and freshout required')
 # Fixed across checkouts, consumed before first native readout opening.
 guard=Path(binding['CPU_only_root']).parent/'E136_WORDS_ONCE.json'
 with guard.open('x') as f:json.dump(dict(spec_sha256=sha(a.spec),code_sha256=sha(Path(__file__).with_name('CODE_SEAL.json')),out=str(a.out.resolve())),f)
 a.out.mkdir(parents=True,exist_ok=False);spec=read(a.spec);rows=load_readouts(spec,key);metrics={};oof=[]
 for block in (44,):
  metrics[str(block)]={}
  for cue in CUES:
   xs=sorted([r for (i,b),r in rows.items() if b==block and r['cue']==cue],key=lambda r:r['id'])
   primary=None
   for view,exclude in [('excluded',True),('unexcluded_descriptive',False)]:
    result,pred,models,audit=analyze(xs,exclude=exclude)
    if primary is None:primary=result;metrics[str(block)][cue]=primary
    else:primary['unexcluded_descriptive']=result
    joblib.dump(models,a.out/f'MODELS_{block}_{cue}_{view}.joblib');write(a.out/f'FOLDS_{block}_{cue}_{view}.PRIVATE.json',audit)
    oof += [dict(id=r['id'],block=block,cue=cue,view=view,probability=float(v),label=r['label'],pair_id=r['pair_id'],base_task=r['base_task']) for r,v in zip(xs,pred)]
 write(a.out/'METRICS.json',dict(experiment='E136_WORDS',blocks=metrics,primary_block=44,overall_R_SW1='BOTH_ACTIVE_CUES_REQUIRE_PROBE_GATE_AND_NAMED_AND_EXCLUDED_CARRIED; SEPARATE_SEALED_JOIN_REQUIRED',no_overall_verdict=True,report_order=list(CUES),not_run_cues=['unreliable_tool','instruction_to_withhold'],active_pairs=200,active_prompts=400,test_pairs_per_cue=80,dev_pairs_per_cue=20))
 write(a.out/'OOF.PRIVATE.json',oof);write(a.out/'SOURCE_SPEC.PRIVATE.json',spec)
 write(a.out/'ANALYSIS_SEAL.json',dict(experiment='E136_WORDS',status='COMPLETE_ONCE',code_sha256=sha(Path(__file__).with_name('CODE_SEAL.json')),input_sha256=binding['input_seal_sha256'],source_spec_sha256=sha(a.spec),files={x.name:sha(x) for x in a.out.iterdir() if x.is_file()}))
 print('COMPLETE_ONCE '+sha(a.out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':main()
