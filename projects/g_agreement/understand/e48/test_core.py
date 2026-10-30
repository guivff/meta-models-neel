import numpy as np
import pytest
from .core import auc,words,shown,fit_score,rules,correlations

def test_auc_orientation_and_ties():
    assert auc([1,1,0,0],[2,1,1,0])==.875
    assert auc([1,0],[0,1])==0
    with pytest.raises(ValueError):auc([1,1],[1,2])
def test_words_strip_commands_and_syntax():
    assert words('  \\frac{Happy}{word} "quoted" (text) 123')==['happy','word','quoted','text']
def test_shown_fixed_directions():
    assert shown('(x))\n  "q" |')=={'close_minus_open_paren':1,'double_quote_parity':0,'single_quote_parity':0,'leading_space_runs':2,'pipe_count':1}
def test_vocabulary_is_dev_only():
    class Tok:
        def decode(self,ids,**kw):return ' '.join('a' if x==1 else 'b' for x in ids)
    dev=[{'ids':[1]},{'ids':[2]}]*4;test=[{'ids':[99]}]
    score,meta=fit_score(dev,test,[0,1]*4,'presence',Tok())
    assert meta['vocabulary']==2 and abs(score[0])<1e-9
def test_falsifiers_and_no_ci_veto_added():
    rows=[{'key':str(i),'row':r,'asked':.5,'presence':.9,'words':.8} for i,r in enumerate(['prose_paren','python_string','list_depth'])]
    p={'rho':.7,'ci95':[.4,.8]};w={'rho':.9,'rho_difference':.2,'difference_ci95':[-.1,.4]}
    r=rules(rows,p,w)
    assert r['H3']['falsification_rule'] and r['H5']['falsification_rule'] and r['H5']['support_rule']
def test_paired_identical_correlation_difference():
    x=[0,1,2,3];r=correlations(x,[0,1,3,2],np.random.default_rng(1),n=30,other=x)
    assert r['rho_difference']==0 and r['difference_ci95']==[0,0]
