"""Items-only E65 onset audit / row medians. No reader or probe dependency."""
from collections import defaultdict
from statistics import median
from datetime import datetime,timezone
import argparse,json
from inventory65 import *
from onsets65 import onset,COUNT_ROWS
from bins65 import count_p
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def duration(offsets,char_end):
 if char_end is None:return None
 if char_end<1:raise ValueError('invalid onset')
 idx=next((i for i,(a,b) in enumerate(offsets) if a<char_end<=b),None)
 if idx is None:raise ValueError('onset outside tokenized text')
 return len(offsets)-idx

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 from transformers import PreTrainedTokenizerFast
 assert sha(TOKENIZER)==TOKENIZER_SHA
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
 inventory=json.loads((HERE/'SOURCE_INVENTORY_V2_2026-10-27.json').read_text())
 groups=defaultdict(list);audit=[]
 base62={x['id']:x for b in ['E56','E57'] for x in read_items(SOURCES[b])}
 state62={'S1':'nesting_depth','S2':'linewrap_implicit','S3':'tense_implicit','S4':'language_continuation','S5':'subject_number'}
 label_path=HERE.parent/'e36/cache/v2_25_2026-10-25/labels.DO_NOT_STAGE.jsonl'
 assert sha(label_path)=='94f6244a8f89b0320408b77e06c84df2f94d9e0c250d84fa28c63fed8e21e50f'
 e36_labels={x['id']:x['value'] for x in read_items(label_path)}
 for bank,p in SOURCES.items():
  assert sha(p)==inventory['sources'][bank]['sha256']
  for x in read_items(p):
   if x['split']!='test':continue
   if bank=='E36':x=dict(x,value=e36_labels[x['id']])
   # E61 has separate read/capture prefix; future completion is never used.
   if bank=='E61_D4':x=dict(x,text=x['read_prefix'],ids=x['read_ids'])
   output_feature=x['feature'];work_bank=bank
   if bank=='E62' and x['state']!='S6':
    base=base62[x['base_item_id']];start=x['text'].index(base['text']);end=start+len(base['text'])
    x=dict(x,feature=state62[x['state']],meta={'body':x['text'][start:]},original_read_char_end=end)
    work_bank=x['source_bank']
   encoded=tok(x['text'],add_special_tokens=False,return_offsets_mapping=True)
   assert encoded['input_ids']==x['ids'],(bank,x['id'],'tokenizer mismatch')
   if x['feature'] in COUNT_ROWS:
    value,rule=count_p(work_bank,x,encoded['offset_mapping']);char_end=None
   else:
    char_end,rule=onset(work_bank,x)
    value=duration(encoded['offset_mapping'],char_end)
   row={'bank':bank,'row':output_feature,'underlying_changes_each_token':x['feature'] in COUNT_ROWS or x['feature'] in {'capacity_list','page_range_digit'},'item_id':x['id'],'P':value,'onset_char_end':char_end,'rule':rule}
   audit.append(row);groups[bank,output_feature].append(row)
 rows=[]
 for (bank,f),items in sorted(groups.items()):
  values=[x['P'] for x in items if x['P'] is not None]
  rows.append({'bank':bank,'row':f,'underlying_changes_each_token':items[0]['underlying_changes_each_token'],'P':median(values) if len(values)==len(items) else None,'status':'EVALUABLE' if len(values)==len(items) else 'NOT_EVALUABLE','test_items':len(items),'determinate_items':len(values),'undetermined_items':len(items)-len(values),'rules':sorted({x['rule'] for x in items}),'aggregation':'median of all test items; no partial-row median substituted'})
 result={'experiment':'E65','registration':'§182 clarifications 1 and 3; 9f6c8b70, 96a8e352','created_utc':datetime.now(timezone.utc).isoformat(),'status':'ITEMS_ONLY_VALUES_READY_FOR_DOWNSTREAM_GATE_JOIN','not_evaluable_policy':'No scalar substituted if any test item lacks a certified onset; all missing entries listed','scope':'All locally inventoried frozen item banks, unfiltered. No probe-eligibility claim; W-lens applies gates.','gates_read':False,'reader_or_probe_files_read':False,'tokenizer_sha256':TOKENIZER_SHA,'convention':'Establishing token included, P=1 when newly set at read; token covering completed establishing span counted','count_convention':'A/B bin; within-bin numeric changes do not reset P','flag_convention':'Definition-based: true for count/index/depth/indentation/length/position rows, including count-only capacity; not an empirical every-token claim','label_source':{'path':str(label_path),'sha256':sha(label_path)},'rows':rows,'sources':inventory['sources'],'external_code':{str(p.relative_to(HERE.parent)):sha(p) for p in [HERE.parent/'e36/check_content.py',HERE.parent/'e36/check_structure.py']},'code':{p.name:sha(p) for p in HERE.glob('*.py')}}
 for name,data in [('ITEM_AUDIT.PRIVATE.json',audit),('E65_PERSISTENCE.json',result)]:
  with (a.out/name).open('x') as o:json.dump(data,o,indent=2,sort_keys=True);o.write('\n')
 print('Rows',len(rows),'evaluable',sum(r['status']=='EVALUABLE' for r in rows))
 print('Incomplete:',[(r['bank'],r['row'],r['undetermined_items']) for r in rows if r['status']!='EVALUABLE'])
if __name__=='__main__':main()
