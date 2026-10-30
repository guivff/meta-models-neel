import pytest
from projects.g_agreement.e95.judging_stages import partition, stage_ids, claim
from projects.g_agreement.readerbench.io import write


def test_original_grid_partitions_without_refill_or_reselection():
    expected = {'a': ('0:real:oracle', 'u:44'),
                'b': ('0:placebo:oracle', 'p:52'),
                'c': ('0:real:oracle', 'u:36'),
                'd': ('0:placebo:nla', 'p:42'),
                'not_chosen': ('0:real:oracle', 'v:60')}
    wanted = {'a', 'b', 'c', 'd'}
    parts = [partition(wanted, expected, i) for i in (1, 2, 3)]
    assert parts == [{'a', 'b'}, {'c'}, {'d'}]
    assert set.union(*parts) == wanted
    assert not any(parts[i] & parts[j] for i in range(3) for j in range(i))
    assert 'not_chosen' not in set.union(*parts)
    with pytest.raises(ValueError): stage_ids(expected, 4)


def test_stage_once_cannot_be_evaded_by_changing_packet_or_output(tmp_path):
    ledger = tmp_path/'e95_60usd'
    claim(ledger, 1, 'a'*64, tmp_path/'first')
    with pytest.raises(FileExistsError):
        claim(ledger, 1, 'b'*64, tmp_path/'second')


def test_stage_two_requires_terminal_stage_one_and_never_accepts_partial(tmp_path):
    ledger = tmp_path/'e95_60usd';out = tmp_path/'first'
    claim(ledger, 1, 'a'*64, out)
    out.mkdir()
    write(out/'JUDGMENT_SEAL.json', dict(status='BLOCKED_PARTIAL_NO_ANALYSIS', judging_stage=1))
    with pytest.raises(ValueError, match='previous complete'):
        claim(ledger, 2, 'b'*64, tmp_path/'second')
    write(out/'JUDGMENT_SEAL.json', dict(status='TERMINAL_BLIND_GRID_NO_ANALYSIS', judging_stage=1))
    claim(ledger, 2, 'b'*64, tmp_path/'second')
