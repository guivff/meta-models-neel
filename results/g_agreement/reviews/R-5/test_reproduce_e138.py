import importlib.util
from pathlib import Path
import pytest
spec = importlib.util.spec_from_file_location('r5_e138', Path(__file__).with_name('reproduce_e138.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def fixture(recipient=4, donor=34, random=0):
    out = []
    for arm in m.ARMS:
        for i in range(84):
            code = (['R'] if i < recipient else ['D'] if i < recipient+donor else []) if arm == 'donor' else (['R'] if i < (84 if arm == 'clean' else random) else [])
            out.append(dict(item_id=str(i), arm=arm, code=code))
    return out


def test_boundary_donor_primary():
    assert m.reproduce(fixture())['donor_primary_observed'] == 'MET'
    assert m.reproduce(fixture(recipient=5))['donor_primary_observed'] == 'NOT MET'
    assert m.reproduce(fixture(donor=33))['donor_primary_observed'] == 'NOT MET'


def test_random_only_counts_against_never_rescues():
    for random in (0, 16, 17, 84):
        assert m.reproduce(fixture(donor=0, random=random))['donor_primary_observed'] == 'NOT MET'
        assert m.reproduce(fixture(random=random))['donor_primary_observed'] == 'MET'
    assert m.reproduce(fixture(random=16))['random_counts_against_observed'] == 'NOT MET'
    assert m.reproduce(fixture(random=17))['random_counts_against_observed'] == 'WITHDRAW WORDING'


def test_coherence_none_dual_missing_separate():
    records = fixture()
    records[84]['code'] = ['R', 'D']
    records[85]['code'] = None
    result = m.reproduce(records)['arms']['donor']
    assert result['dual_or_multiple']['k'] == 1
    assert result['missing_n'] == 1
    assert result['none']['k'] == 46
    assert result['recipient_old']['k'] == 2
    assert result['recipient_mentioned']['k'] == 3
    assert result['donor_old']['n'] == 83


def test_missing_does_not_turn_into_positive_evidence():
    records = fixture()
    records[167]['code'] = None
    assert not m.reproduce(records)['donor_primary_robust_to_missing']
    for r in records:
        if r['arm'] == 'random':
            r['code'] = None
    result = m.reproduce(records)
    assert result['random_counts_against_observed'] == 'NOT EVALUABLE'
    assert result['arms']['random']['none']['rate'] is None


@pytest.mark.parametrize('damage', ['duplicate', 'missing', 'bad_role'])
def test_bad_census_or_code_rejected(damage):
    records = fixture()
    if damage == 'duplicate': records.append(records[0])
    elif damage == 'missing': records.pop()
    else: records[0]['code'] = ['invented']
    with pytest.raises(ValueError): m.reproduce(records)


def test_committed_owner_schema_independent_full_ci_comparison():
    from projects.g_agreement.e138_analysis.analysis import analyze
    from projects.g_agreement.e138_analysis.test_analysis import rows
    from reproduce_e118b import compare
    data = rows()
    for i, row in enumerate(data):
        row['arms'] = dict(clean='recipient-old' if i < 63 else 'none',
                           donor='recipient-old' if i < 4 else 'donor-old' if i < 38 else 'none',
                           random=['recipient-old', 'donor-old'] if i == 0 else 'recipient-old' if i < 17 else 'none')
    data[80]['arms']['donor'] = None
    data[81]['arms']['random'] = None
    # Compare every numeric/count/CI/reading field; descriptive prose is not copied.
    compare(m.reproduce_owner_rows(data), analyze(data))


@pytest.mark.parametrize('mapping', [dict(A='recipient-old', B='donor-old', OTHER='other'),
                                    dict(A='donor-old', B='recipient-old', OTHER='other'),
                                    dict(A='recipient-old', B='other')])
def test_lossless_role_transport_all_subsets(mapping):
    from itertools import combinations
    from projects.g_agreement.e138_analysis.role_codes import normalize
    for size in range(1, len(mapping)+1):
        for letters in combinations(mapping, size):
            code = dict(id='synthetic', category='states_value', values=list(letters), evidence='retained')
            before = repr(code)
            try:
                expected = normalize(code, 'KEPT', 'synthetic', mapping)
            except ValueError:
                with pytest.raises(ValueError): m.original_roles(code, 'KEPT', 'synthetic', mapping)
            else:
                assert m.original_roles(code, 'KEPT', 'synthetic', mapping) == expected
            assert repr(code) == before
    for category in ('silent', 'exhibits', 'names_property_without_value'):
        assert m.original_roles(dict(id='synthetic',category=category,values=[]), 'KEPT', 'synthetic', mapping) == []
    assert m.original_roles(None, 'UNPARSEABLE', 'synthetic', mapping) is None
    assert m.original_roles(dict(id='synthetic',category='UNPARSEABLE',values=[]), 'UNPARSEABLE', 'synthetic', mapping) is None


def test_bound_fields_and_invalid_role_transport():
    good = dict(code=dict(id='j',category='states_value',values=['B','A']), status='KEPT',
                judgment_id='j',value_roles=dict(A='recipient-old',B='donor-old'))
    refs = {k:{'ref':k} for k in good}
    assert m.expand_roles({'e104_role_code':refs}, good.__getitem__) == ['recipient-old','donor-old']
    assert m.expand_roles({'e104_role_code':refs}, good.__getitem__) == m.original_roles(**good)
    for key in good:
        broken = dict(refs); broken[key] = good[key]
        with pytest.raises(ValueError): m.expand_roles({'e104_role_code':broken}, good.__getitem__)
    for change in [dict(status='REFUSED'),dict(judgment_id='different'),dict(code=None),
                   dict(value_roles=dict(A='other',B='other')),dict(status='UNPARSEABLE'),
                   dict(code=dict(id='j',category='silent',values=['A'])),
                   dict(code=dict(id='j',category='states_value',values=['A','A'])),
                   dict(code=dict(id='j',category='states_value',values=['NEW']))]:
        with pytest.raises(ValueError): m.original_roles(**(good|change))
