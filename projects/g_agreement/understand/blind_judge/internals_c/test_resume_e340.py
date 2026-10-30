import json
from copy import deepcopy
from decimal import Decimal
import pytest
from .resume_e340 import book_bound,rate_loop,recovered,AUTHORITY
from projects.g_agreement.readerbench.io import write


def test_upper_bound_booking_is_explicit_once_and_original_response_unchanged(tmp_path):
 p=tmp_path/'ledger.jsonl';p.write_text('{"event":"reserve","id":"r","usd":".01","at":1}\n');response=tmp_path/'r.response.json';write(response,dict(http_status=429,response=dict(error=dict(code=429))));raw=response.read_bytes()
 a=book_bound(tmp_path,'r',response,3);b=book_bound(tmp_path,'r',response,3)
 assert a==b and a['authority']==AUTHORITY and a['provider_actual_cost_known'] is False and Decimal(a['usd'])==Decimal('.01')
 assert len(p.read_text().splitlines())==2 and response.read_bytes()==raw


def test_no_booking_missing_response_or_over_cap(tmp_path):
 p=tmp_path/'ledger.jsonl';p.write_text('{"event":"reserve","id":"r","usd":"3.01","at":1}\n');response=tmp_path/'r.response.json';write(response,dict(http_status=429,response={}))
 with pytest.raises(ValueError):book_bound(tmp_path,'r',response,3)
 assert len(p.read_text().splitlines())==1
 write(response,dict(http_status=500,response={}))
 with pytest.raises(ValueError):book_bound(tmp_path,'r',response,4)


def test_five_rate_retries_exact_backoff_terminal_missing_no_zero():
 sends=[];books=[];waits=[]
 result=rate_loop(lambda i:(sends.append(i) or dict(id=str(i))),lambda rid:dict(http_status=429,response={}),books.append,waits.append)
 assert sends==list(range(6)) and waits==[30,60,120,240,480] and books==list(map(str,range(6))) and result['id']=='5'


def test_429_then_success_or_unexpected_error_no_extra_attempt():
 for status in (200,500,402):
  sends=[];books=[];waits=[]
  rate_loop(lambda i:(sends.append(i) or dict(id=str(i))),lambda rid:dict(http_status=429 if rid=='0' else status,response={}),books.append,waits.append)
  assert sends==[0,1] and books==['0'] and waits==[30]


def test_dense_saved_prefix_preserves_final_null_and_skips_all_completed():
 plans=[dict(calls=['a0','a1','a2']),dict(calls=['b0','b1','b2']),dict(calls=['c0','c1','c2'])]
 ts=[dict(id='a0',status='KEPT',result={'original':True}),dict(id='b0',status='UNPARSEABLE',result=None,reason='CHARGED_LENGTH')]
 out=recovered(plans,ts,2);assert out[0][0] is ts[0] and out[1][0]['result'] is None
 with pytest.raises(ValueError):recovered(plans,ts+[dict(id='c1',status='KEPT')])


def test_unfinished_schema_attempt_not_mislabeled_completed():
 with pytest.raises(ValueError):recovered([dict(calls=['a','b','c'])],[dict(id='a',status='UNPARSEABLE')],1)
