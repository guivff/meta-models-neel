from pathlib import Path
import pytest
from . import adapter as a, exploratory_note1 as e, rules
from .test_rules import transplanted
from .test_adapter import Fixture


def native(shift=-.13613942623138428):
    return dict(R_BEV1='NOT MET',R_BEV2='NOT RUN',selected_contrast_id='formal_vs_informal',native_addressed_shift=dict(estimate=shift,CI95=[shift-.01,shift+.01]))


def test_negative_delta_negative_native_fraction_and_labels():
    result=e.result(transplanted(t=-.08,s=0),native())
    assert result['delta']['CI95']==pytest.approx([-.08,-.08])
    assert result['exploratory_negative_direction_evidence'] is True
    assert result['fraction_recovered']['estimate']==pytest.approx(-.08/native()['native_addressed_shift']['estimate'])
    assert result['confirmatory_record']==dict(R_BEV1='NOT MET',R_BEV2='NOT RUN')
    assert result['exploratory'] and result['post_hoc']


def test_zero_and_positive_not_negative_direction_evidence():
    for delta in (0,.1):
        result=e.result(transplanted(t=delta,s=0),native())
        assert result['exploratory_negative_direction_evidence'] is False
    assert 'CI includes zero' in e.result(transplanted(t=0,s=0),native())['reading']


def test_unclipped_fraction_no_rounding_of_native():
    result=e.result(transplanted(t=-.5,s=0),native())
    assert result['fraction_recovered']['estimate']>1 and result['fraction_recovered']['clipped'] is False
    assert result['fraction_recovered']['denominator']==native()['native_addressed_shift']['estimate']


def test_wrong_contrast_or_changed_confirmatory_result_refused():
    for key,value in [('selected_contrast_id','hedged_vs_direct'),('R_BEV1','MET'),('R_BEV2','MET')]:
        gate=native();gate[key]=value
        with pytest.raises(ValueError):e.result(transplanted(t=-.1,s=0),gate)
    with pytest.raises(ValueError):e.result(transplanted(t=-.1,s=0),native(shift=.2))


def test_missing_cells_not_zero_or_reselected():
    with pytest.raises(ValueError):e.result(transplanted()[:-1],native())


def test_separate_exploratory_guard_no_confirmatory_changes(tmp_path,monkeypatch):
    f=Fixture(tmp_path,monkeypatch);f.gate(test_shift=-2)
    monkeypatch.setattr(e,'CONTRAST','self')  # synthetic contrast ID only
    original={phase:a.sha(a.CANONICAL/phase/'ANALYSIS_SEAL.json')for phase in ('dev_selection','native_test')}
    def negative(raw,index):
        for x in raw:x['pair_logprobs'][1]=[-1003 if x['condition']=='T' else -1001,-1000]
    spec=f.output('transplant',mutator=negative);wrapper=a.read(spec['output_seal'])
    ms=a.read(Path(spec['output_seal']).parent/'MEASUREMENTS.json')
    ip=f.bundle('exploratory_index',{'RAW_INDEX.json':dict(transplant={x['id']:x['conditions']for x in ms})},experiment='E122',status='SOURCE_POINTERS_ONLY',contrast_source_sha256=a.CONTRAST_SHA,source_e85_bank_sha256=a.E85_BANK_SHA,source_seals=wrapper['source_seals'])
    plan=dict(f.base,raw_index_seal=str(ip),raw_index_sha256=a.sha(ip))
    seal=e.run(plan,'synthetic-commit');result=a.read(seal.parent/'RESULTS.json')
    assert result['delta']['estimate']==-2 and result['fraction_recovered']['estimate']==1
    assert all(a.sha(a.CANONICAL/phase/'ANALYSIS_SEAL.json')==h for phase,h in original.items())
    assert not (a.CANONICAL/'transplant_ONCE.json').exists() and not (a.CANONICAL/'transplant').exists()
    for file in seal.parent.glob('*.json'):
        record=a.read(file);assert record['exploratory'] is True and record['post_hoc'] is True
    assert a.read(a.CANONICAL/'exploratory_note1_ONCE.json')['post_hoc'] is True
    with pytest.raises(ValueError,match='already claimed'):e.run(plan,'synthetic-commit')


def test_cli_commit_gate_before_plan_IO(monkeypatch):
    import sys
    monkeypatch.setattr(sys,'argv',['exploratory','--plan','must-not-open'])
    def fail():raise ValueError('uncommitted')
    monkeypatch.setattr(a,'committed',fail);monkeypatch.setattr(a,'read',lambda p:pytest.fail('opened before commit check'))
    with pytest.raises(ValueError,match='uncommitted'):e.main()
