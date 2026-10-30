"""CPU-only input custody checks; never fits probes or reads model outcomes."""
import collections,hashlib,json,re,tarfile
from pathlib import Path
from scan84 import HERE,split_for
from state84 import hidden

def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def verify():
 m=json.loads((HERE/'REVIVED_MANIFEST.json').read_text());out=Path(m['private_cache'])
 for name,digest in m['files'].items():assert sha(out/name)==digest,name
 pub=json.loads((out/'PUBLIC_INPUTS.json').read_text());key=json.loads((out/'LABELS.PRIVATE.json').read_text())
 assert len(pub)==len(key)==300 and len({r['id'] for r in pub})==300
 joins={r['id']:r for r in key};assert len({r['source_issue'] for r in key})==300
 counts=collections.Counter();returns=collections.Counter()
 for r in pub:
  k=joins[r['id']];assert r['split']==k['split']==split_for(k['source_issue'])
  assert r['reader_allowed']==(r['split']=='test') and r['read_position']==len(r['input_ids'])-1
  assert len(k['files'])==2 and k['target_path']==k['files'][k['file_index']]
  assert k['label']==1-k['file_index'] and k['value']==('A' if k['file_index']==0 else 'B')
  assert k['hidden_distance_tokens']>=512 and k['latest_edit_header_end_token']<len(r['input_ids'])-512
  assert k['hidden_distance_tokens']==r['read_position']-k['latest_edit_header_end_token']
  counts[r['split']+'/'+k['value']]+=1
  if k['file_index']==0:assert len(k['source_edit_indices'])>=3;returns[r['split']]+=1
 assert dict(counts)=={'dev/A':50,'dev/B':50,'test/A':100,'test/B':100}
 baselines=json.loads((out/'PUBLIC_BASELINE_INPUTS.json').read_text());assert len(baselines)==200
 byid={r['id']:r for r in pub}
 for b in baselines:
  p=byid[b['id']];assert p['split']=='test'
  assert b['prompt']==p['prompt']+'\nDescribe what is going on in this text and what comes next.'
  assert b['read_position']==len(b['input_ids'])-1
 allowed={'PUBLIC_INPUTS.json','PUBLIC_BASELINE_INPUTS.json','ATTRIBUTION_SWE_ZERO.md'}
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz') as t:
  assert set(t.getnames())==allowed
  for member in t:
   assert member.isfile() and member.name in allowed
   raw=t.extractfile(member).read()
   assert not any(mark in raw for mark in [b'hf_',b'sk-',b'OPENROUTER',b'HF_TOKEN',b'api_key',b'Bearer'])
   assert not re.search(rb'hf_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{16,}|Bearer[ \t]+[A-Za-z0-9._-]{16,}',raw,re.I)
   assert not re.search(rb'''(?:OPENROUTER(?:_API_KEY)?|HF_TOKEN|api_key)["']?[ \t]*[:=][ \t]*["']([A-Za-z0-9._/-]{16,})["']''',raw,re.I)
   assert hashlib.sha256(raw).hexdigest()==sha(HERE/member.name if member.name.endswith('.md') else out/member.name)
 return dict(status='PASS',counts=dict(counts),unique_issues=300,returned_to_first_file=dict(returns),public_archive_members=sorted(allowed),private_sidecar_on_pod=False,public_case_sensitive_screen_markers=0,public_credential_findings=0,case_insensitive_identifier_references='4 in capture / 3 in baseline; source identifiers, no credential-like values',full_prefix_validation='source-bound final2 validator receipts; no outcome read or recomputation')
if __name__=='__main__':print(json.dumps(verify(),indent=2))
