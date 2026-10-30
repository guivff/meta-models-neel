"""Trace frozen candidate UTF-8 bytes to pinned PUBLIC dataset argument cells.

Data reading only: no transcript command/code, model, scoring, or paid call runs.
"""
import collections,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def digest(x):return hashlib.sha256(x.encode()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,ensure_ascii=False);f.write('\n')
def require(ok,msg):
 if not ok:raise ValueError(msg)
def path_cells(messages,stop):
 cells=collections.defaultdict(list)
 for i,m in enumerate(messages[:stop]):
  if m.get('role')!='assistant':continue
  for j,c in enumerate(m.get('tool_calls') or []):
   f=c.get('function') or {}
   if f.get('name')!='str_replace_editor':continue
   raw=f.get('arguments')
   try:a=json.loads(raw) if isinstance(raw,str) else raw
   except (TypeError,ValueError):continue
   if not isinstance(a,dict) or not isinstance(a.get('path'),str):continue
   encoded=raw if isinstance(raw,str) else json.dumps(raw,sort_keys=True,ensure_ascii=False,separators=(',',':'))
   path=a['path']
   cells[path].append(dict(message_index=i,tool_call_index=j,function_name='str_replace_editor',argument_key='path',argument_representation='source_JSON_string' if isinstance(raw,str) else 'source_mapping_canonical_JSON',argument_sha256=digest(encoded),decoded_path_utf8_sha256=digest(path)))
 return cells

def prove():
 import pyarrow as pa
 import pyarrow.parquet as pq
 original=read(HERE/'REVIVED_MANIFEST.json');keypath=Path(original['private_cache'])/'LABELS.PRIVATE.json';require(sha(keypath)==original['files']['LABELS.PRIVATE.json'],'Frozen original key')
 key=[x for x in read(keypath) if x['split']=='test'];require(len(key)==200,'Exact test200')
 provenance=read(HERE/'SWE_ZERO_SOURCE_PROVENANCE.json');source=Path(provenance['source_cache']);grouped=collections.defaultdict(list)
 for x in key:grouped[x['source_shard']].append(x)
 evidence=[];missing=[];source_files=[]
 for name,items in sorted(grouped.items()):
  file=source/name;expected=provenance['files'][name];require(sha(file)==expected,'Exact anonymous-source parquet bytes')
  indexes=sorted({x['source_row'] for x in items});table=pq.read_table(file,columns=['instance_id','trajectory_id','trajectory']).take(pa.array(indexes,type=pa.int64()))
  rows=dict(zip(indexes,table.to_pylist()));del table
  source_files.append(dict(filename=name,sha256=expected,public_url=f"https://huggingface.co/datasets/{provenance['source_repo']}/resolve/{provenance['source_revision']}/data/{name}",selected_test_rows=len(indexes)))
  for x in items:
   row=rows[x['source_row']];require(row['instance_id']==x['source_issue'] and row['trajectory_id']==x['trajectory_id'],'Exact original issue/trajectory source row')
   cells=path_cells(row['trajectory'],x['next_assistant_index'])
   for slot,path in enumerate(x['files']):
    refs=cells.get(path,[])
    if not refs:missing.append(dict(unit_sha256=digest(x['id']),candidate_sha256=digest(path)))
    else:evidence.append(dict(id=x['id'],candidate_slot=slot,candidate_sha256=digest(path),source_shard=name,source_parquet_sha256=expected,source_row=x['source_row'],source_issue=x['source_issue'],trajectory_id=x['trajectory_id'],next_assistant_index=x['next_assistant_index'],source_cell=refs[0],byte_identity='exact decoded source path UTF-8; no normalization, aliasing or rewriting applied in this proof'))
  del rows
  print(json.dumps(dict(shard=name,verified_candidate_values=len(evidence),missing_values=len(missing))),flush=True)
 out=HERE/'cache/public_path_provenance_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False);write(out/'EVIDENCE.PRIVATE.json',evidence)
 summary=dict(experiment='E84',status='ALL_CANDIDATE_BYTES_PUBLIC_SOURCE_VERIFIED' if not missing else 'SOME_CANDIDATE_BYTES_NOT_VERIFIED',source_repo=provenance['source_repo'],source_revision=provenance['source_revision'],license_as_recorded=provenance['license_as_stated_on_card'],original_anonymous_receipts_reference='SWE_ZERO_SOURCE_PROVENANCE.json',original_provenance_sha256=sha(HERE/'SWE_ZERO_SOURCE_PROVENANCE.json'),source_files=source_files,source_test_items=200,candidate_values=400,verified_values=len(evidence),unverified_values=len(missing),unverified_hashes=missing,unique_verified_candidate_sha256=sorted({x['candidate_sha256'] for x in evidence}),byte_identity_definition='Frozen candidate UTF-8 exactly equals JSON-decoded path string in an original str_replace_editor argument cell before read position. Serialized JSON escaping is decoded as data, not rewritten.',no_normalization_or_aliasing=True,raw_model_readouts_opened=False,dataset_commands_or_scripts_executed=False,private_evidence=dict(path=str(out/'EVIDENCE.PRIVATE.json'),sha256=sha(out/'EVIDENCE.PRIVATE.json'),content='Original source row/message/tool-call argument-cell pointers and hashes; keep CPU-only'),privacy_guard_changed=False,guard_exception_applied=False,paid_dispatch_approved_by_this_receipt=False,coordinator_disposition='PUBLIC ORIGIN verified only; existing syntactic path-guard HOLD remains until C/coordinator original-path disposition; no E107 exemption generalized',paid_calls=0)
 write(HERE/'PUBLIC_CANDIDATE_PATH_PROVENANCE.json',summary)
 print(json.dumps({k:summary[k] for k in ['status','candidate_values','verified_values','unverified_values']}))
if __name__=='__main__':prove()
