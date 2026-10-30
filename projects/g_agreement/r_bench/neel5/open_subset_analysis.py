"""Exploratory naming conditional on the concept-arm invisibility gate; CPU only."""
import json
from datetime import datetime, timezone
from . import sa_contract as S

def main():
 out=S.ROOT/'results/g_agreement/r/neel5/sa/analysis_20261021'
 base=S.ROOT/'cache/g_agreement/r/neel5/sa'
 d=json.loads(S.DESIGN.read_text());ev=d['evaluation_concepts']
 pp=[p['prompt_id'] for p in d['prompts'] if p['split']=='evaluation']
 rows=json.loads((base/'open_judge_20261021/SCORED.json').read_text())
 assert json.loads((base/'open_judge_20261021/STATUS.json').read_text())['status']=='COMPLETE'
 idx={tuple(r['key']):r for r in rows};assert len(idx)==3600
 mapping=json.loads((out/'RESULTS.json').read_text())['exploratory_shuffled_concept_mapping']
 gates={}
 for f in (base/'complete_20261021/cells').glob('*.json'):
  r=json.loads(f.read_text());k=r['key']
  if k[:2]==['state','evaluation'] and k[-1]=='concept':gates[tuple(k[2:4])]=bool(r['value']['behaviour']['invisible'])
 assert len(gates)==400 and sum(gates.values())==336
 result={'label':'EXPLORATORY: post-outcome conditioning on concept-arm invisibility; primary verdict unchanged','at':datetime.now(timezone.utc).isoformat(),'same_concept_gate_mask_for_all_controls':True,'subsets':{}}
 for passed in (True,False):
  pairs=[(c,p) for c in ev for p in pp if gates[c,p]==passed];n=len(pairs)
  sub={'denominator':n,'per_concept_n':{c:sum(c==cc for cc,p in pairs) for c in ev},'rates':{}}
  for method in ('nla','oracle','prompt_only','nla_shuffled','oracle_shuffled'):
   shuffled=method.endswith('_shuffled');m=method.removesuffix('_shuffled');sub['rates'][method]={}
   for arm in d['conditions']:
    cells=[(c,idx[mapping[c] if shuffled else c,p,arm,m,'open']) for c,p in pairs]
    hits=[int(c in r['matched_ids']) for c,r in cells]
    rates=[sum(h for (cc,r),h in zip(cells,hits) if cc==c)/sum(cc==c for cc,r in cells) for c in ev if any(cc==c for cc,r in cells)]
    sub['rates'][method][arm]={'hits':sum(hits),'denominator':n,'pooled_rate':sum(hits)/n,'macro_concept_rate':sum(rates)/len(rates),'represented_concepts':len(rates),'missing_judge':sum(r.get('missing_judge',False) for c,r in cells),'invalid_generation':sum(r['invalid_generation'] for c,r in cells)}
  result['subsets']['concept_invisibility_pass' if passed else 'concept_invisibility_fail']=sub
 (out/'OPEN_SUBSETS.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
if __name__=='__main__':main()
