"""Reporting safeguards: retain missing markers and freeze dose orientation."""
import numpy as np
import pytest
from projects.g_agreement.understand.score_analysis import event_rate
from projects.g_agreement.understand.e8 import gains, ALPHAS


def test_neutral_outputs_stay_in_base_rate_denominator():
    r = event_rate([1, .5, .5, 0])
    assert (r['k'], r['n'], r['rate'], r['neutral_n']) == (1, 4, .25, 2)


def test_fractional_proxy_is_not_counted_as_event():
    r = event_rate([.25, .75, 1, 0])
    assert r['rate'] == .25
    assert r['other_fractional_n'] == 2


def test_bootstrap_slope_weights_match_frozen_polyfit_including_negative():
    values = np.array([3., 2., 0., 4., -1., -2.])
    x = np.array(ALPHAS)
    frozen = gains(values, 10)
    assert values @ np.array([-1., 0., 1., 0., 0., 0.]) == pytest.approx(frozen['low_dose_gain'])
    assert values @ ((x-x.mean())/np.sum((x-x.mean())**2)) == pytest.approx(frozen['all_dose_gain'])
    assert frozen['dose_reaching_A_median'] is None
