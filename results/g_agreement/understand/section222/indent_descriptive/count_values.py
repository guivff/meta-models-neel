"""Descriptive counts of existing sealed E100 Oracle indent transplant judgments.
No new labeling, scoring, bootstrap, model calls, or original analysis replay.
"""
import hashlib,json
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=read(HERE/'INPUT_PLAN.json')
 for f,h in p['pins'].items():assert sha(f)==h,f
 a=read(p['analysis_seal']);j=read(p['judgment_seal']);b=read(p['blind_seal'])
 assert sha(p['judgment_seal'])==a['judgment_sha256']
 assert sha(p['blind_seal'])==j['blind_seal_sha256']
 assert sha(p['private'])==b['private_sha256'] and b['output_seal_sha256']==a['output_seal_sha256']
 codes={x['id']:x for x in read(p['judgments'])};rows=read(p['private'])
 assert len(codes)==len(rows)==6720 and set(codes)=={x['opaque_id'] for x in rows}
 rows=[x for x in rows if x['row']=='indent_level' and x['reader']=='oracle' and x['condition']=='transplant']
 assert len(rows)==len({x['item_id'] for x in rows})==84
 groups=Counter();categories=Counter();orientation=Counter();audit=[]
 for x in rows:
  c=codes[x['opaque_id']];v=c['values'];assert c['category'] in ['states_value','names_property_without_value','exhibits','silent','UNPARSEABLE']
  assert set(v)<={'A','B'}
  key=' + '.join(sorted(x['values'][k] for k in v)) if v else 'UNPARSEABLE' if c['category']=='UNPARSEABLE' else 'no stated registered value'
  groups[key]+=1;categories[c['category']]+=1
  tag='both values' if len(v)==2 else 'donor target only' if v==[x['target']] else 'opposite value only' if len(v)==1 else 'UNPARSEABLE' if c['category']=='UNPARSEABLE' else 'no single value'
  orientation[tag]+=1
  audit.append(dict(item_id=x['item_id'],opaque_id=x['opaque_id'],target=x['values'][x['target']],stated_values=[x['values'][k] for k in v],category=c['category'],evidence=c['evidence'],text=x['text']))
 result=dict(label='DESCRIPTIVE: existing sealed judgment categories, no new interpretation',experiment='E100',row='indent_level',reader='oracle',condition='transplant',n=84,counts_by_stated_registered_value=dict(groups),counts_by_original_category=dict(categories),counts_by_donor_orientation=dict(orientation),source_pins=p['pins'],sealed_S=read(p['results'])['rows']['indent_level']['oracle']['transplant'],definition='Exclusive stated-value combinations from sealed code.values. Neither means no registered value explicitly stated, not absence of state. Counts do not infer tab/spaces, implicit indentation, or new numeric synonyms.')
 out=HERE/'COUNTS.json';assert not out.exists();out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
 cache=ROOT/'cache/g_agreement/understand/section222/indent_descriptive';cache.mkdir(parents=True,exist_ok=True)
 (cache/'ITEM_AUDIT.PRIVATE.json').write_text(json.dumps(audit,indent=2,sort_keys=True)+'\n')
 (HERE/'COUNT_SEAL.json').write_text(json.dumps(dict(status='DESCRIPTIVE_COUNTS_ONLY',files={'COUNTS.json':sha(out),'count_values.py':sha(HERE/'count_values.py'),'INPUT_PLAN.json':sha(HERE/'INPUT_PLAN.json')},audit_path=str(cache/'ITEM_AUDIT.PRIVATE.json'),audit_sha256=sha(cache/'ITEM_AUDIT.PRIVATE.json')),indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ['source_pins']},indent=2))
if __name__=='__main__':main()
