import json
from pathlib import Path
import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_cli as C,remainder_r2b_runner as R,remainder_r2b as D


def test_audit_cli_and_extra_file_decoy(tmp_path,capsys):
    cell={'id':'x','tap_blocks':[2]};p=D.stamp('fake','a','a'*64,'test')
    w=R.RunWriter(tmp_path,{'cells':[cell]},p);w.append(cell,{}, {2:np.ones(3,dtype=np.float16)});w.finish()
    assert C.main(['audit-process','--process-dir',str(w.root)])==0
    assert 'VERIFIED' in capsys.readouterr().out
    (w.root/'decoy.txt').write_text('extra')
    with pytest.raises(ValueError,match='decoy.txt'):C.main(['audit-process','--process-dir',str(w.root)])


def test_mac_receipt_rejects_changed_and_extra_bytes(tmp_path):
    (tmp_path/'data').write_text('abc');m={'compact_files':{'data':R.sha(tmp_path/'data')},'files':{}}
    r=C.mac_receipt(tmp_path,m,'pod','vol');assert r['volume_manifest_sha256']==D.digest(m)
    (tmp_path/'decoy').write_text('x')
    with pytest.raises(ValueError,match='decoy'):C.mac_receipt(tmp_path,m,'pod','vol')
    (tmp_path/'decoy').unlink();(tmp_path/'data').write_text('changed')
    with pytest.raises(ValueError,match='data'):C.mac_receipt(tmp_path,m,'pod','vol')


def test_path_escape_named(tmp_path):
    with pytest.raises(ValueError,match='decoy'):C.verify_files(tmp_path,{'../decoy':'a'*64})


def test_compact_package_keeps_states_and_rejects_inventory_decoy(tmp_path):
    from projects.g_agreement.r_bench.remainder_r2b_package import package
    run=tmp_path/'run';run.mkdir()
    for name in ('booking.json','registration.json','manifest.json','volume.json'):(run/name).write_text('{}')
    states=run/'outputs'/'capture'/'states';states.mkdir(parents=True)
    (states/'state.npy').write_bytes(b'state bytes');(states.parent/'rows.jsonl').write_text('{}')
    destination=tmp_path/'compact';m=package(run,destination)
    assert any('/states/' in n for n in m['files'])
    assert not any('/states/' in n for n in m['compact_files'])
    assert C.mac_receipt(destination,m,'pod','volume')['verified_on']=='Mac'
    (destination/'decoy').write_text('extra')
    with pytest.raises(ValueError,match='decoy'):C.mac_receipt(destination,m,'pod','volume')
