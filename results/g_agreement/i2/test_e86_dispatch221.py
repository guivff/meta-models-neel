import importlib.util
from pathlib import Path
import pytest
p=Path(__file__).with_name('e86_dispatch221.py');s=importlib.util.spec_from_file_location('e86d',p);D=importlib.util.module_from_spec(s);s.loader.exec_module(D)
def response(finish='stop',status=200,cost='0.01',provider='Google'):
 return dict(http_status=status,response=dict(provider=provider,model='google/gemini-3.1-flash-lite',usage=dict(cost=cost),choices=[dict(finish_reason=finish)]))
def test_length_terminal():assert D.disposition(response('length'))=='TERMINAL_UNPARSEABLE'
def test_stop_validate():assert D.disposition(response())=='VALIDATE'
def test_402_pause():assert D.disposition(response(status=402))=='PAUSE_402'
@pytest.mark.parametrize('r',[response(status=503),response(provider='other'),response('content_filter')])
def test_unknown_provider_stops(r):
 with pytest.raises(AssertionError):D.disposition(r)
def test_length_never_retried_valid_batchmate_retained():
 calls=[]
 def send(batch,attempt):
  calls.append((len(batch),attempt));return [dict(id=x['id'],status='UNPARSEABLE'if x['id']=='a'else'KEPT',code=None,terminal_reason='CHARGED_LENGTH')for x in batch]
 result=D.judge([dict(id='a'),dict(id='b')],send)
 assert calls==[(2,0)] and len(result)==2
 assert result[0]['status']=='UNPARSEABLE' and result[1]['status']=='KEPT'
def test_only_invalid_singletons_retry_twice():
 calls=[]
 def send(batch,attempt):
  calls.append(([x['id']for x in batch],attempt));return [dict(id=x['id'],status='KEPT'if x['id']=='b'else'INVALID',code=None)for x in batch]
 result=D.judge([dict(id='a'),dict(id='b')],send)
 assert calls==[(['a','b'],0),(['a'],1),(['a'],2)] and result[0]['status']=='UNPARSEABLE'
