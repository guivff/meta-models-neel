"""Versioned CPU build QA; seal only after passing checks, before 10:00 CET."""
import argparse,hashlib,json,shutil
from datetime import datetime,timezone
from dataclasses import asdict
from rows59 import *
from bow_once import score_row
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def build(enc):
 records=[];instructions=[];validation={}
 for row in ROWS:
  items=generate(row);validate(items,spec(row),lambda s:check_label(row,s),enc)
  assert not set(VALUE_TERMS[row][0])&set(VALUE_TERMS[row][1])
  for x in items:
   d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,cluster=x.template_index,label=int(x.variant==0),ids=enc(x.text))
   records.append(d)
   instr=instruction(row,x.template_index,x.variant)
   instructions.append(dict(d,text=instr,ids=enc(instr)))
  ratios=[]
  for t in range(12):
   for f in range(7):
    a,b=[render(row,t,f,v) for v in (0,1)]
    assert a.split('\nQuestion: ')[1]==b.split('\nQuestion: ')[1]
    ratios.append(max(len(enc(a)),len(enc(b)))/min(len(enc(a)),len(enc(b))))
  validation[row]={'spec':asdict(spec(row)),'items':168,'dev':84,'test':84,'A_per_split':42,'B_per_split':42,'max_length_ratio':max(ratios),'shared_question_and_read_token':True,'label_check':'PASS','disjoint_value_terms':VALUE_TERMS[row],'registered_reader_value_words':REGISTERED_VALUE_WORDS[row]}
 return records,instructions,validation

def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seal',action='store_true');a=p.parse_args()
 assert not (HERE/'BANK_FREEZE.lock').exists(),'Frozen bank may not be rebuilt'
 assert sha(a.tokenizer)==TOKENIZER_SHA
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 a.out.mkdir(parents=True,exist_ok=False)
 sources={x.name:sha(x) for x in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,a.out/n)
 records,instructions,validation=build(enc);fits={};metrics={}
 for row in ROWS:
  full=score_row([x for x in records if x['feature']==row]);inst=score_row([x for x in instructions if x['feature']==row])
  fits[row]={'full_prefix':full,'instruction_only':inst}
  metrics[row]={'full_prefix_test_auroc':full['test_auroc'],'instruction_only_test_auroc':inst['test_auroc'],'full_prefix_build_gate_pass':full['test_auroc']<=.65,'instruction_R1_gate_pass':inst['test_auroc']<=.65}
 for n,v in [('items.PRIVATE.json',records),('instructions.PRIVATE.json',instructions),('VALIDATION.json',validation),('BOW_FITS.PRIVATE.json',fits),('BOW_QA.json',metrics)]:dump(a.out/n,v)
 record={'experiment':'E59','stage':'PRESEAL_CPU_QA','files':{x.name:sha(x) for x in a.out.iterdir() if x.is_file()},'source_files':sources,'tokenizer_sha256':TOKENIZER_SHA,'dependencies':{str(x.relative_to(HERE.parent)):sha(x) for x in [HERE.parent/'e49/rows/interface.py',HERE.parent/'e49/bow_once.py',HERE.parent/'e49/freeze_bank.py']}}
 dump(a.out/'QA_RECORD.json',record);print(json.dumps(metrics,indent=2))
 assert all(x['full_prefix_build_gate_pass'] for x in metrics.values()),'Full-prefix BOW build gate failed; preserve attempt'
 if a.seal:
  now=datetime.now(timezone.utc)
  assert now<datetime(2026,10,27,9,tzinfo=timezone.utc),'10:00 CET hard cut: NOT BUILT'
  with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(a.out)+'\n')
  record.update(stage='INPUT_BANK_FROZEN',created_utc=now.isoformat(),items=1008,rows=list(ROWS),QA_record_sha256=sha(a.out/'QA_RECORD.json'))
  dump(a.out/'BANK_SEAL.json',record);print('BANK_SEAL_SHA256',sha(a.out/'BANK_SEAL.json'))
if __name__=='__main__':main()
