"""Prospective finance-only wrapper; reviewed E138R builder/wires remain exact."""
import argparse
from pathlib import Path
from . import e138r_channel254 as original
from .e138r_channel254 import worker,N,PHASE,render,check_r5
from .accounting_wj95255 import snapshot
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require
BASE_GATE=original.source_gate

def source_gate(bank):
    BASE_GATE(bank);p=HERE/'E138R_DISPATCH255_SOURCE.json'
    for n,h in read(p)['files'].items():require(sha(ROOT/n)==h,'finance-only prospective dispatch source')
    return p

def activate():
    original.source_gate=source_gate;original.snapshot=snapshot

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);a=p.parse_args();activate();original.run(a.phase_directory)
