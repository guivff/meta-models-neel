import json
from decimal import Decimal
import pytest
from projects.g_agreement.readerbench.io import read,sha,write
from . import e87


def group(size=16):
    return dict(id='a'*32,property='topic',values={'A':'birds','B':'citrus'},
                positions=[dict(offset=i,readout='birds at '+str(i)) for i in range(1-size,1)])


@pytest.mark.parametrize('size',[8,12,16])
def test_grouped_code_retains_first_position_and_both_values(size):
    item=group(size);e87.validate_source([item])
    code=dict(id=item['id'],category='states_value',values=['A','B'],
              evidence=item['positions'][0]['readout'],first_position=1-size)
    assert e87.classify([item],dict(records=[code]))[0]['status']=='KEPT'
    assert e87.classify([item],dict(records=[dict(code,first_position=0)]))[0]['status']=='INVALID'
    assert e87.classify([item],dict(records=[dict(code,id='b'*32)]))[0]['status']=='INVALID'
    with pytest.raises(ValueError):e87.validate_source([dict(item,positions=item['positions'][:1]+item['positions'][2:])])


def test_readout_redaction_only_and_wires_preserve_positions():
    item=group();item['positions'][0]['readout']='A path: /tmp/synthetic.txt'
    redacted,audit=e87.redact_groups([item]);assert audit['redacted_records']==1
    assert '[REDACTED_PATH]' in redacted[0]['positions'][0]['readout']
    assert item['positions'][0]['readout']=='A path: /tmp/synthetic.txt'
    route=read(e87.ROOT/'results/g_agreement/understand/blind_judge/ROUTE_SEAL.json')
    _,_,protocol,_=e87.route_modules(route)
    rendered=dict(id=redacted[0]['id'],positions=redacted[0]['positions'],
                  rubric=e87.render_record(dict(id=item['id'],property=item['property'],
                       values=item['values'],readout=''),e87.RUBRIC.read_text())['rubric'])
    wire=e87.wire([rendered],protocol)
    data=json.loads(wire['messages'][1]['content'])
    assert len(data)==1 and len(data[0]['positions'])==16
    assert set(data[0])=={'id','rubric','positions'}
    assert wire['provider']['zdr'] and not wire['provider']['allow_fallbacks']


def test_byte_preserving_convert_and_incomplete_custody(tmp_path,monkeypatch):
    monkeypatch.setattr(e87,'EXPECTED_GROUPS',{'oracle':1,'nla':1,'placebo':0})
    monkeypatch.setattr(e87,'EXPECTED_READOUTS',24)
    rubric=tmp_path/'rubric';rubric.write_bytes(e87.RUBRIC.read_bytes())
    monkeypatch.setattr(e87,'RUBRIC',rubric)
    src=tmp_path/'source';src.mkdir();rows=[group(),dict(group(8),id='b'*32)]
    write(src/'GROUPED_PACKET.json',rows)
    seal=src/'SOURCE_SEAL.json'
    write(seal,dict(experiment='E87',n=2,complete=True,rubric_sha256=sha(rubric),
                    authority='47cf57c2',oracle_layers=list(e87.ORACLE_LAYERS),
                    group_counts=e87.EXPECTED_GROUPS,n_readouts=24,
                    files={'GROUPED_PACKET.json':sha(src/'GROUPED_PACKET.json')},
                    row_inventory_verified=True,first_30_frozen_order_verified=True,
                    placebo_matched_verified=True,placebo_random_only_verified=True))
    spec=dict(source_seal=str(seal),source_seal_sha256=sha(seal),
              source_packet=str(src/'GROUPED_PACKET.json'),rubric=str(rubric))
    out=tmp_path/'out';e87.convert(spec,out)
    assert read(out/'GROUPED_PACKET.json')==rows
    with pytest.raises(FileExistsError):e87.convert(spec,out)
    write(src/'GROUPED_PACKET.json',rows[:1])
    with pytest.raises(ValueError,match='frozen complete'):e87.convert(spec,tmp_path/'bad')


def test_amended_grid_requires_seventh_layer_and_full_placebo():
    grid=dict(authority='47cf57c2',oracle_layers=list(e87.ORACLE_LAYERS),
              group_counts=e87.EXPECTED_GROUPS,n_readouts=67920)
    e87.validate_grid(grid,4500)
    with pytest.raises(ValueError,match='seven-layer'):
        e87.validate_grid(dict(grid,oracle_layers=[20,28,36,44,52,60]),4500)
    with pytest.raises(ValueError,match='seven-layer'):
        e87.validate_grid(dict(grid,group_counts=dict(grid['group_counts'],placebo=1800)),4200)
