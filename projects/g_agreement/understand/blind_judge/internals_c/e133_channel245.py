"""Prospective E133 dispatch wrapper; frozen owner copies, original C driver unchanged."""
import argparse,os
from pathlib import Path
from contextlib import contextmanager
from . import e133_channel as original,registered,transport
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require
original_worker=original.worker

def source_gate():
    p=transport.HERE/'E133245_SOURCE_SEAL.json';s=read(p)
    for n,h in s['files'].items():require(sha(transport.ROOT/n)==h,'frozen prospective C source')
    for n,h in s['owner_frozen_files'].items():require(sha(n)==h,'frozen committed tested owner source copy')
    return p

@contextmanager
def worker():
    with original_worker():
        registered.HERE=transport.HERE/'E133245'
        yield

def activate():
    original.source_gate=source_gate;original.worker=worker

def once(dest):
    p=Path(dest)/'JUDGING_ONCE245.json';fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd);write(p,dict(pid=os.getpid(),source_sha256=sha(source_gate()),no_resend=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','run']);p.add_argument('--spec',type=Path);p.add_argument('--phase-directory',type=Path);a=p.parse_args();activate()
    if a.action=='prepare':
        from .e133_packet_intake import prepare_complete
        print(prepare_complete(read(a.spec)))
    else:once(a.phase_directory);original.run(a.phase_directory)
