"""Finish an I-2 timed upload/extraction within its original900-second window."""
import argparse
import json
from pathlib import Path
import tarfile
import time
import subprocess
import sys
from . import ops
from . import smoke as core


def stage(archive, digest, out, started_epoch, source_digest):
    # started_epoch is recorded by I-2 BEFORE uploading, not reset at extraction.
    ops.require(0 < started_epoch <= time.time(), 'actual pre-upload start required')
    end = started_epoch + 900
    ops.deadline(end)
    ops.require(Path(archive).stat().st_size <= 20_000_000 and ops.sha(archive) == digest, 'package differs or exceeds20MB')
    out.mkdir(parents=True, exist_ok=False, mode=0o700)
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        ops.require(len({x.name for x in members}) == len(members), 'duplicate archive members')
        ops.require(all(x.isfile() for x in members) and sum(x.size for x in members) <= 20_000_000, 'unsafe archive')
        for m in members:
            ops.deadline(end)
            p = ops.safe(out, m.name); p.parent.mkdir(parents=True, exist_ok=True)
            with p.open('xb') as f:
                f.write(tar.extractfile(m).read())
            p.chmod(0o600)
    ops.verify_seal(out/'SOURCE_SEAL.json', source_digest)
    ops.deadline(end)
    receipt = {'status': 'VERIFIED', 'started_epoch': started_epoch, 'finished_epoch': time.time(),
               'archive_sha256': digest, 'source_seal_sha256': source_digest}
    ops.write(out/'ARCHIVE_RECEIPT.json', receipt)
    ops.deadline(end)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive', type=Path, required=True); p.add_argument('--sha256', required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--started-epoch', type=float, required=True)
    p.add_argument('--source-sha256', required=True)
    p.add_argument('--worker', action='store_true')
    a = p.parse_args()
    if a.worker:
        stage(a.archive, a.sha256, a.out, a.started_epoch, a.source_sha256)
        return 0
    end = a.started_epoch + 900
    ops.deadline(end)
    proc = subprocess.Popen([sys.executable, '-m', 'projects.g_agreement.e74.archive_stage', '--worker', '--archive', str(a.archive),
                             '--sha256', a.sha256, '--out', str(a.out), '--started-epoch', str(a.started_epoch),
                             '--source-sha256', a.source_sha256], start_new_session=True)
    try:
        code = proc.wait(timeout=max(.01, end-time.time()))
    except subprocess.TimeoutExpired:
        code = 124
    finally:
        core.kill_group(proc.pid)
    print(json.dumps({'status':'VERIFIED' if code==0 else 'STOP_ARCHIVE_STAGE','exit_code':code}))
    return code


if __name__ == '__main__': raise SystemExit(main())
