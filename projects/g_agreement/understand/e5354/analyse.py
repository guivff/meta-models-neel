"""Once-only CPU analysis after verified pull and sealed map/blind judgments."""
import argparse,sys,re
from .contract import *
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from .e15_scorer import valid_pairs
from .judgment_adapter import adapt, bucket, context_binding

def score_grid(raw,items,old,i54):
 expected={(x['id'],'E49','base','true') for x in items if x['split']=='dev'}
 expected|={(x['id'],'E49',r,a) for x in items if x['split']=='test' for r in ('olens','nla') for a in ('true','opposite_swap')}
 expected|={(x['id'],'E36','olens','opposite_swap') for x in old}
 expected|={(x['id'],'E54',r,'native') for x in i54 if x['split']=='test' for r in ('olens','nla')}
 keys=[(x['id'],x['bank'],x['reader'],x['arm']) for x in raw]
 require(len(keys)==len(set(keys)) and set(keys)==expected,'exact output grid, no missing/duplicate/extra records')
 for x in raw:
  if x['arm']!='native':require(len(x['scores'])==(2 if x['bank']=='E36' else 1) and np.isfinite(x['scores']).all(),'score vector')
  else:require(isinstance(x['text'],str) and isinstance(x['raw'],str) and type(x['malformed']) is bool,'native record')
 return dict(zip(keys,raw))

def analyse(a):
 sources();verify(a.inputs,'INPUT_SEAL.json');s=verify(a.outputs,'OUTPUT_SEAL.json',a.output_seal)
 worker_sha=read(HERE/'SOURCE_SEAL.json').get('worker_source_seal_sha256',sha(HERE/'SOURCE_SEAL.json'))
 require(s.get('status')=='COMPLETE' and s['input_seal_sha256']==sha(a.inputs/'INPUT_SEAL.json') and s['source_seal_sha256']==worker_sha,'complete bound output')
 cs=verify(a.context,'INPUT_SEAL.json',a.context_seal);require({'MAP.json','JUDGMENTS.json'}<=set(cs['files']),'unsealed analysis context')
 context_binding(a.context,cs,HERE)
 context=read(a.context/'MAP.json');judgments=read(a.context/'JUDGMENTS.json')
 require(context.get('source_seals') and context.get('issuer')=='integrator','map provenance required')
 for x in context['rows']:
  require(x['J_label'] in ('IN-J','OUT-J','DIFFUSE','NOT EVALUABLE'),'authoritative pursuit J label')
  require(x.get('J_label_method')=='§169 amendment1 pursuit','SVD secondary label must not enter R1')
  for k in ['probe_auc','oracle_unprompted_mention_rate']:
   require(x[k] is None or (isinstance(x[k],(float,int)) and np.isfinite(x[k]) and 0<=x[k]<=1),'map numeric field')
 keys=[(x['bank'],x['row']) for x in context['rows']];require(len(keys)==len(set(keys)),'duplicate map rows');mapping=dict(zip(keys,context['rows']))
 items=read(a.inputs/'e49_items.json');old=read(a.inputs/'e36_items.json');i54=read(a.inputs/'e54_items.json')
 raw=[json.loads(l) for l in (a.outputs/'scores.jsonl').read_text().splitlines()];scores=score_grid(raw,items,old,i54)
 keys=[(x['id'],x['reader']) for x in judgments];expected={(x['id'],r) for x in i54 if x['split']=='test' for r in ('olens','nla')}
 require(len(keys)==len(set(keys)) and set(keys)==expected,'all E54 readouts blind-judged exactly once')
 judgments=[adapt(x) for x in judgments]
 require(all(x.get('blinded') is True and x.get('raw_sha256')==hashlib.sha256(scores[x['id'],'E54',x['reader'],'native']['raw'].encode()).hexdigest() for x in judgments),'judgment schema/identity')
 required={(b,r) for b in ('W1','E36') for r in {x['feature'] for x in old}}|{('E49',x['feature']) for x in items}|{('E54',x['feature']) for x in i54}
 require(required<=set(mapping),'map must explicitly represent every planned row; missing values use null')
 lock=ROOT/'cache/g_agreement/understand/e5354/ANALYSIS_ONCE.json';lock.parent.mkdir(parents=True,exist_ok=True);dump(lock,{'output_seal':a.output_seal,'context_seal':a.context_seal})
 a.out.mkdir(parents=True,exist_ok=False)
 try:
  from dataclasses import asdict
  from mats.metrics import auroc_ci
  labels=read(HERE/'CPU_LABELS.json');y36=read(HERE/'E36_CPU_LABELS.json');y54=read(HERE/'E54_CPU_LABELS.json')
  prior=read(HERE/'EXISTING_ASSEMBLY.json')['rows'];rows=[]
  def estimate(y,x,g):return asdict(auroc_ci(np.array(x),np.array(y),np.array(g),n_boot=2000,seed=20261023))
  for r in sorted({x['feature'] for x in items}):
   dev=[x for x in items if x['feature']==r and x['split']=='dev'];test=[x for x in items if x['feature']==r and x['split']=='test']
   dv=[scores[x['id'],'E49','base','true']['scores'][0] for x in dev];v=valid_pairs([auc([labels[x['id']]['label'] for x in dev],dv)])
   for reader in ('olens','nla'):
    arm={}
    for k in ('true','opposite_swap'):
     arm[k]=estimate([labels[x['id']]['label'] for x in test],[scores[x['id'],'E49',reader,k]['scores'][0] for x in test],[x['cluster'] for x in test])
    rows.append({'bank':'E49','row':r,'reader':reader,'valid_pairs':v,'status':'EVALUABLE' if v else 'NOT EVALUABLE','all_pairs_descriptive':arm,'continuation':arm['true'] if v else None,'opposite_swap':arm['opposite_swap'] if v else None,'native_status':'PRIMARY' if reader=='olens' else 'DESCRIPTIVE_OFF_NATIVE'})
  for p in prior:
   z=dict(p)
   if p['bank']=='E36':
    xx=[x for x in old if x['feature']==p['row']];valid=p['valid_pairs'];require(valid and all(i in (0,1) for i in valid),'frozen E36 mask')
    z['opposite_swap']=estimate([y36[x['id']] for x in xx],[np.mean(np.array(scores[x['id'],'E36','olens','opposite_swap']['scores'])[valid]) for x in xx],[x['cluster'] for x in xx]);z['swap_status']='SEALED_NEW_CONTROL'
   rows.append(z)
  # Registered R1: pooled OUT-J structure rows; bank-specific summaries alongside.
  evaluable=[]
  for z in rows:
   m=mapping[z['bank'],z['row']];z['map']=m
   value=z.get('continuation_auroc') if z['bank']=='E36' else (z.get('continuation') or {}).get('auroc')
   swap=(z.get('opposite_swap') or {}).get('auroc');mention=m['oracle_unprompted_mention_rate']
   if z['reader']=='olens' and m['J_label']=='OUT-J' and m['class'] in ('structure','semantic_state'):
    z['R1_status']='NOT EVALUABLE' if None in (value,swap,mention) else 'EVALUABLE'
    if z['R1_status']=='EVALUABLE':z['R1_row_pass']=bool(value-mention>=.20 and swap<=.40)
    evaluable.append(z)
  def verdict(xs,bank=None):
   n=len(xs);k=sum(x.get('R1_row_pass',False) for x in xs);missing=sum(x['R1_status']!='EVALUABLE' for x in xs)
   unknown=sum(z['reader']=='olens' and (bank is None or z['bank']==bank) and z['map']['class'] in ('structure','semantic_state') and z['map']['J_label']=='NOT EVALUABLE' for z in rows)
   return {'n':n,'pass_rows':k,'missing_rows':missing,'unknown_J_membership':unknown,'status':'NOT EVALUABLE' if n==0 or missing or unknown else ('MET' if 2*k>n else 'NOT MET')}
  dump(a.out/'E53_RESULTS.json',{'rows':rows,'R1_pooled':verdict(evaluable),'R1_by_bank':{b:verdict([z for z in evaluable if z['bank']==b],b) for b in ('W1','E36','E49')},'forced_choice_used':False})
  import torch
  from common.stats import wilson
  from mats.probes import fit_logreg
  torch.set_num_threads(1);torch.manual_seed(SEED)
  h=np.load(a.outputs/'e54_capture/acts44.npy');channels=read(HERE/'E54_CHANNELS.json');report=[];jm={(x['id'],x['reader']):x for x in judgments}
  require(h.shape==(336,5120) and np.isfinite(h).all(),'E54 captured array')
  for r in sorted(channels):
   tr=[i for i,x in enumerate(i54) if x['feature']==r and x['split']=='dev'];te=[i for i,x in enumerate(i54) if x['feature']==r and x['split']=='test']
   require(len(tr)==len(te)==84,'E54 split')
   fit=fit_logreg(torch.from_numpy(h[tr].copy()),torch.tensor([y54[i54[i]['id']] for i in tr]))
   vals=fit.decision(torch.from_numpy(h[te].copy())).numpy();probe=estimate([y54[i54[i]['id']] for i in te],vals,[i54[i]['cluster'] for i in te])
   entry={'row':r,'probe':probe,'J_label':mapping['E54',r]['J_label'],'continuation':'NOT APPLICABLE','readers':{}}
   for reader in ('olens','nla'):
    counts={'correct_only':0,'wrong_only':0,'both':0,'silent':0,'malformed':0};blind={'states_value_correct':0,'states_value_wrong':0,'states_value_both':0,'names_property_without_value':0,'exhibits':0,'silent':0}
    for i in te:
     x=i54[i];v=scores[x['id'],'E54',reader,'native'];label=y54[x['id']];patterns=channels[r]['mention_patterns'];values=channels[r]['values']
     hits=[bool(re.search(patterns[k],v['text'],re.I)) for k in values];correct=hits[0 if label else 1];wrong=hits[1 if label else 0]
     counts['both' if correct and wrong else 'correct_only' if correct else 'wrong_only' if wrong else 'silent']+=1;counts['malformed']+=int(v['malformed'])
     j=jm[x['id'],reader];k=bucket(j,'A' if label else 'B')
     blind[k]+=1
    entry['readers'][reader]={'n':84,'regex_counts':counts,'regex_any_mention_rate':1-counts['silent']/84,'regex_any_mention_wilson95':list(wilson(84-counts['silent'],84)[1:]),'blind_counts':blind,'blind_correct_minus_wrong':(blind['states_value_correct']-blind['states_value_wrong'])/84}
   report.append(entry)
  dump(a.out/'E54_RESULTS.json',{'descriptive_only':True,'rows':report,'forced_choice_run':False,'probe_recipe':'mats.probes.fit_logreg dev-only; lam=.001,iters=200'})
  seal(a.out,'ANALYSIS_SEAL.json',{'output_seal_sha256':a.output_seal,'context_seal_sha256':a.context_seal,'source_seal_sha256':sha(HERE/'SOURCE_SEAL.json')})
 except Exception as e:dump(a.out/'FAILED.json',{'error':str(e),'retry':False});raise
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['inputs','outputs','context','out']:p.add_argument('--'+n,type=Path,required=True)
 for n in ['output-seal','context-seal']:p.add_argument('--'+n,required=True)
 analyse(p.parse_args())
