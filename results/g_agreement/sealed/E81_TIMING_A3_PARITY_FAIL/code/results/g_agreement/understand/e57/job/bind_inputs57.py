"""Normalize W-text's sealed bank, never regenerate items or tokenize again."""
import argparse,json,sys,tarfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[1]/'e56/job'))
from contract56 import read,dump,verify,sha,seal,require,SEED,ROOT
BANK='cff66637fedd6afd795370e3efbe3e8262d77c98a64e60e8580a9507dd295f7c'

def bind(bank,out):
 verify(bank,'BANK_SEAL.json',BANK)
 xs=read(bank/'items.PRIVATE.json');ann=read(bank/'ANNOTATIONS.PRIVATE.json');defs=read(bank/'DEFINITIONS.json');lookup={x['id']:x for x in xs}
 require(len(xs)==3360 and len(defs)==20,'frozen bank grid')
 out.mkdir(parents=True,exist_ok=False);rng=np.random.default_rng(SEED)
 plan={'experiment':'E57','seed':SEED,'bank_seal_sha256':BANK,'shards':{str(i):sorted(defs)[i::3] for i in range(3)},'native_ids':{},'rows':{},'count_metadata':{},'donors':{},'item_pairs':{},'judge_values':{}}
 # Match source keys across all focus arms, and the inherited count-gradient twins.
 keys=sorted({(x['template_index'],x['filler_index']) for x in xs if x['split']=='test'})
 chosen=set(keys[i] for i in sorted(rng.choice(len(keys),20,replace=False)))
 e56sample=read(HERE.parents[1]/'e56/job/SAMPLING.json')['native_ids']
 countkeys={tuple(lookup[k][s] for s in ('template_index','filler_index','variant')) for k in e56sample['linewrap_implicit']}
 animals=sorted({w for a in ann.values() for w in a.get('preceding_animals',[])})
 animals+=sorted({a['last_item'] for k,a in ann.items() if k.startswith('category_switch:') and lookup[k]['label']==0})
 for row,d in defs.items():
  test=[x for x in xs if x['feature']==row and x['split']=='test'];plan['native_ids'][row]=[x['id'] for x in test]
  pairs={'antonym_crosslingual':[' big',' long'],'sentiment_judgement':[' positive',' negative'],'two_hop_answer':[' 8',' 6'],'subject_number':[' barn is',' barn are'],'clause_pending':[' the road dried',' and the road dried'],'nesting_depth':[' ]',' ]]]'],'indent_level':['\n    pass','\n            pass']}.get(row)
  item_specific=row in ('multi_token_entity','page_range_digit')
  plan['rows'][row]={'probe_applicable':d['probe_applicable'],'probe_not_applicable_reason':None if d['probe_applicable'] else 'Registered unlabelled condition','continuation_pairs':[pairs] if pairs else ('PER_ITEM' if item_specific else None),'continuation_not_applicable_reason':None if pairs or item_specific else ('Both spelled-out counts start with s' if row=='count_gradient_first_letter' else 'No frozen discriminating natural next-text pair'),'canonical_row':d['canonical_row']}
  for x in test:
   k=x['id'];a=ann.get(k,{})
   values=a.get('answer_pair',a.get('value_words',d.get('spec',d).get('values')))
   if row.startswith('focus_'):values=['birds','citrus']
   plan['judge_values'][k]=values
   if item_specific:plan['item_pairs'][k]=[[' '+v for v in a['answer_pair']]]
   if pairs or item_specific:
    candidates=[y for y in test if y['label']!=x['label'] and (not item_specific or ann[y['id']]['answer_pair']==a['answer_pair'])]
    require(candidates,'opposite donor');plan['donors'][k]=sorted(candidates,key=lambda y:y['id'])[int(rng.integers(len(candidates)))]['id']
   if row=='category_switch':plan['count_metadata'][k]={'mention_policy':'word_exact_casefold','animal_lexicon':{w:[w] for w in sorted(set(animals))},'last_animal_id':a['last_item'] if x['label']==0 else None}
   if row=='capacity_list':plan['count_metadata'][k]={'mention_policy':'word_exact_casefold','list_nouns':{w:[w] for w in a['list_nouns']}}
 dump(out/'items.json',[{k:v for k,v in x.items() if k not in ('label','value','variant')} for x in xs])
 dump(out/'RUN_PLAN.json',plan)
 seal(out,'INPUT_SEAL.json',{'experiment':'E57','bank_seal_sha256':BANK,'private_items_sha256':sha(bank/'items.PRIVATE.json'),'annotations_sha256':sha(bank/'ANNOTATIONS.PRIVATE.json')})
 return plan
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--bank',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();bind(a.bank,a.out)
