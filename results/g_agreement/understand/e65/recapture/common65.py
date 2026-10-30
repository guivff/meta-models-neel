"""E65 label-free recapture paths, custody and schemas; standard library only."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CACHE = ROOT / 'cache/g_agreement/understand/e65/recapture'
CAP = 1080
RESERVE = 180
SETUP_MAX = 360
STOP = 1793314740
DIM = 5120
BLOCK = 44
TARGET = 'Qwen/Qwen3.6-27B'
REVISION = '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOKENIZER_SHA = '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
BANKS = ('W1', 'E36', 'W12', 'E49', 'E56', 'E57', 'E59')


def require(ok, message):
    if not ok: raise ValueError(message)


def read(p): return json.loads(Path(p).read_text())


def dump(p, value):
    with Path(p).open('x') as f:
        f.write(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''): h.update(chunk)
    return h.hexdigest()


def verify_files(base, record):
    base = Path(base).resolve()
    for name, expected in record['files'].items():
        p = (base / name).resolve()
        require(p.is_relative_to(base) and not (base / name).is_symlink() and sha(p) == expected, 'Sealed file mismatch')


def source_verify():
    verify_files(ROOT, read(HERE / 'POD_SOURCE_SEAL.json'))


def validate_bank(bank):
    require(set(bank) == {'experiment', 'schema', 'rows'} and bank['experiment'] == 'E65'
            and bank['schema'] == 'E65_BLIND_RECAPTURE_V1', 'Exact recapture schema required')
    require(isinstance(bank['rows'], list) and bank['rows'], 'Nonempty row catalog required')
    keys, identities, end = set(), set(), 0
    for row in bank['rows']:
        require(set(row) == {'key', 'items'} and row['key'] not in keys, 'Unique blind row required')
        require(isinstance(row['key'], str) and len(row['key']) == 32
                and all(c in '0123456789abcdef' for c in row['key']), 'Opaque row ID required')
        keys.add(row['key']); require(len(row['items']) == 20, 'Exactly20 selected items per row required')
        for item in row['items']:
            require(set(item) == {'id', 'ids', 'start', 'stop', 'offset'}, 'Unexpected pod item fields')
            require(isinstance(item['id'], str) and len(item['id']) == 32
                    and all(c in '0123456789abcdef' for c in item['id']) and item['id'] not in identities,
                    'Unique opaque item ID required')
            identities.add(item['id'])
            require(isinstance(item['ids'], list) and item['ids']
                    and all(type(t) is int and t >= 0 for t in item['ids']), 'Frozen nonnegative prompt IDs required')
            require(all(type(item[k]) is int for k in ('start', 'stop', 'offset'))
                    and 0 <= item['start'] < item['stop'] == len(item['ids']) and item['offset'] == end,
                    'Contiguous capture offsets and final read token required')
            end += item['stop'] - item['start']
    return [x for row in bank['rows'] for x in row['items']], end


def load_inputs():
    folder = CACHE / 'pod_inputs'
    require({str(p.relative_to(folder)) for p in folder.rglob('*') if p.is_file()} == {'BANK.json', 'INPUT_SEAL.json'}
            and not any(p.is_symlink() for p in folder.rglob('*')), 'Exact pod data file whitelist required')
    record = read(folder / 'INPUT_SEAL.json')
    require(set(record) == {'experiment', 'schema', 'files'} and record['experiment'] == 'E65'
            and record['schema'] == 'E65_INPUT_SEAL_V1' and set(record['files']) == {'BANK.json'}, 'Exact input seal required')
    verify_files(folder, record)
    bank = read(folder / 'BANK.json'); items, positions = validate_bank(bank)
    return bank, items, positions


def batches(items, size): return [items[i:i + size] for i in range(0, len(items), size)]
