"""Descriptive sealed-code census only; no model, judging, bootstrap or verdict calls."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROWS = ('nesting_depth', 'indent_level', 'page_range_digit', 'format_plan',
        'fact_recall', 'tense_implicit', 'language_plan')
CATEGORIES = ('correct-only', 'wrong-only', 'both', 'property-only', 'exhibits', 'silent', 'missing')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def read(p):
    return json.loads(Path(p).read_text())

def verify(p, expected):
    p = Path(p)
    assert sha(p) == expected, 'seal hash'
    seal = read(p)
    for name, digest in seal['files'].items():
        member = (p.parent / name).resolve()
        assert member.is_relative_to(p.parent.resolve())
        assert sha(member) == (digest['sha256'] if isinstance(digest, dict) else digest), name
    return seal

def category(code, target):
    assert target in ('A', 'B')
    cat, values = code['category'], code['values']
    if cat == 'UNPARSEABLE':
        assert values == [] and code['evidence'] == ''
        return 'missing'
    if cat == 'states_value':
        assert values in (['A'], ['B'], ['A', 'B'], ['B', 'A'])
        return 'both' if len(values) == 2 else 'correct-only' if target in values else 'wrong-only'
    assert values == []
    return {'names_property_without_value': 'property-only', 'exhibits': 'exhibits', 'silent': 'silent'}[cat]

def unique(rows, key):
    result = {r[key]: r for r in rows}
    assert len(result) == len(rows)
    return result

def main(spec_path, original_path, destination):
    root = Path(__file__).resolve().parents[3]
    for p in Path(__file__).parent.glob('*.py'):
        assert subprocess.check_output(['git', 'show', 'HEAD:' + str(p.relative_to(root))], cwd=root) == p.read_bytes()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    s = read(spec_path)
    original = Path(original_path)
    # Published original seal is the trust anchor, not a fresh self-hash.
    expected = '76b156f055567cb168b2cfd40ec6bcc65aa21d2aa18fd1d97d533ad5fa86d2d1'
    original_hash = sha(original)
    assert original_hash == expected
    seal = verify(original, original_hash)
    assert seal['status'] == 'COMPLETE_ONCE' and seal['experiment'] == 'E100'
    js = Path(s['judgments']) / 'JUDGMENT_SEAL.json'
    judgment = verify(js, seal['judgment_sha256'])
    bp = Path(s['blind']) / 'BLIND_SEAL.json'
    blind = verify(bp, judgment['blind_seal_sha256'])
    assert judgment['route_verified'] and judgment['redaction_audit_complete']
    assert blind['output_seal_sha256'] == seal['output_seal_sha256']
    assert sha(s['private']) == blind['private_sha256']
    ts = Path(s['targets_seal'])
    verify(ts, seal['targets_sha256'])
    targets = unique(read(ts.parent / 'TARGETS.json'), 'id')
    joins = unique(read(s['private']), 'opaque_id')
    codes = unique(read(js.parent / 'JUDGMENTS.json'), 'id')
    assert set(joins) == set(codes) and len(joins) == 6720
    saved = read(original.parent / 'RESULTS.json')
    result = {}
    for row in ROWS:
        selected = [x for x in joins.values() if x['row'] == row and x['reader'] == 'oracle' and x['condition'] == 'transplant']
        assert len(selected) == 84 and len({x['item_id'] for x in selected}) == 84
        assert {x['item_id'] for x in selected} == {t['id'] for t in targets.values() if t['row'] == row}
        counts = dict.fromkeys(CATEGORIES, 0)
        for x in selected:
            t = targets[x['item_id']]
            assert x['target'] == t['target'] and x['values'] == t['values'] and x['row'] == t['row']
            assert x['id'] == x['item_id'] + ':oracle:transplant'
            counts[category(codes[x['opaque_id']], t['target'])] += 1
        assert sum(counts.values()) == 84
        observed_s = (counts['correct-only'] - counts['wrong-only']) / (84 - counts['missing'])
        assert abs(observed_s - saved['rows'][row]['oracle']['transplant']['estimate']) < 1e-12
        result[row] = dict(counts, total=84, saved_S=observed_s)
    out = Path(destination)
    out.mkdir(parents=True, exist_ok=False)
    payload = dict(description='Descriptive only; original verdicts unchanged', source_commit=commit,
                   original_analysis_seal_sha256=original_hash, judgment_seal_sha256=seal['judgment_sha256'],
                   blind_seal_sha256=judgment['blind_seal_sha256'], targets_seal_sha256=seal['targets_sha256'], rows=result)
    (out / 'COUNTS.json').write_text(json.dumps(payload, indent=2) + '\n')
    lines = ['# E100 Oracle transplant — descriptive category counts', '',
             'Already-sealed E100 codes only. No new judging, bootstrap, primary analysis or verdict change. Each row totals 84.', '',
             'Correct/wrong use the original registered donor-target A/B label. Both means both incompatible values were stated; property-only names the property without a value; exhibits enacts it without stating it; silent is the original silent rubric code; missing is UNPARSEABLE. Categories are mutually exclusive under the original rubric priority.', '',
             '| Row | Correct-only | Wrong-only | Both | Property-only | Exhibits | Silent | Missing | Total | Saved S |',
             '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row, c in result.items():
        lines.append('| ' + row + ' | ' + ' | '.join(str(c[k]) for k in CATEGORIES) + f" | 84 | {c['saved_S']:.6f} |")
    lines += ['', 'S = (correct-only − wrong-only) / (84 − missing); all other observed categories contribute zero. This identity matches the saved transplant estimate in every row. The seven requested rows are shown; language_continuation is outside this request.', '',
              'Post hoc descriptive census requested after the original result was sealed. R-Q independent review requested; pending.', '',
              'Original analysis seal: `' + original_hash + '`. Judgment seal: `' + seal['judgment_sha256'] + '`. Source commit: `' + commit + '`.']
    (out / 'REPORT.md').write_text('\n'.join(lines) + '\n')
    (out / 'DESCRIPTIVE_SEAL.json').write_text(json.dumps(dict(kind='descriptive sealed-code census', files={p.name: sha(p) for p in out.iterdir()}), indent=2) + '\n')

if __name__ == '__main__':
    main(*sys.argv[1:])
