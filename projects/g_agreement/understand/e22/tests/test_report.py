"""CPU fixtures only: E22 ratios, donor signs, full grids and sealed custody."""
import json

import numpy as np
import pytest

from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e22 import report as R


def fixture(n=4):
    items, labels, records = [], [], []
    donors = {arm: [] for arm in R.ARMS}
    for row in R.ROWS:
        for i in range(n):
            key = f'{row}_{i:03}'
            cluster = f'template_{i//(14 if n == 84 else 2)}'
            item = {'id': key, 'feature': row, 'cluster': cluster, 'split': 'test'}
            items.append(item); labels.append({**item, 'y': i % 2})
            for arm in R.ARMS:
                donor_index = (i ^ 1) if arm == 'opposite' else (i+2) % n
                donor_id = f'{row}_{donor_index:03}'
                donors[arm].append({'id': key, 'feature': row, 'donor_id': donor_id})
                sign = 2*(donor_index % 2)-1
                denominator = sign*(4. if arm == 'opposite' else 1.)
                for prompt in R.prompts(row):
                    for layer in R.LAYERS:
                        for position in R.POSITIONS:
                            records.append({'row': row, 'item_id': key, 'cluster': cluster,
                                'donor_id': donor_id, 'arm': arm, 'prompt': prompt, 'layer': layer,
                                'position': position, 'recipient_score': float(i),
                                'donor_score': i+denominator, 'patched_score': i+.5*denominator})
    return items, labels, records, donors


def analyse(items, labels, records):
    return R.analyse(records, items, labels, n_bootstrap=200)


def cell(summary, **criteria):
    return next(c for c in summary['cells'] if all(c[k] == v for k, v in criteria.items()))


def test_all_registered_cells_and_separate_raw_donor_signed_changes():
    items, labels, records, _ = fixture()
    summary, paired = analyse(items, labels, records)
    assert summary['population_status'] == 'COMPLETE'
    assert summary['n_score_records'] == 9*17*2*2*4
    assert len(summary['cells']) == 9*17*2*2
    assert len(summary['curves']) == 9*2*2
    assert summary['prediction']['held'] is None
    assert summary['prediction']['status'] == 'DESCRIPTIVE_ONLY_REQUIRES_OPERATIONAL_RULING'
    assert all(e['layers_at_least_half_recovered'] == list(R.LAYERS)
               for e in summary['prediction']['registered_half_recovery_evidence'])
    assert 'not a hypothesis-test threshold' in summary['method']['control_quantile']
    for c in summary['cells']:
        assert c['fraction']['mean'] == .5 and c['fraction']['ci95'] == [.5, .5]
        assert c['paired_change']['mean'] == 0
        assert c['donor_signed_change']['mean'] == (2. if c['arm'] == 'opposite' else .5)
        assert c['same_value_signed_item_change_q95'] == .5
    first = paired[0]
    assert first['recipient_score'] == 0 and first['donor_score'] == 4 and first['patched_score'] == 2
    assert not any(c['row'] == 'prose_sentiment' and c['prompt'] == 'continuation' for c in summary['cells'])


def test_zero_denominator_prevents_main_mean_without_dropping_or_imputing():
    items, labels, records, _ = fixture()
    for record in records:
        if record['item_id'] == 'prose_paren_000' and record['arm'] == 'opposite':
            record['donor_score'] = record['recipient_score']
    summary, paired = analyse(items, labels, records)
    c = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')
    assert c['n_zero_denominator'] == 1 and c['min_abs_denominator'] == 0
    assert c['fraction'] == {'n_expected': 4, 'n_defined': 3, 'status': 'NOT_EVALUABLE', 'mean': None, 'ci95': None}
    assert c['paired_change']['status'] == 'EVALUABLE'
    assert c['donor_signed_change']['mean'] == 2
    undefined = next(r for r in paired if r['item_id'] == 'prose_paren_000' and r['arm'] == 'opposite')
    assert undefined['fraction'] is None and undefined['fraction_status'] == 'UNDEFINED_ZERO_DENOMINATOR'
    assert undefined['paired_change'] == 2 and undefined['donor_minus_recipient'] == 0


def test_finite_near_zero_denominator_retained_and_unbounded_ratios_not_clipped():
    items, labels, records, _ = fixture()
    for record in records:
        if record['item_id'] == 'prose_paren_000' and record['arm'] == 'opposite':
            record['donor_score'] = 1e-12
    summary, paired = analyse(items, labels, records)
    c = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')
    assert c['fraction']['status'] == 'EVALUABLE'
    assert c['min_abs_denominator'] == 1e-12
    assert c['fraction']['mean'] == pytest.approx((2e12+1.5)/4)
    assert next(r for r in paired if r['item_id'] == 'prose_paren_000' and r['arm'] == 'opposite')['fraction'] == 2e12


def test_donor_label_sign_is_not_flipped_to_observed_full_swap():
    items, labels, records, _ = fixture()
    for record in records:
        if record['item_id'] == 'prose_paren_000' and record['arm'] == 'opposite':
            record['donor_score'] = -4.
    summary, paired = analyse(items, labels, records)
    record = next(r for r in paired if r['item_id'] == 'prose_paren_000' and r['arm'] == 'opposite')
    assert record['donor_sign'] == 1 and record['donor_signed_change'] == 2
    assert record['donor_signed_full_swap'] == -4 and record['fraction'] == -.5
    assert cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')['fraction']['mean'] == .25


def test_same_value_arm_uses_own_denominator_and_empirical_item_quantile():
    items, labels, records, _ = fixture()
    for record in records:
        if record['row'] == 'prose_paren' and record['arm'] == 'same':
            i = int(record['item_id'][-3:])
            sign = 2*(i % 2)-1
            record['patched_score'] = record['recipient_score']+sign*i
    summary, _ = analyse(items, labels, records)
    same = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='same')
    opposite = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')
    assert same['fraction']['mean'] == 1.5
    assert same['same_value_signed_item_change_q95'] == pytest.approx(2.85)
    assert opposite['same_value_signed_item_change_q95'] == pytest.approx(2.85)
    assert opposite['fraction']['mean'] == .5


def test_partial_grid_retains_missing_records_and_cells():
    items, labels, records, _ = fixture()
    records.pop(0)
    summary, paired = analyse(items, labels, records)
    assert summary['population_status'] == 'PARTIAL' and summary['n_missing_score_records'] == 1
    assert len(paired) == 9*17*2*2*4
    missing = [r for r in paired if not r['score_record_present']]
    assert len(missing) == 1 and missing[0]['fraction_status'] == 'MISSING_SCORE'
    c = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')
    assert c['fraction']['status'] == 'NOT_EVALUABLE' and c['paired_change']['mean'] is None


def test_cluster_bootstrap_preserves_template_blocks_and_is_deterministic():
    weights = R._weights(['a', 'a', 'b', 'b'], R.SEED, 2000)
    np.testing.assert_array_equal(weights[:, 0], weights[:, 1])
    np.testing.assert_array_equal(weights[:, 2], weights[:, 3])
    np.testing.assert_array_equal(weights, R._weights(['a', 'a', 'b', 'b'], R.SEED, 2000))
    stats = R._stats([0, 0, 10, 10], weights)
    assert stats['mean'] == 5 and stats['ci95'] == [0, 10]


def test_layer_zero_full_swap_control_is_reported_independently_of_fraction():
    items, labels, records, _ = fixture()
    for record in records:
        if record['layer'] == 0 and record['position'] == 'injection':
            record['patched_score'] = record['donor_score']
        if record['item_id'] == 'prose_paren_000' and record['arm'] == 'opposite':
            record['donor_score'] = record['recipient_score']
            if record['layer'] == 0 and record['position'] == 'injection':
                record['patched_score'] = record['donor_score']
    summary, _ = analyse(items, labels, records)
    controls = summary['layer0_full_swap_controls']
    assert len(controls) == 18 and all(c['all_expected_exact_equal'] for c in controls)
    assert all(c['max_abs_difference'] == 0 for c in controls)
    c = cell(summary, row='prose_paren', prompt='asked', layer=0, position='injection', arm='opposite')
    assert c['fraction']['status'] == 'NOT_EVALUABLE' and c['n_zero_denominator'] == 1


@pytest.mark.parametrize('bad', ['duplicate', 'cluster', 'layer', 'position', 'nonfinite', 'donor', 'baseline', 'sentiment'])
def test_invalid_score_records_rejected(bad):
    items, labels, records, _ = fixture()
    if bad == 'duplicate': records.append(dict(records[0]))
    elif bad == 'cluster': records[0]['cluster'] = 'wrong'
    elif bad == 'layer': records[0]['layer'] = True
    elif bad == 'position': records[0]['position'] = 'preoutput'
    elif bad == 'nonfinite': records[0]['patched_score'] = float('inf')
    elif bad == 'donor': records[0]['donor_id'] = 'prose_paren_002'
    elif bad == 'baseline': records[0]['recipient_score'] += 1
    else: records[-1]['prompt'] = 'continuation'
    with pytest.raises(ValueError): analyse(items, labels, records)


def sealed_fixture(tmp_path, monkeypatch, n=84):
    from projects.g_agreement.understand.e22 import inputs as I
    inputs, scores = tmp_path/'inputs', tmp_path/'scores'
    inputs.mkdir(); scores.mkdir()
    items, labels, records, donors = fixture(n)
    label_path = tmp_path/'labels.DO_NOT_STAGE.jsonl'
    P.jsonl(label_path, labels)
    P.jsonl(inputs/'items.input.jsonl', items)
    (inputs/'REGISTRATION.md').write_text('§114 E22 fixture registration, no scientific data')
    input_provenance = {'experiment': 'E22', 'labels_sha256': P.sha(label_path),
                        'registration_sha256': P.sha(inputs/'REGISTRATION.md')}
    P.dump(inputs/'provenance.json', input_provenance)
    P.seal(inputs, ['items.input.jsonl', 'provenance.json', 'REGISTRATION.md'], 'INPUTS_FROZEN_E22')
    data = {'items': items, 'donors': donors, 'provenance': input_provenance}
    def load(directory):
        P.verify(directory, 'INPUT_SEAL.json')
        return data
    monkeypatch.setattr(I, 'load', load)
    P.jsonl(scores/'scores.jsonl', records)
    P.dump(scores/'manifest.json', {'expected_items': items, 'layer_ids': list(R.LAYERS), 'positions': list(R.POSITIONS),
        'prompts': [[row, prompt] for row in R.ROWS for prompt in R.prompts(row)],
        'arms': list(R.ARMS), 'layer_convention': 'zero-based decoder block INPUT'})
    P.dump(scores/'provenance.json', {'experiment': 'E22', 'input_seal_sha256': P.sha(inputs/'INPUT_SEAL.json'),
        'source_files': {'source.py': 'a'*64}, 'registration_sha256': P.sha(inputs/'REGISTRATION.md')})
    P.dump(scores/'RUN_STATUS.json', {'status': 'COMPLETE'})
    reseal(scores)
    return inputs, scores, label_path, data


def reseal(scores):
    return P.seal(scores, ['scores.jsonl', 'manifest.json', 'provenance.json', 'RUN_STATUS.json'], 'SCORES_SEALED_EXPLORATORY_E22')


def test_tampered_score_rejected_before_label_access(tmp_path, monkeypatch):
    inputs, scores, _, _ = sealed_fixture(tmp_path, monkeypatch, n=4)
    (scores/'scores.jsonl').write_text('unparseable changed bytes')
    with pytest.raises(ValueError, match='seal mismatch'):
        R.generate(scores, inputs, tmp_path/'never-open-labels', tmp_path/'analysis')
    assert not (tmp_path/'analysis').exists()


def test_wrong_input_binding_rejected_before_label_access(tmp_path, monkeypatch):
    inputs, scores, _, _ = sealed_fixture(tmp_path, monkeypatch, n=4)
    provenance = json.loads((scores/'provenance.json').read_text())
    provenance['input_seal_sha256'] = 'c'*64
    P.dump(scores/'provenance.json', provenance); reseal(scores)
    with pytest.raises(ValueError, match='provenance mismatch'):
        R.generate(scores, inputs, tmp_path/'never-open-labels', tmp_path/'analysis')


def test_wrong_analysis_labels_rejected_before_parsing(tmp_path, monkeypatch):
    inputs, scores, labels, _ = sealed_fixture(tmp_path, monkeypatch, n=4)
    labels.write_text('not the frozen labels')
    with pytest.raises(ValueError, match='private labels differ'):
        R.generate(scores, inputs, labels, tmp_path/'analysis')


@pytest.mark.parametrize('field', ['cluster', 'layer_ids', 'prompts', 'arms', 'layer_convention'])
def test_resealed_wrong_manifest_fails_before_labels(tmp_path, monkeypatch, field):
    inputs, scores, _, _ = sealed_fixture(tmp_path, monkeypatch, n=4)
    manifest = json.loads((scores/'manifest.json').read_text())
    if field == 'cluster': manifest['expected_items'][0]['cluster'] = 'changed'
    else: manifest[field] = []
    P.dump(scores/'manifest.json', manifest); reseal(scores)
    with pytest.raises(ValueError, match='manifest'):
        R.generate(scores, inputs, tmp_path/'unopened-labels', tmp_path/'analysis')


def test_resealed_registration_mismatch_fails_before_labels(tmp_path, monkeypatch):
    inputs, scores, _, _ = sealed_fixture(tmp_path, monkeypatch, n=4)
    provenance = json.loads((scores/'provenance.json').read_text())
    provenance['registration_sha256'] = 'c'*64
    P.dump(scores/'provenance.json', provenance); reseal(scores)
    with pytest.raises(ValueError, match='provenance mismatch'):
        R.generate(scores, inputs, tmp_path/'unopened-labels', tmp_path/'analysis')


def test_wrong_frozen_donor_rejected_even_when_label_arm_is_correct(tmp_path, monkeypatch):
    inputs, scores, labels, _ = sealed_fixture(tmp_path, monkeypatch)
    records = P.rows(scores/'scores.jsonl')
    records[0]['donor_id'] = 'prose_paren_003'
    (scores/'scores.jsonl').unlink(); P.jsonl(scores/'scores.jsonl', records); reseal(scores)
    with pytest.raises(ValueError, match='frozen donor assignment'):
        R.generate(scores, inputs, labels, tmp_path/'analysis')


def test_full_registered_fixture_generates_immutable_report(tmp_path, monkeypatch):
    inputs, scores, labels, _ = sealed_fixture(tmp_path, monkeypatch)
    original = P.sha(scores/'SCORE_SEAL.json')
    P.dump(scores/'budget.json', {'science_seconds': 9001., 'science_cap_seconds': 9000., 'cap_overrun_seconds': 1.})
    out = tmp_path/'analysis'
    summary = R.generate(scores, inputs, labels, out)
    assert summary['n_expected_score_records'] == summary['n_score_records'] == 51408
    assert summary['method']['bootstrap_replicates'] == 2000
    assert summary['prediction']['held'] is None
    assert summary['custody_telemetry']['covered_by_primary_score_seal'] is False
    assert summary['custody_telemetry']['status'] == 'CAP_OVERRUN_REPORTED'
    assert P.sha(scores/'SCORE_SEAL.json') == original
    seal = json.loads((out/'ANALYSIS_SEAL.json').read_text())
    assert all(P.sha(out/name) == digest for name, digest in seal['files'].items())
    assert 'no claim that the run stayed within budget' in (out/'RESULTS.md').read_text()
    with pytest.raises(FileExistsError): R.generate(scores, inputs, labels, out)
