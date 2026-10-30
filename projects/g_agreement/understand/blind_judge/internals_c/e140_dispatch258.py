"""Source-bound E140 owner lossless record transport, science integration held."""
import argparse
from pathlib import Path
from . import e140_channel258 as original
from .e140_channel258 import worker,N,PHASE,render
from .transport import ROOT,HERE
from projects.g_agreement.readerbench.io import read,sha
from projects.g_agreement.readerbench.scoring import require
_original_gate=original.source_gate

def source_gate(bank):
 _original_gate(bank);p=HERE/'E140_OWNER_TRANSPORT258_SOURCE.json';s=read(p)
 for n,h in s['files'].items():require(sha(ROOT/n)==h,'frozen source-bound dispatch supplement')
 for n,h in s['owner_frozen_files'].items():require(sha(n)==h,'genuine tested lossless owner source before outputs')
 require(s['sets_preserved']is True and s['scientific_analysis_integration_held']is True,'no scalar conversion or scientific denominator choice')
 return p

def activate():original.source_gate=source_gate

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--phase-directory',type=Path,required=True);a=p.parse_args();activate();original.run(a.phase_directory)
