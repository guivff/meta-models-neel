"""CPU ladder checks and immutable early freeze; no capture or outcomes."""
import argparse,sys,shutil,ast
from collections import Counter
from datetime import datetime,timezone
from bank62 import *
sys.path.insert(0,str(HERE.parent/'e49'));from bow_once import score_row
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def require(ok,message):
 if not ok:raise ValueError(message)
def validate(items,enc):
 # Execute only pure validation definitions from W-mechanism's pinned source.
 env={'require':require}
 for n,fn in [('runtime62.py','validate_items'),('bind62.py','validate_full_grid')]:
  tree=ast.parse((HERE/'cache/runner_contract'/n).read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==fn)
  exec(compile(ast.Module(body=[node],type_ignores=[]),n,'exec'),env)
 env['validate_full_grid']([{k:v for k,v in x.items() if k not in ('label','value')} for x in items])
 result={}
 for state in STATES:
  for rung in range(5):
   cell=f'{state}_L{rung}';rows=[x for x in items if x['feature']==cell];ratios=[]
   for split in ('dev','test'):assert Counter(x['label'] for x in rows if x['split']==split)=={0:42,1:42}
   for t in range(12):
    for f in range(7):
     a,b=sorted([x for x in rows if x['template_index']==t and x['filler_index']==f],key=lambda x:x['variant'])
     assert a['ids'][-1]==b['ids'][-1]
     ratio=max(len(a['ids']),len(b['ids']))/min(len(a['ids']),len(b['ids']));assert ratio<=1.10;ratios.append(ratio)
   result[cell]={'dev':84,'test':84,'A_B_each_split':42,'max_length_ratio':max(ratios),'identical_AB_read_token':True,'label_check':'Exact inherited sealed label','disjointness':'Inherited base value-bearing terms; identical rung scaffolding exempt'}
 for x in items:
  assert enc(x['text'])==x['ids'] and x['read_index']==len(x['ids'])-1
 for base in {x['base_item_id'] for x in items if x['state']=='S6'}:
  group=[x for x in items if x['base_item_id']==base];assert len({x['task_description'] for x in group})==1
  assert all(x['label'] is None and x['value'] is None for x in group)
 for c in range(5):result[f'S6_C{c}']={'test':84,'binary_label':'NOT_APPLICABLE','probe':'NOT_APPLICABLE','same_task_across_rungs':True}
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--seal',action='store_true');a=p.parse_args()
 assert not (HERE/'BANK_FREEZE.lock').exists();assert sha(a.tokenizer)==TOKENIZER_SHA
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 a.out.mkdir(parents=True,exist_ok=False);items=construct(enc);validation=validate(items,enc)
 fits={};metrics={}
 for state in STATES:
  for rung in range(5):
   cell=f'{state}_L{rung}';fit=score_row([x for x in items if x['feature']==cell]);fits[cell]=fit;metrics[cell]={'test_auroc':fit['test_auroc'],'gate_pass':fit['test_auroc']<=.65}
 for n,v in [('items.PRIVATE.json',items),('VALIDATION.json',validation),('RUNG_DEFINITIONS.json',{'states':STATES,'S6_cumulative_cues':CUES,'S6_tasks':TASKS,'first_content_index':'0: raw prompts, no tokenizer-added special token or unrelated archive prefix','source_seals':SOURCES}),('BOW_FITS.PRIVATE.json',fits),('BOW_QA.json',metrics)]:dump(a.out/n,v)
 sources={p.name:sha(p) for p in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,a.out/n)
 record={'experiment':'E62','stage':'PRESEAL_CPU_QA','files':{p.name:sha(p) for p in a.out.iterdir() if p.is_file()},'source_files':sources,'source_banks':SOURCES,'tokenizer_sha256':TOKENIZER_SHA,'runner_commit':'77d3f60de64ac655f5e8ed2bcd73f2d5a39849ed','runner_validators':{n:sha(HERE/'cache/runner_contract'/n) for n in ['runtime62.py','bind62.py']},'BOW_code_sha256':sha(HERE.parent/'e49/bow_once.py')}
 dump(a.out/'QA_RECORD.json',record);print(json.dumps(metrics,indent=2));assert all(x['gate_pass'] for x in metrics.values())
 if a.seal:
  now=datetime.now(timezone.utc);assert now<datetime(2026,10,27,10,tzinfo=timezone.utc),'11:00 CET deadline'
  with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(a.out)+'\n')
  record.update(stage='INPUT_BANK_FROZEN',created_utc=now.isoformat(),items=4620,AB_cells=25,eval_cells=5,QA_record_sha256=sha(a.out/'QA_RECORD.json'))
  dump(a.out/'BANK_SEAL.json',record);print('BANK_SEAL_SHA256',sha(a.out/'BANK_SEAL.json'))
if __name__=='__main__':main()
