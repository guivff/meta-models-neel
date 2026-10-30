from copy import deepcopy
import ast
import subprocess
import pytest
from .test_adapter import fixture
from .sensitivity import mask, report


def sample():
    xs=fixture()
    for x in xs:
        for a,arms in x['arms'].items():
            for arm,z in arms.items():z.update(judgment_id=f"{x['id']}:{a}:{arm}",text_sha256='original')
    x=xs[0]
    mapping=[dict(judgment_id=x['arms'][1]['T']['judgment_id'],original_e113_item_id=x['id'],row=x['row'],alpha=1,arm='T',original_audit=dict(original_readout_sha256='original',judge_readout_sha256='copy'))]
    return xs,mapping


def test_mask_preserves_grid_diagnostics_and_original():
    xs,m=sample();before=deepcopy(xs);masked,counts=mask(xs,m)
    assert xs==before and len(masked)==336 and sum(counts.values())==1
    assert masked[0]['arms'][1]['T']['score'] is None
    assert masked[0]['arms'][1]['T']['degenerate']==before[0]['arms'][1]['T']['degenerate']
    assert masked[0]['arms'][1]['R']==before[0]['arms'][1]['R']


@pytest.mark.parametrize('field,value',[('row','fact_recall'),('alpha',2),('arm','W'),('original_e113_item_id','unknown'),('judgment_id','unknown')])
def test_bad_mapping_rejected(field,value):
    xs,m=sample();m[0][field]=value
    with pytest.raises(ValueError):mask(xs,m)


def test_duplicate_and_text_hash_rejected():
    xs,m=sample()
    with pytest.raises(ValueError):mask(xs,m+m)
    xs[0]['arms'][1]['T']['text_sha256']='changed'
    with pytest.raises(ValueError):mask(xs,m)


def test_full_bootstrap_sensitivity():
    xs,m=sample();r=report(xs,m)
    assert r['redacted_records']==1 and r['result']['rules']['R_IR1']=='MET'
    assert r['result']['rows'][xs[0]['row']][1]['degeneracy']['total']==252


def test_original_scientific_functions_unchanged():
    from .adapter import ROOT,HERE
    old=ast.parse(subprocess.check_output(['git','show','0bcbda1f9:projects/g_agreement/e117_analysis/adapter.py'],cwd=ROOT,text=True))
    new=ast.parse((HERE/'adapter.py').read_text())
    for name in ('degenerate','classify','analyze'):
        get=lambda tree:ast.dump(next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name==name))
        assert get(old)==get(new)
