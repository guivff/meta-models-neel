from .audit104 import environment
from .audit223 import rejection


def test_actual_e104_frozen_validator_accepts_empty_silent_without_position():
    env=environment();item=dict(id='opaque',readout='Bonjour')
    code=dict(id='opaque',category='silent',values=[],evidence='')
    assert env['classify']([item],dict(records=[code]),'E56')[0]['status']=='KEPT'
    code['first_position']=-15
    assert env['classify']([item],dict(records=[code]),'E56')[0]['status']=='KEPT'


def test_actual_e104_exhibits_evidence_and_nonverbatim_rules():
    env=environment();item=dict(id='opaque',readout='Bonjour')
    code=dict(id='opaque',category='exhibits',values=[],evidence='')
    assert rejection('E81',item,dict(records=[code]),env)[0]=='missing evidence'
    code['evidence']='Bonjour'
    assert env['classify']([item],dict(records=[code]),'E56')[0]['status']=='KEPT'
    code.update(category='states_value',values=['French'],evidence='invented quote')
    assert rejection('E81',item,dict(records=[code]),env)[0]=='nonverbatim evidence'
