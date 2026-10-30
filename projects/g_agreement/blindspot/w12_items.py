"""W12 §100: authored syntax families; CPU-only immutable item freeze."""
import hashlib,json,random
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
from .items import Feature,match_pair,encode,load_pinned_tokenizer,TOKENIZER_SHA256
from . import protocol as P
SEED=20261026
NOUNS=('clerk','guard','cook','sailor','teacher','farmer','painter')
# Twelve distinct clause frames; six held-out families per split.
ROLE=(('Greeted by the visitor was the {n}', 'The visitor greeted the {n}'),
 ('Yesterday the {n}', 'Yesterday we thanked the {n}'),
 ('Near the gate stood the {n}', 'Near the gate they met the {n}'),
 ('Although it rained the {n}', 'Although it rained she followed the {n}'),
 ('Called by the visitor was the {n}', 'After lunch he called the {n}'),
 ('In our story the {n}', 'In our story the captain hired the {n}'),
 ('Praised by the visitors was the quiet {n}', 'We praised the quiet {n}'),
 ('On Monday the {n}', 'On Monday I visited the {n}'),
 ('Beside the river the {n}', 'Beside the river we noticed the {n}'),
 ('Warned by the visitor was the {n}', 'Before dawn someone warned the {n}'),
 ('At that moment the {n}', 'At that moment they invited the {n}'),
 ('As expected the {n}', 'As expected the director chose the {n}'))
QUESTION=(('Did the {n}', 'The {n} did'),('Can the {n}','The {n} can'),
 ('Will the {n}','The {n} will'),('Has the {n}','The {n} has'),('Was the {n}','The {n} was'),
 ('Does the {n}','The {n} does'),('Could the {n}','The {n} could'),('Would the {n}','The {n} would'),
 ('Should the {n}','The {n} should'),('Had the {n}','The {n} had'),('Is the {n}','The {n} is'),('Might the {n}','The {n} might'))
LONG=(
 'After a long day at the harbour we walked along the quiet road beside the {n}',
 'While the visitors waited near the entrance a guide carried the heavy box towards the {n}',
 'Before the concert began the organiser checked the doors and then spoke softly to the {n}',
 'During the storm several people stayed inside the old building and waited patiently for the {n}',
 'Although the shop had closed a customer stood outside with a letter addressed to the {n}',
 'When morning came the family packed their bags and left a written message for the {n}',
 'Beyond the village there was a narrow path which led directly to the house of the {n}',
 'Nobody at the meeting could remember who had first suggested sending an invitation to the {n}',
 'If the weather remained fine the children planned to take their drawings over to the {n}',
 'Rather than disturb the workers we left the parcel in the small room behind the {n}',
 'Since the bridge was closed the driver followed a different route and eventually found the {n}',
 'Having finished the repairs the team collected their tools and went to look for the {n}')
CLOSED=('The bell rang.','Rain covered the road.','A train arrived.','Someone opened the gate.',
 'The lantern went out.','A dog crossed the yard.','The market closed.','Birds gathered overhead.',
 'A cart stopped nearby.','The clock struck noon.','A door swung shut.','The visitors sat down.')
EMBED=(('The {n} waited beside the gate and the visitor', 'The {n} who waited beside the gate with the visitor'),
 ('The {n} had a neighbour and the neighbour', 'The {n} whose neighbour'),
 ('The {n} saw the driver and the driver', 'The {n} whom the driver'),
 ('The {n} carried a letter and the captain', 'The {n} who carried a letter for the captain'),
 ('The {n} knew a guide and the guide', 'The {n} whose guide'),
 ('The {n} called the visitor and the visitor', 'The {n} whom the visitor'),
 ('The {n} watched the river and the merchant', 'The {n} who watched the river with the merchant'),
 ('The {n} owned a boat and the boat', 'The {n} whose boat'),
 ('The {n} met the artist and the artist', 'The {n} whom the artist'),
 ('The {n} opened the shop and the customer', 'The {n} who opened the shop for the customer'),
 ('The {n} kept a notebook and the notebook', 'The {n} whose notebook'),
 ('The {n} thanked the officer and the officer', 'The {n} whom the officer'))
DEFS={
 'syntax_role':(('subject','object'),('the current noun as the subject of its clause','the current noun as the object of its clause'),(('subject','object'),('agent','patient'))),
 'sentence_type':(('question','statement'),('a question in progress','a statement in progress'),(('question','statement'),('interrogative','declarative'))),
 'sentence_position':(('first_three','after_twelve'),('the read position within the first three words of the sentence','the read position after word twelve of the sentence'),(('early','late'),('beginning','later'))),
 'paragraph_index':(('first','third_or_later'),('the read position in the first paragraph','the read position in the third or a later paragraph'),(('first','third'),('initial','later'))),
 'paragraph_start':(('first_sentence','later_sentence'),('the read position in the first sentence of a paragraph','the read position in a later sentence of a paragraph'),(('first','later'),('initial','subsequent'))),
 'clause_embedding':(('main','relative'),('the read position in the main clause','the read position inside an unclosed relative clause'),(('main','relative'),('independent','embedded')))}
def bodies(row,t,n):
 if row=='syntax_role':return [s.format(n=n) for s in ROLE[t]]
 if row=='sentence_type':return [s.format(n=n) for s in QUESTION[t]]
 if row=='sentence_position':return ['The '+n,LONG[t].format(n=n)]
 if row=='paragraph_index':return ['The '+n,CLOSED[t]+'\n\n'+CLOSED[(t+1)%12]+'\n\nThe '+n]
 if row=='paragraph_start':return ['The '+n,CLOSED[t]+' The '+n]
 return [s.format(n=n) for s in EMBED[t]]
def specs():
 out={}
 for row,(values,desc,native) in DEFS.items():
  f=Feature('syntax','binary',values,desc,native[0]);out[row]={r:f.pairs(r) for r in ('olens','nla')}
  out[row].update(values=list(values),kind='binary',domain='syntax',**{'class':'structure'},jlens=native,logit=native)
 return out
def build(tok):
 rng=random.Random(SEED);items=[]
 for row,(values,_,_) in DEFS.items():
  for t in range(12):
   for v,n in enumerate(NOUNS):
    bs=bodies(row,t,n);pair=hashlib.sha256(f'W12:{row}:{t}:{v}'.encode()).hexdigest()[:24]
    for side,(text,ids) in enumerate(match_pair(tok,bs,rng)):
     items.append(dict(id=hashlib.sha256(f'{pair}:{side}'.encode()).hexdigest()[:24],feature=row,domain='syntax',split='dev' if t%2==0 else 'test',cluster=f'W12:{row}:{t}',value=values[side],text=text,ids=ids,**{'class':'structure'},meta=dict(pair_id=pair,template_index=t,variant=v,body=bs[side],kind='binary',read_position=len(ids)-1,token_length=len(ids))))
 return items
def verify(tok,items):
 assert len(items)==1008 and len({x['id'] for x in items})==1008
 pairs=defaultdict(list)
 for x in items:
  assert encode(tok,x['text'])==x['ids'];assert x['meta']['read_position']==len(x['ids'])-1
  pairs[x['meta']['pair_id']].append(x)
 for xs in pairs.values():assert len(xs)==2 and len(xs[0]['ids'])==len(xs[1]['ids'])
 for row,(values,_,_) in DEFS.items():
  groups=[x for x in items if x['feature']==row]
  for split in ('dev','test'):
   xs=[x for x in groups if x['split']==split]
   assert Counter(x['value'] for x in xs)==dict.fromkeys(values,42)
   assert len({x['cluster'] for x in xs})==6
  assert not ({x['cluster'] for x in groups if x['split']=='dev'} & {x['cluster'] for x in groups if x['split']=='test'})
 for t in range(12):
  a,b=bodies('sentence_position',t,'clerk');assert len(a.split())<=3 and len(b.split())>12
 return {'items':1008,'rows':6,'families_per_row':12,'per_value_per_split':42,'exact_pair_lengths':True,'no_model_calls':True}
def freeze(tok,out):
 items=build(tok);audit=verify(tok,items);out.mkdir(parents=True,exist_ok=False)
 P.jsonl(out/'items.jsonl',items);P.dump(out/'templates.json',specs());P.dump(out/'AUDIT.json',audit)
 now=datetime.now(timezone.utc).isoformat()
 P.dump(out/'FREEZE.json',dict(experiment='W12',registration='§100; §137 1721470e',actual_freeze_utc=now,seed=SEED,rows=list(DEFS),tokenizer_sha256=TOKENIZER_SHA256,files={n:P.sha(out/n) for n in ['items.jsonl','templates.json','AUDIT.json']},source_sha256=P.sha(Path(__file__)),scoring_hold='W-text D/P seal and §136 mechanical predictions bound to this freeze; no reader scoring before release',reply_check='Gmail 2026-10-26: no matches after Oct23 for Camila/Achim/Blank; no verified feature substitution available; prior Slack source gap remains; retain default six rows'))
 print(json.dumps({'freeze_sha256':P.sha(out/'FREEZE.json'),'actual_freeze_utc':now,**audit},indent=2))
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--tokenizer',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();freeze(load_pinned_tokenizer(a.tokenizer),a.out)
