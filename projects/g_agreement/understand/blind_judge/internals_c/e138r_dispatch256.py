"""Prepared source refresh; paid admission blocked until direct human approval."""
import argparse
from pathlib import Path
from . import e138r_channel254 as original
from .e138r_channel254 import worker,N,PHASE,render,check_r5
from .accounting_wj95255 import snapshot
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require
OPS='projects/g_agreement/understand/blind_judge/operational217.py'
OPS_SHA='198968de9da352b90cf47ca0d614bcf36bbd54527bb974c7322c5d2c8d900eb5'
SAMPLE='a172d37ec937e409b6201d882b8bf32feb1b27e9d9c42bcb201f3723f9a4e062'
REVIEW='25cf4b9ad64940576eb75176a24fa68618aacf9afb75679bef164f204e667685'

def source_gate(bank):
    require(bank=='E138R','same corrected bank')
    old=read(HERE/'E138R_SOURCE254.json')
    for n,h in old['files'].items():require(sha(ROOT/n)==(OPS_SHA if n==OPS else h),'preserved corrected source, exact single shared OPS refresh')
    for n,h in old['owner_frozen_files'].items():require(sha(n)==h,'original genuine owner source copies')
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==(OPS_SHA if n==OPS else h),'original base pins, exact shared OPS refresh')
    p=HERE/'E138R_DISPATCH256_SOURCE.json'
    for n,h in read(p)['files'].items():require(sha(ROOT/n)==h,'prospective refreshed source')
    return p

def human_authority():
    a=read(HERE/'E138R_DIRECT_ADMISSION_APPROVAL256.json')
    require(a.get('issuer')=='Guiv' and a.get('approved')is True and a.get('bank')=='E138R' and a.get('allocation_usd')=='1' and a.get('readouts')==168,'actual direct human admission approval required after automatic-review block')
    require(a.get('sample_sha256')==SAMPLE and a.get('R5_review_sha256')==REVIEW and a.get('review_packet_sha256')==sha(HERE/'E138R_ADMISSION_REVIEW256/REVIEW.md'),'approval binds exact review evidence and concrete action')

def activate():
    human_authority();original.source_gate=source_gate;original.snapshot=snapshot

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);a=p.parse_args();activate();original.run(a.phase_directory)
