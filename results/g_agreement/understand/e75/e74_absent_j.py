"""Write E74's absent-J/category record once, from committed plans and sealed captures."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
RECORD = 'R-G2 NOT EVALUABLE; J-lens unavailable'
CATEGORIES = {'content', 'plan', 'bookkeeping', 'delimiter', 'syntactic', 'format'}
ORDINAL_EXCLUSIONS = {'W1/python_depth_ordinal', 'W1/table_column_ordinal'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def when(value):
    t = datetime.fromisoformat(value.replace('Z', '+00:00'))
    require(t.tzinfo is not None, 'timezone required')
    return t


def local_ref(ref):
    p = Path(ref['path'])
    require(p.is_absolute(), 'absolute evidence path required')
    raw = p.read_bytes()
    require(digest(raw) == ref['sha256'], 'evidence hash mismatch')
    return json.loads(raw)


def git_ref(ref):
    repo = Path(ref['repo']).resolve()
    path = Path(ref['path'])
    require(not path.is_absolute() and '..' not in path.parts, 'repository-relative committed path required')
    commit = ref['commit']
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'full immutable commit required')
    raw = subprocess.check_output(['git', 'show', commit + ':' + str(path)], cwd=repo)
    require(digest(raw) == ref['sha256'], 'committed evidence hash mismatch')
    at = subprocess.check_output(['git', 'show', '-s', '--format=%cI', commit], cwd=repo, text=True).strip()
    return raw, when(at)


def member(seal_ref, seal, name):
    rel = Path(name)
    require(not rel.is_absolute() and '..' not in rel.parts, 'safe sealed member path required')
    p = Path(seal_ref['path']).parent / rel
    raw = p.read_bytes()
    require(digest(raw) == seal['files'][name], 'sealed member hash mismatch')
    return raw


def build(plan, now):
    require(now.tzinfo is not None, 'timezone required')
    require(plan['experiment'] == 'E74', 'E74 binding required')
    capture = local_ref(plan['capture_seal'])
    inputs = local_ref(plan['input_seal'])
    require(capture['track'] == 'G', 'GLM Track G capture required')
    require(capture['input_seal_sha256'] == plan['input_seal']['sha256'], 'capture/input binding differs')
    captured = when(capture['sealed_at'])
    require(captured <= now, 'capture lies in the future')
    require(bool(capture['files']), 'capture payload inventory required')
    for name in capture['files']:
        member(plan['capture_seal'], capture, name)
    input_rows = json.loads(member(plan['input_seal'], inputs, plan['input_rows_member']))['rows']
    captured_units = [r['row'] for r in input_rows]
    require(bool(captured_units) and all(isinstance(x, str) and x for x in captured_units)
            and len(captured_units) == len(set(captured_units)), 'complete unique GLM unit ids required')
    excluded = sorted(set(captured_units) & ORDINAL_EXCLUSIONS)
    expected = sorted(set(captured_units) - ORDINAL_EXCLUSIONS)
    require(bool(expected), 'at least one eligible binary GLM unit required')
    category_raw, category_at = git_ref(plan['category_binding'])
    categories = json.loads(category_raw)['rows']
    require(category_at <= captured, 'categories must be frozen before capture')
    require(len(categories) == len(expected) and len({r['row'] for r in categories}) == len(expected)
            and {r['row'] for r in categories} == set(expected), 'category coverage differs from input units')
    require(all(r['category'] in CATEGORIES for r in categories), 'unknown frozen E58a category')
    verdict_raw, verdict_at = git_ref(plan['asset_verdict'])
    verdict = json.loads(verdict_raw)
    require(verdict['verdict'] == 'FEASIBLE' and verdict['j_lens_available'] is False,
            'feasible GLM absent-J verdict required')
    source = dict(verdict['source_card'])
    source['repo'] = str((Path(plan['asset_verdict']['repo']) / source['repo']).resolve())
    _, asset_at = git_ref(source)
    require(asset_at <= captured and verdict_at <= captured, 'asset evidence must precede capture')
    custody = local_ref(plan['custody_availability_receipt'])
    require(custody['issuer'] == 'I-2', 'I-2 custody receipt required')
    require(custody['capture_seal_sha256'] == plan['capture_seal']['sha256']
            and custody['asset_card_sha256'] == source['sha256'], 'custody evidence binding differs')
    require(captured <= when(custody['checked_at']) <= now, 'availability/custody check must follow capture')
    require(custody['j_lens_public'] is False and custody['go_issued'] is False
            and custody['reader_outputs_accessed'] is False
            and custody['readers_held_until_record_commit'] is True,
            'absent public J, no GO, and unopened held readers required')
    return {'experiment': 'E74', 'track': 'G', 'worker': 'W-lens', 'record': RECORD,
            'created_at': now.isoformat(), 'capture_seal_sha256': plan['capture_seal']['sha256'],
            'input_seal_sha256': plan['input_seal']['sha256'], 'asset_card_sha256': source['sha256'],
            'asset_verdict': plan['asset_verdict'], 'asset_card': source,
            'category_binding': plan['category_binding'],
            'custody_availability_receipt': plan['custody_availability_receipt'],
            'reader_outputs_accessed': False, 'rg2_not_evaluable_permanent': True,
            'captured_units': sorted(captured_units),
            'confirmatory_exclusions': [{'row': row, 'capture_retained': True,
                'reason': 'Original ordinal row; no registered binary or ordinal confirmatory criterion',
                'labels_and_splits': 'PRESERVED_NO_BINARISATION'} for row in excluded],
            'later_J_forecast_role': 'EXPLORATORY_ONLY_NEVER_RESTORE_R_G2',
            'category_forecast': [{'row': r['row'], 'category': r['category'],
                'prediction': 'REPORTED' if r['category'] in ('content', 'plan') else 'MISSED'}
                for r in sorted(categories, key=lambda r: r['row'])],
            'J_forecast': None, 'J_null_median': None, 'J_null_percentile975': None,
            'missing_J_policy': 'Missing, never zero; category baseline only, no paired J performance claim',
            'authority': '§192 clarification2 451e2f4d and Guiv explicit pre-GO absent-J/category ruling'}


def publish(record, output, claim):
    require(not output.exists(), 'record already exists; never overwrite')
    claim.parent.mkdir(parents=True, exist_ok=True)
    with claim.open('x') as f:
        json.dump({'status': 'CLAIMED_NEVER_RESET', 'capture_seal_sha256': record['capture_seal_sha256'],
                   'created_at': record['created_at']}, f)
    with output.open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('committed_plan', type=Path)
    args = parser.parse_args()
    # Deliberately no discovery, downloads, fabricated defaults, or optional partial pools.
    seal = json.loads((HERE / 'E74_ABSENT_J_CODE_SEAL.json').read_text())
    for path, expected in seal['files'].items():
        require(digest((ROOT / path).read_bytes()) == expected, 'writer code/contract seal changed')
    planpath = args.committed_plan.resolve()
    relative = planpath.relative_to(ROOT)
    raw = planpath.read_bytes()
    require(subprocess.check_output(['git', 'show', 'HEAD:' + str(relative)], cwd=ROOT) == raw,
            'input binding plan must be committed before record creation')
    record = build(json.loads(raw), datetime.now(timezone.utc))
    record['plan_sha256'] = digest(raw)
    record['writer_code_seal_sha256'] = digest((HERE / 'E74_ABSENT_J_CODE_SEAL.json').read_bytes())
    output = HERE / 'E74_PREGO_RECORD.json'
    claim = ROOT / 'cache/g_agreement/understand/e74/E74_PREGO_RECORD_ONCE.json'
    publish(record, output, claim)
    print('E74 absent-J and category-only record written once; MUST commit before I-2 GO')


if __name__ == '__main__':
    main()
