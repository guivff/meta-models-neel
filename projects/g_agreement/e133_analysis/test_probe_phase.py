from pathlib import Path
import pytest
from . import adapter as a,probe_phase as p
from .test_adapter import fixture


def probe_spec(tmp,monkeypatch):
    spec,source=fixture(tmp,monkeypatch)
    ms=a.core.read(Path(spec['output_seal']).parent/'MEASUREMENTS.json')
    vectors=[dict(pair_id=x['pair_id'],members=[dict(vectors=m['vectors'])for m in x['members']])for x in ms]
    d=tmp/'probe-input';d.mkdir();a.core.write(d/'VECTORS.PRIVATE.json',vectors)
    a.core.seal(d,'SEAL.json',experiment='E133',status='COMPLETE',labels_cpu_only=True,inventory_sha256=spec['inventory_sha256'],native_output_sha256=a.core.sha(source),layers=list(a.probes.LAYERS),source_seals=[dict(seal=str(source),sha256=a.core.sha(source))])
    spec['probe_input_seal']=str(d/'SEAL.json');spec['probe_input_sha256']=a.core.sha(d/'SEAL.json')
    return spec


def test_probes_can_run_before_judging_and_main_reuses_same_sealed_fit(tmp_path,monkeypatch):
    spec=probe_spec(tmp_path,monkeypatch);seal=p.run(spec,'synthetic-probe');before=seal.read_bytes()
    assert not a.GUARD.exists() # no full-analysis guard claimed, no reader/code join
    def never(*args):pytest.fail('repeated fit after completed probe phase')
    monkeypatch.setattr(a.probes,'analyze',never)
    main=a.run(spec,'synthetic-main');r=a.core.read(main.parent/'RESULTS.json')
    assert r['probes_descriptive']['primary'].startswith('binary twin')
    assert seal.read_bytes()==before
    with pytest.raises(ValueError,match='guard consumed'):p.run(spec,'again')


def test_failed_probe_phase_retains_guard_and_blocks_main_before_claim(tmp_path,monkeypatch):
    spec=probe_spec(tmp_path,monkeypatch)
    def fail(*args):raise ValueError('synthetic invalid vector')
    monkeypatch.setattr(p,'vectors',fail)
    with pytest.raises(ValueError,match='invalid vector'):p.run(spec,'synthetic')
    assert p.paths()[0].exists()and not a.GUARD.exists()
    with pytest.raises(ValueError,match='in progress/failed'):a.run(spec,'synthetic')
    assert not a.GUARD.exists()


def test_reuse_rejects_different_original_native_capture(tmp_path,monkeypatch):
    spec=probe_spec(tmp_path,monkeypatch);p.run(spec,'synthetic')
    with pytest.raises(ValueError,match='same original screened'):p.existing(spec['inventory_sha256'],'another-native-source')
