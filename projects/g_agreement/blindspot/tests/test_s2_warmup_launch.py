"""Launch dependency order/failure tests with a shell double; no installs/models."""
from pathlib import Path
import os
import subprocess
import pytest
from projects.g_agreement.blindspot import protocol as P

SCRIPT=P.ROOT/'projects/g_agreement/blindspot/ops/s2_warmup.sh'


def invoke(tmp_path,installed=False,pip_fail=False):
    interpreter=tmp_path/'python'
    interpreter.write_text('''#!/usr/bin/env bash
set -eu
printf '%s\\n' "$*" >> "$S2_TEST_LOG"
case "$1" in
-c) test -f "$S2_TEST_STATE" ;;
-m) test "$S2_TEST_PIP_FAIL" = 0 || exit 9; touch "$S2_TEST_STATE" ;;
*) printf 'WARMUP_EXECUTED\\n' >> "$S2_TEST_LOG" ;;
esac
''');interpreter.chmod(0o755)
    state=tmp_path/'installed';log=tmp_path/'calls'
    if installed:state.touch()
    env={**os.environ,'S2_PYTHON':str(interpreter),'S2_TEST_STATE':str(state),'S2_TEST_LOG':str(log),'S2_TEST_PIP_FAIL':'1' if pip_fail else '0'}
    result=subprocess.run(['bash',str(SCRIPT),'warmup.py','--unscored'],env=env,capture_output=True,text=True)
    return result,log.read_text().splitlines()


def test_missing_jaxtyping_installed_in_same_interpreter_before_warmup(tmp_path):
    result,calls=invoke(tmp_path)
    assert result.returncode==0
    assert calls[1]=='-m pip install --disable-pip-version-check jaxtyping'
    assert calls[-2:] == ['warmup.py --unscored','WARMUP_EXECUTED']


def test_working_dependency_does_not_trigger_install(tmp_path):
    result,calls=invoke(tmp_path,installed=True)
    assert result.returncode==0 and not any(c.startswith('-m pip') for c in calls)
    assert calls[-1]=='WARMUP_EXECUTED'


def test_failed_install_stops_before_warmup_or_science(tmp_path):
    result,calls=invoke(tmp_path,pip_fail=True)
    assert result.returncode==9 and 'WARMUP_EXECUTED' not in calls


def test_missing_warmup_command_fails_before_interpreter_use():
    result=subprocess.run(['bash',str(SCRIPT)],capture_output=True,text=True)
    assert result.returncode==2 and 'usage:' in result.stderr
