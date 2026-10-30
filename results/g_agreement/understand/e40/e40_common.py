"""E40 source boundaries; 2026-10-26. No compute at import."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
E35 = HERE.parent / 'e35'
if str(E35) not in sys.path:
    sys.path.insert(0, str(E35))
from gate_inputs import sha, dump_new, canonical, read_corpus, is_heldout, TOKENIZER_SHA
import json

def read(path):
    return json.loads(Path(path).read_text())

def verify_files(folder, seal_name='OUTPUT_SEAL.json', arrays=None):
    folder = Path(folder).resolve()
    seal = read(folder / seal_name)
    for name, expected in seal['files'].items():
        path = folder / name
        if not path.is_file() and arrays is not None:
            path = Path(arrays).resolve() / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError('sealed output missing or checksum mismatch: ' + name)
    return seal
