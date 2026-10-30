"""E67 (§184) once-only reader-fidelity analysis. Integrator-owned; frozen before any E67 judgment is opened.

Inputs (all bound by sha256 in the spec): W-sae's private pairing map, the two sealed terminal judgment grids
(one per blind packet), and W-lens's sealed E58a categories. Outputs one exclusive directory, sealed.

Registered measures (§184), per reader: F = share of readouts with >= 1 CONTRADICTED claim, G = share GENERIC,
Sup = share with >= 1 SUPPORTED claim, each under matched and mismatched pairing, with item-bootstrap CIs.
R-F1: Sup(matched) - Sup(mismatched) >= 0.10 with bootstrap lower bound > 0 (paired by sampled readout).
R-F2: F(matched) with Wilson CI; MET iff F >= 0.20 and Wilson lower bound >= 0.10; predictions NLA F >= 0.20,
Oracle F <= 0.10 with G >= 0.40. R-F3 (descriptive): F and G by E58a category and the structure/content collapse;
E63 placebo comparison where available. UNPARSEABLE codes (clarification 2) are excluded and counted per cell,
flagged above 5%. E49/E54 NLA (the 128-token cohort) is reported apart from the NLA primary cohort.
"""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from common.stats import wilson, bootstrap_ci  # noqa: E402

SEED, DRAWS = 20261027, 2000
TRUNCATED = 'NLA_128_TOKEN_LIMIT_REPORTED_SEPARATELY'
STRUCTURE = {'bookkeeping', 'delimiter', 'format', 'syntactic'}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def require(ok, msg):
    if not ok:
        raise ValueError(msg)


def read(p):
    return json.loads(Path(p).read_text())


def verify_seal(seal_path, expected):
    seal_path = Path(seal_path)
    require(sha(seal_path) == expected, 'seal hash: ' + str(seal_path))
    s = read(seal_path)
    for name, digest in s['files'].items():
        require(sha(seal_path.parent / name) == digest, 'sealed member changed: ' + name)
    return s


def flags(code):
    verdicts = [c['verdict'] for c in code['claims']]
    return {'F': 'CONTRADICTED' in verdicts, 'Sup': 'SUPPORTED' in verdicts, 'G': bool(code['generic'])}


def load_codes(terminal_dir, seal_sha):
    s = verify_seal(Path(terminal_dir) / 'RESULT_SEAL.json', seal_sha)
    require(s.get('bank') == 'E67' and s.get('status') == 'TERMINAL_BLIND_GRID_NO_ANALYSIS', 'terminal E67 grid')
    out = {}
    for row in read(Path(terminal_dir) / 'JUDGMENTS.json'):
        require(row['id'] not in out, 'duplicate opaque id')
        if row['status'] == 'UNPARSEABLE':
            require(row['code'] is None, 'UNPARSEABLE sentinel')
            out[row['id']] = None
        else:
            require(row['status'] == 'KEPT' and row['code']['id'] == row['id'], 'kept code identity')
            require(row['code']['generic'] == (len(row['code']['claims']) == 0), 'GENERIC iff no claims')
            out[row['id']] = flags(row['code'])
    return out


def rate(values):
    """Share of True among kept units, with item-bootstrap 95% CI; None when nothing is kept."""
    xs = np.asarray([float(v) for v in values], dtype=float)
    if not len(xs):
        return {'n': 0, 'share': None, 'CI95': None}
    p, lo, hi = bootstrap_ci(xs, n_boot=DRAWS, seed=SEED)
    return {'n': int(len(xs)), 'k': int(xs.sum()), 'share': p, 'CI95': [lo, hi]}


def summarise(units):
    """units: list of dicts {matched: flags|None, mismatched: flags|None}. One unit = one sampled readout = one item."""
    out = {}
    for cond in ('matched', 'mismatched'):
        kept = [u[cond] for u in units if u[cond] is not None]
        out[cond] = {m: rate([k[m] for k in kept]) for m in ('F', 'G', 'Sup')}
        out[cond]['UNPARSEABLE'] = sum(u[cond] is None for u in units)
        out[cond]['total'] = len(units)
        out[cond]['over_5_percent'] = 20 * out[cond]['UNPARSEABLE'] > len(units)
    paired = [float(u['matched']['Sup']) - float(u['mismatched']['Sup'])
              for u in units if u['matched'] is not None and u['mismatched'] is not None]
    if paired:
        d, lo, hi = bootstrap_ci(np.asarray(paired), n_boot=DRAWS, seed=SEED)
        rf1 = {'Sup_matched_minus_mismatched': d, 'CI95': [lo, hi], 'paired_units': len(paired),
               'verdict': 'MET' if round(d, 12) >= 0.10 and lo > 0 else 'NOT MET'}
    else:
        rf1 = {'paired_units': 0, 'verdict': 'NOT EVALUABLE'}
    fm = [u['matched']['F'] for u in units if u['matched'] is not None]
    if fm:
        p, lo, hi = wilson(int(sum(fm)), len(fm))
        rf2 = {'F_matched': p, 'Wilson95': [lo, hi], 'n': len(fm),
               'verdict': 'MET' if round(p, 12) >= 0.20 and lo >= 0.10 else 'NOT MET'}
    else:
        rf2 = {'n': 0, 'verdict': 'NOT EVALUABLE'}
    out['R_F1'] = rf1
    out['R_F2'] = rf2
    return out


def analyse(spec):
    seal = verify_seal(spec['private_seal'], spec['private_seal_sha256'])
    require('PAIRING_CONDITION_MAP.PRIVATE.json' in seal['files'], 'sealed private pairing map')
    pairs = read(Path(spec['private_seal']).parent / 'PAIRING_CONDITION_MAP.PRIVATE.json')['pairs']
    codes = {}
    for packet, g in spec['terminal_grids'].items():
        codes[int(packet)] = load_codes(g['dir'], g['result_seal_sha256'])
    require(sha(spec['categories']) == spec['categories_sha256'], 'E58a categories pin')
    cats = {(r['bank'], r['row']): r['category'] for r in read(spec['categories'])['rows']}
    units, seen = [], set()
    for p in pairs:
        by = {r['condition']: r for r in p['records']}
        require(set(by) == {'matched', 'mismatched'} and by['matched']['packet'] != by['mismatched']['packet'],
                'one matched and one mismatched record in opposite packets')
        u = {'bank': p['bank'], 'reader': p['reader'], 'row': p['row'], 'arm': p.get('arm'),
             'cohort': p['truncation_cohort'], 'category': cats.get(('E49' if p['bank'] == 'E49' else p['bank'], p['row']))}
        for cond, r in by.items():
            require(r['id'] not in seen and r['id'] in codes[int(r['packet'])], 'complete unique judgment grid')
            seen.add(r['id'])
            u[cond] = codes[int(r['packet'])][r['id']]
        units.append(u)
    require(seen == {i for c in codes.values() for i in c}, 'every judged id joins the private map exactly once')
    result = {'experiment': 'E67', 'wave': spec['wave'], 'banks': sorted({u['bank'] for u in units}),
              'bootstrap': {'draws': DRAWS, 'seed': SEED, 'unit': 'sampled readout (one per item)'},
              'readers': {}, 'by_bank_reader': {}, 'R_F3': {}}
    for reader in ('oracle', 'nla'):
        mine = [u for u in units if u['reader'] == reader]
        primary = [u for u in mine if u['cohort'] != TRUNCATED]
        block = {'primary_cohort': summarise(primary), 'primary_banks': sorted({u['bank'] for u in primary})}
        trunc = [u for u in mine if u['cohort'] == TRUNCATED]
        if trunc:
            block['NLA_128_token_cohort_reported_apart'] = summarise(trunc)
            block['NLA_128_token_cohort_banks'] = sorted({u['bank'] for u in trunc})
        s = block['primary_cohort']
        if reader == 'nla':
            f = s['R_F2'].get('F_matched')
            block['prediction'] = {'registered': 'F(matched) >= 0.20', 'holds': None if f is None else f >= 0.20}
        else:
            f, g = s['R_F2'].get('F_matched'), s['matched']['G']['share']
            block['prediction'] = {'registered': 'F(matched) <= 0.10 with G >= 0.40',
                                   'holds': None if f is None or g is None else (f <= 0.10 and g >= 0.40)}
        result['readers'][reader] = block
        for bank in sorted({u['bank'] for u in mine}):
            result['by_bank_reader'][bank + '|' + reader] = summarise([u for u in mine if u['bank'] == bank])
        for label, test in (('structure', lambda c: c in STRUCTURE), ('content', lambda c: c == 'content'),
                            ('uncategorised', lambda c: c is None)):
            group = [u for u in primary if test(u['category'])]
            if group:
                result['R_F3'][reader + '|' + label] = {k: summarise(group)[k] for k in ('matched', 'mismatched')}
        for cat in sorted({u['category'] for u in primary if u['category']}):
            result['R_F3'][reader + '|E58a:' + cat] = {k: summarise([u for u in primary if u['category'] == cat])[k]
                                                         for k in ('matched', 'mismatched')}
    result['R_F3']['E63_placebo'] = spec.get('e63_placebo_status', 'NOT AVAILABLE in this wave')
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--spec', type=Path, required=True)
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    frozen = read(here / 'SOURCE_SEAL.json')
    for name, digest in frozen['files'].items():
        require(sha(here / name) == digest, 'E67 analysis source changed: ' + name)
    spec = read(a.spec)
    out = Path(spec['out'])
    out.mkdir(parents=True, exist_ok=False)  # once-only: an existing directory, even from a failure, blocks a rerun
    (out / 'ONCE.json').write_text(json.dumps({'experiment': 'E67', 'spec_sha256': sha(a.spec)}) + '\n')
    try:
        result = analyse(spec)
        (out / 'RESULTS.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
        files = {p.name: sha(p) for p in sorted(out.iterdir()) if p.is_file()}
        (out / 'ANALYSIS_SEAL.json').write_text(json.dumps({'experiment': 'E67', 'status': 'COMPLETE_ONCE',
            'source_seal_sha256': sha(here / 'SOURCE_SEAL.json'), 'spec_sha256': sha(a.spec), 'files': files},
            indent=2, sort_keys=True) + '\n')
    except BaseException as error:
        (out / 'FAILURE.json').write_text(json.dumps({'error': str(error)}) + '\n')
        raise


if __name__ == '__main__':
    main()
