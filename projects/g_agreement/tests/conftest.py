"""Write isolation for the new R2-B tests only; other suites are unchanged."""
import tempfile
import sys
import pytest


@pytest.fixture(autouse=True)
def r2b_write_isolation(request,tmp_path,monkeypatch):
    if not request.node.path.name.startswith('test_remainder_r2b'):
        yield
        return
    monkeypatch.setattr(sys,'dont_write_bytecode',True)
    from projects.g_agreement.r_bench.remainder_x1b import write_guard
    monkeypatch.setattr(tempfile,'tempdir',str(tmp_path))
    with write_guard(roots=[tmp_path]):yield
