from .audit223 import frozen,rejection


def test_e81_already_accepts_empty_silent_ignores_unrequested_position():
    env=frozen('E81');item=dict(id='opaque',readout='Bonjour')
    code=dict(id='opaque',category='silent',values=[],evidence='',first_position=-15)
    assert env['classify']([item],dict(records=[code]),'E56')[0]['status']=='KEPT'


def test_e81_exhibits_needs_explicit_verbatim_evidence():
    env=frozen('E81');item=dict(id='opaque',readout='Bonjour')
    code=dict(id='opaque',category='exhibits',values=[],evidence='')
    assert rejection('E81',item,dict(records=[code]),env)[0]=='missing evidence'
    code['evidence']='Bonjour'
    assert env['classify']([item],dict(records=[code]),'E56')[0]['status']=='KEPT'


def test_e82_already_accepts_silent_without_position_field():
    env=frozen('E82');item=dict(id='opaque',rubric='\nA: foo\nB: bar\n',positions=[dict(offset=0,readout='native words')])
    code=dict(id='opaque',category='silent',values=[],evidence='')
    assert env['classify']([item],dict(records=[code]),{'opaque':['A','B']})[0]['status']=='KEPT'


def test_e82_verbatim_and_id_requirements_are_real():
    env=frozen('E82');item=dict(id='opaque',rubric='\nA: foo\nB: bar\n',positions=[dict(offset=0,readout='native words')])
    code=dict(id='opaque',category='states_value',values=['A'],evidence='not in native')
    assert rejection('E82',item,dict(records=[code]),env)[0]=='nonverbatim evidence'
    code['id']='other'
    assert rejection('E82',item,dict(records=[code]),env)[0]=='missing_or_duplicate_opaque_ID'
