"""E137: identical E133 fixed fits, retaining original once-produced private evidence."""
import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning
from projects.g_agreement.e127_analysis.common import require
LAYERS=(36,44,48,52,56,60)


def analyze(pairs,fixed_name_list,audit=None):
    require(isinstance(fixed_name_list,list)and len(set(fixed_name_list))==len(fixed_name_list)and all(isinstance(v,str)and v for v in fixed_name_list),'frozen CPU fixed name list')
    multi=sorted([p for p in pairs if p['kind']=='multi_hop'],key=lambda p:p['generation_index'])
    dev=multi[:30];test=multi[30:];out={}
    for layer in LAYERS:
        out[str(layer)]={}
        for target in ('twin_identity','current','previous'):
            train=[m for p in dev for m in p['members']]
            label=lambda m:m['member']if target=='twin_identity'else m[target]
            labels=[label(m)for m in train];fixed=[0,1]if target=='twin_identity'else fixed_name_list
            require(all(v in fixed for v in labels),'frozen probe targets, no invented label universe')
            entry=dict(dev_pairs=len(dev),test_pairs=len(test),target=target,role='PRIMARY_PROBE_DESCRIPTIVE_TO_R_NL2'if target=='twin_identity'else'DESCRIPTIVE_IDENTITY_PROBE',model='E109 fixed LogisticRegression C1/lbfgs/max_iter2000/seed0; no scaling/tuning',n_fixed_classes=len(fixed))
            if len(dev)!=30 or len(set(labels))<2 or any(m['vectors'].get(layer)is None for m in train):
                entry.update(status='NOT EVALUABLE',reason='requires first30 multi-hop pairs, finite dev vectors and at least2 dev classes');out[str(layer)][target]=entry;continue
            x=np.asarray([m['vectors'][layer]for m in train],dtype=float)
            require(x.ndim==2 and np.isfinite(x).all(),'finite original dev activations')
            model=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs')
            try:
                with warnings.catch_warnings():warnings.simplefilter('error',ConvergenceWarning);model.fit(x,labels)
            except ConvergenceWarning:
                entry.update(status='NOT EVALUABLE',reason='fixed dev-only probe failed convergence; no tuning/refit, R-NL1 unchanged');out[str(layer)][target]=entry;continue
            saved=dict(layer=layer,target=target,classes=model.classes_.tolist(),coefficients=model.coef_.tolist(),intercepts=model.intercept_.tolist(),dev_pair_ids=[p['pair_id']for p in dev],test_pair_ids=[p['pair_id']for p in test],dev_labels=labels,predictions={})
            groups={}
            for kind,selected in [('multi_hop_test',test),('one_hop_descriptive',[p for p in pairs if p['kind']=='one_hop'])]:
                rows=[m for p in selected for m in p['members']];known=[m for m in rows if m['vectors'].get(layer)is not None];missing=len(rows)-len(known);classes=[];binary=None
                if known:
                    xx=np.asarray([m['vectors'][layer]for m in known],dtype=float);require(xx.ndim==2 and xx.shape[1]==x.shape[1]and np.isfinite(xx).all(),'finite test vectors, fixed dimension')
                    require(all(label(m)in fixed for m in known),'test labels within frozen fixed list')
                    probs=model.predict_proba(xx)
                    saved['predictions'][kind]=dict(item_ids=[m.get('item_id')for m in known],labels=[label(m)for m in known],probabilities=probs.tolist())
                    for j,value in enumerate(fixed):
                        yy=np.asarray([label(m)==value for m in known],dtype=int)
                        fitted=value in model.classes_;column=None if not fitted else list(model.classes_).index(value)
                        auc=None if not fitted or len(set(yy))<2 else float(roc_auc_score(yy,probs[:,column]))
                        classes.append(dict(class_index=j,trained=bool(fitted),AUROC=auc,n_positive=int(yy.sum()),n_negative=int((1-yy).sum())))
                    if target=='twin_identity':binary=classes[1]['AUROC']
                eligible=[c['AUROC']for c in classes if c['AUROC']is not None]
                groups[kind]=dict(planned_n=len(rows),n=len(known),missing_n=missing,unseen_target_n=sum(label(m)not in model.classes_ for m in known),classes=classes,binary_AUROC=binary,macro_ovr_AUROC=None if target=='twin_identity'or not eligible else float(np.mean(eligible)),n_evaluable_classes=len(eligible),n_trained_classes=len(model.classes_),n_fixed_classes=len(fixed),status='DESCRIPTIVE'if eligible else'NOT EVALUABLE')
            if audit is not None:audit.append(saved)
            entry.update(status='DESCRIPTIVE',groups=groups);out[str(layer)][target]=entry
    babi=[p for p in pairs if p['kind']=='babi_qa2']
    return dict(babi_qa2_episode_cv=None,primary='binary twin identity (which frozen recipient is current); AUROC',descriptive='current holder and previous holder, each multiclass over fixed names, macroOVR; absent/unseen classes explicit',split='first30 selected multi-hop pairs DEV, remaining TEST; pair members NEVER cross folds; one-hop transfer descriptive; QA2 separately episode-grouped CV',threshold_role='none of these probe metrics enters R-NL2',layers=out)
