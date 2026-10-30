import pytest
from decimal import Decimal
from projects.g_agreement.understand.e13 import api,protocol as P,analyse

def test_cap_reservation(tmp_path):
 l=api.Ledger(tmp_path/'ledger');assert l.reserve('a',Decimal('4.9'));assert not l.reserve('b',Decimal('.2'));l.settle('a',Decimal('.1'));assert l.reserve('b',Decimal('.2'));assert api.CAP==Decimal(5)
def test_evidence_flag_not_attrition():
 v=P.validate('code',{'mentions':True,'value':'A','evidence':'paraphrase'},[{'readout':'inside parentheses'}]);assert v['mentions'] and v['evidence_quality_issue']
def test_schema_and_consistency():
 for v in [{'mentions':'yes','value':'A','evidence':''},{'mentions':False,'value':'A','evidence':''},{'mentions':True,'value':'UNSTATED','evidence':''}]:
  with pytest.raises(ValueError):P.validate('code',v,[{'readout':'text'}])
def test_only_question_readout_and_route():
 x={'question':'property A or B?','readout':'literal output'};wire=P.payload('code',[x]);P.check_wire('code',[x],wire)
 assert wire['provider']['only']==['google-vertex/global'] and wire['provider']['zdr'] and wire['provider']['data_collection']=='deny'
 with pytest.raises(ValueError):P.payload('code',[dict(x,reader='oracle')])
 with pytest.raises(ValueError):P.check_wire('code',[dict(x,readout='/Users/private/data')],P.payload('code',[dict(x,readout='/Users/private/data')]))
def test_keywords_not_just_enacted_punctuation():
 assert not P.keyword('prose_paren','(continuation)');assert P.keyword('prose_paren','parenthetical expression');assert P.keyword('table_column','third column');assert not P.keyword('table_column','a data table')
def test_paired_direction_and_zero_mention():
 d=analyse.paired({'i':{'oracle':{'mention':False,'correct':False},'nla':{'mention':True,'correct':True}}});assert d['mention_difference']==1;assert d['accuracy_ci95'] is None
