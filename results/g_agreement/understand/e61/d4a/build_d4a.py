"""D4a amendments 1/2; CPU-only construction and descriptive BOW."""
from pathlib import Path
import json,hashlib,sys,shutil
from collections import Counter
HERE=Path(__file__).resolve().parent;UNDER=HERE.parents[1]
sys.path.insert(0,str(UNDER/'e49'));from bow_once import score_row
SOURCE=HERE.parent/'cache/bank_2026-10-27_v1'
SOURCE_SEAL='08197f8fffe98ab2d562d618b6be9f0d17d86e3769c415e301a6ef765eb29e2d'
CONCEPTS=('birds','citrus','musical_instruments','planets');NAMES=('birds','citrus fruits','musical instruments','planets')
ARMS=('think','ignore','none','mention','cross')
DEV_VERBS=('examined','lifted','shifted','rested','arranged','balanced');DEV_OBJECTS=('box','tray','case','pouch','bag','satchel','container')
PROMPTS=('The animal with feathers that flies is a','The sour yellow fruit is a','The large keyboard instrument with black and white keys is a','The red planet is')
ANSWERS=(' bird',' lemon',' piano',' Mars')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def instruction(c,arm):
 name=NAMES[c]
 return {'think':f'Think about {name} while copying.','ignore':f'Do not think about {name}.','none':'','mention':f'The note mentions {name}.','cross':f'Do not think about {NAMES[c^1]}.'}[arm]
def make(c,t,f,sentence,arm,split,enc):
 base=f'D4a:{split}:{c}:{t}:{f}';ins=instruction(c,arm)
 prefix=(ins+'\n' if ins else '')+'Copy the following sentence exactly.\nSentence: '+sentence+'\nCopy: '+sentence
 suffix='\nComplete: '+PROMPTS[c];text=prefix+suffix;ids=enc(text);read=enc(prefix);ans=enc(ANSWERS[c]);assert len(ans)==1 and enc(text+ANSWERS[c])==ids+ans
 return {'id':base+':'+arm,'base_item_id':base,'feature':'white_bear','split':split,'arm':arm,'concept':CONCEPTS[c],'label':None if arm=='none' else int(c%2==0),'instruction':ins,'copied_sentence':sentence,'read_prefix':prefix,'read_ids':read,'read_token_index':len(read)-1,'completion_suffix':suffix,'completion_prompt':text,'completion_ids':ids,'answer':ANSWERS[c],'answer_token_id':ans[0],'answer_token_boundary_stable':True,'matching_concept_metadata_only':arm=='none'}
def construct(enc):
 assert sha(SOURCE/'BANK_SEAL.json')==SOURCE_SEAL
 seal=json.loads((SOURCE/'BANK_SEAL.json').read_text());assert sha(SOURCE/'D4_ITEMS.PRIVATE.json')==seal['files']['D4_ITEMS.PRIVATE.json']
 old=json.loads((SOURCE/'D4_ITEMS.PRIVATE.json').read_text());items=list(old);meta={}
 for c in range(4):
  for t in range(6):
   for f in range(7):
    oldnone=next(x for x in old if x['base_item_id']==f'D4:{t}:{f}:{c%2}' and x['arm']=='none')
    arms=('mention','cross') if c<2 else ARMS
    for arm in arms:
     x=make(c,t,f,oldnone['copied_sentence'],arm,'test',enc)
     if c<2:x['base_item_id']=oldnone['base_item_id']
     items.append(x)
    sentence=f'The assistant {DEV_VERBS[t]} the {DEV_OBJECTS[f]} beside the window and read the tag before returning to the counter.'
    items.append(make(c,t,f,sentence,'think','dev',enc))
 for x in items:
  c=CONCEPTS.index(x['concept']);meta[x['id']]={'probe_pair':('birds_vs_citrus' if c<2 else 'instruments_vs_planets'),'target_label':int(c%2==0),'target_concept':x['concept'],'instructed_concept':CONCEPTS[c^1] if x['arm']=='cross' else None if x['arm']=='none' else x['concept'],'reused_D4_record':x['id'].startswith('D4:')}
 return items,meta,old

def validate(items,meta,old,enc):
 assert len(items)==1008 and len({x['id'] for x in items})==1008
 by={x['id']:x for x in items};assert all(by[x['id']]==x for x in old)
 assert sum(x['split']=='dev' for x in items)==168
 test=[x for x in items if x['split']=='test'];assert len(test)==840
 for c in CONCEPTS:
  assert Counter(x['arm'] for x in test if x['concept']==c)=={a:42 for a in ARMS}
 for base in {x['base_item_id'] for x in test}:
  rows=[x for x in test if x['base_item_id']==base];assert len(rows)==5
  for k in ['copied_sentence','completion_suffix','completion_prompt','answer']:
   if k=='completion_prompt':continue
   assert len({x[k] for x in rows})==1
  none=next(x for x in rows if x['arm']=='none')
  assert none['instruction']==''
  for x in rows:
   assert x['read_prefix']==(x['instruction']+'\n' if x['instruction'] else '')+none['read_prefix']
 for x in items:assert enc(x['read_prefix'])==x['read_ids'] and enc(x['completion_prompt'])==x['completion_ids']
 # Paired concepts share copied sentences, read tokens and matched prefix lengths.
 ratios=[]
 for split in ('dev','test'):
  rows=[x for x in items if x['split']==split]
  for pair in ('birds_vs_citrus','instruments_vs_planets'):
   for arm in (('think',) if split=='dev' else ARMS):
    group=[x for x in rows if meta[x['id']]['probe_pair']==pair and x['arm']==arm]
    sentences={x['copied_sentence'] for x in group};assert len(sentences)==42
    for sentence in sentences:
     a,b=[x for x in group if x['copied_sentence']==sentence];assert a['read_ids'][-1]==b['read_ids'][-1]
     ratio=max(len(a['read_ids']),len(b['read_ids']))/min(len(a['read_ids']),len(b['read_ids']));assert ratio<=1.10;ratios.append(ratio)
 dev_s={x['copied_sentence'] for x in items if x['split']=='dev'};test_s={x['copied_sentence'] for x in test};assert not dev_s&test_s
 return {'records':1008,'dev':168,'test':840,'reused_D4_records':252,'new_records':756,'test_base_items':168,'arms':ARMS,'concepts':CONCEPTS,'max_paired_read_length_ratio':max(ratios),'source_records_unchanged':True,'dev_test_copy_sentences_disjoint':True,'BOW_gate':False}

def freeze(enc):
 out=HERE/'cache/bank_2026-10-27';out.mkdir(parents=True,exist_ok=False)
 items,meta,old=construct(enc);v=validate(items,meta,old,enc);fits={};report={}
 for pair in ('birds_vs_citrus','instruments_vs_planets'):
  dev=[dict(x,ids=x['read_ids'],label=meta[x['id']]['target_label']) for x in items if x['split']=='dev' and meta[x['id']]['probe_pair']==pair]
  for arm in ARMS:
   test=[dict(x,ids=x['read_ids'],label=meta[x['id']]['target_label']) for x in items if x['split']=='test' and x['arm']==arm and meta[x['id']]['probe_pair']==pair]
   fit=score_row(dev+test);key=pair+'/'+arm;fits[key]=fit;report[key]={'test_auroc':fit['test_auroc'],'descriptive_only':True,'excludes_items':False}
 for n,x in [('items.PRIVATE.json',items),('PROBE_TARGETS.PRIVATE.json',meta),('VALIDATION.json',v),('BOW_FITS.PRIVATE.json',fits),('BOW_REPORT.json',report)]:dump(out/n,x)
 sources={p.name:sha(p) for p in HERE.glob('*.py')}
 for n in sources:shutil.copyfile(HERE/n,out/n)
 dump(out/'BANK_SEAL.json',{'experiment':'E61 D4a amendments 1/2','source_D4_seal':SOURCE_SEAL,'files':{p.name:sha(p) for p in out.iterdir() if p.is_file()},'source_files':sources,'provisional_note_sha256':sha(HERE/'PROVISIONAL_2026-10-27.md'),'BOW_code_sha256':sha(UNDER/'e49/bow_once.py')})
 print('D4a seal',sha(out/'BANK_SEAL.json'));print(json.dumps(report,indent=2))
if __name__=='__main__':
 from transformers import PreTrainedTokenizerFast
 p=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json');assert sha(p)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
 t=PreTrainedTokenizerFast(tokenizer_file=str(p));freeze(lambda s:t.encode(s,add_special_tokens=False))
