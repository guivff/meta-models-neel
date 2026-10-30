"""E113 §226 CPU kernel. No real capture loading or test evaluation at import."""
import warnings
import numpy as np
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
CS=(0.01,0.1,1.,10.,100.)
SEED=20261029
ROWS=('nesting_depth','indent_level','page_range_digit','fact_recall','format_plan','language_plan')
POSITIONS=('injected_activation','first_generated_token')
def validate_ids(dev_ids,test_ids):
    assert len(dev_ids)==len(set(dev_ids))==84
    assert len(test_ids)==len(set(test_ids))==84
    assert set(dev_ids).isdisjoint(test_ids),'dev/test identity overlap'
def validate_x(x,y):
    x=np.asarray(x,dtype=float);y=np.asarray(y)
    assert x.ndim==2 and len(x)==len(y)==84 and np.isfinite(x).all()
    assert set(y.tolist())=={0,1} and np.bincount(y.astype(int)).min()>=5
    return x,y.astype(int)
def model(c):
    return make_pipeline(StandardScaler(),LogisticRegression(C=c,max_iter=2000,solver='lbfgs',random_state=SEED))
def fit_dev(x,y):
    """Five folds fit scaler inside each train fold; select C using dev AUROC only."""
    x,y=validate_x(x,y);folds=list(StratifiedKFold(5,shuffle=True,random_state=SEED).split(x,y));scores=[]
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning)
        for c in CS:
            auc=[]
            for train,valid in folds:
                m=model(c).fit(x[train],y[train]);auc.append(float(roc_auc_score(y[valid],m.decision_function(x[valid]))))
            scores.append({'C':c,'fold_AUROC':auc,'mean_AUROC':float(np.mean(auc))})
        # Grid ascending: exact ties select smaller C. Orientation fixed by original class1.
        best=max(range(len(CS)),key=lambda i:scores[i]['mean_AUROC'])
        fitted=model(CS[best]).fit(x,y)
    return fitted,{'selected_C':CS[best],'dev_CV':scores,'seed':SEED,'test_used_for_selection':False}
def evaluate_test_once(fitted,x,y):
    """Only the future sealed once-only driver may call this on real test data."""
    x,y=validate_x(x,y)
    return float(roc_auc_score(y,fitted.decision_function(x)))
def decisions(aucs):
    """Require complete row × layer × position grid; no missing-to-negative conversion."""
    assert set(aucs)==set(ROWS)
    grids=[set(aucs[r]) for r in ROWS];assert grids[0] and all(g==grids[0] for g in grids)
    for r in ROWS:
        for layer in grids[0]:
            assert set(aucs[r][layer])==set(POSITIONS)
            assert all(np.isfinite(v) and 0<=v<=1 for v in aucs[r][layer].values())
    maxima={r:max(v for ps in aucs[r].values() for v in ps.values()) for r in ROWS}
    return {'R_IN1':sum(maxima[r]>=.90 for r in ROWS[:3])>=2,
            'falsifier':sum(maxima[r]<=.65 for r in ROWS[:3])>=2 and all(maxima[r]>=.90 for r in ROWS[3:]),
            'row_max_AUROC':maxima}
