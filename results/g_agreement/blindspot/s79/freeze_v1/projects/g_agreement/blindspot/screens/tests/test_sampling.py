import copy,json
from collections import Counter
import pytest
from projects.g_agreement.blindspot.screens import features as F
from projects.g_agreement.blindspot.screens import corpus as C,sampling as S

class Encoding:
 def __init__(self,ids):self.ids=ids
class CharacterTokenizer:
 def encode(self,text,add_special_tokens=False):return Encoding(list(map(ord,text)))
 def decode(self,ids,skip_special_tokens=False):return ''.join(map(chr,ids))

def fixture_pool(n=25):
 pool=[];values=[]
 for i in range(n):
  for y in [0,1]:
   for pos in [30,31,40,41]:
    doc=f'doc{i}_{y}';pool.append({'id':doc+':'+str(pos),'document_id':doc,'source_group_id':doc,'domain':'python','family':'source','position':pos,'position_bin':S.position_bin(pos)});values.append(y)
 return pool,values

def test_score_orientation_and_class_names():
 for f in F.FEATURES:
  assert f.phrasing_pair[0]==F.ASKED_TEMPLATE.format(statement=f.positive)
  assert f.phrasing_pair[1]==F.ASKED_TEMPLATE.format(statement=f.negative)
  assert f.record()['class_label'] in F.CLASSES

@pytest.mark.parametrize('pos,expected',[(0,0),(31,0),(32,1),(63,1),(64,2),(127,2),(128,3),(255,3),(256,4),(511,4)])
def test_absolute_bins(pos,expected):assert S.position_bin(pos)==expected

@pytest.mark.parametrize('pos',[-1,512,999,3.5])
def test_bin_decoys(pos):
 with pytest.raises(ValueError):S.position_bin(pos)

def test_label_blind_prefix_pool():
 doc={'id':'example','domain':'python','group_id':'source-group','source':{'repo':'source'},'text':'x = 12\n'*100}
 document,pool=S.prefix_pool(doc,CharacterTokenizer())
 assert len(document['ids'])==512;assert len(pool)==16
 assert {r['position_bin'] for r in pool}==set(range(5))
 for r in pool:
  prefix=doc['text'][:r['position']+1]
  assert r['text']==prefix;assert r['prefix_sha256']==C.digest(prefix)
 assert S.prefix_pool(doc,CharacterTokenizer())==(document,pool)


def test_matching_is_exact_and_capped():
 pool,values=fixture_pool();pairs,report=S.select_feature('fixed',pool,values,target=35,floor=20)
 assert report['status']=='RETAINED' and len(pairs)==35
 counts=Counter();used=set()
 for p,n in pairs:
  a,b=pool[p],pool[n]
  assert values[p]==1 and values[n]==0
  assert (a['domain'],a['family'],a['position'],a['position_bin'])==(b['domain'],b['family'],b['position'],b['position_bin'])
  assert a['source_group_id']!=b['source_group_id']
  for r in [a,b]:counts[r['document_id']]+=1;assert r['id'] not in used;used.add(r['id'])
 assert max(counts.values())<=3
 assert S.select_feature('fixed',pool,values,target=35,floor=20)==(pairs,report)

@pytest.mark.parametrize('change',['all-negative','cross-domain','cross-family','cross-position','same-group','missing'])
def test_no_invented_matches(change):
 pool,values=fixture_pool()
 if change=='all-negative':values=[0]*len(values)
 if change=='missing':values=[-1]*len(values)
 for i,r in enumerate(pool):
  if values[i]!=1:continue
  if change=='cross-domain':r['domain']='latex'
  if change=='cross-family':r['family']='other-source'
  if change=='cross-position':r['position']+=5;r['position_bin']=S.position_bin(r['position'])
 if change=='same-group':
  for r in pool:r['source_group_id']='one-group'
 pairs,report=S.select_feature('fixed',pool,values,target=35,floor=20)
 assert not pairs and report['status']=='DROPPED'

@pytest.mark.parametrize('change',['duplicate','bad-bin','nonbinary'])
def test_malformed_pool_decoys(change):
 pool,values=fixture_pool()
 if change=='duplicate':pool[1]['id']=pool[0]['id']
 if change=='bad-bin':pool[0]['position_bin']=4
 if change=='nonbinary':values[0]=2
 with pytest.raises(ValueError):S.select_feature('fixed',pool,values)


def test_source_table_rendering():
 table={'page_title':'Example','header':['Name','A|B'],'rows':[['a\\b','two\nlines']]}
 t=C.render_table(table);assert '# Example' in t and 'A\\|B' in t and 'two<br>lines' in t and 'a\\\\b' in t
 with pytest.raises(ValueError):C.render_table({'header':['x','y'],'rows':[['x']]})


@pytest.mark.skipif(not (C.CACHE/'prepared/INPUT_SEAL.json').is_file(),reason='private frozen corpus cache unavailable; no network in tests')
def test_frozen_actual_corpus_and_input_hashes():
 manifest=json.loads((C.OUT/'CORPUS_MANIFEST.json').read_text())
 assert manifest['domain_counts']=={d:600 for d in F.DOMAINS}
 assert len(manifest['documents'])==2400 and len({r['id'] for r in manifest['documents']})==2400
 assert C.sha(C.ROOT/manifest['corpus_path'])==manifest['corpus_sha256']
 for source in manifest['source_files']:assert C.sha(C.ROOT/source['path'])==source['sha256']
 assert C.sha(manifest['frozen_bank']['path'])==manifest['frozen_bank']['sha256']
 bank=S.CACHE/'prepared';seal=json.loads((bank/'INPUT_SEAL.json').read_text())
 for n,h in {**seal['files'],**seal['private_label_files']}.items():assert C.sha(bank/n)==h
 assert seal['tokenizer_sha256']==C.sha(S.TOKENIZER)


@pytest.mark.skipif(not (C.CACHE/'prepared/INPUT_SEAL.json').is_file(),reason='private frozen corpus cache unavailable; no network in tests')
def test_actual_selected_pairs_stay_blind_and_matched():
 bank=S.CACHE/'prepared';labels=C.rows(bank/'labels.selected.DO_NOT_STAGE.jsonl');mapping={(x['feature'],x['id']):x for x in labels};assign=C.rows(bank/'assignments.input.jsonl');counts=Counter()
 for row in assign:
  assert set(row)=={'feature','id','donor_id'}
  a=mapping[row['feature'],row['id']];b=mapping[row['feature'],row['donor_id']]
  assert a['value']!=b['value'];assert a['source_group_id']!=b['source_group_id']
  assert (a['domain'],a['family'],a['position'])==(b['domain'],b['family'],b['position'])
  counts[a['feature'],a['document_id']]+=1
 assert max(counts.values())<=3
 eligibility=json.loads((C.OUT/'ELIGIBILITY.json').read_text())
 for r in eligibility['features']:
  n=sum(x['feature']==r['feature'] for x in assign)
  assert n==2*r['matched_per_side'] if r['status']=='RETAINED' else n==0
  if r['status']=='RETAINED':assert r['matched_per_side']>=100


def test_public_manifest_without_private_cache():
 manifest=json.loads((C.OUT/'CORPUS_MANIFEST.json').read_text())
 assert len(manifest['documents'])==2400
 assert Counter(r['domain'] for r in manifest['documents'])==Counter({d:600 for d in F.DOMAINS})
 assert all(len(r['text_sha256'])==64 and r['group_id'] and r['source_id'] for r in manifest['documents'])
 assert all(len(r['revision'])==40 and len(r['sha256'])==64 for r in manifest['source_files'])
