"""Freeze only available E84 file state, with exact full-tail and issue-split proof."""
import collections,hashlib,json,tarfile
from pathlib import Path
from scan84 import HERE,SEED,split_for
GENERIC='Describe what is going on in this text and what comes next.'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')
def select(records):
 by={}
 for r in records:
  if r['id'] in by:
   assert by[r['id']]['prompt']==r['prompt'] and by[r['id']]['label']==r['label'],'source identity collision'
  else:by[r['id']]=r
 selected=[];used=set();counts={}
 for split,n in [('dev',50),('test',100)]:
  for index in (0,1):
   pool=sorted((r for r in by.values() if r['split']==split and r['label']==index),key=lambda r:r['rank'])
   chosen=[]
   for r in pool:
    if r['instance_id'] in used:continue
    assert split_for(r['instance_id'])==split
    chosen.append(r);used.add(r['instance_id'])
    if len(chosen)==n:break
   counts[split+'/'+str(index)]=dict(available=len(pool),chosen=len(chosen),required=n)
   if len(chosen)!=n:return None,counts
   selected.extend(chosen)
 return sorted(selected,key=lambda r:r['id']),counts

def build():
 from transformers import PreTrainedTokenizerFast
 from scan84 import TOK
 records=[]
 paths=sorted((HERE/'cache').glob('validated_shard*_final2.PRIVATE.jsonl'))
 for p in paths:
  with p.open() as f:
   for line in f:
    r=json.loads(line);meta={k:r[k] for k in ['id','label','split','instance_id','rank']};meta['prompt']=hashlib.sha256(r['prompt'].encode()).hexdigest();records.append(meta)
 chosen,counts=select(records)
 print(json.dumps(counts,indent=2),flush=True)
 if chosen is None:raise SystemExit('Not enough balanced unique issues; bank not frozen')
 ids_needed={r['id'] for r in chosen};full={}
 for path in paths:
  with path.open() as f:
   for line in f:
    r=json.loads(line)
    if r['id'] in ids_needed:full[r['id']]=r
 chosen=[full[r['id']] for r in chosen]
 out=HERE/'cache/revived_bank_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False)
 public=[];private=[];baselines=[];tok=PreTrainedTokenizerFast(tokenizer_file=str(TOK/'tokenizer.json'))
 for r in chosen:
  assert r['full_exact_tail_checked'] and r['hidden_distance_tokens']>=512
  index=r['label'];target=r['files'][index]
  assert len(r['files'])==2 and target==r['last_file']
  public.append(dict(id=r['id'],prompt=r['prompt'],input_ids=r['input_ids'],read_position=r['read_position'],split=r['split'],reader_allowed=r['split']=='test'))
  private.append(dict(id=r['id'],feature='file_being_edited',split=r['split'],label=1-index,value='A' if index==0 else 'B',value_name='first_file' if index==0 else 'second_file',file_index=index,files=r['files'],target_path=target,source_issue=r['instance_id'],source_repo=r['repo'],source_license=r['source_license'],trajectory_id=r['trajectory_id'],source_shard=r['source_shard'],source_row=r['row_in_shard'],next_assistant_index=r['next_assistant_index'],source_edit_indices=r['edit_proof'],latest_edit_header_end_token=r['latest_edit_header_end_token'],hidden_distance_tokens=r['hidden_distance_tokens'],tail512_sha256=r['tail512_sha256'],tokens=len(r['input_ids'])))
  if r['split']=='test':
   text=r['prompt']+'\n'+GENERIC;ids=tok.encode(text,add_special_tokens=False)
   baselines.append(dict(id=r['id'],prompt=text,input_ids=ids,read_position=len(ids)-1))
 assert len(public)==300 and len(baselines)==200 and len({x['source_issue'] for x in private})==300
 assert {x['source_issue'] for x in private if x['split']=='dev'}.isdisjoint(x['source_issue'] for x in private if x['split']=='test')
 write(out/'PUBLIC_INPUTS.json',public);write(out/'PUBLIC_BASELINE_INPUTS.json',baselines);write(out/'LABELS.PRIVATE.json',private)
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz') as t:
  for n in ['PUBLIC_INPUTS.json','PUBLIC_BASELINE_INPUTS.json']:t.add(out/n,arcname=n)
  t.add(HERE/'ATTRIBUTION_SWE_ZERO.md',arcname='ATTRIBUTION_SWE_ZERO.md')
 scanpaths=sorted((HERE/'cache').glob('scan_shard*_final2.PRIVATE.json'));summary=[]
 for p in scanpaths:
  s=json.loads(p.read_text());summary.append(dict(shard=Path(s['shard']).name,trajectories=s['rows'],counters=s['counters'],scan_sha256=sha(p)))
 lengths=collections.defaultdict(list)
 for x in private:lengths[x['split']+'/'+x['value_name']].append(x['tokens'])
 report=dict(experiment='E84',status='AVAILABLE_FILE_ROW_FROZEN_TWO_TEST_ROWS_NOT_BUILT',states={'file_being_edited':dict(status='FROZEN_PROBE_PENDING',test=200,dev=100),'last_test_passed':dict(status='NOT_BUILT_SOURCE_HAS_NO_UNAMBIGUOUS_TEST_RUNS',test=0,dev=0),'failed_attempts':dict(status='NOT_BUILT_SOURCE_HAS_NO_UNAMBIGUOUS_TEST_RUNS',test=0,dev=0)},seed=SEED,selection_counts=counts,unique_source_issues=300,split_rule='SHA256(UTF8(E84|20261029|instance_id)) first16hex as integer modulo3:0 dev,1/2 test; whole issue including all trajectories assigned together',class_mapping={'A':{'file_index':0,'probe_label':1,'meaning':'first distinct successfully edited file, when most recently edited'},'B':{'file_index':1,'probe_label':0,'meaning':'second distinct successfully edited file, when most recently edited'}},within_split_balance={'dev':{'A':50,'B':50},'test':{'A':100,'B':100}},source_scans=summary,validated_pools={str(p):sha(p) for p in paths},lengths={k:dict(min=min(v),max=max(v),mean=sum(v)/len(v)) for k,v in lengths.items()},minimum_hidden_distance_tokens=min(x['hidden_distance_tokens'] for x in private),max_input_tokens=max(x['tokens'] for x in private),original_transcript_messages_cropped=False,raw_tool_arguments_transformation='JSON string decoded to equivalent object for native Qwen template, never executed',first_output_utc='unknown',first_output_reason='CPU input-bank construction only; no model/probe/reader/judge output',private_cache=str(out.resolve()),files={p.name:sha(p) for p in out.iterdir() if p.is_file()})
 write(HERE/'REVIVED_MANIFEST.json',report)
 print('Frozen300 file items,200 test/100dev; unique source issues; native rows unscored.',flush=True)
if __name__=='__main__':build()
