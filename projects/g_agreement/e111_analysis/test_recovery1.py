from pathlib import Path
import pytest
from . import recovery1 as r


def test_both_original_plot_functions_synthetic(tmp_path):
    r.plot_smoke(tmp_path)
    assert all((tmp_path/p).stat().st_size>100 for p in ('contrast.png','bins.png'))


def test_original_guard_is_never_reused():
    assert r.GUARD != r.a.GUARD
    assert r.GUARD.name=='RECOVERY1_ONCE.json'
    assert r.OUT.name=='recovery1_analysis_once'


def test_failure_and_guard_must_match(tmp_path,monkeypatch):
    g=tmp_path/'guard';g.write_text('original')
    f=tmp_path/'FAILURE.json'
    r.c.write(f,dict(guard_sha256=r.c.sha(g),status='FAILED_AFTER_GUARD_NO_SCIENTIFIC_RESULT_SAVED',original_output_files=[]))
    monkeypatch.setattr(r.c,'verify',lambda *args: {})
    r.validate_failure(tmp_path/'seal',g)
    g.write_text('changed')
    with pytest.raises(ValueError):r.validate_failure(tmp_path/'seal',g)
