"""Exact full-prefix and hidden-tail QA for candidate file states; CPU data only."""
import collections,hashlib,json,sys
from pathlib import Path
import pyarrow.parquet as pq
from transformers import PreTrainedTokenizerFast
from state84 import scan,hidden
from scan84 import HERE,TOK,split_for,messages_prefix
SECRET_MARKERS=('hf_','sk-','OPENROUTER','HF_TOKEN','api_key','Bearer')

def validate(scanfile,out):
 spec=json.loads(Path(scanfile).read_text())
 for name,digest in spec.get('source_sha256',{}).items():
  if hashlib.sha256((HERE/name).read_bytes()).hexdigest()!=digest:raise ValueError('State source changed after scan')
 wanted=collections.defaultdict(list)
 # All rare first-file candidates; sufficient deterministic reserve of second-file candidates.
 majority=collections.defaultdict(list)
 for c in spec['candidates']:
  if c['state']!='file_being_edited':continue
  if c['label']==0:wanted[c['row_in_shard']].append(c)
  else:majority[c['split']].append(c)
 for split,cs in majority.items():
  for c in sorted(cs,key=lambda c:c['rank'])[:250]:wanted[c['row_in_shard']].append(c)
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK/'tokenizer.json'));tok.chat_template=(TOK/'chat_template.jinja').read_text();stats=collections.Counter();counts=collections.Counter();rowno=0
 out=Path(out);out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():raise ValueError('Candidate validation file already exists; preserve it')
 with out.open('w') as dest:
  for batch in pq.ParquetFile(spec['shard']).iter_batches(batch_size=25,columns=['instance_id','repo','license','trajectory_id','trajectory']):
   for row in batch.to_pylist():
    candidates=wanted.get(rowno,[]);rowno+=1
    if not candidates:continue
    snapshots={s['next_assistant_index']:s for s in scan(row['trajectory'])}
    for c in candidates:
     stats['considered']+=1;n=c['next_assistant_index'];snap=snapshots[n]
     if snap['labels'].get('file_being_edited')!=c['label'] or snap['files']!=c['files']:
      stats['ambiguous_history_under_final_parser_rejected']+=1;continue
     text=tok.apply_chat_template(messages_prefix(row['trajectory'],n),tokenize=False,add_generation_prompt=True,enable_thinking=False)
     if any(s in text for s in SECRET_MARKERS):stats['secret_marker_rejected']+=1;continue
     enc=tok(text,add_special_tokens=False,return_offsets_mapping=True);ids=enc['input_ids'];offsets=enc['offset_mapping']
     if len(ids)<513:stats['short_prefix_rejected']+=1;continue
     tail=tok.decode(ids[-512:],skip_special_tokens=False)
     if not hidden('file_being_edited',tail,c['files']):stats['full_tail_visible_rejected']+=1;continue
     latest=snap['edit_proof'][-1];header=next((s.strip() for s in row['trajectory'][latest]['content'].splitlines() if s.strip()),'')
     past=tok.apply_chat_template(messages_prefix(row['trajectory'],latest+1),tokenize=False,add_generation_prompt=False,enable_thinking=False)
     if not text.startswith(past):stats['nonprefix_render_rejected']+=1;continue
     at=past.rfind(header)
     if at<0:stats['evidence_locator_rejected']+=1;continue
     end=at+len(header);evidence_token=max((i for i,(a,b) in enumerate(offsets) if a<end),default=-1)
     if evidence_token<0 or evidence_token>=len(ids)-512:stats['evidence_in_last512_rejected']+=1;continue
     ident=hashlib.sha256(f'E84|revive|{row["instance_id"]}|{row["trajectory_id"]}|{n}'.encode()).hexdigest()[:24]
     rec=dict(c,id=ident,prompt=text,input_ids=ids,read_position=len(ids)-1,tail512_sha256=hashlib.sha256(tail.encode()).hexdigest(),latest_edit_header_end_token=evidence_token,hidden_distance_tokens=len(ids)-1-evidence_token,full_exact_tail_checked=True)
     dest.write(json.dumps(rec,ensure_ascii=False)+'\n');stats['passed']+=1;counts[str(c['label'])+'/'+c['split']]+=1
 print(json.dumps(dict(file=str(out),statistics=dict(stats),available=dict(counts)),indent=2),flush=True)
 out.with_suffix('.QA.json').write_text(json.dumps(dict(source_scan=str(Path(scanfile).resolve()),source_shard=spec['shard'],statistics=dict(stats),available=dict(counts)),indent=2)+'\n')
if __name__=='__main__':validate(sys.argv[1],sys.argv[2])
