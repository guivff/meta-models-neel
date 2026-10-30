from collections import Counter
import pytest
from projects.g_agreement.understand.e13 import io as I,prepare_claude as C

def fixture():
 specs={f'f{i}':{} for i in range(10)};labels={};readers={'oracle':{},'nla':{}}
 for f in specs:
  for value in ['present','absent']:
   for j in range(12):
    iid=f'{f}:{value}:{j}';labels[iid]={'id':iid,'feature':f,'split':'test','value':value}
    for rd in readers:
     for sample in [0,1]:readers[rd][iid,sample]={'raw':'synthetic readout'}
 return specs,labels,readers

def test_matched_strata_unique_and_deterministic():
 specs,labels,readers=fixture();a=C.sample_selection(labels,readers,specs);b=C.sample_selection(dict(reversed(list(labels.items()))),readers,specs)
 assert a==b and len(a)==len({r['id'] for r in a})==150
 assert Counter(r['feature'] for r in a)=={f:15 for f in specs};assert Counter(r['value'] for r in a)=={'present':75,'absent':75}
 assert all(n in [7,8] for n in Counter((r['feature'],r['value']) for r in a).values())
def test_no_empty_counterpart_or_dev_selection():
 specs,labels,readers=fixture()
 for sample in [0,1]:readers['nla']['f0:present:0',sample]['raw']=''
 labels['f1:present:0']['split']='dev';a=C.sample_selection(labels,readers,specs)
 assert not {'f0:present:0','f1:present:0'} & {r['id'] for r in a}
def test_insufficient_scope_refuses():
 specs,labels,readers=fixture()
 for r in labels.values():r['split']='dev'
 with pytest.raises(ValueError):C.sample_selection(labels,readers,specs)
def test_blind_export_has_only_three_fields(tmp_path,monkeypatch):
 monkeypatch.setattr(I,'CACHE',tmp_path);rs=[]
 for i in range(150):
  for reader in ['oracle','nla']:
   opaque=I.rank('fake',i,reader);rs.append(({'id':opaque,'question':'property?','readout':'words'},{'id':opaque,'reader':reader,'feature':'r','label':'present','item':str(i)}))
 receipt=C.export('test',rs);blind=I.rows(receipt['sample']);key=I.rows(receipt['key_cache_only'])
 assert len(blind)==len(key)==300 and all(set(r)=={'id','question','readout'} for r in blind)
 assert {r['id'] for r in blind}=={r['id'] for r in key}
def test_source_requires_real_seal(tmp_path):
 with pytest.raises(FileNotFoundError):C.verified(tmp_path,'FREE_SEAL.json',[])
