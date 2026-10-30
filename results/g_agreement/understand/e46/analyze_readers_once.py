"""Once-only CPU probe and asked analysis after the E46 reader output is sealed."""
from io46 import *
import argparse,sys,numpy as np
from sklearn.metrics import roc_auc_score

def rules(metrics):
 rows=['fenced_code','latex_list','word_first_piece','number_completion']
 if any(r not in metrics or metrics[r]['probe']<.85 for r in rows):return {'status':'NOT EVALUABLE','reason':'Each required cell needs both eligible rows and probe >= .85'}
 long=np.mean([metrics[r]['oracle_descriptive'] for r in rows[:2]])
 short=np.mean([metrics[r]['oracle_descriptive'] for r in rows[2:]])
 r1=long>=.70 and short<=.65;r2=long<=.65 and short>=.70
 return {'long_syntactic_mean':float(long),'short_semantic_mean':float(short),'R1':bool(r1),'R2':bool(r2),'status':'BOTH' if r1 and r2 else 'R1' if r1 else 'R2' if r2 else 'NEITHER'}

def run(receipt):
 with (HERE/'READER_ANALYSIS_ATTEMPT.lock').open('x') as f:f.write('E46 reader analysis once\n')
 verify(HERE,'READER_CODE_SEAL.json');plan=read(HERE/'READER_PLAN.json')
 for path,h in plan['source_files'].items():
  if sha(ROOT/path)!=h:raise ValueError('source changed')
 verify(HERE,'BANK_SEAL.json');verify(HERE/'persistence_2026-10-26','PERSISTENCE_SEAL.json',plan['persistence_seal']['sha256'])
 r=read(receipt)
 if r.get('issuer')!='integrator' or r.get('experiment')!='E46_READERS' or r.get('verified') is not True:raise ValueError('verified integrator receipt required')
 out=Path(r['output_directory']);verify(out,'READER_OUTPUT_SEAL.json',r['reader_output_seal_sha256'])
 runtime=read(out/'RUNTIME.json')
 if runtime['status']!='COMPLETE' or runtime['plan_sha256']!=sha(HERE/'READER_PLAN.json') or runtime['persistence_seal_sha256']!=plan['persistence_seal']['sha256']:raise ValueError('reader provenance')
 if read(out/'PARITY_RESULT.json')['status']!='PASS':raise ValueError('parity failed')
 sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
 from projects.g_agreement.blindspot.analysis import grouped_probe
 items=[x for x in read(HERE/'cache/prepared/items.PRIVATE.json') if x['feature'] in plan['eligible_rows']]
 order=read(out/'items.order.json');ix={k:i for i,k in enumerate(order)}
 if len(ix)!=len(order) or set(ix)!={x['id'] for x in items}:raise ValueError('capture grid')
 acts=np.load(out/'acts44.npy',allow_pickle=False);scores=rows(out/'scores.jsonl');by={(x['channel'],x['id']):x for x in scores}
 tests=[x for x in items if x['split']=='test']
 expected={(c,x['id']) for c in ['oracle_descriptive','nla'] for x in tests}
 if len(by)!=len(scores) or set(by)!=expected:raise ValueError('score grid')
 metrics={};oof=[]
 for name in plan['eligible_rows']:
  group=[x for x in tests if x['feature']==name];y=np.array([x['label']=='A' for x in group],int);clusters=np.array([x['cluster'] for x in group])
  # E36 grouped-probe recipe; donors stay within held-out template groups.
  donors=np.array([next(j for j,z in enumerate(group) if z['cluster']==x['cluster'] and z['label']!=x['label'] and z['filler_index']==x['filler_index']) for x in group])
  pred,_,folds=grouped_probe(acts[[ix[x['id']] for x in group]],y,clusters,donors)
  metrics[name]={'probe':float(roc_auc_score(y,pred)),'n':len(group),'folds':folds}
  for c in ['oracle_descriptive','nla']:
   values=[np.mean(by[c,x['id']]['scores']) for x in group];metrics[name][c]=float(roc_auc_score(y,values))
  oof.extend({'id':x['id'],'row':name,'probe':float(v)} for x,v in zip(group,pred))
 ref=plan['reference_seal'];path=ROOT/ref['path'];verify(path.parent,path.name,ref['sha256'])
 references=read(path.parent/'METRICS.json')['metrics']
 report={'metrics':metrics,'rules':rules(metrics),'reference_cells':{k:references[k] for k in ['prose_paren','python_string','prose_topic','latex_subject']},'reference_seal_sha256':ref['sha256'],'persistence_seal_sha256':plan['persistence_seal']['sha256'],'reader_output_seal_sha256':r['reader_output_seal_sha256'],'no_new_reference_items':True}
 target=HERE/'reader_analysis_2026-10-26';target.mkdir(exist_ok=False)
 dump(target/'METRICS.json',report);dump(target/'PROBE_OOF.json',oof)
 (target/'RESULTS.md').write_text('# E46 registered reader analysis\n\n```json\n'+json.dumps(report,indent=2)+'\n```\n')
 seal(target,['METRICS.json','PROBE_OOF.json','RESULTS.md'],'ANALYSIS_SEAL.json')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);run(p.parse_args().receipt)
