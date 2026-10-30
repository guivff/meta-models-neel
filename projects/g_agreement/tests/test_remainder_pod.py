import json
import subprocess
from pathlib import Path
import pytest
from projects.g_agreement.r_bench import remainder_pod as P


def test_exact_queue_state():
    text = '| 1 | WAITING | x READY | owner |\n| 2 | READY | yes | owner |\n| 3 | BLOCKED | z | owner |\n| 4 | ready | wrong | owner |'
    assert P.queue_ready(text) == ['yes']


def test_mac_pull_requires_all_bytes(tmp_path):
    (tmp_path/'x').write_bytes(b'abc')
    r = {'mac_verified': True, 'files': P.manifest(tmp_path)}
    P.verify_pull(tmp_path, r)
    (tmp_path/'x').write_bytes(b'different')
    with pytest.raises(ValueError): P.verify_pull(tmp_path, r)
    with pytest.raises(ValueError): P.verify_pull(tmp_path, {'files': r['files']})


@pytest.mark.parametrize('exp', ['r2','r3','r4','r5','r6'])
def test_bootstrap_shared_guards_and_first_id(exp):
    s = P.bootstrap(exp, 'testpod', 'run1')
    assert s.index('POD ID MISMATCH') < s.index('mkdir')
    assert 'ws2_watchdog.sh' in s and 'ws2_hardstop.sh' in s
    assert 'kill -0' in s and 'grep -q "armed:"' in s
    assert 'REFUSE reused run directory' in s
    assert s.index('guard.json') < s.index('nohup setsid')
    assert f'GUARD_DEADLINE=$((GUARD_STARTED + {P.CAPS[exp]}))' in s
    assert f'"experiment":"{exp}"' in s
    assert not any(line.lstrip().startswith('trap ') for line in s.splitlines())
    subprocess.run(['bash', '-n'], input=s, text=True, check=True)


def test_bad_id_and_overbudget():
    with pytest.raises(ValueError): P.bootstrap('r4', 'x;evil', 'run')
    with pytest.raises(ValueError): P.bootstrap('r4', 'pod', 'run', 3601)


def test_pull_manifest_rejects_symlink_omissions(tmp_path):
    (tmp_path/'file').write_text('payload')
    (tmp_path/'link').symlink_to(tmp_path/'file')
    with pytest.raises(ValueError, match='symlinks'): P.manifest(tmp_path)


def test_original_deadline_receipt_is_valid_json(tmp_path):
    import shlex
    s = P.bootstrap('r4', 'testpod', 'fresh', 3500)
    prefix = '\n'.join(s.splitlines()[:s.splitlines().index('REMAINDER_GUARD_EOF')])
    # Execute only receipt creation, never any installed/shared guard.
    receipt_lines = prefix[prefix.index('GUARD_STARTED='):prefix.index('cat >')]
    subprocess.run(['bash', '-c', f'RUN={shlex.quote(str(tmp_path))}\n'+receipt_lines], check=True)
    receipt = json.loads((tmp_path/'guard.json').read_text())
    assert receipt['pod'] == 'testpod' and receipt['experiment'] == 'r4'
    assert receipt['deadline_epoch']-receipt['started_epoch'] == 3500


def test_current_retention_ceiling_is_explicit():
    assert 'export WD_CEIL=90' in P.bootstrap('r4', 'pod', 'fresh', idle_ceiling=90)
    assert 'export WD_CEIL=45' in P.bootstrap('r4', 'pod', 'fresh')
    with pytest.raises(ValueError): P.bootstrap('r4', 'pod', 'fresh', idle_ceiling=180)
