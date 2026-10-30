"""Prospective §202 clauses and sealed seeded original-rubric comparison grid."""
import hashlib
import math
from pathlib import Path
from .run import ROOT
from projects.g_agreement.readerbench.scoring import require

CLAUSE_NEG="A value mentioned only inside a negation, a prohibition or a quoted instruction (e.g. 'do not think about birds', 'X is not the answer') does not count as stating that value."
CLAUSE_FORMAT="A bare option letter, label or format token (e.g. ': A', '(b)', 'Option 1') does not count as stating a value unless the readout says what it stands for."
BASE=ROOT/'results/g_agreement/understand/blind_judge/e66_e68/E68_RUBRIC.md'
SPEC=ROOT/'results/g_agreement/understand/blind_judge/later_banks/RUBRIC202_VALUE.md'
ACTUAL=SPEC.with_name('RUBRIC202_VALUE.txt')
SEED=20261028


def amended(base=None):
    original=BASE.read_bytes() if base is None else base
    require(SPEC.read_text().count(CLAUSE_NEG)==1 and SPEC.read_text().count(CLAUSE_FORMAT)==1,
            'frozen §202 clauses')
    value=original+b'\n\n'+CLAUSE_NEG.encode()+b'\n'+CLAUSE_FORMAT.encode()+b'\n'
    require(value==ACTUAL.read_bytes(),'§202 value rubric byte seal')
    return value


def original_ids(ids,bank):
    require(len(ids)==len(set(ids)) and bool(ids),'unique seeded sample scope')
    scored=sorted(ids,key=lambda x:hashlib.sha256(f'{SEED}:{bank}:{x}'.encode()).digest())
    return sorted(scored[:math.ceil(len(ids)/4)])
