import pytest
from . import e101_judging as m
from projects.g_agreement.readerbench.io import write,sha

def grid():
    return [dict(id=f'{i}_{c}',base_id=str(i),row='fact_recall',block=44,alpha=4,condition=c) for i in range(84) for c in ('steered','random')]

def test_same84_steered_random_only():
    xs=grid();m.validate_grid(xs,'fact_recall')
    for field,value in [('block',42),('alpha',2),('row','format_plan'),('condition','baseline')]:
        bad=[dict(x) for x in xs];bad[0][field]=value
        with pytest.raises(ValueError):m.validate_grid(bad,'fact_recall')
    with pytest.raises(ValueError):m.validate_grid(xs[:-1],'fact_recall')
    bad=[dict(x) for x in xs];bad[0]['base_id']='other'
    with pytest.raises(ValueError):m.validate_grid(bad,'fact_recall')

def test_shared402_blocks_before_route_or_send(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'HERE',tmp_path);monkeypatch.setattr(m,'CACHE',tmp_path/'E101');m.CACHE.mkdir()
    monkeypatch.setattr(m.funded,'CACHE',tmp_path);monkeypatch.setattr(m,'source_gate',lambda:None)
    write(tmp_path/'SOURCE_SEAL.json',{});write(tmp_path/'INPUTS.json',{})
    write(m.CACHE/'ADMISSION.json',dict(source_seal_sha256=sha(tmp_path/'SOURCE_SEAL.json'),inputs_sha256=sha(tmp_path/'INPUTS.json')))
    write(tmp_path/'PAUSED_402.json',{'bank':'E87'})
    monkeypatch.setattr(m.funded,'route_api',lambda:pytest.fail('must not load route/send'))
    with pytest.raises(ValueError,match='credit pause'):m.execute()
