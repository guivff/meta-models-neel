"""E49 draft construction and final freeze after CPU BOW build QA.

All 16 modules must exist. The exclusive output directory prevents replacement.
"""
import argparse, hashlib, importlib, json, shutil, math
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from rows.interface import REGISTRY, validate

HERE=Path(__file__).resolve().parent
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def dump(path,obj):
 with Path(path).open('x') as f:json.dump(obj,f,indent=2,sort_keys=True);f.write('\n')

def construct(encode):
 modules={name:importlib.import_module('rows.'+name) for name,_ in REGISTRY.values()}
 banks={};report={}
 for number,(name,kind) in REGISTRY.items():
  m=modules[name];s=m.SPEC
  if (s.row_id,s.kind)!=(name,kind):raise ValueError('registry mismatch: '+name)
  items=m.generate(banks[s.twin_of]) if s.twin_of else m.generate()
  validate(items,s,m.check_label,encode)
  if s.twin_of:
   source={x.source_key:x for x in banks[s.twin_of]}
   for x in items:
    y=source[x.source_key]
    if x.text!=y.text or encode(x.text)!=encode(y.text):raise ValueError('twin changed prefix')
  banks[name]=items
  ratios=[]
  for t in range(12):
   for f in range(7):
    pair=[x for x in items if x.pair_key==(t,f)]
    lengths=[len(encode(x.text)) for x in pair];ratios.append(max(lengths)/min(lengths))
  report[name]={'number':number,'spec':asdict(s),'items':len(items),'max_length_ratio':max(ratios),'split_labels':{split:dict(Counter(x.value for x in items if x.split==split)) for split in ['dev','test']}}
 return banks,report

def verify_files(directory,manifest):
 for n,h in manifest['files'].items():
  if sha(directory/n)!=h:raise ValueError('artifact hash mismatch: '+n)

def qa_passes(metrics,validation):
 if set(metrics)!=set(validation):raise ValueError('BOW row coverage')
 for row,m in metrics.items():
  tracked=validation[row]['spec']['kind']!='descriptor'
  score=m['test_auroc']
  if not isinstance(score,(int,float)) or not math.isfinite(score) or not 0<=score<=1:raise ValueError('invalid BOW AUROC')
  passed=not tracked or score<=.65
  if m['tracked']!=tracked or m['gate_pass']!=passed:raise ValueError('BOW gate reporting mismatch')
  if not passed:raise ValueError('pre-seal BOW build QA failed: '+row)

def seal_draft(draft,qa,out):
 manifest=json.loads((draft/'DRAFT_MANIFEST.json').read_text())
 if manifest.get('status')!='DRAFT_NOT_FROZEN' or manifest['items']!=2688:raise ValueError('complete draft required')
 verify_files(draft,manifest)
 for n,h in manifest['source_files'].items():
  if sha(HERE/n)!=h:raise ValueError('source changed since QA draft')
 if sha(HERE/'PRECALLS_SEAL.json')!=manifest['precalls_seal_sha256']:raise ValueError('precall seal changed')
 verify_files(HERE,json.loads((HERE/'PRECALLS_SEAL.json').read_text()))
 q=json.loads((qa/'BOW_SEAL.json').read_text());verify_files(qa,q)
 if q.get('complete') is not True or q.get('stage')!='PRESEAL_BUILD_QA' or q['draft_manifest_sha256']!=sha(draft/'DRAFT_MANIFEST.json') or q['code_sha256']!=sha(HERE/'bow_once.py'):raise ValueError('BOW provenance mismatch')
 if q['lock_sha256']!=sha(draft/'BOW_ATTEMPT.lock'):raise ValueError('BOW attempt lock mismatch')
 metrics=json.loads((qa/'METRICS.json').read_text());validation=json.loads((draft/'VALIDATION.json').read_text())
 if set(validation)!={name for name,_ in REGISTRY.values()}:raise ValueError('16 rows required')
 qa_passes(metrics,validation)
 if out.exists():raise FileExistsError(out)
 with (HERE/'BANK_FREEZE.lock').open('x') as f:f.write(str(out.resolve())+'\n')
 out.mkdir(parents=True,exist_ok=False)
 for name in ['items.PRIVATE.json','VALIDATION.json']:shutil.copyfile(draft/name,out/name)
 shutil.copyfile(qa/'METRICS.json',out/'BOW_METRICS.json')
 shutil.copyfile(qa/'BOW_SEAL.json',out/'BOW_QA_SEAL.json')
 result={k:v for k,v in manifest.items() if k not in ['status','files']}
 result.update(complete=True,status='INPUT_BANK_FROZEN',draft_manifest_sha256=sha(draft/'DRAFT_MANIFEST.json'),bow_qa_seal_sha256=sha(qa/'BOW_SEAL.json'),bow_qa_directory=str(qa.resolve()),files={n:sha(out/n) for n in ['items.PRIVATE.json','VALIDATION.json','BOW_METRICS.json','BOW_QA_SEAL.json']})
 dump(out/'BANK_SEAL.json',result)
 print('Input bank frozen:',sha(out/'BANK_SEAL.json'))

def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path);p.add_argument('--out',type=Path,required=True);p.add_argument('--seal-draft',type=Path);p.add_argument('--qa',type=Path);a=p.parse_args()
 if (HERE/'BANK_FREEZE.lock').exists():raise ValueError('input bank already frozen or freeze attempted; no rebuild')
 if a.seal_draft:
  if not a.qa:p.error('--qa required with --seal-draft')
  seal_draft(a.seal_draft,a.qa,a.out);return
 if not a.tokenizer:p.error('--tokenizer required for draft construction')
 if sha(a.tokenizer)!=TOKENIZER_SHA:raise ValueError('tokenizer identity')
 precalls=json.loads((HERE/'PRECALLS_SEAL.json').read_text())
 for n,h in precalls['files'].items():
  if sha(HERE/n)!=h:raise ValueError('precall seal mismatch')
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));encode=lambda s:tok.encode(s,add_special_tokens=False)
 banks,report=construct(encode)
 a.out.mkdir(parents=True,exist_ok=False)
 records=[]
 for row,items in banks.items():
  spec=report[row]['spec']
  for x in items:
   d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,cluster=x.template_index,label=int(x.value==spec['values'][0]),ids=encode(x.text));records.append(d)
 dump(a.out/'items.PRIVATE.json',records)
 dump(a.out/'VALIDATION.json',report)
 sources={str(p.relative_to(HERE)):sha(p) for p in sorted((HERE/'rows').glob('*.py'))}
 for name in ['freeze_bank.py','bow_once.py','rules49.py']:sources[name]=sha(HERE/name)
 dump(a.out/'DRAFT_MANIFEST.json',{'status':'DRAFT_NOT_FROZEN','experiment':'E49','tokenizer_sha256':TOKENIZER_SHA,'source_files':sources,'precalls_seal_sha256':sha(HERE/'PRECALLS_SEAL.json'),'files':{n:sha(a.out/n) for n in ['items.PRIVATE.json','VALIDATION.json']},'row_order':[name for name,_ in REGISTRY.values()],'items':len(records),'outcomes_used':False})
 print('Draft built:',len(records),'items; run CPU BOW build QA before sealing.')
if __name__=='__main__':main()
