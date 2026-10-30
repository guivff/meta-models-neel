"""Repeatable CPU input custody check; no reader/probe/judge files or model calls."""
import collections,hashlib,tarfile
from pathlib import Path
from build114 import HERE,ROWS,read,sha,require,number,variants

def verify():
 m=read(HERE/'MANIFEST.json');out=Path(m['cache_directory']);config=read(HERE/'SENTENCES.json')
 for n,h in m['files'].items():require(sha(out/n)==h,'Frozen artifact changed')
 private=read(out/'TARGETS.PRIVATE.json');public=read(out/'PUBLIC_INPUTS.json');by={x['id']:x for x in public}
 require(len(by)==len(public)==len(private)==504,'Complete unique capture grid')
 source=Path(m['source_directory']);old=read(source/'items.PRIVATE.json');sourceby={x['id']:x for x in old};counts=collections.Counter();arms=collections.defaultdict(set)
 for k in private:
  x=sourceby[k['source_id']];other=sourceby[k['source_opposite_id']];p=by[k['id']]
  require(k['source_item']==x and x['split']=='test','Unmodified original test source')
  require(k['label']==x['label'] and k['value']==x['value'],'No control-arm gold flip')
  expected={a:(s,t,n) for a,s,t,n in variants(x,other,config['templates'])};sentence,text,n=expected[k['arm']]
  require(k['sentence']==sentence and k['stated_number']==n and p['prompt']==text,'Exact frozen statement/control frame')
  require(p['id']==hashlib.sha256(('E114|'+x['id']+'|'+k['arm']).encode()).hexdigest()[:24],'Opaque stable item identity')
  require(set(p)=={'id','prompt','input_ids','read_position'},'Pod fields exclude private state/arm/gold/source keys')
  require(p['read_position']==len(p['input_ids'])-1 and p['input_ids'][-1]==x['ids'][-1],'Exact original registered read-token identity')
  arms[x['id']].add(k['arm']);counts[k['feature']+'/'+k['arm']+'/'+str(k['label'])]+=1
 require(len(arms)==252 and all(v==set(config['arms']) for v in arms.values()),'All source items in both arms')
 require(len(counts)==12 and all(x==42 for x in counts.values()),'Balanced84 per row per arm')
 with tarfile.open(out/'PUBLIC_INPUTS.tar.gz') as t:
  require(t.getnames()==['PUBLIC_INPUTS.json'],'Only public capture input sent to pod')
  raw=t.extractfile('PUBLIC_INPUTS.json').read();require(hashlib.sha256(raw).hexdigest()==sha(out/'PUBLIC_INPUTS.json'),'Archive binds exact JSON')
  require(not any(mark in raw.lower() for mark in [b'hf_',b'sk-',b'openrouter',b'hf_token',b'api_key',b'bearer']),'No literal credential markers')
 return dict(status='PASS',original_items=252,capture_items=504,counts=dict(sorted(counts.items())),read_token_identity_all504=True,source_unchanged=True,private_targets_off_pod=True,archive_members=['PUBLIC_INPUTS.json'],public_credential_markers=0)
if __name__=='__main__':
 import json
 print(json.dumps(verify(),indent=2))
