import json
from pathlib import Path
import pytest
from . import inventory as i
from .adapter import ROWS


def packet(tmp_path, monkeypatch):
    def write(p, value):
        p.write_text(json.dumps(value))
    original = tmp_path / 'original'
    original.mkdir()
    roster = [dict(id=f'{row}-{j}', row=row, slot=j) for row in ROWS for j in range(84)]
    write(original / 'items.json', roster)
    manifest = dict(experiment='E117', alphas=[1,2,4], arms=['T','W','R'], rows={r:dict(gap=1,lens_layer=48) for r in ROWS})
    write(original / 'MANIFEST.json', manifest)
    for name in ['H44.npy','DELTAS.npy']:
        (original / name).write_bytes(b'synthetic-only')
    write(original / 'INPUT_SEAL.json', dict(experiment='E117',labels_on_pod=False,files={p.name:i.c.sha(p) for p in original.iterdir()}))
    sha=i.c.sha(original/'INPUT_SEAL.json')
    monkeypatch.setattr(i,'INPUT_SHA',sha)
    monkeypatch.setattr(i.subprocess,'check_output',lambda *a,**k:json.dumps(dict(input_seal_sha256=sha,rows=manifest['rows'])).encode())
    normalized=[dict(id=x['id'],row=x['row'],split='test') for x in roster]
    write(tmp_path/'INVENTORY.json',normalized)
    seal=dict(experiment='E117',directions_committed_before_output=True,status=i.STATUS,created_utc='now',original_input_seal=dict(seal=str(original/'INPUT_SEAL.json'),sha256=sha),files={'INVENTORY.json':i.c.sha(tmp_path/'INVENTORY.json')})
    write(tmp_path/'INVENTORY_SEAL.json',seal)
    spec=dict(inventory_mode='original_sealed_input',inventory_commit=None,inventory_seal=str(tmp_path/'INVENTORY_SEAL.json'),inventory_sha256=i.c.sha(tmp_path/'INVENTORY_SEAL.json'))
    return spec,seal,normalized,write


def test_original_roster(tmp_path,monkeypatch):
    spec,*_=packet(tmp_path,monkeypatch)
    assert len(i.load_inventory(spec,tmp_path,ROWS))==336


@pytest.mark.parametrize('change',['order','row','duplicate','split','input_pin','backdate','mode','bytes','lineage'])
def test_reject_custody_drift(tmp_path,monkeypatch,change):
    spec,seal,roster,write=packet(tmp_path,monkeypatch)
    if change=='order': roster.reverse()
    if change=='row': roster[0]['row']=ROWS[1]
    if change=='duplicate': roster[1]=roster[0]
    if change=='split': roster[0]['split']='dev'
    if change=='input_pin': seal['original_input_seal']['sha256']='0'*64
    if change=='backdate': spec['inventory_commit']='pretend-pre-output'
    if change=='mode': spec['inventory_mode']='guess'
    if change=='bytes': (tmp_path/'original'/'DELTAS.npy').write_bytes(b'changed')
    if change=='lineage': monkeypatch.setattr(i.subprocess,'check_output',lambda *a,**k:json.dumps(dict(input_seal_sha256=i.INPUT_SHA,rows={})).encode())
    write(tmp_path/'INVENTORY.json',roster)
    seal['files']['INVENTORY.json']=i.c.sha(tmp_path/'INVENTORY.json')
    write(tmp_path/'INVENTORY_SEAL.json',seal)
    spec['inventory_sha256']=i.c.sha(tmp_path/'INVENTORY_SEAL.json')
    with pytest.raises((ValueError,RuntimeError,AssertionError)):
        i.load_inventory(spec,tmp_path,ROWS)
