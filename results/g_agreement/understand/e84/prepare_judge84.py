"""Materialize original E84 test candidate paths; no readouts, calls or path rewriting."""
import hashlib,json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
# Immutable E10 guard patterns, decoded value view. No new exception or redaction.
PATTERNS=[r'\b(?:hf_|sk-or-v1-|sk-proj-)[A-Za-z0-9_-]{16,}',r'/(?:Users|home|workspace|private|var|tmp|etc)/',r'(?<![A-Za-z])[A-Za-z]:\\[A-Za-z0-9_.-]+',r'\b(?:projects|results|cache)/[A-Za-z0-9_.-]+/',r'\b(?:\d{1,3}\.){3}\d{1,3}:\d+']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def require(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True);f.write('\n')
def packetize(key):
 public=[];private=[];seen=set()
 for x in key:
  if x['split']!='test':continue
  require(x['id'] not in seen,'Unique original item ID');seen.add(x['id'])
  require(len(x['files'])==2 and len(set(x['files']))==2,'Two distinct exact source paths')
  require(x['value'] in ('A','B') and x['file_index']==('A','B').index(x['value']) and x['label']==int(x['value']=='A'),'Original class binding')
  require(x['target_path']==x['files'][x['file_index']],'Most-recent file original target')
  public.append(dict(id=x['id'],property='file_being_edited',values={'A':x['files'][0],'B':x['files'][1]}))
  private.append(dict(id=x['id'],source_id=x['id'],gold=x['value'],correct_path=x['target_path'],original_file_index=x['file_index'],split='test'))
 return public,private

def candidate_privacy(packet):
 failures=[];counts={str(i):0 for i in range(len(PATTERNS))}
 for r in packet:
  for v in r['values'].values():
   matches=[i for i,p in enumerate(PATTERNS) if re.search(p,v)]
   for i in matches:counts[str(i)]+=1
   if matches:failures.append(dict(unit_sha256=digest(r['id']),candidate_sha256=digest(v),guard_pattern_indices=matches))
 return dict(status='HOLD_CANDIDATE_PRIVACY' if failures else 'CANDIDATE_ONLY_PASS_FULL_WIRE_PENDING',units=len(packet),candidate_values=2*len(packet),failed_candidate_values=len(failures),pattern_match_counts=counts,failures=failures,contains_actual_path_values=False,paths_rewritten=False,exceptions_applied=False,paid_calls=0)

def prepare():
 m=read(HERE/'REVIVED_MANIFEST.json');source=Path(m['private_cache'])/'LABELS.PRIVATE.json'
 require(sha(source)==m['files']['LABELS.PRIVATE.json'],'Original frozen CPU key')
 public,private=packetize(read(source));require(len(public)==len(private)==200,'Original200 test candidates only')
 release=ROOT/'results/g_agreement/sealed/E84_C3_MEASURED/CPU_GATE_PUBLIC_RELEASE.json'
 r=read(release);require({x['id'] for x in public}==set(r['released_ids']) and r['probe_pass_by_reader']=={'oracle':False,'nla':False},'Only completed generic baseline eligible')
 out=HERE/'cache/judge_candidates_2026-10-29_v1';out.mkdir(parents=True,exist_ok=False)
 write(out/'JUDGE_CANDIDATES.PRIVATE.json',public);write(out/'PRIVATE_CROSSWALK.PRIVATE.json',private)
 diag=candidate_privacy(public);write(HERE/'JUDGE_CANDIDATE_PRIVACY_DIAGNOSTIC.json',diag)
 write(HERE/'JUDGE_PROPERTY_DEFINITION.json',dict(property='file_being_edited',registered_definition='which of two files the agent edited most recently.',source_registration='section198 E84 deviation1 b9e2899b3',source_order='A is first distinct successfully edited file; B is second distinct successfully edited file',candidate_description_rule='two original actual normalized full file paths, verbatim, no aliases/basenames/path stripping',private_target_rule='original most recently edited path and original A/B gold remain CPU-side'))
 return out,diag
if __name__=='__main__':
 out,diag=prepare();print(json.dumps({k:v for k,v in diag.items() if k!='failures'},indent=2))
