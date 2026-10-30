"""One pre-score E42 inventory and state-function freeze; no persistence computed."""
import argparse
from datetime import datetime,timezone
from collections import Counter
from io42 import *

def main(w1):
 out=HERE/'cache/prepared';out.mkdir(parents=True,exist_ok=False)
 manifest=read(w1/'manifest.json')
 for n in ['items.DO_NOT_STAGE.jsonl','templates.json']:
  if sha(w1/n)!=manifest['files'][n]:raise ValueError('W1 input identity')
 # Authorized denominator metadata extraction; do not export numeric outcomes.
 metric=ROOT/'results/g_agreement/blindspot/w1/analysis/metrics.json'
 source_seal=read(metric.parent/'ANALYSIS_SEAL.json')
 if sha(metric)!=source_seal['files']['metrics.json']:raise ValueError('W1 metadata seal')
 selected=sorted(r['feature'] for r in read(metric)['rows'] if r['reader']=='olens' and r['layer']==44 and r['class'] in ['count-like','state-like'] and r['status']=='EVALUABLE')
 if len(selected)!=19:raise ValueError('exact 19-row denominator required')
 specs=read(w1/'templates.json');allitems=[];sources={str(w1/n):sha(w1/n) for n in ['manifest.json','templates.json','items.DO_NOT_STAGE.jsonl']}
 def append(bank,r,values,value,offset):
  allitems.append({'key':bank+':'+r['id'],'id':r['id'],'bank':bank,'feature':r['feature'],'text':r['text'],'ids':r['ids'],'value':value,'values':values,'body_offset':offset,'prefix_chars':len(r['text'])})
 for r in rows(w1/'items.DO_NOT_STAGE.jsonl'):
  if r['split']=='test' and r['feature'] in selected:
   body=r['meta']['body'];assert r['text'].endswith(body)
   append('W1',r,specs[r['feature']]['values'],r['value'],len(r['text'])-len(body))
 e36=HERE.parent/'e36';bank=e36/'cache/v2_25_2026-10-25';definitions=read(e36/'ROW_DEFINITIONS.json')['rows']
 selected36=sorted(n for n,d in definitions.items() if d['class']!='semantic')
 prepared=read(e36/'PREPARED_SEAL.json')
 for n in ['items.input.jsonl','labels.DO_NOT_STAGE.jsonl']:
  if sha(bank/n)!=prepared['files'][n]:raise ValueError('E36 bank seal')
  sources[str(bank/n)]=sha(bank/n)
 labels={r['id']:r for r in rows(bank/'labels.DO_NOT_STAGE.jsonl')}
 for r in rows(bank/'items.input.jsonl'):
  if r['split']=='test' and r['feature'] in selected36:append('E36',r,definitions[r['feature']]['values'],labels[r['id']]['value'],0)
 bank=ROOT/'cache/g_agreement/blindspot/w12-freeze-2833a200'
 verify(bank,'FREEZE.json','2833a20091db5e1e3b5548bf8d0e581b1fe23718989dc9e6e698da6eb767109f')
 spec=read(bank/'templates.json')
 for n in ['FREEZE.json','items.jsonl','templates.json']:sources[str(bank/n)]=sha(bank/n)
 for r in rows(bank/'items.jsonl'):
  if r['split']=='test':append('W12',r,spec[r['feature']]['values'],r['value'],len(r['text'])-len(r['meta']['body']))
 assert len(allitems)==3444 and len({r['key'] for r in allitems})==3444
 assert set(Counter((r['bank'],r['feature']) for r in allitems).values())=={84}
 # Original ID arrays are authoritative; verify exact tokenizer roundtrip without model.
 from transformers import PreTrainedTokenizerFast
 tokpath=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
 assert sha(tokpath)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
 tok=PreTrainedTokenizerFast(tokenizer_file=str(tokpath))
 for r in allitems:assert tok.decode(r['ids'],skip_special_tokens=False,clean_up_tokenization_spaces=False)==r['text']
 dump(out/'private_items.json',allitems)
 with (out/'prefixes.jsonl').open('x') as f:
  for r in sorted(allitems,key=lambda x:(len(x['ids']),x['key'])):f.write(json.dumps({k:r[k] for k in ['key','id','bank','feature','ids','text']})+'\n')
 seal(out,['prefixes.jsonl'],'INPUT_SEAL.json')
 dump(HERE/'INVENTORY.json',{'created_at':datetime.now(timezone.utc).isoformat(),'items':3444,'rows':{'W1':selected,'E36':selected36,'W12':list(spec)},'counts':{'W1':1596,'E36':1344,'W12':504},'W1_denominator_metadata_sha256':sha(metric),'W1_scope_difference':[],'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'private_items_sha256':sha(out/'private_items.json'),'source_hashes':sources,'provenance':'model-expected continuation; no E1b reuse','content_rows':'outside structure-only acquisition; no lexical semantic state guessed','scores_joined':False,'persistence_computed':False})
 dump(HERE/'STATE_FUNCTION_SEAL.json',{'complete':True,'created_at':datetime.now(timezone.utc).isoformat(),'authority':'§151 clarification 1, 85e9ff2f','rows':{'W1':selected,'E36':selected36,'W12':list(spec)},'files':{n:sha(HERE/n) for n in ['states.py','persistence_core.py','test_persistence_core.py','INVENTORY.json']},'external_sources':{'results/g_agreement/understand/e36/check_structure.py':sha(e36/'check_structure.py')}})
 print({'items':len(allitems),'state_seal':sha(HERE/'STATE_FUNCTION_SEAL.json')})
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--w1-bank',type=Path,required=True);main(p.parse_args().w1_bank)
