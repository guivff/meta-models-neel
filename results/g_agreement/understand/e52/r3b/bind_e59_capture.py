"""E59 follow402 capture adapter: sealed test slice and registered value words only."""
from pathlib import Path
from datetime import datetime
import sys
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
CHANNEL = ROOT / 'results/g_agreement/understand/e57/jlens'
sys.path.insert(0, str(CHANNEL))
from cpu_job import read, dump, sha, verify, validate_units, committed
from prepare import words_for


def bind():
    source = ROOT / 'cache/g_agreement/understand/e59/capture_delivery'
    receipt = read(source / 'DELIVERY.json')
    verify(source, receipt['files'])
    assert receipt['issuer'] == 'integrator' and receipt['experiment'] == 'E59'
    assert receipt['R3b'] == 'own block-42/44 capture (follow402) before any reader output exists; no probe scores or class means (W-mechanism CPU step not adapted to follow402)'
    cap = read(source / 'CAPTURE_SEAL.json')
    ready = read(source / 'CAPTURE_READY.json')
    assert sha(source / 'CAPTURE_SEAL.json') == receipt['capture_seal_sha256'] == ready['capture_seals']['E59']
    assert cap['experiment'] == 'E59' and cap['layers'] == [42, 44]
    assert cap['cohort_id'] == receipt['cohort_id'] == ready['cohort_id']
    assert ready['pod_id'] == receipt['pod_id']
    verify(source, cap['files'])
    inp = ROOT.parent / 'wt-wmech/cache/g_agreement/understand/follow402_v1/E59'
    assert sha(inp / 'INPUT_SEAL.json') == cap['input_seal_sha256'] == ready['input_seals']['E59']
    inputseal = read(inp / 'INPUT_SEAL.json')
    assert inputseal['experiment'] == 'E59' and inputseal['label_free'] is True
    # Only capture-input metadata is read; no parity outcome, probe or reader score.
    for name in ('items.json', 'SHARD.json', 'PLAN.json'):
        assert sha(inp / name) == inputseal['files'][name]
    manifest = ROOT / 'results/g_agreement/understand/e59/FREEZE_MANIFEST.json'
    committed(manifest)
    m = read(manifest)
    folder = Path(m['bank_directory'])
    assert sha(folder / 'BANK_SEAL.json') == m['bank_seal_sha256']
    seal = read(folder / 'BANK_SEAL.json')
    private = folder / 'items.PRIVATE.json'
    definition = folder / 'VALIDATION.json'
    for p in (private, definition):
        assert sha(p) == seal['files'][p.name]
    records = read(private)
    byid = {r['id']: r for r in records}
    public = read(inp / 'items.json')
    assert len(byid) == len(records) == len(public) == 1008
    assert {r['id'] for r in public} == set(byid)
    for r in public:
        assert set(r) == {'id', 'feature', 'split', 'text', 'ids'}
        assert all(r[k] == byid[r['id']][k] for k in r)
    order = read(source / 'items.order.json')
    h = np.load(source / 'acts44.npy', allow_pickle=False)
    assert len(order) == len(set(order)) == 1008 and set(order) == set(byid)
    assert h.shape == (1008, 5120) and np.isfinite(h).all()
    ix = [i for i, item in enumerate(order) if byid[item]['split'] == 'test']
    testorder = [order[i] for i in ix]
    assert len(testorder) == 504
    definitions = read(definition)
    expected = {'format_plan', 'language_plan', 'stance_plan', 'length_plan', 'hedge_plan', 'decline_plan'}
    assert set(definitions) == set(seal['rows']) == {byid[i]['feature'] for i in testorder} == expected
    from transformers import AutoTokenizer
    sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tr = read(HERE.parent / 'BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']
    assert sha(tr['path']) == tr['sha256'] == seal['tokenizer_sha256']
    tok = AutoTokenizer.from_pretrained(Path(tr['path']).parent, local_files_only=True)
    units = []; audit = {}
    for row in sorted(expected):
        spec = definitions[row]
        ids = sorted(i for i in testorder if byid[i]['feature'] == row)
        values = spec['spec']['values']
        assert all(byid[i]['value'] == values[1 - byid[i]['label']] for i in ids)
        phrases = spec['registered_reader_value_words']
        words, removed = words_for(phrases)
        tokens = [token_variants(tok, w) for w in words]
        audit[row] = {'source': 'sealed VALIDATION.json registered_reader_value_words (not authoring synonyms)',
                      'values': values, 'source_phrases': phrases, 'words': words,
                      'shared_removed': removed, 'token_ids': tokens}
        units.append({'id': row, 'source_row': row, 'condition': None, 'binary': True,
                      'item_ids': ids, 'value_token_ids': {i: tokens for i in ids},
                      'descriptive_token_sets': {i: {} for i in ids}})
    validate_units(units, records, testorder)
    target = CHANNEL / 'E59_INPUT_PLAN.json'
    normal = ROOT / 'cache/g_agreement/understand/e52/r3b/E59_DELIVERY.json'
    assert not target.exists() and not normal.exists()
    bound = ROOT / 'cache/g_agreement/understand/e59/jlens/bound_capture'
    bound.mkdir(parents=True, exist_ok=False)
    # Pure registered split selection, preserving values/dtype; no class means/scoring here.
    np.save(bound / 'acts44.npy', h[ix], allow_pickle=False)
    assert np.array_equal(np.load(bound / 'acts44.npy', allow_pickle=False), h[ix])
    dump(bound / 'order.json', testorder)
    dump(bound / 'WORD_AUDIT.json', audit)
    dump(bound / 'CAPTURE_SEAL.json', {'experiment': 'E59', 'layer': 44, 'split': 'test',
         'normalizer': 'exact registered test slice of follow402 dev+test capture, dtype unchanged',
         'original_delivery_sha256': sha(source / 'DELIVERY.json'),
         'original_capture_seal_sha256': sha(source / 'CAPTURE_SEAL.json'),
         'original_input_seal_sha256': sha(inp / 'INPUT_SEAL.json'), 'test_indices': ix,
         'files': {n: sha(bound / n) for n in ('acts44.npy', 'order.json', 'WORD_AUDIT.json')}})
    def ref(p):
        return {'path': str(p), 'sha256': sha(p), 'member': p.name}
    sources = [manifest, private, definition, folder / 'BANK_SEAL.json', source / 'DELIVERY.json',
               source / 'CAPTURE_SEAL.json', inp / 'INPUT_SEAL.json', inp / 'items.json', Path(tr['path']),
               bound / 'WORD_AUDIT.json', Path(__file__).resolve()]
    plan = {'experiment': 'E59', 'layer': 44, 'split': 'test',
            'bank_seal': {'path': str(folder / 'BANK_SEAL.json'), 'sha256': sha(folder / 'BANK_SEAL.json')},
            'capture_seal': {'path': str(bound / 'CAPTURE_SEAL.json'), 'sha256': sha(bound / 'CAPTURE_SEAL.json')},
            'records': ref(private), 'order': ref(bound / 'order.json'), 'activations': ref(bound / 'acts44.npy'),
            'units': units, 'value_sources': [{'path': str(p), 'sha256': sha(p)} for p in sources],
            'word_audit': audit, 'exclusions': [],
            'value_word_policy': 'E59 explicitly registered reader words; unchanged E52 extraction/shared removal and Suraj single-token variants',
            'reader_outcomes_accessed': False}
    dump(target, plan)
    dump(normal, {'issuer': 'integrator', 'normalizer': 'W-lens from original hash-bound Integrator capture-only receipt',
         'experiment': 'E59', 'status': 'VERIFIED_CAPTURE_ONLY', 'original_delivery_path': str(source / 'DELIVERY.json'),
         'original_delivery_sha256': sha(source / 'DELIVERY.json'),
         'delivered_epoch': datetime.fromisoformat(receipt['delivered_utc'].replace('Z', '+00:00')).timestamp(),
         'bank_seal_sha256': sha(folder / 'BANK_SEAL.json'), 'capture_seal_sha256': sha(bound / 'CAPTURE_SEAL.json'),
         'reader_outputs_opened_at_registration': False, 'reader_outputs_opened_before_forecast': False,
         'readers_held_until_forecast_commit': True,
         'custody_authority': 'Integrator receipt before any reader output exists; Guiv requires forecast FIRST within45 minutes',
         'current_user_deadline_seconds': 2700, 'integrator_go_deadline_epoch': receipt['go_deadline_epoch']})
    print('E59 verified/bound: 1008 captured items -> all504 registered test items; 6 binary rows; 0 exclusions; no scoring')


if __name__ == '__main__':
    bind()
