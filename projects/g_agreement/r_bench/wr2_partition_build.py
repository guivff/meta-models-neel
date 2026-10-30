"""BRIEF_R §19: build metadata-only optimistic/strengthened partition MILPs.
No state array payload, reader prediction, model weight or performance is read.
"""
from __future__ import annotations
import argparse, ast, collections, csv, hashlib, json, re, subprocess, time, unicodedata
from pathlib import Path
from wr2_partition_aliases import build_alias_metadata, norm_alias

REG='7ca927957c43ef4eba416b5f4cf915701322f72e'
ROWS_SHA='02ea8e6050d769da4f09453be937b82cf758b3680400cb59b7a33631c72926e8'
DEFECTS={'139_news_class_Politics','140_news_class_Technology','141_news_class_Entertainment','97_news_class','145_disease_class_digestive system diseases','146_disease_class_cardiovascular diseases','101_disease_class'}
INVALID={'rb_context_against_belief','x25_wsb_wrong_bridge'}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def digest(x):return hashlib.sha256(json.dumps(x,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
def oldkey(s):
 s=' '.join(unicodedata.normalize('NFKD',str(s)).casefold().split())
 s=''.join(c for c in s if not unicodedata.combining(c))
 return s[4:] if s.startswith('the ') else s
def oldtpl(s):
 s=s.replace('x01_ao_personaqa_base:','PersonaQA:').replace('x02_ao_personaqa_fantasy:','PersonaQA:')
 for base in ('rb_khop_landmark_capital','rb_khop_landmark_currency','rb_khop_capital_language'):
  s=s.replace(base+'_bridge:',base+':').replace(base+'_answer:',base+':')
 return s
class DSU:
 def __init__(self):self.p={}
 def find(self,x):
  self.p.setdefault(x,x)
  if self.p[x]!=x:self.p[x]=self.find(self.p[x])
  return self.p[x]
 def join(self,a,b):
  a,b=self.find(a),self.find(b)
  if a!=b:self.p[max(a,b)]=min(a,b)
def constants(path,names):
 out={}
 for node in ast.parse(path.read_text()).body:
  name=node.target.id if isinstance(node,ast.AnnAssign) and isinstance(node.target,ast.Name) else node.targets[0].id if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) else None
  if name in names:out[name]=ast.literal_eval(node.value)
 assert set(out)==set(names),(path,names,set(out))
 return out
def strings(x):
 if isinstance(x,str):yield x
 elif isinstance(x,dict):
  for v in x.values():yield from strings(v)
 elif isinstance(x,(list,tuple)):
  for v in x:yield from strings(v)
def wholetext(x):
 # Do not strip an initial article from context text; alias phrases may omit it.
 s=unicodedata.normalize('NFKD',x).casefold()
 s=''.join(c for c in s if not unicodedata.combining(c))
 return ' '.join(''.join(c if c.isalnum() else ' ' for c in s).split())
def capture(item):return {'messages':item.get('capture_messages'),'system':item.get('system'),'prompt_text':item['prompt_text']}
def baserow(r,alias,template):
 return dict(item_id=r['item_id'],dataset=r['dataset'],capture=r['prompt_hash'],alias=alias,template=template,block=r['regroup_key']+'::prefix_'+r['target_first_token'],source=r['source_family'],prefix=r['target_first_token'],suffix=json.dumps(json.loads(r['target_tokens'])[1:]),answer=r['answer'],parent=r['parent_id'],state_row=int(r['state_row']),original_split=r['split'])
def filter_blocks(rows):
 blocks=collections.defaultdict(list)
 for r in rows:blocks[r['block']].append(r)
 valid={k for k,rs in blocks.items() if len({r['alias'] for r in rs})>=2 and len({r['suffix'] for r in rs})>=2}
 return [r for r in rows if r['block'] in valid]
def component_close(rows):
 d=DSU(); resources={}
 for r in rows:
  b=r['block'];d.find(b)
  keys=[('alias',r['alias']),('capture',r['capture'])]
  if r['parent']:keys.append(('parent',r['source'],r['parent']))
  for key in keys:
   if key in resources:d.join(b,resources[key])
   else:resources[key]=b
 for r in rows:r['component']=d.find(r['block'])
 return {k:d.find(k) for k in sorted(d.p)}
def summary(problem):
 ts,ps=problem['test'],problem['pool']
 return dict(test_rows=len(ts),test_captures=len({r['capture'] for r in ts}),pool_rows=len(ps),pool_captures=len({r['capture'] for r in ps}),target_identities=len({r['alias'] for r in ts}),prefixes=len({r['prefix'] for r in ts}),blocks=len({r['block'] for r in ts}),independent_components=len({r['component'] for r in ts}),sources=sorted({r['source'] for r in ts}),test_templates=len({r['template'] for r in ts}),pool_templates=len({r['template'] for r in ps}))
def main():
 wall,cpu=time.monotonic(),time.process_time()
 ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--out-dir',type=Path,required=True);ap.add_argument('--alias-audit',type=Path);a=ap.parse_args();root=a.repo.resolve();out=a.out_dir
 subprocess.run(['git','merge-base','--is-ancestor',REG,'refs/remotes/origin/r/i2-wr2'],cwd=root,check=True)
 ip=root/'results/g_agreement/r/i2/wr2_stage_workspace_inventory.json';inventory=json.loads(ip.read_text())
 rp=root/'cache/g_agreement/r/i2/wr2_stage_inventory/wr2_stage_workspace_inventory_rows.csv';assert sha(rp)==ROWS_SHA
 rows=list(csv.DictReader(rp.open()));byid={r['item_id']:r for r in rows};assert len(byid)==len(rows)
 items={};sources={str(rp):sha(rp),str(ip):sha(ip)}
 for bank in inventory['banks']:
  p=Path(bank['path']);assert sha(p)==bank['sha256'];sources[str(p)]=sha(p)
  for it in json.loads(p.read_text())['items']:
   if it['item_id'] in byid:items[it['item_id']]=it
 assert len(items)==len(rows)
 # Index/hash checks and file sizes only. No array open, mmap, or model import.
 for ds,s in inventory['states'].items():
  idxp=Path(s['index_path']);hp=Path(s['state_path'])
  assert idxp.exists() and hp.exists() and sha(idxp)==s['index_sha256'],ds
  assert hp.stat().st_size==s['header']['file_bytes'],ds
  idx=json.loads(idxp.read_text())
  for r in rows:
   if r['dataset']==ds:
    pos=int(r['state_row']);it=items[r['item_id']]
    assert idx['item_ids'][pos]==r['item_id']
    assert idx['labels'][pos]==int(r['label'])==it['label']
    assert idx['splits'][pos]==r['split']==it['split']
    assert digest(capture(it))==r['prompt_hash']
    assert it['primary']['answer']==r['answer']
 selected=[r for r in rows if r['identity_task_candidate']=='True' and r['two_to_four_tokens']=='True' and r['state_available']=='True' and r['template_known']=='True' and r['dataset'] not in DEFECTS]
 out.mkdir(parents=True,exist_ok=True)
 # First problem is explicitly optimistic, with previous §18 string/template rules.
 ts=filter_blocks([baserow(r,oldkey(r['target_alias_id']),oldtpl(r['template_id'])) for r in selected if r['split']=='test' and r['regroup_key']])
 triggers=collections.defaultdict(set)
 for r in ts:
  r['component']=r['block']
  for s in json.loads(byid[r['item_id']]['target_aliases'])+[r['alias']]:triggers[oldkey(s)].add(r['alias'])
 ps=[]
 for r in selected:
  if r['split']!='pool':continue
  aliases=set()
  for v in json.loads(r['candidates'])+json.loads(r['target_aliases'])+[r['target_alias_id']]:aliases.update(triggers.get(oldkey(v),set()))
  ps.append(dict(item_id=r['item_id'],dataset=r['dataset'],capture=r['prompt_hash'],aliases=sorted(aliases),template=oldtpl(r['template_id']),source=r['source_family'],state_row=int(r['state_row']),answer=r['answer'],original_split=r['split']))
 optimistic=dict(mode='optimistic_previous_observed_exclusions',registration_commit=REG,test=ts,pool=ps,alias_completeness_established=False,interpretation='Upper-bound relaxation; not a sufficient training partition.')
 dump(out/'optimistic_input.json',optimistic)
 # Strengthened, explicitly conservative aliases and full capture exclusions.
 am=build_alias_metadata(root,inventory,rows,items)
 if a.alias_audit:
  from wr2_alias_overlay import apply_overlay
  audit_path=a.alias_audit.resolve();relative=audit_path.relative_to(root).as_posix()
  # A local draft cannot authorize a data-dependent rerun.
  pushed=subprocess.check_output(['git','show','refs/remotes/origin/r/i2-wr2:'+relative],cwd=root)
  assert pushed==audit_path.read_bytes(),'Alias table must be committed and pushed before coverage'
  subprocess.run(['git','merge-base','--is-ancestor','ee07607','refs/remotes/origin/r/i2-wr2'],cwd=root,check=True)
  table=json.loads(pushed)
  old_input=root/'cache/g_agreement/r/i2/wr2_partition/strengthened_input.json'
  assert sha(old_input)==table['original_input_sha256']
  assert {r['original_identity'] for r in table['records']}=={r['alias'] for r in json.loads(old_input.read_text())['test']}
  am=apply_overlay(am,table);sources[str(audit_path)]=sha(audit_path)
  sources[str(Path(__file__).with_name('wr2_alias_overlay.py'))]=sha(Path(__file__).with_name('wr2_alias_overlay.py'))
 dump(out/'alias_metadata.json',am)
 canonical=am['canonical_to_identity'];exclusions=am['identity_to_exclusion_phrases']
 def identity(s):return canonical[norm_alias(s)]
 tds=DSU();tplkeys={};frames={}
 rbfile=root/'projects/g_agreement/r_bench/readerbench/khop.py';refile=root/'projects/g_agreement/r_bench/beyond_text.py'
 rb=constants(rbfile,['CAPITAL_TEMPLATES','CURRENCY_TEMPLATES','LANGUAGE_TEMPLATES','THREE_HOP_TEMPLATES'])
 redefs=constants(refile,['KHOP2_TEMPLATES','KHOP3_TEMPLATES']);red={t['id']:t['text'] for values in redefs.values() for t in values}
 sources.update({str(rbfile):sha(rbfile),str(refile):sha(refile)})
 framevar={'rb_khop_landmark_capital':'CAPITAL_TEMPLATES','rb_khop_landmark_currency':'CURRENCY_TEMPLATES','rb_khop_capital_language':'LANGUAGE_TEMPLATES','rb_khop_3hop_middle':'THREE_HOP_TEMPLATES'}
 for r in selected:
  k=oldtpl(r['template_id']);tds.find(k);frame=None;ds=r['dataset']
  if ds.startswith(('x01_','x02_')):tds.join(k,'PersonaQA:shared_card_and_attribute_question_frame')
  elif ds.startswith('re_khop'):frame=red[items[r['item_id']]['construction']['template']]
  elif ds.startswith('rb_khop'):
   base=ds.removesuffix('_bridge').removesuffix('_answer')
   frame=rb[framevar[base]][int(items[r['item_id']]['construction']['template'])]
  if frame:
   frame=' '.join(re.sub(r'\{[^}]+\}','{slot}',frame).casefold().split())
   if frame in frames:tds.join(k,frames[frame])
   else:frames[frame]=k
  tplkeys[r['item_id']]=k
 strictselected=[r for r in selected if r['dataset'] not in INVALID]
 strict_all=[baserow(r,identity(r['answer']),tds.find(tplkeys[r['item_id']])) for r in strictselected if r['split']=='test' and r['regroup_key']]
 components=component_close(strict_all)
 strict_ts=filter_blocks(strict_all)
 if a.alias_audit:strict_ts=[r for r in strict_ts if am['identity_completeness'][r['alias']]]
 strict_ts=filter_blocks(strict_ts)
 held_identities={r['alias'] for r in strict_ts}
 # Reverse complete-phrase index; every identity conflict remains independently recorded.
 phrases=collections.defaultdict(set)
 for entity in sorted(held_identities):
  for s in exclusions[entity]:
   phrase=wholetext(s)
   if phrase:phrases[phrase].add(entity)
 first_index=collections.defaultdict(list)
 for phrase,entities in sorted(phrases.items()):first_index[phrase.split()[0]].append((phrase.split(),entities,phrase))
 strict_ps=[];hits=[]
 for r in strictselected:
  if r['split']!='pool':continue
  item=items[r['item_id']];texts=[]
  # Structured candidate/target/alias plus all source metadata values, not field keys.
  texts.extend(json.loads(r['candidates'])+json.loads(r['target_aliases'])+[r['answer'],r['target_alias_id']])
  texts.extend(strings(capture(item)))
  texts.extend(strings(item.get('construction',{})));texts.extend(strings(item.get('extra',{})))
  texts.extend(strings(item.get('raw_target')))
  texts.extend(strings(item))  # All frozen item metadata values, never field keys.
  texts.extend(strings(am.get('extra_raw_text',{}).get(r['item_id'],[])))
  conflicts=set();matched=set()
  # Preserve the old explicit component exclusion even if text normalization differs.
  for v in json.loads(r['candidates'])+json.loads(r['target_aliases'])+[r['answer'],r['target_alias_id']]:
   entity=canonical.get(norm_alias(v))
   if entity in held_identities:conflicts.add(entity)
  for text in texts:
   tokens=wholetext(text).split()
   for i,word in enumerate(tokens):
    for phrase,entities,ptext in first_index.get(word,[]):
     if tokens[i:i+len(phrase)]==phrase:
      conflicts.update(entities);matched.add(ptext)
  strict_ps.append(dict(item_id=r['item_id'],dataset=r['dataset'],capture=r['prompt_hash'],aliases=sorted(conflicts),template=tds.find(tplkeys[r['item_id']]),source=r['source_family'],state_row=int(r['state_row']),answer=r['answer'],original_split=r['split']))
  if conflicts:hits.append(dict(item_id=r['item_id'],conflicting_test_identities=sorted(conflicts),matching_exclusion_phrases=sorted(matched)))
 strengthened=dict(mode='strengthened_full_capture_global_alias_template_closure',registration_commit=REG,test=strict_ts,pool=strict_ps,alias_completeness_established=False,interpretation='Numerical candidate only until finite-corpus alias adjudication; no training.')
 if a.alias_audit:
  strengthened.update(alias_registration_commit='ee07607',mode='finite_corpus_adjudicated_full_capture_holdouts',finite_corpus_alias_audit_complete=all(am['identity_completeness'][r['alias']] for r in strict_ts),alias_table_sha256=sha(a.alias_audit),interpretation='Finite-corpus adjudicated metadata coverage; no training.')
 dump(out/'strengthened_input.json',strengthened);dump(out/'pool_exclusion_matches.json',hits)
 dump(out/'template_components.json',{k:tds.find(k) for k in sorted(tds.p)});dump(out/'challenge_components.json',components)
 manifest=dict(registration_commit=REG,script_sha256=sha(__file__),alias_helper_sha256=sha(Path(__file__).with_name('wr2_partition_aliases.py')),input_hashes=sources,alias_source_hashes=am.get('sources',[]),status='complete',optimistic=summary(optimistic),strengthened=summary(strengthened),excluded_provisional_label_datasets=sorted(INVALID),semantic_alias_completeness_established=False,fit_count=0,gpu_hours=0,state_array_payload_bytes_read=0,cpu_seconds=time.process_time()-cpu,wall_seconds=time.monotonic()-wall)
 if a.alias_audit:manifest['alias_registration_commit']='ee07607'
 manifest['output_hashes']={p.name:sha(p) for p in sorted(out.glob('*.json'))}
 dump(out/'build.json',manifest);print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
