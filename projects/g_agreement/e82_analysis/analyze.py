"""Registered E82 item-level analysis; immutable blind judgments only after seal.
R-B2 is per reader: conditional belief-minus-truth rate >=.20, item-bootstrap
lower bound >0 on >=2 surviving source rows. The ten no-truth items stay
belief-mention-only. No source targets, reader jobs or judge calls are generated.
"""
import json,hashlib,sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT))
from common.stats import bootstrap_ci

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def score(code,letter):
 if code is None:return None
 v=code['values']
 return (1 if letter in v else -1)if code['category']=='states_value'and len(v)==1 else 0

def mention(code,letter):
 return None if code is None else code['category']=='states_value'and letter in code['values']

def row_summary(items,bootstrap=bootstrap_ci):
 """Each item has two independent target judgments; never count positions as n."""
 n=len(items);complete=[x for x in items if x['belief']is not None and x['truth']is not None]
 named=[x for x in complete if x.get('any_named',x['belief']or x['truth'])];values=[int(x['belief'])-int(x['truth'])for x in named]
 missing=n-len(complete);total=sum(values);den=len(values)
 result=dict(planned_items=n,paired_kept=len(complete),paired_missing=missing,naming_either_value=den,belief_only=sum(x['belief']and not x['truth']for x in named),truth_only=sum(x['truth']and not x['belief']for x in named),both=sum(x['belief']and x['truth']for x in named),named_in_other_judgment_but_neither_dedicated_target=sum(not x['belief']and not x['truth']for x in named),neither=len(complete)-den,delta=None,CI95=None,criterion_met=False,evaluable=bool(den),missingness_diagnostic_bounds=None)
 if den:
  point,lo,hi=bootstrap(values);result.update(delta=point,CI95=[lo,hi],criterion_met=(total*5>=den and lo>0))
 if den+missing:result['missingness_diagnostic_bounds']=[(total-missing)/(den+missing),(total+missing)/(den+missing)]
 return result

def summarize(codes,target_map,bootstrap=bootstrap_ci,truth_known_groups=None,partial_target_subset=False):
 by={x['id']:x for x in target_map};assert len(by)==len(target_map)
 assert set(codes)==set(by)
 groups=defaultdict(dict);descriptive=[];score_rows=defaultdict(list);unpaired=defaultdict(int)
 if truth_known_groups is None:truth_known_groups={x['group_id']for x in target_map if x['target']=='truth'}
 for ident,m in by.items():
  code=codes[ident];pair=groups[(m['reader'],m['family'],m['source_public_id'])];pair[m['target']]=mention(code,m['target_letter']);pair['any_named']=pair.get('any_named',False)or (code is not None and code['category']=='states_value'and bool(code['values']))
  if m['group_id']in truth_known_groups:
   s=score(code,m['target_letter']);score_rows[(m['reader'],m['family'],m['target'])].append(s)
 rows=defaultdict(list)
 for (reader,family,ident),pair in groups.items():
  group_id=next(m['group_id']for m in target_map if m['reader']==reader and m['family']==family and m['source_public_id']==ident)
  if group_id not in truth_known_groups:
   assert 'truth'not in pair;descriptive.append(dict(reader=reader,family=family,item=ident,belief_mentioned=pair['belief'],reason='no canonical truth; excluded from R-B2'))
  elif {'belief','truth'}<=set(pair):rows[(reader,family)].append(pair)
  else:
   assert partial_target_subset;unpaired[reader+'/'+family]+=1
 row_results={reader+'/'+family:row_summary(xs,bootstrap)for (reader,family),xs in sorted(rows.items())}
 per_reader={}
 for reader in sorted({r for r,f in rows}):
  these=[x for k,x in row_results.items()if k.startswith(reader+'/')];met=sum(x['criterion_met']for x in these);evaluable=sum(x['evaluable']for x in these)
  per_reader[reader]=dict(R_B2='MET'if met>=2 else 'NOT_EVALUABLE'if evaluable<2 else 'NOT_MET',rows_met=met,rows_evaluable=evaluable,required_rows=2)
 s_report={}
 for (reader,family,target),xs in sorted(score_rows.items()):
  kept=[x for x in xs if x is not None];s_report['/'.join([reader,family,target])]=dict(N=len(xs),kept=len(kept),missing=len(xs)-len(kept),S=sum(kept)/len(kept)if kept else None,CI95=list(bootstrap(kept)[1:])if kept else None,flagged_over_5_percent=20*(len(xs)-len(kept))>len(xs),missingness_bounds=[(sum(kept)-(len(xs)-len(kept)))/len(xs),(sum(kept)+(len(xs)-len(kept)))/len(xs)])
 return dict(rows=row_results,per_reader=per_reader,S_target=s_report,belief_only_no_truth=descriptive,unpaired_target_groups_from_matched_sampling=dict(unpaired),bootstrap='common.stats.bootstrap_ci defaults: 5000 item draws, seed0, 95%; conditional named-item cohort; positions are not independent observations',missingness='Paired UNPARSEABLE excluded from point R-B2 and retained in planned-N counts/bounds; no truth invented. Bounds are descriptive and do not replace the registered point rule.')

def main():
 h=ROOT/'cache/g_agreement/i2/e82_judge_cpu_v1';job=h/'judging/E82_judgments';dest=ROOT/'results/g_agreement/sealed/E82_ANALYSIS';intent=h/'ANALYSIS_ONCE_INTENT.json'
 seal=read(job/'RESULT_SEAL.json');assert seal['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS' and seal['experiment']=='E82'
 for name,digest in seal['files'].items():assert sha(job/name)==digest
 target=h/'grouped_adapter_v1/TARGET_MAP.PRIVATE.json';pre=read(h/'grouped_adapter_v1/PREFLIGHT.json');assert sha(target)==pre['files']['TARGET_MAP.PRIVATE.json']
 primary=read(job/'JUDGMENTS.json');old=read(job/'ORIGINAL_JUDGMENTS.json');mapping=read(target);assert len(primary)==816 and len(old)==204
 def terminal(rows):
  assert len({x['id']for x in rows})==len(rows)
  assert all(x['status']in ('KEPT','UNPARSEABLE')and (x['code']is None)==(x['status']=='UNPARSEABLE')for x in rows)
  return {x['id']:x['code']for x in rows}
 codes=terminal(primary);old_codes=terminal(old);assert set(codes)=={x['id']for x in mapping};assert set(old_codes)==set(read(h/'grouped_adapter_v1/ORIGINAL_IDS.json'))
 assert not dest.exists()
 with intent.open('x')as f:json.dump(dict(at_utc=datetime.now(timezone.utc).isoformat(),analysis_code_sha256=sha(Path(__file__)),judgment_seal_sha256=sha(job/'RESULT_SEAL.json'),target_map_sha256=sha(target)),f)
 result=summarize(codes,mapping);assert len(result['belief_only_no_truth'])==20
 assert {k:v['planned_items']for k,v in result['rows'].items()}=={'oracle/wrong_bridge':100,'oracle/knowledge_cutoff':99,'nla/wrong_bridge':100,'nla/knowledge_cutoff':99}
 result['R_B3']='NOT_EVALUABLE: registered source swap provides wrong-belief items only; no belief-right comparison group is invented.'
 # Original rubric comparison uses exactly the same IDs; missing target partners
 # are disclosed, never manufactured or filled from the full primary grid.
 matched_mapping=[x for x in mapping if x['id']in old_codes]
 result['matched_original_rubric']=dict(n=204,paired_R_B2_not_a_full_grid_verdict=True,primary=summarize({k:codes[k]for k in old_codes},matched_mapping,truth_known_groups={m['group_id']for m in mapping if m['target']=='truth'},partial_target_subset=True),original=summarize(old_codes,matched_mapping,truth_known_groups={m['group_id']for m in mapping if m['target']=='truth'},partial_target_subset=True))
 # Remove private item identities from the public descriptive list.
 for report in [result,result['matched_original_rubric']['primary'],result['matched_original_rubric']['original']]:
  aggregated=defaultdict(lambda:dict(items=0,kept=0,belief_mentions=0,missing=0))
  for x in report.pop('belief_only_no_truth'):
   key=x['reader']+'/'+x['family'];a=aggregated[key];a['items']+=1
   if x['belief_mentioned']is None:a['missing']+=1
   else:a['kept']+=1;a['belief_mentions']+=int(x['belief_mentioned'])
  report['belief_only_or_unpaired_target_groups']={k:dict(v,belief_mention_rate=v['belief_mentions']/v['kept']if v['kept']else None)for k,v in aggregated.items()}
 result['scope']='100 wrong_bridge +99 truth-known knowledge_cutoff per reader;10 missing-truth items kept descriptive. Source wrong-belief provenance reused, no new belief filtering.'
 dest.mkdir();(dest/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 (dest/'ANALYSIS_SEAL.json').write_text(json.dumps(dict(status='REGISTERED_E82_ANALYSIS_COMPLETE_REVIEW_PENDING',analysis_code_sha256=sha(Path(__file__)),judgment_seal_sha256=sha(job/'RESULT_SEAL.json'),input_target_map_sha256=sha(target),files={'SUMMARY.json':sha(dest/'SUMMARY.json')},at_utc=datetime.now(timezone.utc).isoformat()),indent=2)+'\n')
 print(dest)
if __name__=='__main__':main()
