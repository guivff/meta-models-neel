"""CPU-only E61 validation, descriptive dev-fit BOW, and once-only freeze."""
import argparse,sys,shutil
from collections import Counter
from datetime import datetime,timezone
from banks61 import *
sys.path.insert(0,str(HERE.parent/'e49'))
from bow_once import score_row
UPSTREAM={'E59':('e59/cache/bank_2026-10-27_v1','b73463a88b0691d152180e8c7d0b9887bb890cc9c2750a76ce6fb6631bcf0452'),'E57':('e57/cache/bank_2026-10-27_v1','cff66637fedd6afd795370e3efbe3e8262d77c98a64e60e8580a9507dd295f7c')}
def source(bank):
 relative,expected=UPSTREAM[bank];p=HERE.parent/relative
 assert sha(p/'BANK_SEAL.json')==expected
 s=json.loads((p/'BANK_SEAL.json').read_text())
 for n,h in s['files'].items():assert sha(p/n)==h
 return json.loads((p/'items.PRIVATE.json').read_text())
def validate(a,b,enc):
 assert len(a)==24 and len({x['pair_id'] for x in a})==12
 assert len(b)==252 and len({x['base_item_id'] for x in b})==84
 assert len({x['id'] for x in a+b})==276
 ratios=[]
 for pair in {x['pair_id'] for x in a}:
  aa,bb=[x for x in a if x['pair_id']==pair]
  assert aa['question']==bb['question'] and aa['ids'][-1]==bb['ids'][-1]
  ratio=max(len(aa['ids']),len(bb['ids']))/min(len(aa['ids']),len(bb['ids']));assert ratio<=1.10;ratios.append(ratio)
 for x in a:
  assert x['read_token_indices']==list(range(x['instruction_end_token_index'],len(x['ids'])))
  assert x['value']==('decline' if 'withhold' in x['instruction'] else 'answer')
  assert enc(x['text'])==x['ids']
 for base in {x['base_item_id'] for x in b}:
  rows=[x for x in b if x['base_item_id']==base]
  assert {x['arm'] for x in rows}==set(ARMS)
  for key in ['copied_sentence','completion_suffix','answer','answer_token_id']:
   assert len({x[key] for x in rows})==1
  none=next(x for x in rows if x['arm']=='none')
  assert none['instruction']=='' and none['label'] is None
  assert not any(w in none['read_prefix'].lower() for w in ['birds','citrus','avian','oranges','lemons','bird','lemon'])
  for x in rows:
   assert x['read_prefix'].endswith(x['copied_sentence'])
   assert x['read_token_index']==len(x['read_ids'])-1
   assert x['completion_prompt']==x['read_prefix']+x['completion_suffix']
   assert x['answer_token_boundary_stable']
   assert x['answer']==(' bird' if x['concept']=='birds' else ' lemon')
   if x['arm']!='none':assert x['read_prefix']==x['instruction']+'\n'+none['read_prefix']
 for arm in ARMS:
  rows=[x for x in b if x['arm']==arm]
  assert Counter(x['concept'] for x in rows)=={'birds':42,'citrus':42}
  for t in range(6):
   for f in range(7):
    aa,bb=[x for x in rows if x['base_item_id'].startswith(f'D4:{t}:{f}:')]
    assert aa['read_ids'][-1]==bb['read_ids'][-1]
    ratio=max(len(aa['read_ids']),len(bb['read_ids']))/min(len(aa['read_ids']),len(bb['read_ids']));assert ratio<=1.10;ratios.append(ratio)
 return {'D3_pairs':12,'D3_prompts':24,'D4_base_items':84,'D4_prompts':252,'D4_each_concept_per_arm':42,'max_AB_prefix_length_ratio':max(ratios),'label_checks':'PASS','shared_read_token':'PASS','matched_D4_arms':'PASS','D3_value_terms':[['withhold'],['supply']],'D4_value_terms':[['avian','creatures'],['oranges','lemons']],'disjointness_scope':'value-bearing terms only; shared scaffolding exempt','D4_capture':'read_prefix only, before completion_suffix','BOW_is_gate':False}
def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--seal',action='store_true');args=p.parse_args()
 assert not (HERE/'BANK_FREEZE.lock').exists()
 assert sha(args.tokenizer)==TOKENIZER_SHA
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(args.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 args.out.mkdir(parents=True,exist_ok=False)
 a,b=d3(enc),d4(enc);validation=validate(a,b,enc)
 dev3=[x for x in source('E59') if x['feature']=='decline_plan' and x['split']=='dev']
 dev4=[x for x in source('E57') if x['feature'] in ['focus_think','focus_mention','focus_ignore'] and x['split']=='dev']
 fits={'D3':score_row(dev3+a)}
 for arm in ['think','ignore']:
  test=[dict(x,ids=x['read_ids']) for x in b if x['arm']==arm]
  fits['D4_'+arm]=score_row(dev4+test)
 test=[dict(x,ids=x['read_ids']) for x in b if x['arm']!='none'];fits['D4_pooled']=score_row(dev4+test)
 metrics={n:{'test_auroc':v['test_auroc'],'dev_items':v['dev_items'],'test_items':v['test_items'],'gate':False} for n,v in fits.items()}
 metrics['D4_none']={'status':'NOT_APPLICABLE','reason':'No concept instruction or binary target at capture; matching concept metadata is not a probe label','gate':False}
 # Exact dev records are preserved in this package, without adding new dev items.
 for n,v in [('D3_ITEMS.PRIVATE.json',a),('D4_ITEMS.PRIVATE.json',b),('BOW_DEV.PRIVATE.json',{'D3':dev3,'D4':dev4}),('VALIDATION.json',validation),('BOW_FITS.PRIVATE.json',fits),('BOW_REPORT.json',metrics)]:dump(args.out/n,v)
 sources={p.name:sha(p) for p in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,args.out/n)
 record={'experiment':'E61 D3/D4','stage':'PRESEAL_CPU_QA','files':{p.name:sha(p) for p in args.out.iterdir() if p.is_file()},'source_files':sources,'upstream_seals':UPSTREAM,'tokenizer_sha256':TOKENIZER_SHA,'BOW_code_sha256':sha(HERE.parent/'e49/bow_once.py'),'BOW_no_exclusions':True}
 dump(args.out/'QA_RECORD.json',record);print(json.dumps(metrics,indent=2))
 if args.seal:
  now=datetime.now(timezone.utc);assert now<datetime(2026,10,27,8,tzinfo=timezone.utc),'09:00 CET hard cut'
  with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(args.out)+'\n')
  record.update(stage='INPUT_BANK_FROZEN',created_utc=now.isoformat(),QA_record_sha256=sha(args.out/'QA_RECORD.json'))
  dump(args.out/'BANK_SEAL.json',record);print('BANK_SEAL_SHA256',sha(args.out/'BANK_SEAL.json'))
if __name__=='__main__':main()
