import pytest
from decimal import Decimal
from projects.g_agreement.understand.e10 import io as I,protocol as P,api,run,report

def test_opaque_complete_and_evidence():
 src=[{'id':'x','readout':'A cat sleeps.'}];v={'items':[{'id':'x','claims':[{'claim':'A cat sleeps.','evidence':'cat sleeps'}]}]}
 assert P.validate('extract',v,src)==v
 for bad in [{'items':[]},{'items':[{'id':'y','claims':[]}]},{'items':[{'id':'x','claims':[{'claim':'Dog','evidence':'dog'}]}]}]:
  with pytest.raises(ValueError):P.validate('extract',bad,src)

def test_claims_dont_transfer():
 src=[{'id':'x','readout':'cat'},{'id':'y','readout':'dog'}]
 with pytest.raises(ValueError):P.validate('extract',{'items':[{'id':'x','claims':[{'claim':'dog','evidence':'dog'}]},{'id':'y','claims':[]}]},src)

def test_matching_bounds_one_to_one():
 src=[{'id':'x','a':['a','b'],'b':['a','b']}]
 for matches in [[{'a':0,'b':2}],[{'a':0,'b':0},{'a':0,'b':1}],[{'a':True,'b':0}]]:
  with pytest.raises(ValueError):P.validate('match',{'items':[{'id':'x','matches':matches}]},src)
 assert P.validate('match',{'items':[{'id':'x','matches':[]}]},src)

def test_taxonomy_membership():
 with pytest.raises(ValueError):P.validate('classify',{'items':[{'id':'x','type':'T09'}]},[{'id':'x'}],[{'id':'T01'}])

def test_ledger_cap_unknown_and_duplicate(tmp_path):
 l=api.Ledger(tmp_path/'l');assert l.reserve('a',api.CAP-Decimal('1'))
 assert not l.reserve('b',Decimal('2'))
 with pytest.raises(RuntimeError):l.reserve('a',Decimal('1'))
 assert Decimal(l.summary()['unresolved_reserve_usd'])==api.CAP-Decimal('1')
 l.settle('a',Decimal('.1'));assert l.reserve('b',Decimal('2'))
 assert Decimal(l.summary()['committed_usd'])==Decimal('2.1')

def test_exact_cache_no_double_send(tmp_path):
 calls=[]
 def send(w):
  calls.append(w);return 200,{'provider':P.PROVIDER_NAME,'model':P.MODEL,'usage':{'cost':.00001},'choices':[{'finish_reason':'stop','message':{'content':'{"items":[{"id":"x","claims":[]}]}'}}]}
 c=api.Client(tmp_path,'FAKE',send);items=[{'id':'x','readout':'cat'}]
 assert c.one('extract',items)['status']=='OK';assert c.one('extract',items)['status']=='OK';assert len(calls)==1
 assert len(c.ledger.totals()[1])==1

def test_missing_cost_no_retry(tmp_path):
 calls=[]
 def send(w):calls.append(w);return 429,{'error':'rate'}
 c=api.Client(tmp_path,'FAKE',send);items=[{'id':'x','readout':'cat'}]
 assert c.one('extract',items)['status']=='MISSING';assert c.one('extract',items)['status']=='MISSING';assert len(calls)==1
 assert Decimal(c.ledger.summary()['unresolved_reserve_usd'])>0

def test_no_paired_extraction_or_metadata():
 blind=[{'pair_id':'private','READOUT_A':'one','READOUT_B':'two'},{'pair_id':'secret','READOUT_A':'two','READOUT_B':'three'}]
 jobs=run.extraction_jobs(blind);assert sum(map(len,jobs))==3
 for job in jobs:
  hashes={r['id'] for r in job};assert not {I.digest('one'),I.digest('two')}<=hashes;assert not {I.digest('two'),I.digest('three')}<=hashes
  assert all(set(x)=={'id','readout'} for x in job)

def test_selection_unique_ties_exposure_random():
 pairs=[{'pair_id':str(i),'examples_eligible':i!=0} for i in range(12)]
 typed=[{'pair_id':str(i),'type':'T0'+str((i%3)+1)} for i in range(12)]
 chosen=report.select(pairs,typed,['10','11']);assert len(chosen)==8;assert len({c['pair_id'] for c in chosen})==8;assert '0' not in {c['pair_id'] for c in chosen};assert chosen==report.select(pairs,list(reversed(typed)),['10','11'])

def test_verbatim_block():
 raw='```\n<x> exact\n\n';b=report.block(raw);assert b.split('\n',1)[1].rsplit('\n',2)[0]==raw


def test_fail_closed_zdr_policy():
 from projects.g_agreement.understand.e10 import privacy
 src=[{'id':'opaque','readout':'A cat sleeps.'}];wire=P.payload('extract',src)
 privacy.check_wire('extract',src,wire)
 assert wire['provider']['zdr'] is True and wire['provider']['data_collection']=='deny'
 wire['provider']['zdr']=False
 with pytest.raises(ValueError):privacy.check_wire('extract',src,wire)

def test_no_paths_keys_or_metadata():
 from projects.g_agreement.understand.e10 import privacy
 for src in [[{'id':'opaque','readout':'/Users/private/data'}],[{'id':'opaque','readout':'words','label':'A'}],[{'id':'opaque','readout':'sk-or-v1-'+'x'*30}]]:
  with pytest.raises(ValueError):privacy.check_wire('extract',src,P.payload('extract',src))


def test_missing_zdr_route_fails_before_inference(tmp_path,monkeypatch):
 from projects.g_agreement.understand.e10 import privacy
 class Response:
  def raise_for_status(self):pass
  def json(self):return {'data':[]}
 monkeypatch.setattr(I,'CACHE',tmp_path)
 monkeypatch.setattr(privacy.requests,'get',lambda *a,**k:Response())
 with pytest.raises(RuntimeError,match='NO_APPROVED_ZDR_ROUTE'):privacy.check_route('FAKE')

def test_route_requires_openrouter_logging_proof(tmp_path,monkeypatch):
 from projects.g_agreement.understand.e10 import privacy
 class Response:
  def raise_for_status(self):pass
  def json(self):return {'data':[{'model_id':P.MODEL,'provider_name':P.PROVIDER_NAME,'tag':P.PROVIDER}]}
 monkeypatch.setattr(I,'CACHE',tmp_path)
 monkeypatch.setattr(privacy.requests,'get',lambda *a,**k:Response())
 with pytest.raises(RuntimeError,match='not verified off'):privacy.check_route('FAKE')


def test_newline_is_not_a_windows_path():
 from projects.g_agreement.understand.e10 import privacy
 src=[{'id':'opaque','readout':'Words:\nMore words.'}]
 privacy.check_wire('extract',src,P.payload('extract',src))
