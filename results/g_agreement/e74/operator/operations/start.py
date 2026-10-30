"""Start only the SSH control plane. Never starts an E74 worker or engine."""
import base64
import os
from pathlib import Path
import subprocess
import sys


def public_keys(value):
    if len(value) > 32768:
        raise ValueError('SSH public-key input too large')
    lines = []
    for line in value.splitlines():
        fields = line.strip().split()
        if not fields:
            continue
        if len(fields) < 2 or fields[0] not in {
            'ssh-ed25519', 'ssh-rsa', 'ecdsa-sha2-nistp256',
            'ecdsa-sha2-nistp384', 'ecdsa-sha2-nistp521',
        }:
            raise ValueError('Only plain OpenSSH public keys are accepted')
        blob = base64.b64decode(fields[1], validate=True)
        size = int.from_bytes(blob[:4], 'big')
        if size > 64 or blob[4:4+size] != fields[0].encode():
            raise ValueError('Public-key type and wire encoding differ')
        # Comments and options are deliberately not interpreted or retained.
        lines.append(fields[0] + ' ' + fields[1])
    if not lines:
        raise ValueError('SSH_PUBLIC_KEY must contain at least one public key')
    return '\n'.join(lines) + '\n'


def main():
    if os.geteuid() != 0:
        raise ValueError('The SSH control entrypoint requires root')
    keys = public_keys(os.environ.pop('SSH_PUBLIC_KEY', ''))
    os.umask(0o077)
    run = Path('/run/e74-ssh')
    run.mkdir(mode=0o700, parents=True, exist_ok=True)
    run.chmod(0o700)
    Path('/run/sshd').mkdir(mode=0o755, exist_ok=True)
    Path('/run/sshd').chmod(0o755)
    auth = run / 'authorized_keys'
    auth.write_text(keys)
    auth.chmod(0o600)
    subprocess.run(['ssh-keygen', '-l', '-f', str(auth)], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    host = run / 'ssh_host_ed25519_key'
    for path in [host, Path(str(host)+'.pub')]:
        path.unlink(missing_ok=True)
    subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-f', str(host)],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(['/usr/sbin/sshd', '-t', '-f', '/opt/e74-ops/sshd_config'], check=True)
    print('E74_SSH_CONTROL_READY; scientific execution requires I-2 admission', flush=True)
    os.execv('/usr/sbin/sshd', ['/usr/sbin/sshd', '-D', '-e', '-f', '/opt/e74-ops/sshd_config'])


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError):
        # Do not echo supplied keys or subprocess output into provider logs.
        print('E74 SSH startup rejected invalid or missing configuration', file=sys.stderr)
        raise SystemExit(78)
