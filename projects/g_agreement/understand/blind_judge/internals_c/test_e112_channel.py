from types import SimpleNamespace
import pytest
from .e112_channel import family_call,validate_grid,CAP
from ..e80_channel import wire_for
from .transport import frozen_wire

P=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')


def test_literal_original_family_wire_and_schema_not_e56_value_rubric():
    packet=dict(headline_scorer='judge',mode='basic',schema=dict(name='family_bool',strict=True,schema=dict(type='boolean')))
    renderer=SimpleNamespace(judge_messages=lambda packet,sample:[dict(system='Original literal family instruction.',user=sample)])
    call,validate=family_call('source',packet,'Exact unchanged readout',P,renderer)
    assert frozen_wire(call,P)==wire_for(packet,'Exact unchanged readout',P,renderer)
    validate(True)
    with pytest.raises(ValueError):validate('true')
    assert str(CAP)=='3'
    packet['headline_scorer']='regex'
    with pytest.raises(ValueError):family_call('source',packet,'text',P,renderer)


def test_all_original_items_and_both_reader_sites_required():
    packets={str(i):{}for i in range(518)}
    records=[dict(id=f'{i:04d}:{reader}',item_id=str(i),reader=reader,layer=44 if reader=='oracle' else 42,readout='')for i in range(518)for reader in ('oracle','nla')]
    validate_grid(records,packets)
    with pytest.raises(ValueError):validate_grid(records[:-1],packets)
    records[0]['layer']=42
    with pytest.raises(ValueError):validate_grid(records,packets)
