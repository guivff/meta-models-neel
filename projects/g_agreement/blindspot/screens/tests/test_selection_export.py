import hashlib,json
import pytest
from projects.g_agreement.blindspot.screens import export_selection as E


def test_receipt_preserves_exact_order_and_binds_bytes():
 data=json.dumps({'section':79,'status':'FROZEN_BEFORE_ANY_S84_ITEMS','candidates':[{'feature':'second_candidate'},{'feature':'first_candidate'}]}).encode()
 r=E.receipt('a'*40,'results/g_agreement/blindspot/s79/final/TOP10.json',data)
 assert set(r)=={'source_commit','selection_file','selection_sha256','section79_features','section81_features'}
 assert r['section79_features']==['second_candidate','first_candidate'] and r['section81_features']==[]
 assert r['selection_sha256']==hashlib.sha256(data).hexdigest()
 assert r['source_commit']=='a'*40 and r['selection_file'].startswith('results/')


@pytest.mark.parametrize('decoy',['absolute','parent','branch','duplicate','empty','notsealed'])
def test_bad_selection_receipt_rejected(decoy):
 d={'section':79,'status':'FROZEN_BEFORE_ANY_S84_ITEMS','candidates':[{'feature':'candidate'}]};commit='a'*40;path='results/selection.json'
 if decoy=='absolute':path='/tmp/selection.json'
 if decoy=='parent':path='../selection.json'
 if decoy=='branch':commit='HEAD'
 if decoy=='duplicate':d['candidates']*=2
 if decoy=='empty':d['candidates']=[]
 if decoy=='notsealed':d['status']='PENDING'
 with pytest.raises(ValueError):E.receipt(commit,path,json.dumps(d).encode())


def test_export_requires_committed_real_sealed_analysis(tmp_path,monkeypatch):
 monkeypatch.setattr(E.subprocess,'check_output',lambda *a,**kw: (_ for _ in ()).throw(RuntimeError('uncommitted selection')))
 with pytest.raises(RuntimeError,match='uncommitted'):E.export('a'*40,'results/not_committed.json',tmp_path/'receipt.json')
 assert not (tmp_path/'receipt.json').exists()


@pytest.mark.parametrize('decoy',[None,'sealhash','testkind','order','freeze'])
def test_export_committed_seal_and_registered_order(tmp_path,monkeypatch,decoy):
 from projects.g_agreement.blindspot.screens import corpus as C
 rows=[{'feature':'probe_only_a','reader':'olens','evaluable':True,'w1_overlap':[],'gap':.4},{'feature':'probe_only_b','reader':'olens','evaluable':True,'w1_overlap':[],'gap':.2}]
 rb=json.dumps({'status':'COMPLETE','rows':rows}).encode()
 top={'section':79,'status':'FROZEN_BEFORE_ANY_S84_ITEMS','candidates':rows,'results_sha256':hashlib.sha256(rb).hexdigest(),'freeze_sha256':C.sha(C.OUT/'FREEZE.json')}
 if decoy=='order':top['candidates']=rows[::-1]
 if decoy=='freeze':top['freeze_sha256']='0'*64
 tb=json.dumps(top).encode();seal={'run_kind':'test' if decoy=='testkind' else 'real','files':{'TOP10.json':hashlib.sha256(tb).hexdigest(),'RESULTS.json':hashlib.sha256(rb).hexdigest()}}
 if decoy=='sealhash':seal['files']['TOP10.json']='0'*64
 blobs={'TOP10.json':tb,'RESULTS.json':rb,'ANALYSIS_SEAL.json':json.dumps(seal).encode()}
 monkeypatch.setattr(E.subprocess,'check_output',lambda args,**kw:blobs[args[-1].rsplit('/',1)[-1]])
 out=tmp_path/'receipt.json'
 if decoy:
  with pytest.raises(ValueError):E.export('a'*40,'results/s79/TOP10.json',out)
  assert not out.exists()
 else:
  result=E.export('a'*40,'results/s79/TOP10.json',out)
  assert result['section79_features']==['probe_only_a','probe_only_b']
  assert result['section81_features']==[] and json.loads(out.read_text())==result
