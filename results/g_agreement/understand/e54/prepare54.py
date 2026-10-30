"""CPU construction + pre-seal BOW QA, then one immutable E54 input seal."""
import argparse,importlib,math,shutil
from dataclasses import asdict
from collections import Counter
from common54 import *
ROWS=('reasoning_bridge','injection_awareness')

def construct(encode):
 records=[];report={};channels={}
 for row in ROWS:
  m=importlib.import_module(row);items=m.generate();validate(items,m.SPEC,m.check_label,encode)
  ratios=[]
  for t in range(12):
   for f in range(7):
    pair=[x for x in items if x.pair_key==(t,f)];lengths=[len(encode(x.text)) for x in pair];ratios.append(max(lengths)/min(lengths))
  report[row]={'spec':asdict(m.SPEC),'n':len(items),'split_labels':{s:dict(Counter(x.value for x in items if x.split==s)) for s in ['dev','test']},'max_length_ratio':max(ratios),'read_token_ids':sorted({encode(x.text)[-1] for x in items})}
  channels[row]={'values':m.SPEC.values,'descriptive_phrasings':m.PHRASINGS,'continuations':m.CONTINUATIONS,'continuation_status':'NOT APPLICABLE' if m.CONTINUATIONS is None else 'DEFINED','continuation_reason':m.CONTINUATION_REASON,'mention_patterns':m.MENTION_PATTERNS}
  for x in items:
   d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,cluster=x.template_index,label=int(x.value==m.SPEC.values[0]),ids=encode(x.text));records.append(d)
 return records,report,channels

def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if (HERE/'BANK_FREEZE.lock').exists():raise ValueError('already frozen; no rebuild or rerun')
 if sha(a.tokenizer)!=TOKENIZER_SHA:raise ValueError('wrong tokenizer')
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));records,validation,channels=construct(lambda x:tok.encode(x,add_special_tokens=False))
 a.out.mkdir(parents=True,exist_ok=False)
 dump(a.out/'items.PRIVATE.json',records);dump(a.out/'VALIDATION.json',validation);dump(a.out/'CHANNEL_DEFINITIONS.json',channels)
 sources={n:sha(HERE/n) for n in ['common54.py','prepare54.py','reasoning_bridge.py','injection_awareness.py','test_rows54.py']}
 upstream={str(p.relative_to(HERE.parent)):sha(p) for p in [E49/'rows/interface.py',E49/'bow_once.py',E49/'freeze_bank.py']}
 dump(a.out/'DRAFT_MANIFEST.json',{'stage':'PRESEAL_BUILD_QA','files':{n:sha(a.out/n) for n in ['items.PRIVATE.json','VALIDATION.json','CHANNEL_DEFINITIONS.json']},'source_files':sources,'upstream_source_files':upstream,'tokenizer_sha256':TOKENIZER_SHA})
 with (a.out/'BOW_ATTEMPT.lock').open('x') as f:f.write(sha(a.out/'DRAFT_MANIFEST.json')+'\n')
 metrics={};fits={}
 for row in ROWS:
  fit=score_row([r for r in records if r['feature']==row]);fits[row]=fit;s=fit['test_auroc']
  if not math.isfinite(s):raise ValueError('invalid BOW result')
  metrics[row]={'test_auroc':s,'gate_pass':s<=.65,'tracked':True}
 dump(a.out/'BOW_FITS.PRIVATE.json',fits);dump(a.out/'BOW_METRICS.json',metrics)
 dump(a.out/'BOW_QA_SEAL.json',{'stage':'PRESEAL_BUILD_QA','draft_sha256':sha(a.out/'DRAFT_MANIFEST.json'),'files':{n:sha(a.out/n) for n in ['BOW_FITS.PRIVATE.json','BOW_METRICS.json','BOW_ATTEMPT.lock']}})
 failed=[row for row,m in metrics.items() if not m['gate_pass']]
 if failed:raise ValueError('BOW QA failed; preserve this attempt, fix before seal: '+','.join(failed))
 with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(a.out.resolve())+'\n')
 names=['items.PRIVATE.json','VALIDATION.json','CHANNEL_DEFINITIONS.json','DRAFT_MANIFEST.json','BOW_FITS.PRIVATE.json','BOW_METRICS.json','BOW_QA_SEAL.json','BOW_ATTEMPT.lock']
 dump(a.out/'BANK_SEAL.json',{'experiment':'E54','registration':'§171 aebc9d1f','status':'INPUT_BANK_FROZEN','items':336,'rows':list(ROWS),'dev_items':168,'test_items':168,'tokenizer_sha256':TOKENIZER_SHA,'source_files':sources,'upstream_source_files':upstream,'files':{n:sha(a.out/n) for n in names},'model_inference_before_seal':False})
 print('Bank seal:',sha(a.out/'BANK_SEAL.json'));print('BOW metrics:',metrics)
if __name__=='__main__':main()
