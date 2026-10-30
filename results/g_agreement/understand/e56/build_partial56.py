"""Preserve completed E56 draft rows and CPU QA; never issue a final bank seal."""
import argparse,math
from dataclasses import asdict
from common56 import *
import twin_bases,independent_rows
IMPLICIT=('tense_implicit','linewrap_implicit','language_continuation','anomaly_state')
def main():
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 if sha(a.tokenizer)!=TOKENIZER_SHA:raise ValueError('tokenizer mismatch')
 if (HERE/'BANK_FREEZE.lock').exists():raise ValueError('already frozen')
 from transformers import PreTrainedTokenizerFast
 tok=PreTrainedTokenizerFast(tokenizer_file=str(a.tokenizer));enc=lambda s:tok.encode(s,add_special_tokens=False)
 items=[];definitions={}
 for module in [twin_bases,independent_rows]:
  for row,spec in module.SPECS.items():
   group=module.generate(row);validate(group,spec,lambda s:module.check_label(row,s),enc)
   definitions[row]=asdict(spec)
   for x in group:
    d=asdict(x);d.update(id=f'{row}:{x.template_index}:{x.filler_index}:{x.variant}',feature=row,split=x.split,cluster=x.template_index,label=int(x.value==spec.values[0]),ids=enc(x.text));items.append(d)
 e54=HERE.parent/'e54';manifest=json.loads((e54/'FREEZE_MANIFEST.json').read_text());root=HERE.parents[3]
 seal_path=root/manifest['bank_seal']['path'];assert sha(seal_path)==manifest['bank_seal']['sha256']
 seal=json.loads(seal_path.read_text())
 for n,h in seal['files'].items():assert sha(seal_path.parent/n)==h,n
 original=json.loads((root/manifest['items']['path']).read_text()) if 'items' in manifest else json.loads((seal_path.parent/'items.PRIVATE.json').read_text())
 bridge=[x for x in original if x['feature']=='reasoning_bridge']
 assert len(bridge)==168
 items.extend(bridge)  # Exact dicts and IDs from the sealed E54 bank, no regeneration.
 definitions['reasoning_bridge']={'A':'cat','B':'dog','answer_digit':'4','E54_bank_seal_sha256':sha(seal_path),'reused_exactly':True}
 a.out.mkdir(parents=True,exist_ok=False);dump(a.out/'items.PRIVATE.json',items);dump(a.out/'ROW_DEFINITIONS.json',definitions)
 sources={n:sha(HERE/n) for n in ['common56.py','twin_bases.py','independent_rows.py','build_partial56.py','test_build56.py']}
 dump(a.out/'DRAFT_MANIFEST.json',{'status':'PARTIAL_DRAFT_NOT_FROZEN','items':len(items),'rows':list(definitions),'source_files':sources,'E54_bank_seal_sha256':sha(seal_path),'files':{n:sha(a.out/n) for n in ['items.PRIVATE.json','ROW_DEFINITIONS.json']}})
 with (a.out/'BOW_ATTEMPT.lock').open('x') as f:f.write(sha(a.out/'DRAFT_MANIFEST.json')+'\n')
 fits={};metrics={}
 for row in IMPLICIT:
  fit=score_row([x for x in items if x['feature']==row]);fits[row]=fit;s=fit['test_auroc']
  if not math.isfinite(s):raise ValueError('invalid BOW score')
  metrics[row]={'test_auroc':s,'gate_pass':s<=.65}
 dump(a.out/'BOW_FITS.PRIVATE.json',fits);dump(a.out/'BOW_METRICS.json',metrics)
 dump(a.out/'QA_RECORD.json',{'status':'PRESEAL_CPU_QA_ONLY','draft_manifest_sha256':sha(a.out/'DRAFT_MANIFEST.json'),'files':{n:sha(a.out/n) for n in ['BOW_FITS.PRIVATE.json','BOW_METRICS.json','BOW_ATTEMPT.lock']}})
 print('Preserved partial draft:',len(items),'items; CPU BOW:',metrics)
if __name__=='__main__':main()
