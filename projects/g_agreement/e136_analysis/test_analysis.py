import copy
import numpy as np
import pytest
from .analysis import CUES, analyze, validate, probe, behaviour, paired_summary

def rows():
    out=[]
    for cue in CUES:
        for t in range(25):
            for k in range(4):
                for y in (0,1):
                    out.append(dict(id=f'{cue}-{t}-{k}-{y}', cue=cue, pair_key=f'{cue}-{t}-{k}',
                        base_task=t, template=k, split='dev' if t<5 else 'test', label=y,
                        block=44, read_index=8, original_read_index=8, candidate_ids=[10,20],
                        correct_index=1, user_text_sha256=f'synthetic-{t}-{k}',
                        hidden44=[2*y-1,0], pair_logits=[0.,float(y)]))
    return out

def test_full_synthetic_and_paired_orientation():
    r=analyze(rows())
    for q in r['cues'].values():
        assert q['probe']['test_auroc']==1 and q['probe']['gate'] is True
        assert q['behaviour']['margin_change']['estimate']==1
        assert q['behaviour']['margin_change']['ci95']==[1.,1.]
        assert q['behaviour']['whole_task_sensitivity']['kept']==20

def test_fit_has_no_test_leakage():
    a=rows()[:200]; b=copy.deepcopy(a)
    for r in b:
        if r['split']=='test':r['hidden44'][0]*=-1
    pa,pb=probe(a),probe(b)
    assert pa['coefficients']==pb['coefficients'] and pa['intercept']==pb['intercept']
    assert pb['test_auroc']==0 and not pb['gate']

def test_missing_capture_is_unknown_not_failed_gate():
    a=rows()[:200];a[0]['hidden44']=None
    assert probe(a)['gate'] is None

def test_missing_pair_never_zero_imputed():
    a=rows();a[40]['pair_logits']=None
    b=behaviour({k:p for k,p in validate(a).items() if p[0]['cue']==CUES[0]})
    assert b['missing_pairs']==1 and b['margin_change']['kept']==79
    assert b['whole_task_sensitivity']['kept']==19

@pytest.mark.parametrize('change', ['duplicate','task_leak','wrong_block','wrong_token','wrong_twin','bad_logits','bad_hidden','bad_candidates'])
def test_custody_rejections(change):
    a=rows()
    if change=='duplicate':a[1]['id']=a[0]['id']
    if change=='task_leak':a[40]['base_task']=0
    if change=='wrong_block':a[0]['block']=52
    if change=='wrong_token':a[0]['read_index']=7
    if change=='wrong_twin':a[0]['correct_index']=0
    if change=='bad_logits':a[0]['pair_logits']=[float('nan'),0]
    if change=='bad_hidden':a[0]['hidden44']=[float('inf')]
    if change=='bad_candidates':a[0]['candidate_ids']=[20,10]
    with pytest.raises(ValueError):validate(a)

def test_bootstrap_deterministic_and_empty_unknown():
    assert paired_summary([1.,-1.,2.])==paired_summary([1.,-1.,2.])
    assert paired_summary([])['estimate'] is None

def test_correctness_sign_reversal():
    a=rows()
    for r in a:r['correct_index']=0
    p={k:p for k,p in validate(a).items() if p[0]['cue']==CUES[0]}
    assert behaviour(p)['margin_change']['estimate']==-1

def test_gate_exact_boundary(monkeypatch):
    from . import analysis
    monkeypatch.setattr(analysis,'roc_auc_score',lambda *a:.90)
    assert probe(rows()[:200])['gate'] is True
    monkeypatch.setattr(analysis,'roc_auc_score',lambda *a:.899999)
    assert probe(rows()[:200])['gate'] is False


def test_deviation2_exact_scope_and_dispositions():
    a=rows()
    assert len(a)==400 and len(validate(a))==200
    result=analyze(a)
    assert set(result['cues'])=={'sycophancy_pressure','misuse_intent'}
    assert result['planned_pairs']==200
    assert set(result['not_run_cues'])=={'unreliable_tool','instruction_to_withhold'}
    for cue in CUES:
        assert sum(r['cue']==cue and r['split']=='dev' for r in a)==40
        assert sum(r['cue']==cue and r['split']=='test' for r in a)==160

@pytest.mark.parametrize('cue', ['unreliable_tool','instruction_to_withhold'])
def test_excluded_cue_rejected_even_with_correct_row_count(cue):
    a=rows()
    for r in a:
        if r['cue']==CUES[0]:r['cue']=cue
    with pytest.raises(ValueError):validate(a)

def test_historical_partial_and_unamended_spec_rejected():
    from .run import validate_scope
    a=rows()
    with pytest.raises(ValueError):validate(a+a)
    with pytest.raises(ValueError):validate(a[:-2])
    for spec in ({}, {'deviation':1,'cues':list(CUES)},
                 {'deviation':2,'cues':[CUES[0]]}):
        with pytest.raises(ValueError):validate_scope(spec)
    validate_scope({'deviation':2,'cues':list(CUES)})
