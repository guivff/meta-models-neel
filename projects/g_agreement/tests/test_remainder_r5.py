import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest
from sklearn.metrics import roc_auc_score

from projects.g_agreement.r_bench import remainder_r5 as r


def bank(n=5):
    rows = []
    for k in range(n):
        for split in ('pool', 'test'):
            for j in range(8):
                rows.append({'dataset': f'{k}_fact', 'tag': f'tag{k%2}', 'split': split,
                             'label': j%2, 'item_id': f'{k}-{split}-{j}', 'prompt_text': str(j),
                             'primary': {'sided': 'two', 'candidates': ['yes', 'no']}})
    return rows


def fixture(n=20):
    facts = []
    for ds in ('a', 'b'):
        items = []
        for split in ('pool', 'test'):
            ids = [f'{ds}-{split}-{i}' for i in range(n)]
            donors = r.derangement(ids, ds+split)
            for j, iid in enumerate(ids):
                items.append({'item_id': iid, 'split': split, 'label': j%2,
                              'text_hash': f'{split}-{j}', 'state_row': len(items),
                              'donor_item_id': donors[iid], 'donor_state_row': ids.index(donors[iid])+(0 if split=='pool' else n)})
        facts.append({'dataset': ds, 'tag': 'TEST', 'corpus': 'shared', 'items': items})
    return {'facts': facts, 'n_facts': 2, 'n_test': n, 'n_pool': n, 'base_alpha': 16000.,
            'expected_rows': 2*2*n*len(r.SETTINGS), 'errors': []}


def rows_for(m):
    rows = []
    for f in m['facts']:
        for it in f['items']:
            for layer, gain, arm in r.SETTINGS:
                rows.append({'key': r.row_key(f['dataset'], it['item_id'], layer, gain, arm),
                             'dataset': f['dataset'], 'item_id': it['item_id'], 'split': it['split'],
                             'label': it['label'], 'layer': layer, 'gain': gain, 'arm': arm,
                             'alpha': gain*m['base_alpha'], 'layer_in_prompt':layer,
                             'state_item_id': it['item_id'] if arm=='natural' else it['donor_item_id'],
                             'lo': it['label'], 'score': it['label'], 'pod': 'fixture', 'git_sha': 'abc',
                             'code_sha': 'def', 'manifest_sha': r.digest(m)})
    return rows


def test_selection_is_order_invariant_and_never_uses_outcome_or_state_availability():
    items = bank()
    a = r.select_items(items, 3, 4, 4)
    altered = list(reversed(copy.deepcopy(items)))
    for row in altered:
        row['reader_auc'] = 0.999
        row['model_correct'] = True
        row['state_available'] = False
    b = r.select_items(altered, 3, 4, 4)
    assert [x['item_id'] for x in a] == [x['item_id'] for x in b]
    assert all(sum(x['dataset']==ds and x['split']==split for x in a)==4
               for ds in {x['dataset'] for x in a} for split in ('pool','test'))


def test_label_defects_excluded_even_if_eligible():
    items = bank(1)
    for item in items:
        item['dataset'] = next(iter(r.I.LABEL_DEFECT))
    with pytest.raises(ValueError, match='eligible facts'):
        r.select_items(items, 1, 4, 4)


def test_shuffle_is_exact_bijection_no_self_and_fixed_across_settings():
    ids = [str(i) for i in range(100)]
    a = r.derangement(ids, 'ds|test')
    assert sorted(a.values()) == sorted(ids)
    assert all(k != v for k, v in a.items())
    assert a == r.derangement(ids, 'ds|test')
    assert a != r.derangement(ids, 'ds|pool')


def test_gain_restored_after_success_and_exception():
    reader = SimpleNamespace(alpha=123.)
    with r.insertion_gain(reader, 4, 16000):
        assert reader.alpha == 64000
    assert reader.alpha == 123
    with pytest.raises(RuntimeError):
        with r.insertion_gain(reader, .5, 16000):
            raise RuntimeError()
    assert reader.alpha == 123


def test_live_smoke_requires_every_setting_split_and_control():
    m = fixture(); rows = rows_for(m)
    assert r.assert_coverage(rows, m) == m['expected_rows']
    with pytest.raises(ValueError, match='SMOKE FAILED: missing'):
        r.assert_coverage([x for x in rows if not (x['arm']=='shuffled' and x['layer']==36 and x['gain']==4)], m)
    with pytest.raises(ValueError, match='duplicate'):
        r.assert_coverage(rows+[rows[0]], m)
    bad = copy.deepcopy(rows); bad[0]['state_item_id'] = 'wrong'
    with pytest.raises(ValueError, match='incorrect donor'):
        r.assert_coverage(bad, m)
    bad = copy.deepcopy(rows); bad[0]['score'] = None
    with pytest.raises(ValueError, match='nonfinite'):
        r.assert_coverage(bad, m)


def test_weighted_auc_exact_ties_match_explicit_repeated_observations():
    y = np.array([0,1,1,0,1,0]); s = np.array([0,0,1,2,3,3.])
    weights = np.array([[1,1,1,1,1,1], [3,0,2,1,3,2]])
    out = r.weighted_auc(y, s, weights)[:,0]
    for k, w in enumerate(weights):
        np.testing.assert_allclose(out[k], roc_auc_score(np.repeat(y,w), np.repeat(s,w)))


def test_pool_selection_ties_prefer_frozen_default_and_not_test():
    a = np.full(len(r.SETTINGS), .6)
    assert r.choose_pool_setting(a) == r.SETTINGS.index(r.DEFAULT)
    a[0] = .9
    assert r.choose_pool_setting(a) == 0
    a[1] = 1.  # shuffled controls cannot be selected as the reader setting
    assert r.choose_pool_setting(a) == 0


def test_crossed_slice_ranges_cannot_cancel_in_marginal_average():
    a = np.full(len(r.SETTINGS), .5)
    for i,(layer,gain,arm) in enumerate(r.SETTINGS):
        if arm == 'natural':
            a[i] = .9 if (r.LAYERS.index(layer)+r.GAINS.index(gain))%2 else .5
    values, names = r.metric_values(a, r.SETTINGS.index(r.DEFAULT))
    assert values[names.index('gain_range')] == pytest.approx(.4)
    assert values[names.index('layer_range')] == pytest.approx(.4)
    assert values[names.index('nuisance_robust_share')] == 0


def test_identical_settings_and_controls_have_zero_paired_effect_in_both_bootstraps():
    m = fixture(); analysis = r.analyze_rows(rows_for(m), m, 30)
    for group in analysis['population']+analysis['facts']:
        for name, metric in group['metrics'].items():
            if name.startswith('delta_') or name in ('selected_minus_default','selected_minus_shuffled'):
                assert metric['estimate'] == 0
                assert metric['item_ci95'] == [0,0]
                assert metric['corpus_ci95'] == [0,0]
    assert analysis['population'][0]['metrics']['nuisance_robust_share']['estimate'] == 1


def test_throughput_gate_refuses_mock_and_caps_without_reducing_population(monkeypatch):
    m = fixture(); meta = {'pod':'id','code_sha':'sha','git_sha':'git'}
    monkeypatch.setattr(r.time, 'time', lambda: 1000.)
    cert = {**meta, 'mock':False, 'live':True, 'manifest_sha':r.digest(m), 'batch':32,
            'deadline_epoch':2000., 'coverage_rows':m['n_facts']*4*len(r.SETTINGS),
            'timing':[{'seconds_per_sequence':.001}]}
    assert r.throughput_gate(cert,m,meta,2000.,32)['full_candidate_sequences']==m['expected_rows']*2
    with pytest.raises(ValueError,match='CPU mock'):
        r.throughput_gate({**cert,'mock':True},m,meta,2000.,32)
    with pytest.raises(ValueError,match='differs: code_sha'):
        r.throughput_gate(cert,m,{**meta,'code_sha':'different'},2000.,32)
    with pytest.raises(ValueError,match='THROUGHPUT BLOCKED'):
        r.throughput_gate({**cert,'timing':[{'seconds_per_sequence':1}]},m,meta,2000.,32)


def test_manifest_change_fails_instead_of_reselecting(tmp_path):
    m = fixture(); target = tmp_path/'manifest.json'
    r.freeze_manifest(m,target)
    with pytest.raises(ValueError,match='Frozen manifest changed'):
        r.freeze_manifest({**m,'base_alpha':2},target)
    with pytest.raises(ValueError,match='PREFLIGHT FAILED'):
        r.freeze_manifest({**m,'errors':['missing layer36']},target)


def test_native_one_sided_score_preserved_and_alpha_not_leaked(tmp_path):
    m = fixture(); items = {}
    for fact in m['facts']:
        (tmp_path/fact['dataset']).mkdir()
        for it in fact['items']:
            items[it['item_id']] = {'primary':{'sided':'one'}}
        for layer in r.LAYERS:
            np.save(tmp_path/fact['dataset']/f'chat_L{layer}.npy', np.ones((40,3)))
    reader = SimpleNamespace(alpha=77)
    def scorer(reader,H,items,layer,batch):
        return [{'lo':-2.,'lp_A':5.,'lp_B':7.} for _ in items]
    rows,_ = r.collect_scores(m,items,reader,scorer,{'pod':'mock','git_sha':'a','code_sha':'b','mock':True},
                              tmp_path/'scores.jsonl',smoke=True,states_dir=tmp_path)
    assert all(row['score']==5 and row['lo']==-2 and row['score_kind']=='lp_A' for row in rows)
    assert reader.alpha==77


def test_guard_record_binds_original_deadline_and_experiment():
    record = {'pod':'booked', 'experiment':'r5', 'started_epoch':1000., 'deadline_epoch':2800.}
    r.validate_guard_record(record, 'booked', 2800., 1800.)
    r.validate_guard_record(record, 'booked', 2700., 1800.)
    with pytest.raises(ValueError, match='renews the original'):
        r.validate_guard_record(record, 'booked', 2900., 1800.)
    with pytest.raises(ValueError, match='wrong pod or experiment'):
        r.validate_guard_record({**record,'experiment':'r4'}, 'booked', 2800., 1800.)
    with pytest.raises(ValueError, match='wrong pod or experiment'):
        r.validate_guard_record(record, 'other', 2800., 1800.)
    with pytest.raises(ValueError, match='original 0.5 pod-hour cap'):
        r.validate_guard_record({**record,'deadline_epoch':3000.}, 'booked', 2800., 1800.)
    with pytest.raises(ValueError, match='No remaining budget'):
        r.validate_guard_record(record, 'booked', 2800., 2500.)
    with pytest.raises(ValueError, match='invalid epoch'):
        r.validate_guard_record(record, 'booked', float('nan'), 1800.)


def test_smoke_certificate_rejects_renewed_deadline(monkeypatch):
    m = fixture(); meta = {'pod':'id','code_sha':'sha','git_sha':'git'}
    monkeypatch.setattr(r.time, 'time', lambda: 1000.)
    cert = {**meta, 'mock':False, 'live':True, 'manifest_sha':r.digest(m), 'batch':32,
            'deadline_epoch':2000., 'coverage_rows':m['n_facts']*4*len(r.SETTINGS),
            'timing':[{'seconds_per_sequence':.001}]}
    with pytest.raises(ValueError, match='differs: deadline_epoch'):
        r.throughput_gate(cert,m,meta,2100.,32)
