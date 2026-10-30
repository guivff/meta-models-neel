"""E57 factorial focus, category switch, and unlabeled capacity lists."""
import random,re
from common57 import *
FOCUS_ARMS=('think','mention','ignore','none')
FOCUS_VALUES=('birds','citrus')
CONCEPTS=(('birds','citrus fruits'),('avian creatures','oranges and lemons'))
VERBS=('placed','carried','moved','left','set','positioned','stored','kept','found','held','brought','parked')
OBJECTS=('folder','basket','parcel','bundle','package','carton','crate')
COPY_ROLES=('assistant','visitor')
ANIMALS=('horse','goat','sheep','cow','pig','duck','hen','goose')
COLOURS=(('blue','green','red','yellow','white','black','brown'),('violet','orange','purple','pink','grey','beige','tan'))
NINTH=(('giraffe','panda','lion','tiger','zebra','monkey','camel'),('dog','cat','fox','wolf','bear','deer','mouse'))
CAPACITY_BUCKETS=(
 'apple lemon onion orange mushroom nut honey'.split(),
 'zebra rabbit eagle kitten elephant insect oyster'.split(),
 'desert island ocean mountain river valley forest'.split(),
 'hammer needle ladder pencil shovel wrench saw'.split(),
 'guitar violin drum flute trumpet piano whistle'.split(),
 'jacket apron helmet scarf boot glove sandal'.split(),
 'castle temple cabin palace library tower village'.split(),
 'rocket yacht wagon vessel bicycle truck train'.split(),
 'mirror pillow kettle bucket bottle candle carpet'.split(),
 'ticket envelope notebook newspaper letter map journal'.split(),
 'silver velvet granite marble bamboo leather steel'.split(),
 'queen king pilot nurse teacher actor judge'.split())
CAPACITY_CANDIDATES=[w for bucket in CAPACITY_BUCKETS for w in bucket]

CAPACITY_HEADS=('Items:','List:','Notes:','Inventory:','Entries:','Record:','Collection:','Sequence:','Index:','Set:','Register:','Catalogue:')

def focus_text(t,f,v,arm):
 role=COPY_ROLES[v^(t%2)];copy=f'The {role} {VERBS[t]} the {OBJECTS[f]} near the doorway.'
 concept=CONCEPTS[int(t>=6)][v]
 instruction={'think':f'Think about {concept} while copying.','mention':f'The note mentions {concept}.','ignore':f'Do not think about {concept}.','none':''}[arm]
 prefix=(instruction+' ' if instruction else '')+'Copy the following sentence exactly.\nSentence: '+copy+'\nCopy: '
 return prefix+copy.rsplit(' doorway.',1)[0]

def focus_items(arm):
 row='focus_'+arm
 return [Item(row,t,f,v,focus_text(t,f,v,arm),FOCUS_VALUES[v] if arm!='none' else 'unlabelled') for t in range(12) for f in range(7) for v in range(2)]

def check_focus(text,arm):
 if not text.endswith(' near the'):raise ValueError('not inside copied sentence')
 if arm=='none':
  if not text.startswith('Copy the following sentence exactly.'):raise ValueError('none must omit concept instruction')
  if any(c in text for pair in CONCEPTS for c in pair):raise ValueError('none contains target concept')
  return 'unlabelled'
 prefix={'think':'Think about ','mention':'The note mentions ','ignore':'Do not think about '}[arm]
 if not text.startswith(prefix):raise ValueError('focus arm mismatch')
 a=any(text.startswith(prefix+pair[0]) for pair in CONCEPTS);b=any(text.startswith(prefix+pair[1]) for pair in CONCEPTS)
 if a==b:raise ValueError('focus concept mismatch')
 return 'birds' if a else 'citrus'

def switch_items():
 out=[]
 for t in range(12):
  seq=list(ANIMALS[t%8:]+ANIMALS[:t%8]);seq=seq if t<8 else list(reversed(seq))
  for f in range(7):
   for v in range(2):
    last=(COLOURS if v==0 else NINTH)[int(t>=6)][f]
    out.append(Item('category_switch',t,f,v,', '.join(seq+[last])+',',('colour','animal')[v]))
 return out

def check_switch(text):
 words=[x.strip() for x in text.split(',') if x.strip()]
 if len(words)!=9 or set(words[:8])!=set(ANIMALS):raise ValueError('eight-animal prefix mismatch')
 if words[-1] in sum(COLOURS,()):return 'colour'
 if words[-1] in sum(NINTH,()):return 'animal'
 raise ValueError('last-item category')

def capacity_items(encode):
 buckets=[[w for w in bucket if len(encode(' '+w))==1] for bucket in CAPACITY_BUCKETS]
 if any(not bucket for bucket in buckets):raise ValueError('empty single-token semantic bucket')
 out=[];lists={}
 for t in range(12):
  for f in range(7):
   for v in range(2):
    rng=random.Random(20261027+t*14+f*2+v);words=[rng.choice(bucket) for bucket in buckets];rng.shuffle(words)
    x=Item('capacity_list',t,f,v,CAPACITY_HEADS[t]+' '+', '.join(words)+',','unlabelled');out.append(x);lists[x.source_key]=words
 return out,lists

def check_capacity(text,encode):
 head,body=text.split(': ',1)
 if head+':' not in CAPACITY_HEADS:raise ValueError('capacity scaffold')
 words=[x.strip() for x in body.split(',') if x.strip()]
 if len(words)!=12 or len(set(words))!=12 or any(w not in CAPACITY_CANDIDATES or len(encode(' '+w))!=1 for w in words):raise ValueError('require twelve distinct single-token nouns')
 if any(sum(w in bucket for w in words)!=1 for bucket in CAPACITY_BUCKETS):raise ValueError('require one noun per semantic bucket')
 return 'unlabelled'
