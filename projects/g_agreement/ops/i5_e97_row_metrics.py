"""Pure E97 item-to-row reporting metrics; no file I/O or outcomes on import.
Original signed-rate/missingness kernels and frozen E75 REPORTED convention.
"""
from pathlib import Path
import sys
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e56/job'))
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/analysis402'))
from missingness import signed_value,rate
from projects.g_agreement.e97.taxonomy import TAGS

def row_metrics(records,rowmeta,forecast,excluded=()):
 if len(records)!=6720 or len({x['id']for x in records})!=6720:raise ValueError('full6720 native ID grid required')
 if set(rowmeta)!=set(forecast) or len(rowmeta)!=40:raise ValueError('40 exact frozen taxonomy/forecast rows')
 excluded=set(excluded)
 if not excluded<={x['id']for x in records}:raise ValueError('unknown excluded ID')
 groups=defaultdict(list)
 for x in records:
  if x['reader']not in ('oracle','nla') or x['row']not in rowmeta or x['label']not in ('A','B'):raise ValueError('frozen reader/row/A-B truth')
  c=x['code']
  if c.get('id')!=x['id']:raise ValueError('code/native ID binding')
  if c['category']not in ('states_value','names_property_without_value','exhibits','silent','UNPARSEABLE'):raise ValueError('terminal original code required')
  groups[(x['reader'],x['row'])].append(x)
 if len(groups)!=80 or any(len(xs)!=84 for xs in groups.values()):raise ValueError('exact84 items/row/reader, no drops')
 output={}
 for reader in ('oracle','nla'):
  rows=[]
  for row in sorted(rowmeta):
   tag=rowmeta[row]['taxonomy'];f=forecast[row]
   if tag not in TAGS or f['label']not in ('IN-J','DIFFUSE','OUT-J'):raise ValueError('frozen taxonomy/J labels')
   pred=f[reader+'_prediction']
   if pred!=('REPORTED'if f['label']=='IN-J'else'MISSED'):raise ValueError('frozen J prediction mismatch')
   xs=sorted(groups[(reader,row)],key=lambda x:x['id']);kept=[x for x in xs if x['id']not in excluded]
   scores=[signed_value(x['code'],1 if x['label']=='A'else 0)for x in kept];r=rate([[v]for v in scores])
   s,ci=r['S'],r['CI95'];truth=None if s is None or ci is None else bool(s>=.20 and ci[0]>0)
   rows.append(dict(row=row,taxonomy=tag,j_label=f['label'],j_reported=pred=='REPORTED',reported=truth,S=s,CI95=ci,native_planned=84,excluded_affected=len(xs)-len(kept),included_items=len(kept),UNPARSEABLE=sum(v is None for v in scores),rate_kernel=r))
  output[reader]=rows
 return output


def old_rubric_summary(records,old,excluded=()):
 """Exact seeded matched subset only; no full-grid old-rubric substitution."""
 index={x['id']:x for x in records};oldmap={x['id']:x for x in old};excluded=set(excluded)
 if len(records)!=6720 or len(index)!=6720 or len(old)!=1667 or len(oldmap)!=1667 or not set(oldmap)<=set(index):raise ValueError('full native grid/exact1667 original IDs')
 if any(index[i].get('code_source')!='judge'for i in oldmap):raise ValueError('old sample must come from original unresolved judge units')
 groups=defaultdict(list)
 for x in records:groups[(x['reader'],x['row'])].append(x)
 result=[];common=category=values=retained=0
 for (reader,row),full in sorted(groups.items()):
  xs=sorted([x for x in full if x['id']in oldmap and x['id']not in excluded],key=lambda x:x['id']);a=[];b=[]
  for x in xs:
   one,two=x['code'],oldmap[x['id']]
   if two['category']not in ('states_value','names_property_without_value','exhibits','silent','UNPARSEABLE'):raise ValueError('original terminal code required')
   label=1 if x['label']=='A'else 0;a.append(signed_value(one,label));b.append(signed_value(two,label))
   if one['category']!='UNPARSEABLE'and two['category']!='UNPARSEABLE':common+=1;category+=one['category']==two['category'];values+=set(one['values'])==set(two['values'])
  retained+=len(xs);result.append(dict(reader=reader,row=row,selected_items=len(xs),amended_matched=rate([[v]for v in a]),original_matched=rate([[v]for v in b]),amended_UNPARSEABLE=sum(v is None for v in a),original_UNPARSEABLE=sum(v is None for v in b)))
 return dict(scope='EXACT_SEEDED_25PCT_UNRESOLVED_MATCHED_SUBSET_ONLY_NOT_FULL_GRID',original_sample_items=1667,retained_items=retained,excluded_affected=1667-retained,common_parseable=common,category_equal=category,value_set_equal=values,rows=result)
