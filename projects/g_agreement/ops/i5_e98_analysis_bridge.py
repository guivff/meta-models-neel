"""E98 final schema bridge; pure functions, no I/O/claim/statistics on import.
Owner W-lens invokes only inside its already registered exclusive once claim.
Uses unchanged signed-rate kernels; old rubric is the exact matched subset only.
"""
from pathlib import Path
import importlib.util
ROOT=Path(__file__).resolve().parents[3]
p=ROOT/'results/g_agreement/understand/e98/wlens_analysis_count_intake/adapter.py'
s=importlib.util.spec_from_file_location('e98_count_intake_adapter',p);adapter=importlib.util.module_from_spec(s);s.loader.exec_module(adapter)

def count_objects(measures):
 return {iid:dict(id=iid,measurement=value)for iid,value in measures.items()}

def old_rubric_sensitivity(units,judgments,old,native):
 rows={u['bank']+'|'+u['row']:u for u in units};lookup={x['id']:(k,x,u['binary'])for k,u in rows.items()for x in u['items']}
 if len(old)!=447 or len({x['id']for x in old})!=447:raise ValueError('exact447 seeded old-rubric units required')
 oldmap={x['id']:x for x in old}
 if not set(oldmap)<=set(judgments):raise ValueError('old subset only matches unresolved primary units')
 grouped={};common=category=values=0
 for iid,x in oldmap.items():
  adapter.validate_judgment(x,native[iid]);a=judgments[iid];adapter.validate_judgment(a,native[iid])
  if x['category']!='UNPARSEABLE'and a['category']!='UNPARSEABLE':
   common+=1;category+=x['category']==a['category'];values+=set(x['values'])==set(a['values'])
  k,item,binary=lookup[iid];grouped.setdefault(k,[]).append(iid)
 result=[]
 for k,u in sorted(rows.items()):
  ids=sorted(grouped.get(k,[]));row=dict(bank=u['bank'],row=u['row'],sampled_items=len(ids),binary=u['binary'])
  if u['binary']:
   row['amended_matched']=adapter.rate([[adapter.signed_value(judgments[i],lookup[i][1]['label'])]for i in ids])
   row['original_matched']=adapter.rate([[adapter.signed_value(oldmap[i],lookup[i][1]['label'])]for i in ids])
  else:row.update(amended_matched=None,original_matched=None,reason='nonbinary count/mention unit; no signed S')
  result.append(row)
 return dict(scope='EXACT_SEEDED_25PCT_OF_REGEX_UNRESOLVED_ONLY_NOT_FULL_GRID',items=447,common_parseable=common,category_equal=category,value_set_equal=values,rows=result)

def describe_final(binding,native_seal,judgment_seal,units,judgments,native,forecast,qwen,counts,old):
 adapter.gate(binding,native_seal,judgment_seal)
 main=adapter.describe(units,judgments,native,forecast,qwen,count_measures=count_objects(counts))
 main['original_rubric_sensitivity']=old_rubric_sensitivity(units,judgments,old,native)
 main['review_status']='R5_REVIEW_PENDING'
 return main
