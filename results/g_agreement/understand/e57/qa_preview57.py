"""Versioned pre-seal CPU QA of completed generators; never creates a bank seal."""
from dataclasses import asdict
import argparse,importlib,json
from common57 import *
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--tokenizer',type=Path,required=True);a=p.parse_args()
 if sha(a.tokenizer)!=TOKENIZER_SHA:raise ValueError('tokenizer')
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 a.out.mkdir(parents=True,exist_ok=False);report={};fits={};records=[]
 for modname in ['group_b','group_a','amendment_rows']:
  m=importlib.import_module(modname)
  for row,spec in m.SPECS.items():
   items=m.generate(row)
   try:validate(items,spec,lambda s:m.check_label(row,s),enc)
   except ValueError as e:report[row]={'build':'FAIL','reason':str(e)};continue
   data=[]
   for x in items:
    d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,label=int(x.value==spec.values[0]),ids=enc(x.text));data.append(d)
   records+=data;fit=score_row(data);fits[row]=fit
   report[row]={'build':'PASS','BOW':fit['test_auroc'],'gate_pass':fit['test_auroc']<=.65}
 dump(a.out/'ITEMS.PRIVATE.json',records);dump(a.out/'FITS.PRIVATE.json',fits);dump(a.out/'REPORT.json',report)
 dump(a.out/'QA_RECORD.json',{'stage':'PRESEAL_QA_ONLY','files':{n:sha(a.out/n) for n in ['ITEMS.PRIVATE.json','FITS.PRIVATE.json','REPORT.json']},'source_files':{n:sha(HERE/n) for n in ['common57.py','group_a.py','group_b.py','amendment_rows.py','qa_preview57.py']}})
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
