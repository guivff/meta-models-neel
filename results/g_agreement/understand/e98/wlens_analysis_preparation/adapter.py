"""E98 CPU descriptive adapter. No CLI, dispatch, forecast or claim reset.
A committed final binding is required before this pure adapter sees real outcomes.
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / 'results/g_agreement/understand/e56/job'))
sys.path.insert(0, str(ROOT / 'results/g_agreement/understand/analysis402'))
from missingness import rate, reported, signed_value, validate_judgment

FORECAST = '2cd5727a33255c4295c3130948631c373733b9bdc246c31d6063e3b9b2947c1d'
CATEGORIES = {'states_value', 'names_property_without_value', 'exhibits', 'silent', 'UNPARSEABLE'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def gate(binding, native_seal, judgment_seal):
    """Metadata-only admission, before opening raw outcomes or creating a claim."""
    require(binding['experiment'] == 'E98' and binding['status'] == 'FINAL_BOUND', 'final E98 binding')
    require(binding['forecast_sha256'] == FORECAST, 'original forecast immutable')
    require(binding['final_binding_committed'] is True, 'commit final binding first')
    require(binding['adapter_committed_before_judging_seal'] is True, 'pre-seal adapter proof')
    for kind, seal in [('native', native_seal), ('judgment', judgment_seal)]:
        require(seal['experiment'] == 'E98' and seal['status'] == 'COMPLETE', kind + ' complete seal')
        require(seal['items'] == 2184 and seal['unique_items'] == 2184, kind + ' complete grid')
        require(seal['capture_seal_sha256'] == binding['capture_seal_sha256'], kind + ' capture binding')
        require(seal['input_seal_sha256'] == binding['input_seal_sha256'], kind + ' input binding')
        require(seal['sha256'] == binding[kind + '_seal_sha256'], kind + ' exact seal')
    require(judgment_seal['native_seal_sha256'] == native_seal['sha256'], 'judge/native lineage')
    require(judgment_seal['rubric_sha256'] == binding['rubric_sha256'], 'unchanged rubric')
    require(judgment_seal['terminal'] is True, 'terminal judgments required')
    require(binding['original_qwen_metrics_sealed'] is True, 'sealed original Qwen comparison')
    require(binding['normalized_files_verified'] is True, 'verify original members and normalized hashes first')
    return True


def describe(units, judgments, native, forecast, qwen):
    """Pure result builder; use only after gate + exact file/hash/ID verification.
    units: frozen CPU token-plan units; native/judgments keyed by opaque E98 id.
    qwen: original sealed per-row Oracle metrics keyed by bank|row, never refit.
    """
    ids = [x['id'] for u in units for x in u['items']]
    require(len(ids) == 2184 and len(set(ids)) == 2184, 'all 2184 unique native items')
    require(set(ids) == set(judgments) == set(native), 'exact terminal/native ID grid')
    require(len(units) == 26 and sum(u['binary'] for u in units) == 23, '26 rows / 23 binary')
    keys = [u['bank'] + '|' + u['row'] for u in units]
    require(len(set(keys)) == 26 and set(qwen) == set(keys), 'complete original Qwen row mapping')
    f = {r['bank'] + '|' + r['row']: r for r in forecast['rows']}
    require(set(f) == {k for k,u in zip(keys,units) if u['binary']}, '23 original J predictions')
    rows = []
    for key, u in sorted(zip(keys, units)):
        require(len(u['items']) == 84, '84 original test items per row')
        for x in u['items']:
            j = judgments[x['id']]
            require(j['id'] == x['id'], 'judgment identity')
            validate_judgment(j, native[x['id']])
        row = {'bank': u['bank'], 'row': u['row'], 'native_items': 84,
               'original_Qwen': qwen[key], 'binary': u['binary']}
        if u['binary']:
            require(all(type(x['label']) is int and x['label'] in (0,1) for x in u['items']), 'binary labels')
            scores = [[signed_value(judgments[x['id']], x['label'])] for x in sorted(u['items'], key=lambda x:x['id'])]
            r = rate(scores)
            label = None if r['S'] is None else ('REPORTED' if reported(r) else 'MISSED')
            row.update(S=r, UNPARSEABLE=sum(s[0] is None for s in scores), native_label=label,
                       original_J_prediction=f[key]['oracle_prediction'],
                       J_agrees=None if label is None else label == f[key]['oracle_prediction'])
        else:
            row.update(S=None, native_label=None, J_agrees=None,
                       reason='Inherited nonbinary unit: no binary S or A/B J direction; retain registered count/mention summaries separately')
        rows.append(row)
    return {'experiment':'E98', 'scope':'DESCRIPTIVE; no new confirmatory rule',
            'native_items':2184, 'binary_items':1932, 'nonbinary_items':252, 'port_drops':0,
            'rows':rows, 'forecast_sha256':FORECAST}
