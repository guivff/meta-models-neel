import unittest,types,tempfile,json
from pathlib import Path
from decimal import Decimal
from unittest.mock import patch
from .backend248 import zero_error,retry_action,retry_id,cap_guard,BackendTransport
from .recover_backend248 import split_prefix,traceable
P=types.SimpleNamespace(PROVIDER_NAME='Google',MODEL='google/gemini-3.1-flash-lite')
def response(cost=0,finish='error',status=200):return dict(http_status=status,response=dict(provider=P.PROVIDER_NAME,model=P.MODEL,usage=dict(cost=cost),choices=[dict(finish_reason=finish,error=dict(code=429),message=dict(content='{"verdict":"YES"}'))]))
class BackendTest(unittest.TestCase):
 def test_partial_content_is_backend_error_not_success(self):self.assertTrue(zero_error(response(),P))
 def test_positive_charge_error_not_zero_retry(self):self.assertFalse(zero_error(response(.1),P))
 def test_unknown_charge_stops(self):
  with self.assertRaises(ValueError):zero_error(response(None),P)
 def test_wrong_provider_stops(self):
  r=response();r['response']['provider']='other'
  with self.assertRaises(ValueError):zero_error(r,P)
 def test_normal_stop_zero_is_real_response(self):
  r=response(finish='stop');r['response']['choices'][0]['error']=None;self.assertFalse(zero_error(r,P))
 def test_direct_E118_five_retry_doubling(self):
  self.assertEqual([retry_action(response(),P,i,0,5)for i in range(6)],[('zero',30),('zero',60),('zero',120),('zero',240),('zero',480),('zero_exhausted',0)])
 def test_otherbank_registered_two_only(self):self.assertEqual(retry_action(response(),P,2,0,2),('zero_exhausted',0))
 def test_HTTP429_separate_bounded_counter(self):
  r=dict(http_status=429,response=dict(error=dict(code=429)));self.assertEqual(retry_action(r,P,0,4,5),('rate',480));self.assertEqual(retry_action(r,P,0,5,5),('rate_exhausted',0))
 def test_distinct_traceable_physical_ids(self):
  ids={retry_id('base',z,r)for z in range(6)for r in range(6)};self.assertEqual(len(ids),36);self.assertNotIn('base',ids);self.assertTrue(traceable(retry_id('base',5,2),'base',5));self.assertFalse(traceable(retry_id('base',5,2),'base',2))
 def test_success_prefix_is_not_resent(self):
  ps=[dict(calls=[c])for c in('a','b','c')];done={c:dict(id=c,status='KEPT')for c in('a','b')};ok,partial,cursor=split_prefix(ps,done);self.assertEqual((len(ok),partial,cursor),(2,[],2))
 def test_pending_schema_attempt_is_retained(self):
  ps=[dict(calls=['a','b','c'])];d={'a':dict(id='a',status='UNPARSEABLE',reason='FROZEN_SCHEMA_OR_EVIDENCE_FAILED')};ok,partial,cursor=split_prefix(ps,d);self.assertEqual((len(ok),len(partial),cursor),(0,1,0))
 def test_nonprefix_terminal_rejected(self):
  with self.assertRaises(ValueError):split_prefix([dict(calls=['a']),dict(calls=['b'])],{'b':dict(id='b',status='KEPT')})
 def test_actual_ledger_cap_reasserted_after_reload(self):
  n={'CAP':Decimal(5)};exec('class Ledger:\n def reserve(self,x):return x<=CAP\n def settle(self,x):return x<=CAP\n def summary(self):return {"cap_usd":str(CAP)}\ndef one(client):return CAP\n',n);api=types.SimpleNamespace(CAP=Decimal(5));client=types.SimpleNamespace(ledger=n['Ledger']());cap_guard(api,client,n['one'],1);self.assertFalse(client.ledger.reserve(Decimal('1.01')));n['CAP']=Decimal(5);cap_guard(api,client,n['one'],1);self.assertEqual(n['one'](client),Decimal(1))
 def test_exhaustion_does_not_decode_or_score_partial_content(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td);p=root/'ledger/E118_judging';p.mkdir(parents=True);(p/'r.response.json').write_text(json.dumps(response()));ch=object.__new__(BackendTransport);ch.bank='E118';ch.allowed={'c':dict(id='c',phase='judging')};ch.input_sha='s';ch.root=root;ch.io=types.SimpleNamespace(digest=None);ch.protocol=P;ch.exhausted={'c':'UNCHARGED_BACKEND_RETRIES_EXHAUSTED'};ch.client=types.SimpleNamespace(one=lambda *a:dict(id='r'),ledger=types.SimpleNamespace(totals=lambda:({'r':0},{'r'})))
   with patch('projects.g_agreement.understand.blind_judge.internals_c.transport.unpaused'),patch('projects.g_agreement.understand.blind_judge.internals_c.transport.decode',side_effect=AssertionError('partial content must not be decoded')):
    t,a=ch.call('c');self.assertEqual(t['status'],'UNPARSEABLE');self.assertIsNone(t['result']);self.assertEqual(t['reason'],'UNCHARGED_BACKEND_RETRIES_EXHAUSTED')
if __name__=='__main__':unittest.main()
