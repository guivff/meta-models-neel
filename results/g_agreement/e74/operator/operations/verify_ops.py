"""Check exact OS lock, unchanged scientific file hashes, and no baked keys."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8*1024*1024), b''):
            h.update(b)
    return h.hexdigest()


def main():
    root = Path('/opt/e74-ops')
    lock = json.loads((root/'OS_LOCK.json').read_text())
    observed = {}
    for p in lock['packages']:
        name = p['package']
        version = subprocess.check_output(['dpkg-query', '-W', '-f=${Version}', name], text=True)
        assert version == p['version'], name
        observed[name] = version
    status = subprocess.check_output(['dpkg', '--audit'], text=True)
    assert not status.strip(), status
    tools = {n:shutil.which(n) for n in ['sshd','ssh','sftp','rsync','ps','pkill','setsid','timeout','tini','curl','bash','sha256sum','tar','gzip']}
    assert all(tools.values()), tools
    assert not list(Path('/etc/ssh').glob('ssh_host_*key*'))
    assert not Path('/root/.ssh').exists()
    assert not Path('/run/e74-ssh').exists()
    files = json.loads((root/'SCIENTIFIC_FILES.json').read_text())
    for name, expected in files.items():
        assert digest(Path(name)) == expected, name
    return dict(status='PASS_CPU_OPERATIONS_CONTRACT', os_packages=observed,
                tools=tools, scientific_files_byte_identical=len(files),
                baked_host_or_authorized_keys=False, engine_invoked=False,
                gpu_used=False, model_weights_present=False)


if __name__ == '__main__':
    print(json.dumps(main(), sort_keys=True, indent=2))
