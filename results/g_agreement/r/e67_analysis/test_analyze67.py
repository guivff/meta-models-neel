"""Synthetic tests for the frozen E67 analysis. No real judgment, map or readout is touched."""
import hashlib, json
from pathlib import Path
import pytest
import analyze67 as A


def _seal(d, name, extra):
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(d).iterdir()) if p.is_file() and p.name != name}
    (Path(d) / name).write_text(json.dumps(dict(extra, files=files)))
    return hashlib.sha256((Path(d) / name).read_bytes()).hexdigest()


def _build(tmp, codes_by_id, pairs):
    priv = tmp / 'priv'; priv.mkdir()
    (priv / 'PAIRING_CONDITION_MAP.PRIVATE.json').write_text(json.dumps({'pairs': pairs}))
    ps = _seal(priv, 'INTEGRATOR_SEAL.json', {})
    grids = {}
    for packet in (1, 2):
        g = tmp / f'g{packet}'; g.mkdir()
        rows = [codes_by_id[r['id']] for p in pairs for r in p['records'] if r['packet'] == packet]
        (g / 'JUDGMENTS.json').write_text(json.dumps(rows))
        grids[str(packet)] = {'dir': str(g), 'result_seal_sha256': _seal(g, 'RESULT_SEAL.json', {'bank': 'E67', 'status': 'TERMINAL_BLIND_GRID_NO_ANALYSIS'})}
    cats = tmp / 'cats.json'; cats.write_text(json.dumps({'rows': [{'bank': 'E49', 'row': 'r', 'category': 'bookkeeping'}]}))
    return {'wave': 'test', 'private_seal': str(priv / 'INTEGRATOR_SEAL.json'), 'private_seal_sha256': ps,
            'terminal_grids': grids, 'categories': str(cats), 'categories_sha256': hashlib.sha256(cats.read_bytes()).hexdigest(),
            'out': str(tmp / 'out')}


def _code(i, verdicts):
    return {'id': i, 'status': 'KEPT', 'attempts': 0,
            'code': {'id': i, 'claims': [{'claim': 'c', 'verdict': v} for v in verdicts], 'generic': not verdicts}}


def _pairs(n, reader='oracle', bank='E49', cohort='NOT_THE_128_TOKEN_NLA_COHORT'):
    return [{'bank': bank, 'reader': reader, 'row': 'r', 'truncation_cohort': cohort, 'records': [
        {'condition': 'matched', 'id': f'{reader}{k}m', 'packet': 1 + k % 2},
        {'condition': 'mismatched', 'id': f'{reader}{k}x', 'packet': 2 - k % 2}]} for k in range(n)]


def test_rates_rules_and_pairing(tmp_path):
    pairs = _pairs(40) + _pairs(40, reader='nla')
    codes = {}
    for p in pairs:
        m, x = p['records']
        codes[m['id']] = _code(m['id'], ['SUPPORTED', 'CONTRADICTED'] if p['reader'] == 'nla' else ['SUPPORTED'])
        codes[x['id']] = _code(x['id'], [])
    r = A.analyse(_build(tmp_path, codes, pairs))
    o, n = r['readers']['oracle']['primary_cohort'], r['readers']['nla']['primary_cohort']
    assert o['matched']['Sup']['share'] == 1.0 and o['mismatched']['G']['share'] == 1.0
    assert o['R_F1']['verdict'] == 'MET' and o['R_F2']['verdict'] == 'NOT MET'
    assert n['R_F2']['verdict'] == 'MET' and r['readers']['nla']['prediction']['holds'] is True
    assert r['R_F3']['oracle|structure']['matched']['F']['share'] == 0.0


def test_unparseable_excluded_and_counted(tmp_path):
    pairs = _pairs(10)
    codes = {r['id']: _code(r['id'], ['SUPPORTED']) for p in pairs for r in p['records']}
    bad = pairs[0]['records'][0]['id']
    codes[bad] = {'id': bad, 'status': 'UNPARSEABLE', 'attempts': 2, 'code': None}
    r = A.analyse(_build(tmp_path, codes, pairs))
    m = r['readers']['oracle']['primary_cohort']['matched']
    assert m['UNPARSEABLE'] == 1 and m['F']['n'] == 9 and m['over_5_percent'] is True
    assert r['readers']['oracle']['primary_cohort']['R_F1']['paired_units'] == 9


def test_truncated_cohort_reported_apart(tmp_path):
    pairs = _pairs(6, reader='nla', cohort=A.TRUNCATED) + _pairs(6, reader='nla', bank='D4')
    for p in pairs[6:]:
        for r in p['records']:
            r['id'] = 'd' + r['id']
    codes = {r['id']: _code(r['id'], ['UNVERIFIABLE']) for p in pairs for r in p['records']}
    r = A.analyse(_build(tmp_path, codes, pairs))
    assert r['readers']['nla']['primary_banks'] == ['D4']
    assert r['readers']['nla']['NLA_128_token_cohort_banks'] == ['E49']


def test_tamper_and_missing_rejected(tmp_path):
    pairs = _pairs(4)
    codes = {r['id']: _code(r['id'], []) for p in pairs for r in p['records']}
    spec = _build(tmp_path, codes, pairs)
    Path(spec['categories']).write_text('{}')
    with pytest.raises(ValueError):
        A.analyse(spec)
