"""Prospective §163 rules. No filesystem or outcome loading at import time."""
import numpy as np
SEED=20261026
BOOTSTRAPS=2000

def qualify(rows):
 """Read gate metrics only; never inspect any reader score here.
 All required gates must exist and be finite. Never impute missing gates.
 """
 gated={};excluded={}
 for row,m in rows.items():
  if m['kind'] not in {'semantic_state','descriptor','surface_state'}:raise ValueError('unknown row kind')
  fields=['probe','base']+(['bow'] if m['kind']!='descriptor' else [])
  if any(k not in m or not np.isfinite(m[k]) or not 0<=m[k]<=1 for k in fields):
   excluded[row]=['missing or invalid metric'];continue
  reasons=[]
  if m['kind']!='descriptor' and m['bow']>.65:reasons.append('BOW > 0.65')
  if m['probe']<.90:reasons.append('probe < 0.90')
  if m['base']<.85:reasons.append('base text < 0.85')
  if reasons:excluded[row]=reasons
  else:gated[row]=m
 return gated,excluded

def evaluate(rows,precalls):
 gated,excluded=qualify(rows)
 for m in gated.values():
  if 'oracle' not in m or not np.isfinite(m['oracle']) or not 0<=m['oracle']<=1:raise ValueError('missing or invalid qualified Oracle score')
 states=[m['oracle'] for m in gated.values() if m['kind']=='semantic_state']
 descriptors=[m['oracle'] for m in gated.values() if m['kind']=='descriptor']
 result={'gated_rows':list(gated),'excluded_rows':excluded,'semantic_state_n':len(states),'descriptor_n':len(descriptors)}
 enough=bool(states and descriptors)
 result['R1']={'status':'NOT EVALUABLE' if not enough else ('HOLDS' if np.mean(np.asarray(states)<=.65)>=.75 and np.mean(np.asarray(descriptors)>=.80)>=.75 else 'NOT MET'),'state_unsayable_count':sum(x<=.65 for x in states),'descriptor_sayable_count':sum(x>=.80 for x in descriptors)}
 if enough:
  rng=np.random.default_rng(SEED)
  deltas=[float(np.mean(rng.choice(descriptors,len(descriptors),replace=True))-np.mean(rng.choice(states,len(states),replace=True))) for _ in range(BOOTSTRAPS)]
  ci=np.quantile(deltas,[.025,.975]).tolist()
  result['R2']={'status':'HOLDS' if ci[0]>0 or ci[1]<0 else 'NOT MET','mean_gap':float(np.mean(descriptors)-np.mean(states)),'ci95':ci,'resampling':'within each kind, rows with replacement','replicates':BOOTSTRAPS,'direction':'descriptor higher' if np.mean(descriptors)>np.mean(states) else 'state higher or equal'}
 else:result['R2']={'status':'NOT EVALUABLE'}
 twins=['topic_twin','asserted_vs_hypothetical']
 result['R3']={'status':'NOT EVALUABLE' if not all(x in gated for x in twins) else ('HOLDS' if gated['topic_twin']['oracle']>=.80 and gated['asserted_vs_hypothetical']['oracle']<=.65 else 'NOT MET')}
 result['falsifier']={'status':'NOT EVALUABLE' if not states else ('HOLDS' if np.mean(np.asarray(states)>=.80)>=.50 else 'NOT MET'),'state_sayable_count':sum(x>=.80 for x in states)}
 correct={}
 for row,m in gated.items():
  call=precalls[row].upper()
  if call not in {'SAYABLE','UNSAYABLE'}:raise ValueError('unknown blind pre-call')
  correct[row]=bool(m['oracle']>=.80 if call=='SAYABLE' else m['oracle']<=.65)
 result['precall_accuracy']={'role':'primary','correct_by_row':correct,'n':len(correct),'accuracy':sum(correct.values())/len(correct) if correct else None,'middle_band':'incorrect, §163 clarification 1','population':'gated rows only'}
 middle=[row for row,m in gated.items() if .65<m['oracle']<.80]
 descriptive={row:value for row,value in correct.items() if row not in middle}
 result['precall_accuracy_middle_band_excluded']={'role':'descriptive','correct_by_row':descriptive,'n':len(descriptive),'accuracy':sum(descriptive.values())/len(descriptive) if descriptive else None,'excluded_middle_band_rows':middle,'population':'gated rows only, excluding 0.65 < Oracle AUROC < 0.80'}
 return result
