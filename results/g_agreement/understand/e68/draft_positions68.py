"""Draft only: no position seal or capture request is produced."""
import hashlib,json,re
from pathlib import Path
from collections import Counter
from transformers import PreTrainedTokenizerFast
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'e49/cache/frozen_2026-10-26'
TOKENIZER=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9/tokenizer.json')
ROWS=('container_after_move','holder_after_handovers','arith_compare','topic_twin')
SUFFIX='\nQ: Who has it now?\nA:'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,obj):p.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def boundary(row,text):
 if row=='container_after_move':
  marker=' The light remains steady throughout the activity.'
  assert text.count(marker)==1
  end=text.index(marker);assert text[end-1]=='.';return end
 if row=='holder_after_handovers':
  marker=' The room stays quiet for a moment. The clock ticks by the door.'
  assert text.count(marker)==1
  end=text.index(marker);assert text[end-1]=='.';return end
 if row=='arith_compare':
  m=re.search(r'\nIs \d+ × \d+ more than \d+\? Answer:$',text);assert m
  return text.index('? Answer:',m.start())+1
 if row=='topic_twin':
  m=re.search(r'the (?:engineer inspected the safety interlock|gardener inspected the flower beds)(?= and adjusted )',text);assert m
  return m.end()
 raise ValueError(row)
def main():
 source=SOURCE/'items.PRIVATE.json';seal=json.loads((SOURCE/'BANK_SEAL.json').read_text())
 assert sha(source)==seal['files'][source.name]
 assert sha(TOKENIZER)=='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))
 items=[i for i in json.loads(source.read_text()) if i['split']=='test' and i['feature'] in ROWS]
 records=[];examples={r:[] for r in ROWS}
 for item in items:
  row=item['feature'];original=item['text'];text=original+(SUFFIX if row=='holder_after_handovers' else '')
  enc=tok(text,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];offsets=enc['offset_mapping']
  assert ids[:len(item['ids'])]==item['ids']
  end=boundary(row,original);matches=[j for j,(a,b) in enumerate(offsets) if a<=end-1<b];assert len(matches)==1
  far=matches[0];pre=len(ids)-1;mid=(far+pre)//2;gap=pre-far
  assert far<=mid<=pre
  positions={k:{'index':j,'token_id':ids[j],'token_text':tok.decode([ids[j]]),'char_span':offsets[j]} for k,j in [('P_far',far),('P_mid',mid),('P_pre',pre)]}
  rec={'id':item['id'],'row':row,'source_prefix_sha256':hashlib.sha256(original.encode()).hexdigest(),'source_tokens':len(item['ids']),'append_suffix':SUFFIX if row=='holder_after_handovers' else '', 'positions':positions,'gap':gap,'dropped':gap<6,'reason':'fewer than six tokens' if gap<6 else None,'far_clause_end_char_exclusive':end}
  records.append(rec)
  if len(examples[row])<3:examples[row].append(dict(rec,original_text=original,far_context=original[max(0,end-140):end],suffix_after_far=text[end:]))
 counts={r:{'test':sum(x['row']==r for x in records),'kept':sum(x['row']==r and not x['dropped'] for x in records),'dropped':sum(x['row']==r and x['dropped'] for x in records),'gap_counts':dict(sorted(Counter(x['gap'] for x in records if x['row']==r).items()))} for r in ROWS}
 assert all(x['test']==84 for x in counts.values())
 draft={'status':'DRAFT_AWAITING_COORDINATOR_RATIFICATION_NO_CAPTURE','authority_commit':'24070152','source_bank_seal_sha256':sha(SOURCE/'BANK_SEAL.json'),'source_items_sha256':sha(source),'rules_sha256':sha(HERE/'POSITION_RULES_DRAFT_2026-10-27.md'),'generator_sha256':sha(Path(__file__)),'tokenizer_sha256':sha(TOKENIZER),'counts':counts,'items':records}
 dump(HERE/'POSITIONS_DRAFT.json',draft);dump(HERE/'WORKED_EXAMPLES_DRAFT.json',examples)
 lines=['# E68 worked examples — draft for ratification','', 'No position seal. No capture authorised by this draft.','', '| Row | Test | Kept | Dropped | Token-gap distribution |','|---|---:|---:|---:|---|']
 for r,c in counts.items():lines.append(f"| {r} | {c['test']} | {c['kept']} | {c['dropped']} | {c['gap_counts']} |")
 for r,exs in examples.items():
  lines+=['',f'## {r}']
  for ex in exs:
   lines+=['',f"### {ex['id']} — {'DROP' if ex['dropped'] else 'KEEP'}, gap {ex['gap']}",'',f"Final state clause context: `{ex['far_context']}`",'',f"Text after P_far's clause boundary: `{json.dumps(ex['suffix_after_far'],ensure_ascii=False)}`",'', '| Position | Index | Token ID | Decoded token |','|---|---:|---:|---|']
   for k,p in ex['positions'].items():lines.append(f"| {k} | {p['index']} | {p['token_id']} | `{json.dumps(p['token_text'],ensure_ascii=False)}` |")
 (HERE/'WORKED_EXAMPLES_DRAFT.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
