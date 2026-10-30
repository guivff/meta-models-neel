"""E58b custody, hashes and fixed paths; standard-library only."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
CACHE = ROOT / 'cache/g_agreement/understand/e58b'
ARMS = ('none', 'J', 'random0', 'random1', 'random2', 'random3', 'random4', 'PCA')
SEEDS = tuple(20261027 + i for i in range(5))
CONTROLS = ('rhyme_plan', 'antonym_crosslingual', 'two_hop_answer')
SHALLOW = ('fact_recall', 'sentiment_judgement')
BLOCK = 44
RANK = 384
DIM = 5120
CAP = 2700
MAX_CAP = 5400  # User-authorized conditional extension after the batch-8 NO_FIT.
RESERVE = 180
PROGRAMME_STOP = 1793314740  # 2026-10-29 22:59:00 UTC, programme amendment.
TARGET = 'Qwen/Qwen3.6-27B'
REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
J_SHA = 'a8f4b64c010aa2f3a72aac70e087ce5204d463c2bb93d1ebf3b22b21a0bdb4fb'


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, value):
    with Path(path).open('x') as f:
        f.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def seal(folder, name, **metadata):
    folder = Path(folder)
    files = {str(p.relative_to(folder)): sha(p) for p in sorted(folder.rglob('*'))
             if p.is_file() and p.name != name}
    dump(folder / name, {**metadata, 'files': files})


def verify(folder, seal_name):
    folder = Path(folder).resolve()
    record = read(folder / seal_name)
    for name, expected in record['files'].items():
        path = (folder / name).resolve()
        require(path.is_relative_to(folder) and sha(path) == expected, 'Sealed file mismatch')
    return record


def source_verify(seal_name='SOURCE_SEAL.20261027.json'):
    record = read(HERE / seal_name)
    for name, expected in record['files'].items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT.resolve()) and sha(path) == expected, 'Source pin mismatch')
    return record


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)
