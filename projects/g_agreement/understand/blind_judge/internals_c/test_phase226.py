import pytest
from . import phase226 as p
from projects.g_agreement.readerbench.io import write


def test_missing_extended_admission_blocks_before_old_launcher_or_call(tmp_path, monkeypatch):
    here = tmp_path/'source'
    here.mkdir()
    phase = tmp_path/'phase'
    phase.mkdir()
    write(here/'ACCOUNTING226_SOURCE_SEAL.json', dict(files={}))
    write(phase/'ADMISSION.json', dict(section226_operations_source_seal_sha256='unpublished'))
    monkeypatch.setattr(p, 'HERE', here)
    monkeypatch.setattr(p.phase_run, 'run', lambda dest: pytest.fail('must not reach dispatch'))
    with pytest.raises(ValueError):
        p.run(phase)
