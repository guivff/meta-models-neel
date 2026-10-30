import numpy as np
import pytest
from projects.g_agreement.understand import e13_completion as E


def test_forecast_uses_median_and_keeps_full_scope():
    t = {name: [1., 100., 2.] for name in E.READERS}
    result = E.forecast(t, 53, 309.)
    assert result['fresh_pass_forecast_s'] == 318.
    assert result['science_allocation_s'] == 1.5*627+360
    assert result['fits']
    assert result['timing_outputs_used'] is False


def test_forecast_no_fit_never_reduces_full_bank():
    result = E.forecast({name: [20., 20., 20.] for name in E.READERS}, 53, 180.)
    assert result['science_allocation_s'] == 2400
    assert not result['fits']
    assert result['fresh_units_per_reader'] == 53


@pytest.mark.parametrize('bad', [0., -1., float('nan')])
def test_reject_bad_timing(bad):
    with pytest.raises(ValueError):
        E.forecast({name: [bad, 1., 1.] for name in E.READERS}, 53, 10.)


def test_timing_preserves_canonical_seeds_at_partial_last_batch(monkeypatch):
    seen = {}
    def collector(items, h, reader, layer, name, policy, **kw):
        seen.update(kw)
        assert len(items) == len(h) == 16
        return iter([{'status': 'COMPLETE'}])
    monkeypatch.setattr(E.R, 'collect_unasked', collector)
    E.collect_unit(list(range(1680)), np.zeros((1680, 3)), None, 'olens', {}, 1664, lambda: None)
    assert seen['canonical_indices'] == list(range(1664, 1680))
    assert seen['batch'] == 32


def test_full_phase_grid_includes_baselines_and_two_samples():
    items = [{'id': str(i)} for i in range(1680)]
    records = [{'id': x['id'], 'reader': name, 'sample': sample, 'layer': 44,
                'status': 'COMPLETE', 'canonical_index': i, 'canonical_batch_start': i//32*32}
               for i, x in enumerate(items) for name in E.READERS for sample in range(2)]
    assert len(records) == 10080
    E.check_grid(records, items)
    with pytest.raises(ValueError):
        E.check_grid(records[:-1], items)
    with pytest.raises(ValueError):
        E.check_grid(records+[records[0]], items)
