"""§101 CPU-only sealed §84 keyword counts and matched Claude sample exports."""
from pathlib import Path
from collections import Counter
import argparse,time,subprocess,re
from . import io as I,protocol as P
from ...blindspot.w1b import registry_features as S
CORE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement')
BANK=CORE/'blindspot/w1b-bank-v1'
ORACLE=CORE/'understand/e13a-units/jivab2a1xudpkk/e13a-out'
NLA=CORE/'blindspot/w1b-units/ybqkwg5zoc3vwg/w1b-out/nla'
SELECTION=I.ROOT/'results/g_agreement/blindspot/s79/final_n5w4505k68u2hm/TOP10.json'

def source_ref(p):return {'path':str(p),'bytes':p.stat().st_size,'sha256':I.sha(p)}
def verified(base,name,refs):
 p=base/name;v=I.read(p);refs.append(source_ref(p))
 for n,h in v['files'].items():
  if Path(n).is_absolute() or '..' in Path(n).parts or I.sha(base/n)!=h:raise ValueError('source seal changed')
 return v

def rowspecs():
 top=I.read(SELECTION);features=top['candidates'] if isinstance(top,dict) else top
 # The committed selection may store detailed feature records; preserve its exact order.
 features=[x['feature'] if isinstance(x,dict) and 'feature' in x else x['id'] if isinstance(x,dict) else x for x in features]
 return {f:{'question':f'Does this readout explicitly state whether the original target read position satisfies this property: {S.BY_ID[f].definition}? A = {S.BY_ID[f].positive}; B = {S.BY_ID[f].negative}.','values':['present','absent'],'definition':S.BY_ID[f].definition} for f in features}

def freeze():
 specs=rowspecs();I.save(I.OUT/'QUESTIONS_S84.json',specs)
 plan={'section':101,'status':'PREPARATION_FROZEN_BEFORE_S84_SAMPLING','seed':I.SEED,'states':150,'readouts':300,'rows':list(specs),'states_per_row':15,'sampling':'Distinct test items only;7/8 per row/value, five rows with present8 and five with absent8, chosen by seeded row hash. IDs ranked by seeded row/value/item hash. One common nonempty generation0/1 per state chosen by seeded item/sample hash; paired native44/42 readers. No outcome/keyword selection.','w1':'Export exact existing150-state sample; no resampling or code/key join.','input_fields':['id','question','readout'],'private_keys':'cache only; KEY.DO_NOT_SHARE.jsonl; never coder input','api_calls':0,'gpu_h':0,'frozen_files':{str(p.relative_to(I.ROOT)):I.sha(p) for p in [Path(__file__),I.OUT/'S84_SCOPE.md',I.OUT/'QUESTIONS_S84.json',SELECTION,Path(S.__file__),I.ROOT/'projects/g_agreement/understand/e13/protocol.py']}}
 I.save(I.OUT/'PREPARATION_PLAN.json',plan);print('Preparation frozen:',len(specs),'rows')

def verify_plan():
 plan=I.read(I.OUT/'PREPARATION_PLAN.json')
 for n,h in plan['frozen_files'].items():
  if I.sha(I.ROOT/n)!=h:raise ValueError('preparation freeze changed: '+n)
 subprocess.run(['git','cat-file','-e','HEAD:results/g_agreement/understand/e13/S84_SCOPE.md'],cwd=I.ROOT,check=True)
 return plan

def load_s84():
 refs=[];verified(BANK,'INPUT_SEAL.json',refs);input_hash=I.sha(BANK/'INPUT_SEAL.json')
 for base,name in [(ORACLE,'provenance.unasked.target.json'),(NLA,'provenance.unasked.nla.json')]:
  free=verified(base,'FREE_SEAL.json',refs)
  if free['status']!='UNASKED_COMPLETE_BEFORE_LABEL_JOIN':raise ValueError('free phase not complete')
  pv=I.read(base/name);refs.append(source_ref(base/name))
  if pv['input_seal_sha256']!=input_hash:raise ValueError('reader bank lineage mismatch')
 pv=I.read(ORACLE/'provenance.unasked.target.json')
 if pv.get('fresh_full_run') is not True or pv.get('old_partial_outputs_used') is not False:raise ValueError('not fresh sealed E13(a) collection')
 items=I.rows(BANK/'items.input.jsonl');refs.append(source_ref(BANK/'items.input.jsonl'));ids=[x['id'] for x in items];index={i:k for k,i in enumerate(ids)}
 o=I.rows(ORACLE/'unasked.target.jsonl');n=I.rows(NLA/'unasked.nla.jsonl');refs += [source_ref(ORACLE/'unasked.target.jsonl'),source_ref(NLA/'unasked.nla.jsonl')]
 expected={(i,s,r) for i in ids for s in [0,1] for r in ['olens','jlens','logit']};keys=[(x['id'],x['sample'],x['reader']) for x in o]
 if len(ids)!=1680 or len(index)!=1680 or len(o)!=10080 or len(set(keys))!=10080 or set(keys)!=expected:raise ValueError('incomplete E13(a) target grid')
 if any(x['layer']!=44 or x['canonical_index']!=index[x['id']] for x in o):raise ValueError('target native site/order')
 nk=[(x['id'],x['sample']) for x in n]
 if len(n)!=3360 or len(set(nk))!=3360 or set(nk)!={(i,s) for i in ids for s in [0,1]} or any(x['reader']!='nla' or x['layer']!=42 or x['canonical_index']!=index[x['id']] for x in n):raise ValueError('incomplete NLA native grid')
 labels=I.rows(BANK/'labels.DO_NOT_STAGE.jsonl');refs.append(source_ref(BANK/'labels.DO_NOT_STAGE.jsonl'));lookup={x['id']:x for x in labels}
 if set(lookup)!=set(ids):raise ValueError('label coverage')
 return items,lookup,{'oracle':{(r['id'],r['sample']):r for r in o if r['reader']=='olens'},'nla':{(r['id'],r['sample']):r for r in n}},refs

def sample_selection(labels,readers,specs):
 extra=set(sorted(specs,key=lambda f:I.rank('s84-extra-row',f))[:5]);selected=[]
 for feature in specs:
  for value in ['present','absent']:
   count=7+int((feature in extra)==(value=='present'))
   candidates=[r for r in labels.values() if r['feature']==feature and r['split']=='test' and r['value']==value]
   candidates=[r for r in candidates if any(all((r['id'],s) in readers[rd] and isinstance(readers[rd][r['id'],s]['raw'],str) and readers[rd][r['id'],s]['raw'].strip() for rd in ['oracle','nla']) for s in [0,1])]
   candidates.sort(key=lambda r:I.rank('s84-item',feature,value,r['id']))
   if len(candidates)<count:raise ValueError('insufficient paired nonempty test states')
   for r in candidates[:count]:
    samples=[s for s in [0,1] if all(readers[rd].get((r['id'],s),{}).get('raw','').strip() for rd in ['oracle','nla'])]
    selected.append({**r,'sample':min(samples,key=lambda s:I.rank('s84-sample',r['id'],s))})
 if len(selected)!=150 or len({r['id'] for r in selected})!=150 or Counter(x['value'] for x in selected)!={'present':75,'absent':75}:raise ValueError('sample balance/uniqueness')
 return selected

def export(name,records):
 folder=I.CACHE/'blind_samples'/name;folder.mkdir(parents=True,exist_ok=True)
 records=sorted(records,key=lambda x:I.rank('claude-order',name,x[0]['id']));blind=[x[0] for x in records];key=[x[1] for x in records]
 if len(blind)!=300 or len({r['id'] for r in blind})!=300 or any(set(r)!={'id','question','readout'} for r in blind) or Counter(x['reader'] for x in key)!={'oracle':150,'nla':150}:raise ValueError('blind schema/coverage')
 I.jsonl(folder/'blind_sample.jsonl',blind);I.jsonl(folder/'KEY.DO_NOT_SHARE.jsonl',key)
 return {'sample':str(folder/'blind_sample.jsonl'),'sample_sha256':I.sha(folder/'blind_sample.jsonl'),'key_cache_only':str(folder/'KEY.DO_NOT_SHARE.jsonl'),'key_sha256':I.sha(folder/'KEY.DO_NOT_SHARE.jsonl'),'n':300,'states':150,'reader_counts':dict(Counter(x['reader'] for x in key)),'strata':[{'feature':k[0],'value':k[1],'n_states':v} for k,v in sorted(Counter((x['feature'],x['label']) for x in key if x['reader']=='oracle').items())]}

def build():
 verify_plan();items,labels,readers,refs=load_s84();specs=I.read(I.OUT/'QUESTIONS_S84.json');selected=sample_selection(labels,readers,specs);records=[]
 for r in selected:
  for rd in ['oracle','nla']:
   src=readers[rd][r['id'],r['sample']];opaque=I.rank('e13-s84-claude',r['id'],r['sample'],rd)
   records.append(({'id':opaque,'question':specs[r['feature']]['question'],'readout':src['raw']},{'id':opaque,'reader':rd,'item':r['id'],'label':r['value'],'feature':r['feature'],'sample':r['sample'],'layer':src['layer'],'readout_sha256':I.digest(src['raw'])}))
 second=export('s84',records)
 old=I.read(I.OUT/'POOL_MANIFEST.json')
 for n,h in old['files'].items():
  if I.sha(I.CACHE/n)!=h:raise ValueError('original W1 sample changed')
 sel={r['id']:r for r in I.rows(I.CACHE/'sample.private.DO_NOT_SEND.jsonl')};records=[]
 for r in I.rows(I.CACHE/'pool.private.jsonl'):
  records.append(({'id':r['case_id'],'question':P.QUESTIONS[r['feature']]['question'],'readout':r['raw']},{'id':r['case_id'],'reader':r['reader'],'item':r['item_id'],'label':sel[r['item_id']]['value'],'feature':r['feature'],'sample':r['sample'],'layer':r['layer'],'readout_sha256':r['raw_sha256']}))
 first=export('w1',records)
 receipt={'section':101,'status':'BOTH_CLAUDE_SAMPLES_READY_NOT_CODED','seed':I.SEED,'at':time.time(),'w1':first,'s84':second,'s84_sources':refs,'sampling_scope_sha256':I.sha(I.OUT/'S84_SCOPE.md'),'questions_s84_sha256':I.sha(I.OUT/'QUESTIONS_S84.json'),'api_calls':0,'gpu_h':0,'privacy':'Only blind_sample.jsonl goes to the coder. Both keys remain untracked cache only. No automatic API call or key join.'}
 I.save(I.OUT/'CLAUDE_SAMPLES_RECEIPT.json',receipt);print({k:v['sample'] for k,v in [('w1',first),('s84',second)]})

def keywords():
 verify_plan();frozen=I.read(I.OUT/'KEYWORDS_S84.json');patterns=frozen['patterns']
 # The mapping must already be committed before any counts.
 committed=subprocess.check_output(['git','show','HEAD:results/g_agreement/understand/e13/KEYWORDS_S84.json'],cwd=I.ROOT)
 if committed!=(I.OUT/'KEYWORDS_S84.json').read_bytes():raise ValueError('keyword map differs from committed freeze')
 items,labels,readers,refs=load_s84();lookup={x['id']:x for x in items};rows=[]
 if set(patterns)!={x['feature'] for x in items}:raise ValueError('keyword row scope mismatch')
 for f in patterns:
  for rd in ['oracle','nla']:
   cases=[r for (iid,s),r in readers[rd].items() if lookup[iid]['feature']==f];valid=[r for r in cases if isinstance(r['raw'],str) and r['raw'].strip()];test=[r for r in valid if labels[r['id']]['split']=='test'];fn=lambda r:bool(re.search(patterns[f],r['raw'],re.IGNORECASE))
   rows.append({'feature':f,'reader':rd,'layer':44 if rd=='oracle' else 42,'expected':len(cases),'valid_raw':len(valid),'missing_raw':len(cases)-len(valid),'keyword_hits':sum(fn(r) for r in valid),'test_valid_raw':len(test),'test_keyword_hits':sum(fn(r) for r in test)})
 data={'section':101,'status':'DESCRIPTIVE_LITERAL_CROSSCHECK_ONLY','rows':rows,'keyword_map_sha256':I.sha(I.OUT/'KEYWORDS_S84.json'),'source_refs':refs,'scope':'All sealed dev/test and generation0/1; native Oracle44 from full E13(a), NLA42 from earlier §84. No old partials, J/logit excluded. Literal terms do not establish semantic mention or value accuracy.','api_calls':0,'gpu_h':0}
 I.save(I.OUT/'S84_KEYWORD_COUNTS.json',data);lines=['# §101 E13(b) — §84 literal keyword cross-check','','DESCRIPTIVE. All sealed dev/test records and generation indices0/1; denominators differ from W1’s matched75/reader/row sample. Test-only subset also shown. Keywords are literal-name flags, not explicit-state assertions or value accuracy. Shared feature families use the same regex across thresholds; this does not test threshold-specific correctness.','','| Row | Oracle L44: hits/raw | NLA L42: hits/raw | Oracle test only | NLA test only | Empty raw (O/N) |','|---|---:|---:|---:|---:|---:|']
 for f in patterns:
  o=next(r for r in rows if r['feature']==f and r['reader']=='oracle');n=next(r for r in rows if r['feature']==f and r['reader']=='nla');lines.append(f"| {f} | {o['keyword_hits']}/{o['valid_raw']} | {n['keyword_hits']}/{n['valid_raw']} | {o['test_keyword_hits']}/{o['test_valid_raw']} | {n['test_keyword_hits']}/{n['test_valid_raw']} | {o['missing_raw']}/{n['missing_raw']} |")
 lines+=['','Exact regex map and pre-count scope note: KEYWORDS_S84.json / S84_SCOPE.md. Source FREE_SEAL hashes verified before reading the sealed outputs; all10,080 E13(a) cells and3,360 earlier NLA cells verified. Only3,360 Oracle and3,360 NLA records enter this table. Raw strings preserved, including incomplete endings/parser failures. Repeats and dev/test records are not independent.0 API cost,0 GPU-h.']
 (I.OUT/'S84_KEYWORD_COUNTS.md').write_text('\n'.join(lines)+'\n');I.save(I.OUT/'S84_KEYWORD_SEAL.json',{'files':{n:I.sha(I.OUT/n) for n in ['S84_KEYWORD_COUNTS.json','S84_KEYWORD_COUNTS.md','KEYWORDS_S84.json']}});print('Keyword table written')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','build','keywords']);a=p.parse_args();{'freeze':freeze,'build':build,'keywords':keywords}[a.action]()
