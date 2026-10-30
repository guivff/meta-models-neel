"""Seal ratified E68 anchors without changing or recomputing the draft anchors."""
import copy,hashlib,json,tarfile
from pathlib import Path
from collections import Counter
from transformers import PreTrainedTokenizerFast
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'e49/cache/frozen_2026-10-26'
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def main():
 assert not (HERE/'POSITION_SEAL.json').exists(),'Already sealed; do not overwrite'
 draft=read(HERE/'POSITIONS_DRAFT.json')
 assert sha(SOURCE/'BANK_SEAL.json')==draft['source_bank_seal_sha256']
 assert sha(SOURCE/'items.PRIVATE.json')==draft['source_items_sha256']
 assert sha(HERE/'POSITION_RULES_DRAFT_2026-10-27.md')==draft['rules_sha256']
 assert sha(TOKENIZER)==draft['tokenizer_sha256']
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
 sources={x['id']:x for x in read(SOURCE/'items.PRIVATE.json')}
 records=[];inputs=[];labels=[]
 for old in draft['items']:
  x=copy.deepcopy(old);item=sources[x['id']]
  assert item['split']=='test' and item['feature']==x['row']
  assert hashlib.sha256(item['text'].encode()).hexdigest()==x['source_prefix_sha256']
  x['dropped']=x['row']=='arith_compare'
  x['reason']='INFEASIBLE: comparison fully stated only two tokens before answer; §185 deviation 2' if x['dropped'] else None
  records.append(x)
  if x['dropped']:continue
  text=item['text']+x['append_suffix'];ids=tok.encode(text,add_special_tokens=False)
  assert ids[:len(item['ids'])]==item['ids']
  assert x['gap']=={'container_after_move':14,'holder_after_handovers':26,'topic_twin':5}[x['row']]
  for p in x['positions'].values():assert ids[p['index']]==p['token_id']
  assert x['positions']['P_pre']['index']==len(ids)-1
  inputs.append({'id':item['id'],'feature':x['row'],'text':text,'ids':ids,'positions':{k:v['index'] for k,v in x['positions'].items()},'source_prefix_tokens':len(item['ids'])})
  labels.append({'id':item['id'],'feature':x['row'],'label':item['label'],'value':item['value']})
 assert len(inputs)==252 and len(records)==336
 out=HERE/'cache/ratified_2026-10-27';out.mkdir(parents=True,exist_ok=False)
 write(out/'INPUTS.json',inputs);write(out/'LABELS.PRIVATE.json',labels)
 final={'experiment':'E68','status':'SEALED_RATIFIED','authority_commit':'7e6ea0ccb8c3b60af382660e3b221e8af6ea896a','ratified_draft_commit':'2587767','draft_sha256':sha(HERE/'POSITIONS_DRAFT.json'),'source_bank_seal_sha256':draft['source_bank_seal_sha256'],'source_items_sha256':draft['source_items_sha256'],'indexing':'zero-based tokens, inclusive capture position','counts':{'container_after_move':{'kept':84,'dropped':0},'holder_after_handovers':{'kept':84,'dropped':0},'arith_compare':{'kept':0,'dropped':84,'status':'INFEASIBLE'},'topic_twin':{'kept':84,'dropped':0}},'items':records}
 write(HERE/'POSITIONS.json',final)
 files=[HERE/'POSITIONS.json',HERE/'POSITIONS_DRAFT.json',HERE/'POSITION_RULES_DRAFT_2026-10-27.md',HERE/'WORKED_EXAMPLES_DRAFT.json',HERE/'seal_positions68.py',HERE/'test_sealed68.py',out/'INPUTS.json',out/'LABELS.PRIVATE.json']
 write(HERE/'POSITION_SEAL.json',{'experiment':'E68','status':'SEALED','authority_commit':final['authority_commit'],'tokenizer_sha256':sha(TOKENIZER),'files':{str(p.relative_to(HERE)):sha(p) for p in files}})
 archive=HERE/'cache/E68_POSITIONS_2026-10-27.tar.gz'
 with tarfile.open(archive,'w:gz') as tf:
  for p in files+[HERE/'POSITION_SEAL.json']:tf.add(p,arcname=str(p.relative_to(HERE)))
 write(HERE/'LAUNCH_REQUEST.json',{'experiment':'E68','status':'READY','runner_owner':'W-mechanism','launch_owner':'Integrator','authority_commit':final['authority_commit'],'position_seal_sha256':sha(HERE/'POSITION_SEAL.json'),'archive_path':str(archive),'archive_sha256':sha(archive),'inputs_path':str(out/'INPUTS.json'),'private_labels_CPU_only':str(out/'LABELS.PRIVATE.json'),'items':252,'positions_per_item':3,'capture_positions':756,'gpu_cap_seconds':2160,'readers':{'Oracle':{'block':44,'max_new_tokens':128},'NLA':{'block':42,'max_new_tokens':512,'stop':'</explanation>'}},'greedy_readouts_per_item_position_reader':1,'reader_sees_item_text':False,'probe':'AUROC at each position; preserve registered probe protocol','judge':'blind, §172 rubric','R_O1':'For each reader, S(P_pre)-S(P_far) >= 0.30 on BOTH container_after_move and holder_after_handovers; topic_twin changes by < 0.15 (unchanged §185 control criterion).','falsifier':'S(P_pre)-S(P_far) < 0.10 on BOTH state rows','infeasible_row':'arith_compare; excluded by §185 deviation 2, not a negative result','control_gap_exception':'topic_twin has no minimum gap; all 84 gap-5 items retained','ratification_required':False})
 print(json.dumps({'seal':sha(HERE/'POSITION_SEAL.json'),'items':len(inputs),'counts':final['counts']},indent=2))
if __name__=='__main__':main()
