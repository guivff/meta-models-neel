"""Input-only QA for the obscure-bridge bank, never reads filter/model outputs."""
import collections,hashlib,json,sys,tarfile
from pathlib import Path
from build_dev2 import HERE,PARENT,frequencies,render
from source110 import read,sha,require,load_rows
from amendment110 import bind_quarter,quarter_ids

def verify():
 m=read(HERE/'MANIFEST.json');out=Path(m['cache_directory']);rows=load_rows(Path(m['source_csv']));freq=frequencies(rows);source={x['uid']:x for x in rows}
 for n,h in m['cache_files'].items():require(sha(out/n)==h,'Frozen bank bytes')
 items=read(out/'ITEMS.PRIVATE.json');jobs=read(out/'PUBLIC_FILTER_INPUTS.json');byjob={x['id']:x for x in jobs};templates=read(HERE/'PARAPHRASE_TEMPLATES.json')['types']
 require(len(items)==len({x['id'] for x in items})==3000 and len({x['composition_type'] for x in items})==52,'3000 triples / all52 types')
 require(len(byjob)==len(jobs),'Global unique filter job grid')
 for x in items:
  old=source[x['source_uid']];n=freq[x['e2_qid']]
  require(n==x['bridge_record_frequency_any_position'] and 1<=n<10,'Strict global any-role rarity')
  require(x['e2_qid']==old['e2.wikidata_qid'] and x['e3_qid']==old['e3.wikidata_qid'],'Unchanged factual bridge/final truth')
  native,two=render(old);expected=[native]+[t.format(e1=old['e1.value']) for t in templates[x['composition_type']]['paraphrases']]+[two]
  for ident,text in zip(x['onehop_job_ids']+[x['twohop_job_id']],expected):
   j=byjob[ident];require(j['prompt']==text and j['read_position']==len(j['input_ids'])-1 and set(j)=={'id','prompt','input_ids','read_position'},'Exact template prefix/final read/no CPU targets')
  require(x['twohop_tokens']==len(byjob[x['twohop_job_id']]['input_ids']),'Native two-hop read length')
 quarters=quarter_ids(items);qjobs=0
 for s in m['shards']:
  d=Path(s['directory'])
  for n,h in s['files'].items():require(sha(d/n)==h,'Quarter input bytes')
  cw=read(d/'CROSSWALK.PRIVATE.json');public=read(d/'PUBLIC_FILTER_INPUTS.json');bind_quarter(items,jobs,quarters[s['shard']],cw,public,s['shard'])
  require(len(cw['quarter_items'])==750,'Every planned quarter750')
  with tarfile.open(d/'PUBLIC_FILTER_INPUTS.tar.gz') as t:
   require(t.getnames()==['PUBLIC_FILTER_INPUTS.json'],'Only public prefixes on pod');b=t.extractfile('PUBLIC_FILTER_INPUTS.json').read();require(hashlib.sha256(b).hexdigest()==sha(d/'PUBLIC_FILTER_INPUTS.json'),'Exact archive')
   require(not any(x in b.lower() for x in [b'hf_',b'sk-',b'openrouter',b'hf_token',b'api_key',b'bearer']),'Literal credential markers absent')
  qjobs+=len(public)
 return dict(status='PASS',candidates=3000,relation_types=52,unique_bridges=len({x['e2_qid'] for x in items}),frequency_min=min(x['bridge_record_frequency_any_position'] for x in items),frequency_max=max(x['bridge_record_frequency_any_position'] for x in items),global_jobs=len(jobs),quarter_jobs=qjobs,quarters=4,candidates_per_quarter=750,public_fields=['id','prompt','input_ids','read_position'],old_outcomes_opened=False,new_model_calls=0)
if __name__=='__main__':print(json.dumps(verify(),indent=2))
