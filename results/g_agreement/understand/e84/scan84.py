"""Read-only SWE-Zero candidate scan. No code/command from transcripts is executed."""
import collections,hashlib,json,sys
from pathlib import Path
import pyarrow.parquet as pq
from transformers import PreTrainedTokenizerFast
from state84 import scan,hidden,STATES
HERE=Path(__file__).resolve().parent
SEED=20261029
TOK=Path('/Users/guivff/.cache/huggingface/hub/models--Qwen--Qwen3.6-27B/snapshots/6a9e13bd6fc8f0983b9b99948120bc37f49c13e9')

def split_for(issue):return 'dev' if int(hashlib.sha256(f'E84|{SEED}|{issue}'.encode()).hexdigest()[:16],16)%3==0 else 'test'
def priority(key):return hashlib.sha256(f'E84|{SEED}|{key}'.encode()).hexdigest()
def messages_prefix(messages,n):
 out=[]
 for m in messages[:n]:
  row=dict(role=m['role'],content=m.get('content') or '')
  if m.get('tool_calls'):
   calls=[]
   for call in m['tool_calls']:
    f=call['function'];a=f.get('arguments') or '{}'
    a=json.loads(a) if isinstance(a,str) else a
    if not isinstance(a,dict):raise ValueError('Tool arguments must be object data')
    calls.append(dict(id=call.get('id'),type=call.get('type','function'),function=dict(name=f['name'],arguments=a)))
   row['tool_calls']=calls
  out.append(row)
 return out

def inspect_shard(path,out):
 tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK/'tokenizer.json'));tok.chat_template=(TOK/'chat_template.jinja').read_text()
 counts=collections.Counter();best={};rows=0;first=0
 fields=['instance_id','repo','license','trajectory_id','trajectory']
 for batch in pq.ParquetFile(path).iter_batches(batch_size=25,columns=fields):
  for row in batch.to_pylist():
   rows+=1;issue=row['instance_id'];messages=row['trajectory'];split=split_for(issue)
   if not isinstance(messages,list):counts['invalid_trajectory']+=1;continue
   last_stats={}
   for snap in scan(messages):
    last_stats=snap['stats']
    counts['next_assistant_sites']+=1
    for state in STATES:
     if state not in snap['labels']:counts[state+'/undetermined_or_outside_bins']+=1
    if not snap['labels']:counts['no_determined_state']+=1;continue
    n=snap['next_assistant_index']
    try:rendered=tok.apply_chat_template(messages_prefix(messages,n),tokenize=False,add_generation_prompt=True,enable_thinking=False)
    except Exception:counts['chat_render_error']+=1;continue
    # Suffix-only tokenization is a screening optimization, never the final proof.
    suffix=rendered[-16384:];suffix_ids=tok.encode(suffix,add_special_tokens=False)
    if len(suffix_ids)<513:counts['context_not_beyond512']+=1;continue
    tail=tok.decode(suffix_ids[-512:],skip_special_tokens=False)
    possible=[s for s in snap['labels'] if hidden(s,tail,snap['files'])]
    for s in snap['labels']:
     if s not in possible:counts[s+'/visible_tail']+=1
    if not possible:continue
    for state in possible:
     label=snap['labels'][state];key=(state,label,split,issue)
     candidate_key=f"{issue}|{row['trajectory_id']}|{n}|{state}"
     rank=priority(candidate_key)
     record=dict(state=state,label=label,split=split,instance_id=issue,repo=row['repo'],source_license=row['license'],trajectory_id=row['trajectory_id'],source_shard=Path(path).name,row_in_shard=rows-1,next_assistant_index=n,files=snap['files'],last_file=snap['last_file'],known_failed=snap['known_failed'],unknown_tests=snap['unknown_tests'],last_test_message=snap['last_test_message'],edit_proof=snap['edit_proof'],rank=rank)
     counts[state+'/screened_hidden']+=1
     if key not in best or rank<best[key]['rank']:best[key]=record
   for key,value in last_stats.items():counts['parser/'+key]+=value
   if rows%500==0:print(json.dumps({'rows':rows,'unique_state_issue_candidates':len(best),'counts':{k:v for k,v in counts.items() if k.endswith('/screened_hidden')}}),flush=True)
 output=Path(out);output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps(dict(shard=str(Path(path).resolve()),rows=rows,source_sha256={n:hashlib.sha256((HERE/n).read_bytes()).hexdigest() for n in ['state84.py','scan84.py']},counters=dict(counts),candidates=sorted(best.values(),key=lambda x:x['rank'])),indent=2)+'\n')
 summary=collections.Counter((x['state'],str(x['label']),x['split']) for x in best.values())
 print('COMPLETE',str(output),json.dumps({'/'.join(k):v for k,v in sorted(summary.items())}),flush=True)
if __name__=='__main__':inspect_shard(sys.argv[1],sys.argv[2])
