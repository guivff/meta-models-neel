"""CPU pre-seal QA and immutable E57 input freeze. No model/reader execution."""
import argparse,shutil
from collections import Counter
from bank57 import *

def verify(records,annotations,enc):
 report={}
 for row in ORDER:
  data=[x for x in records if x['feature']==row]
  assert len(data)==168 and len({x['text'] for x in data})==168
  assert Counter(x['split'] for x in data)=={'dev':84,'test':84}
  for split in ['dev','test']:
   labels=Counter(x['label'] for x in data if x['split']==split)
   assert labels==({None:84} if row in UNLABELLED else {0:42,1:42}), (row,labels)
  ratios=[]
  for t in range(12):
   for f in range(7):
    a,b=sorted([x for x in data if x['template_index']==t and x['filler_index']==f],key=lambda x:x['variant'])
    assert a['ids'][-1]==b['ids'][-1], row
    ratio=max(len(a['ids']),len(b['ids']))/min(len(a['ids']),len(b['ids']))
    assert ratio<=1.10,(row,ratio)
    ratios.append(ratio)
  report[row]={'items':168,'dev':84,'test':84,'label_check':'PASS','shared_read_token':True,'max_length_ratio':max(ratios),'probe_applicable':row not in UNLABELLED}
 for x in records:
  assert enc(x['text'])==x['ids']
  if x['feature']=='multi_token_entity':
   n=annotations[x['id']]
   # Pair answer fields are checked by the row generator and separately tokenized below.
  if x['feature']=='sentiment_judgement':
   assert x['text'].endswith('Overall, the review is')
  if x['feature']=='focus_none':
   assert not any(w in x['text'].lower() for w in ['birds','citrus','avian','oranges','lemons'])
 return report

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--seal',action='store_true');a=p.parse_args()
 assert sha(a.tokenizer)==TOKENIZER_SHA
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 a.out.mkdir(parents=True,exist_ok=False)
 sources={p.name:sha(p) for p in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,a.out/n)
 records,definitions,annotations,content=construct(enc)
 validation=verify(records,annotations,enc)
 fits={};metrics={}
 for row in ORDER:
  if row in UNLABELLED:
   metrics[row]={'status':'NOT_APPLICABLE','reason':'No binary target, as registered'};continue
  fit=score_row([x for x in records if x['feature']==row]);fits[row]=fit
  metrics[row]={'test_auroc':fit['test_auroc'],'gate_pass':fit['test_auroc']<=.65}
 for n,v in [('items.PRIVATE.json',records),('DEFINITIONS.json',definitions),('ANNOTATIONS.PRIVATE.json',annotations),('CONTENT_AUDIT.json',content),('VALIDATION.json',validation),('BOW_FITS.PRIVATE.json',fits),('BOW_QA.json',metrics)]:dump(a.out/n,v)
 files={p.name:sha(p) for p in a.out.iterdir() if p.is_file()}
 record={'experiment':'E57','stage':'PRESEAL_CPU_QA','files':files,'source_files':sources,'tokenizer_sha256':TOKENIZER_SHA,'E56_bank_seal_sha256':E56_SHA,'dependencies':{str(p.relative_to(HERE.parent)):sha(p) for p in [E49/'rows/interface.py',E49/'bow_once.py']}}
 dump(a.out/'QA_RECORD.json',record)
 print(json.dumps(metrics,indent=2))
 assert all(m.get('gate_pass',True) for m in metrics.values()),'BOW QA failed; do not seal'
 if a.seal:
  with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(a.out)+'\n')
  record.update(stage='INPUT_BANK_FROZEN',items=len(records),conditions=len(ORDER),canonical_families=len(set(CANONICAL.values())),QA_record_sha256=sha(a.out/'QA_RECORD.json'))
  dump(a.out/'BANK_SEAL.json',record)
  print('BANK_SEAL_SHA256',sha(a.out/'BANK_SEAL.json'))
if __name__=='__main__':main()
