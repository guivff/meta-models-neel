"""Bind W-text's sealed amendments; strip private labels, retain read-point dev/test grid."""
import argparse,sys
from pathlib import Path
from prepare_second import manifest
from runtime62 import *
from amendment_inputs import validate_placebo,validate_d4a

def main():
 p=argparse.ArgumentParser();p.add_argument('--wtext',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 for e,rel in [('E62P','e62/placebo'),('D4A','e61/d4a')]:
  root=a.wtext/'results/g_agreement/understand'/rel/'cache/bank_2026-10-27';verify(root,'BANK_SEAL.json');private=read(root/'items.PRIVATE.json');public=[]
  for x in private:
   if e=='E62P':item={k:x[k] for k in ('id','ids','text','feature','split','base_item_id','state','rung','first_content_index','read_index','alpha_token_id','beta_token_id') if k in x}
   else:item={'id':x['id'],'ids':x['read_ids'],'text':x['read_prefix'],'feature':x['feature'],'split':x['split'],'pair_id':x['base_item_id'],'concept':x['concept'],'arm':x['arm'],'read_index':x['read_token_index'],'completion_ids':x['completion_ids'],'completion_text':x['completion_prompt'],'answer_text':x['answer'],'answer_token_id':x['answer_token_id'],'reuse_first_wave':x['id'].startswith('D4:')}
   public.append(item)
  (validate_placebo if e=='E62P' else validate_d4a)(public);out=a.out/e.lower();out.mkdir(parents=True,exist_ok=False);dump(out/'items.json',public)
  if e=='D4A':
   lex=read(Path(read(HERE.parents[1]/'e61/job/INPUT_BINDING.json')['inputs'])/'LEXICON.json');lex.update(musical_instruments=['musical instrument','musical instruments','instrument','instruments','piano','pianos'],planets=['planet','planets','Mars']);dump(out/'LEXICON.json',lex)
  b=manifest(out,e,{'bank_seal_sha256':sha(root/'BANK_SEAL.json'),'private_items':str(root/'items.PRIVATE.json'),'private_items_sha256':sha(root/'items.PRIVATE.json')});dump(HERE/(e+'_INPUT_BINDING.json'),b)
 print('AMENDMENT_INPUTS_BOUND')
if __name__=='__main__':main()
