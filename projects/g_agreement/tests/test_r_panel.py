"""BRIEF_RP collector mechanics (``projects/r_panel``), CPU, MOCK. Each check runs ``python -m projects.r_panel.selftest``
in a fresh process, because ``setup.activate`` re-points r_gemma's module constants for the whole process (other tests in
this session import r_gemma for Gemma).

Run: ``.venv/bin/python -m pytest projects/g_agreement/tests/test_r_panel.py -q``
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]


def _run(*args: str) -> None:
    r = subprocess.run([sys.executable, "-m", "projects.r_panel.selftest", *args], cwd=REPO, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0 and r.stdout.strip().endswith("ok"), r.stdout[-2000:] + r.stderr[-4000:]


@pytest.mark.parametrize("check", ["activate_q8", "q8b_reader", "qwen_chat_ids", "base_reader"])
def test_selftest(check):
    _run(check)


def test_q8b_load_states(tmp_path):
    _run("q8b_load_states", str(tmp_path))
