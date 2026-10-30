"""Public-only execution contract for sections 198/199; CPU keys never enter it."""
import hashlib
import json
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
EXPERIMENTS = {'E81', 'E82', 'E83', 'E85', 'E86', 'E91', 'E92'}

def require(ok, message):
    if not ok:
        raise ValueError(message)

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def write(path, value, replace=False):
    path = Path(path)
    if replace:
        tmp = path.with_suffix(path.suffix + '.tmp')
        tmp.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')
        tmp.replace(path)
    else:
        with path.open('x') as f:
            json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
            f.write('\n')

def seal(root, name, **metadata):
    root = Path(root)
    files = {str(p.relative_to(root)): sha(p) for p in sorted(root.rglob('*'))
             if p.is_file() and p.name != name and '__pycache__' not in p.parts}
    write(root / name, dict(metadata, files=files))
    return sha(root / name)

def verify(root, name, digest):
    root = Path(root).resolve()
    require(sha(root / name) == digest, 'seal identity: ' + name)
    s = read(root / name)
    for name, expected in s['files'].items():
        p = root / name
        require(p.resolve().is_relative_to(root), 'unsafe sealed path')
        require(sha(p) == expected, 'sealed file changed: ' + name)
    return s

def digest(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None

def validate_items(items, metadata=True):
    fields = {'id', 'text', 'ids', 'read_index'}
    if metadata:
        fields |= {'feature', 'arm', 'split'}
    require(len({x['id'] for x in items}) == len(items), 'duplicate item IDs')
    for x in items:
        require(set(x) == fields, 'strict public item allowlist')
        require(isinstance(x['id'], str) and x['id'], 'item ID')
        require(isinstance(x['text'], str) and x['ids'] and all(type(t) is int and t >= 0 for t in x['ids']), 'tokens')
        require(type(x['read_index']) is int and x['read_index'] == len(x['ids']) - 1, 'frozen final read token')
        if metadata:
            require(x['split'] in ('dev', 'test'), 'frozen split')

def validate_plan(plan, items, scores, downstream):
    require(set(plan) == {'experiment', 'seed', 'bank_seal_sha256', 'item_ids', 'score_ids',
                         'downstream_ids', 'forecast_required', 'owner_contract_sha256'}, 'public plan allowlist')
    exp = plan['experiment']
    require(exp in EXPERIMENTS and type(plan['seed']) is int, 'experiment/seed')
    require(digest(plan['bank_seal_sha256']) and digest(plan['owner_contract_sha256']), 'owner seals required')
    require(type(plan['forecast_required']) is bool, 'forecast requirement explicit')
    validate_items(items)
    validate_items(scores, False)
    validate_items(downstream, False)
    for key, values in [('item_ids', items), ('score_ids', scores), ('downstream_ids', downstream)]:
        require(plan[key] == [x['id'] for x in values], 'frozen ordered ' + key)
    require(bool(scores) == (exp in ('E82', 'E86')), 'behaviour gate occurs first')
    require(bool(downstream) == (exp == 'E85'), 'fixed E85 downstream question')
    if exp == 'E81':
        require({x['arm'] for x in items} == {'describe', 'oracle_wording'}, 'both E81 instruction arms')
    if exp == 'E83':
        require(all(x['split'] == 'test' for x in items), 'E83 test only')
    if exp == 'E86':
        require({x['arm'] for x in items} == {'honest', 'lie', 'role'}, 'three E86 arms')
    return exp

def deadline(assignment, limits, now):
    a = assignment
    require(a['experiment'] == limits['experiment'] and a['gpu_count'] == 1, 'assignment identity')
    numbers = [a[k] for k in ('cap_seconds', 'prior_seconds', 'pod_created_epoch', 'custody_start_epoch', 'absolute_deadline_epoch')]
    require(all(type(x) in (float, int) and math.isfinite(x) for x in numbers), 'finite custody')
    require(0 < a['cap_seconds'] <= limits['cap_seconds'] and a['prior_seconds'] >= 0
            and a['prior_seconds'] + a['cap_seconds'] <= limits['cumulative_cap_seconds'], 'request cap')
    require(a['pod_created_epoch'] <= a['custody_start_epoch'] <= now
            and a['absolute_deadline_epoch'] == a['custody_start_epoch'] + a['cap_seconds'], 'fixed custody clock')
    require(a['daily_budget_verified'] is True and 0 <= a['projected_daily_USD'] <= limits['account_gate_USD'], 'account gate')
    return a['absolute_deadline_epoch']

def check_release(release, ready, allowed, now, forecast_required=False, probe=False):
    fields = {'experiment', 'pod_id', 'source_seal_sha256', 'input_seal_sha256', 'stage_seal_sha256',
              'released_ids', 'issued_epoch', 'authorized', 'cpu_receipt_sha256'}
    if forecast_required:
        fields |= {'forecast_commit', 'forecast_seal_sha256'}
    if probe:
        fields |= {'probe_seal_sha256'}
    require(set(release) == fields, 'public release allowlist: no labels or targets')
    for key in ('experiment', 'pod_id', 'source_seal_sha256', 'input_seal_sha256', 'stage_seal_sha256'):
        require(release[key] == ready[key], 'release binding: ' + key)
    require(release['authorized'] is True and ready['ready_epoch'] <= release['issued_epoch'] <= now, 'post-stage authorization')
    ids = release['released_ids']
    require(len(set(ids)) == len(ids) and set(ids) <= set(allowed), 'release subset')
    require(ids == [x for x in allowed if x in set(ids)], 'release preserves frozen order')
    require(digest(release['cpu_receipt_sha256']), 'CPU decision receipt required')
    if probe:
        require(digest(release['probe_seal_sha256']), 'CPU dev-only probe seal required')
    if forecast_required:
        require(re.fullmatch('[0-9a-f]{40}', release['forecast_commit']) and digest(release['forecast_seal_sha256']), 'prospective forecast required')
    return ids
