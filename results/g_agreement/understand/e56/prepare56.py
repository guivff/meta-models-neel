"""CPU full-bank build QA and a single E56 input freeze, no reader/model calls."""
import argparse,math
from collections import Counter
from common56 import *
from bank56 import construct,IMPLICIT,E54_SHA
ORDER=['tense_implicit','tense_asked','linewrap_implicit','linewrap_asked','language_continuation','language_report','adjective_implicit','adjective_asked','anomaly_state','fact_recall','reasoning_bridge','rhyme_plan','instructed_focus']

def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if (HERE/'BANK_FREEZE.lock').exists():raise ValueError('freeze already attempted; no rebuilding')
 if sha(a.tokenizer)!=TOKENIZER_SHA:raise ValueError('wrong tokenizer')
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 items,definitions,twins,vocab=construct(enc)
 items=sorted(items,key=lambda x:(ORDER.index(x['feature']),x['template_index'],x['filler_index'],x['variant']))
 checks={}
 for row in ORDER:
  group=[x for x in items if x['feature']==row];ratios=[]
  for t in range(12):
   for f in range(7):
    pair=[x for x in group if x['template_index']==t and x['filler_index']==f]
    lengths=[len(x['ids']) for x in pair]
    if len(pair)!=2 or pair[0]['ids'][-1]!=pair[1]['ids'][-1]:raise ValueError('read-token identity failed')
    ratios.append(max(lengths)/min(lengths))
  if max(ratios)>1.10:raise ValueError('length ratio failed')
  counts={s:dict(Counter(x['label'] for x in group if x['split']==s)) for s in ['dev','test']}
  if any(v!={0:42,1:42} for v in counts.values()):raise ValueError('balance failed')
  checks[row]={'items':len(group),'split_labels':counts,'max_length_ratio':max(ratios),'values':definitions[row]['values']}
 a.out.mkdir(parents=True,exist_ok=False)
 dump(a.out/'items.PRIVATE.json',items)
 dump(a.out/'ROW_DEFINITIONS.json',{'rows':definitions,'twins':twins,'adjective_content_vocabulary':vocab,'adjective_BOW_caveat':'Disjoint dev/test content vocabulary; BOW QA tests held-out lexical generalization. The other four implicit pairs have identical token-count bags.','E54_injection_awareness':'attached original E54 bank only, outside all E56 rules'})
 dump(a.out/'VALIDATION.json',checks)
 source_names=['common56.py','twin_bases.py','independent_rows.py','adjective_row.py','bank56.py','prepare56.py','test_build56.py']
 sources={n:sha(HERE/n) for n in source_names}
 upstream={str(p.relative_to(HERE.parent)):sha(p) for p in [E49/'rows/interface.py',E49/'bow_once.py',E49/'freeze_bank.py']}
 dump(a.out/'DRAFT_MANIFEST.json',{'status':'PRESEAL_BUILD_QA','source_files':sources,'upstream_source_files':upstream,'files':{n:sha(a.out/n) for n in ['items.PRIVATE.json','ROW_DEFINITIONS.json','VALIDATION.json']},'E54_bank_seal_sha256':E54_SHA})
 with (a.out/'BOW_ATTEMPT.lock').open('x') as f:f.write(sha(a.out/'DRAFT_MANIFEST.json')+'\n')
 fits={};metrics={}
 for row in IMPLICIT:
  fit=score_row([x for x in items if x['feature']==row]);fits[row]=fit;s=fit['test_auroc']
  if not math.isfinite(s):raise ValueError('invalid BOW score')
  metrics[row]={'test_auroc':s,'gate_pass':s<=.65}
 dump(a.out/'BOW_FITS.PRIVATE.json',fits);dump(a.out/'BOW_METRICS.json',metrics)
 dump(a.out/'BOW_QA_SEAL.json',{'stage':'PRESEAL_CPU_BUILD_QA','draft_manifest_sha256':sha(a.out/'DRAFT_MANIFEST.json'),'files':{n:sha(a.out/n) for n in ['BOW_FITS.PRIVATE.json','BOW_METRICS.json','BOW_ATTEMPT.lock']}})
 failed=[row for row,m in metrics.items() if not m['gate_pass']]
 if failed:raise ValueError('BOW QA failed before freeze: '+','.join(failed))
 # The archive of early completed-row QA remains intact; this is the only bank freeze.
 with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(a.out.resolve())+'\n')
 names=['items.PRIVATE.json','ROW_DEFINITIONS.json','VALIDATION.json','DRAFT_MANIFEST.json','BOW_FITS.PRIVATE.json','BOW_METRICS.json','BOW_QA_SEAL.json','BOW_ATTEMPT.lock']
 dump(a.out/'BANK_SEAL.json',{'experiment':'E56','registration':'§172 4c187fda; clarification 1 0f1e4dd','status':'INPUT_BANK_FROZEN','families':9,'conditions':13,'items':len(items),'dev_items':1092,'test_items':1092,'row_order':ORDER,'tokenizer_sha256':TOKENIZER_SHA,'source_files':sources,'upstream_source_files':upstream,'files':{n:sha(a.out/n) for n in names},'E54_bridge_reuse_seal_sha256':E54_SHA,'exclusions':[],'model_inference_before_seal':False})
 print('Bank seal:',sha(a.out/'BANK_SEAL.json'));print('BOW:',metrics)
if __name__=='__main__':main()
