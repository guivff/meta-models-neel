"""The isolation guard catches every write route the guarded modules use, ignores writes elsewhere, and never lets the
planted probe touch the disk (tests/_write_guard.py)."""

from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from projects.g_agreement.tests import _write_guard as WG  # noqa: E402


@pytest.fixture
def roots(tmp_path):
    prot, free = tmp_path / "protected", tmp_path / "free"
    prot.mkdir()
    free.mkdir()
    (prot / "existing.txt").write_text("x")
    (prot / "existing_dir").mkdir()
    return prot, free


def test_every_write_route_is_recorded(roots):
    prot, free = roots
    g = WG.ModuleWriteGuard([prot])
    with g.watching():
        open(prot / "a.txt", "w").close()                       # builtins.open
        (prot / "b.txt").write_text("b")                        # pathlib → io.open
        np.save(prot / "c.npy", np.zeros(2))                   # numpy
        pd.DataFrame({"x": [1]}).to_csv(prot / "d.csv")         # pandas
        with open(prot / "e.json", "a") as fh:                  # append mode
            json.dump({}, fh)
        (prot / "new_dir").mkdir()                              # mkdir of a new dir
        os.makedirs(prot / "deep" / "er")                       # makedirs
        os.rename(prot / "a.txt", prot / "a2.txt")              # rename
        (prot / "b.txt").unlink()                               # unlink
        shutil.rmtree(prot / "new_dir")                         # rmtree
        fd = os.open(prot / "f.bin", os.O_WRONLY | os.O_CREAT)  # low-level
        os.close(fd)
    ops = {op.split("(")[0] for op, _ in g.violations}
    assert {"open", "makedirs", "mkdir", "rename", "unlink", "rmtree", "os.open"} <= ops, ops
    hit = {Path(p).name for _, p in g.violations}
    assert {"a.txt", "b.txt", "c.npy", "d.csv", "e.json", "new_dir", "f.bin"} <= hit, hit


def test_writes_elsewhere_and_reads_are_ignored(roots):
    prot, free = roots
    g = WG.ModuleWriteGuard([prot])
    with g.watching():
        (free / "ok.txt").write_text("ok")
        np.save(free / "ok.npy", np.zeros(1))
        assert (prot / "existing.txt").read_text() == "x"       # reading a protected file is fine
        os.makedirs(prot / "existing_dir", exist_ok=True)       # an existing dir is no modification
        list(prot.rglob("*"))
    assert g.violations == []


def test_relative_paths_and_symlinked_roots(roots, tmp_path, monkeypatch):
    prot, free = roots
    link = tmp_path / "link"
    link.symlink_to(prot)
    g = WG.ModuleWriteGuard([link])            # guarding through a symlink also guards its target
    monkeypatch.chdir(prot)
    with g.watching():
        Path("rel.txt").write_text("r")        # relative to the cwd inside the root
        (prot / "direct.txt").write_text("d")  # the resolved target
    assert {Path(p).name for _, p in g.violations} == {"rel.txt", "direct.txt"}


def test_patches_are_removed_and_report_names_paths(roots):
    prot, _ = roots
    orig_open = open
    g = WG.ModuleWriteGuard([prot])
    with g.watching():
        (prot / "z.txt").write_text("z")
    assert open is orig_open and os.unlink.__module__ in ("posix", "nt", "os")
    assert "z.txt" in g.report() and "open('w')" in g.report()
    with pytest.raises(AssertionError, match="not active"):
        g.assert_clean()


def test_planted_probe_is_intercepted_not_written(roots, monkeypatch):
    prot, _ = roots
    g = WG.ModuleWriteGuard([prot])
    with g.watching():
        with open(prot / WG.PROBE_NAME, "w") as fh:
            fh.write("probe")
    assert not (prot / WG.PROBE_NAME).exists()
    assert [Path(p).name for _, p in g.violations] == [WG.PROBE_NAME]
