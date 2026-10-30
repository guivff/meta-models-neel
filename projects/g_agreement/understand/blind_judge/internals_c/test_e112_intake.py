from types import SimpleNamespace
import pytest
from .e112_intake import make_units, native_members
from .e112_family import unit_call
from .transport import frozen_wire
from ..e80_channel import wire_for


def fixture():
    packets = {str(i): dict(id=str(i), headline_scorer='regex' if i < 198 else 'judge',
        regex_units=['frozen'], mode='basic', schema=dict(name='family', strict=True, schema=dict(type='boolean')))
        for i in range(518)}
    records = [(dict(member='batch.json', keys=[i, 'text']), dict(id=f'{i}:{r}', unit_id=str(i),
        reader=r, layer=44 if r == 'oracle' else 42, text='frozen readout', condition='PCA1_ablated', repeat=0))
        for i in range(518) for r in ('oracle', 'nla')]
    return records, packets


def test_exact_full_grid_original_regex_and_separate_family_calls():
    records, packets = fixture()
    regex = SimpleNamespace(score_sample=lambda units, text: dict(original=True))
    units, resolved, joins = make_units(records, packets, regex)
    assert len(units) == 640 and len(resolved) == 396 and len(joins) == 1036
    assert all(x['code'] == dict(original=True) for x in resolved)
    assert all(x['kind'] == 'family80' and x['data']['readout'] == 'frozen readout' for x in units)


def test_missing_or_wrong_arm_source_rejected():
    records, packets = fixture();regex = SimpleNamespace(score_sample=lambda *args: {})
    with pytest.raises(ValueError):make_units(records[:-1], packets, regex)
    records[0][1]['condition'] = 'none'
    with pytest.raises(ValueError):make_units(records, packets, regex)


def test_family_worker_wire_is_original_family_renderer_and_schema():
    records, packets = fixture()
    unit = dict(id='a'*32, kind='family80', rubric=None,
                data=dict(id='a'*32, packet=packets['200'], readout='frozen readout'))
    protocol = SimpleNamespace(MODEL='google/gemini-3.1-flash-lite', PROVIDER='google-vertex/global', PROVIDER_NAME='Google')
    renderer = SimpleNamespace(judge_messages=lambda packet, text: [dict(system='Original family instruction', user=text)])
    call, validate = unit_call(unit, protocol, renderer)
    assert frozen_wire(call, protocol) == wire_for(unit['data']['packet'], unit['data']['readout'], protocol, renderer)
    validate(True)
    with pytest.raises(ValueError):validate('true')


def test_stage_metadata_is_not_a_native_batch_and_full_batch_census_required():
    names = [f'jobs/{r}_PCA1_ablated_{i:04d}.json' for r in ('oracle', 'nla') for i in range(65)]
    assert len(native_members(names+['jobs/oracle_STAGE_SEAL.json', 'jobs/nla_STAGE_SEAL.json'])) == 130
    with pytest.raises(ValueError):native_members(names[:-1]+['jobs/STAGE_SEAL.json'])
    with pytest.raises(ValueError):native_members(names+['jobs/unregistered_readouts.json'])
