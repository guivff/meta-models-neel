"""E51: one CPU-only count using the pre-data frozen lexicons."""
import hashlib
import json
from pathlib import Path
import re
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
DATA = ROOT / 'cache/g_agreement/understand/e51/targets_v1'
OUT = HERE / 'count_20261027'
FREEZE = 'LEXICON_FREEZE.amended1.20261026.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def dump(path, data):
    with Path(path).open('x') as f:
        f.write(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n')


def bullets(text):
    """Literal backslash-n and actual newlines both delimit bullet starts."""
    starts = list(re.finditer(r'(?:^|\n|\\n)[ \t]*-[ \t]+', text))
    for i, marker in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        value = text[marker.end():end].strip()
        value = re.sub(r'(?:\s*<\|[^<>]*\|>)+\s*$', '', value).strip()
        # A marked empty bullet still belongs to the denominator.
        yield value


def compile_forms(forms):
    return re.compile(r'(?<!\w)(?:' + '|'.join(
        r'\s+'.join(re.escape(part) for part in form.casefold().split())
        for form in sorted(forms, key=lambda s: (-len(s), s))) + r')(?!\w)')


def count(stream, lexicons, excluded):
    patterns = {category: {family: compile_forms(forms) for family, forms in groups.items()}
                for category, groups in lexicons.items()}
    families = {category: {family: 0 for family in groups} for category, groups in patterns.items()}
    totals = dict.fromkeys(patterns, 0)
    sensitivity = n = 0
    for bullet in stream:
        n += 1
        folded = bullet.casefold()
        for category, groups in patterns.items():
            matched = {family for family, pattern in groups.items() if pattern.search(folded)}
            totals[category] += bool(matched)
            for family in matched:
                families[category][family] += 1
            if category == 'structure':
                sensitivity += bool(matched - set(excluded))
    if not n:
        raise ValueError('No target bullets; R1 not evaluable')
    rates = {category: 10000 * hits / n for category, hits in totals.items()}
    # Integer comparisons implement the exact strict and inclusive boundaries.
    return {'target_bullets': n, 'matching_bullets': totals, 'per_10000_bullets': rates,
            'family_matching_bullets': families,
            'structure_without_ambiguous': {'matching_bullets': sensitivity,
                'per_10000_bullets': 10000 * sensitivity / n, 'excluded_families': excluded},
            'R1': {'uses': 'full lexicons', 'met': totals['structure'] * 10000 < n
                   and totals['content'] * 10000 >= 100 * n}}


def verify():
    seal = read(HERE / 'COUNT_CODE_SEAL.20261027.json')
    for name, digest in seal['files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Count source or frozen input mismatch')
    for name, digest in read(HERE / FREEZE)['files'].items():
        if sha(ROOT / name) != digest:
            raise ValueError('Amended lexicon freeze mismatch')
    plan = read(HERE / 'COUNT_PLAN.20261027.json')
    if plan['bullet_extraction_approved'] is not True:
        raise ValueError('Bullet extraction is awaiting coordinator approval')
    for name, digest in plan['data_files'].items():
        if sha(DATA / name) != digest:
            raise ValueError('Verified target delivery mismatch')
    return plan


def main():
    plan = verify()
    dump(HERE / 'COUNT.RUN_ONCE.json', {'experiment': 'E51', 'started_epoch': time.time(),
        'code_seal_sha256': sha(HERE / 'COUNT_CODE_SEAL.20261027.json')})
    OUT.mkdir(exist_ok=False)
    try:
        rows = [json.loads(line) for line in (DATA / 's3d_b3_train_targets.jsonl').read_text().splitlines()]
        run = read(DATA / 'run.s3d.omp4bp.s2.step251.json')['config']
        if (len(rows) != 14773 or run['n_train_rows'] != 14773
                or run['run_name'] != 'ao.iolens.ptag.s3d.omp4bp.s2'
                or len({(r['shard'], r['i']) for r in rows}) != len(rows)
                or any(r['split'] != 'train' or not isinstance(r['target_text'], str) for r in rows)):
            raise ValueError('Exact complete training-target population required')
        lexicons = {k: read(HERE / ('LEXICON.' + k + '.20261026.json'))['forms_by_family']
                    for k in ('structure', 'content', 'passage_position')}
        excluded = read(HERE / 'MATCHING_CONTRACT.amended1.20261026.json')['sensitivity']['excluded_structure_families']
        result = count((b for r in rows for b in bullets(r['target_text'])), lexicons, excluded)
        result.update(experiment='E51', status='COMPLETE', training_rows=len(rows),
            rows_without_bullet_marker=sum(not list(bullets(r['target_text'])) for r in rows),
            freeze_sha256=sha(HERE / FREEZE), code_seal_sha256=sha(HERE / 'COUNT_CODE_SEAL.20261027.json'),
            input_files=plan['data_files'], eval_targets_used=False, deduplicated=False,
            gpu_seconds=0, analysis_invocations=1)
        dump(OUT / 'RESULTS.json', result)
        verdict = 'HOLDS' if result['R1']['met'] else 'DOES NOT HOLD'
        lines = ['# E51 — registered naming count', '', 'R1 ' + verdict + ' (full lexicons).', '',
                 f"Training rows: {len(rows):,}; target bullets: {result['target_bullets']:,}.", '',
                 '| Lexicon | Matching bullets | Per 10,000 target bullets |', '|---|---:|---:|']
        for k in ('structure', 'content', 'passage_position'):
            lines.append(f"| {k} | {result['matching_bullets'][k]} | {result['per_10000_bullets'][k]:.6f} |")
        s = result['structure_without_ambiguous']
        lines += [f"| structure, eight ambiguous families removed | {s['matching_bullets']} | {s['per_10000_bullets']:.6f} |", '',
                  'The sensitivity uses the same full bullet denominator. This is an enumerated English lexical audit; multilingual and implicit naming are not inferred.', '',
                  'Teacher-target naming rates describe this delivered training population; they do not by themselves establish the cause of the policy gap.', '']
        (OUT / 'RESULTS.md').write_text('\n'.join(lines))
        dump(OUT / 'ANALYSIS_SEAL.json', {'experiment': 'E51', 'status': 'COMPLETE',
             'files': {name: sha(OUT / name) for name in ('RESULTS.json', 'RESULTS.md')},
             'code_seal_sha256': result['code_seal_sha256']})
    except Exception as exc:
        dump(OUT / 'FAILURE.json', {'status': 'STOPPED', 'error_type': type(exc).__name__, 'guard_preserved': True})
        raise


if __name__ == '__main__':
    main()
