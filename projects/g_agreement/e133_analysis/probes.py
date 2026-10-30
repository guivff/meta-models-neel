"""§241/e39e8f475 probes: binary twin primary; current+previous identity descriptive."""
import warnings
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.exceptions import ConvergenceWarning
from projects.g_agreement.e127_analysis.common import require
LAYERS=(36,44,48,52,56,60)


def analyze(pairs,fixed_name_list):
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
            entry=dict(dev_pairs=len(dev),test_pairs=len(test),target=target,role='PRIMARY_PROBE_DESCRIPTIVE_TO_R_NL1'if target=='twin_identity'else'DESCRIPTIVE_IDENTITY_PROBE',model='E109 fixed LogisticRegression C1/lbfgs/max_iter2000/seed0; no scaling/tuning',n_fixed_classes=len(fixed))
            if len(dev)!=30 or len(set(labels))<2 or any(m['vectors'].get(layer)is None for m in train):
                entry.update(status='NOT EVALUABLE',reason='requires first30 multi-hop pairs, finite dev vectors and at least2 dev classes');out[str(layer)][target]=entry;continue
            x=np.asarray([m['vectors'][layer]for m in train],dtype=float)
            require(x.ndim==2 and np.isfinite(x).all(),'finite original dev activations')
            model=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs')
            try:
                with warnings.catch_warnings():warnings.simplefilter('error',ConvergenceWarning);model.fit(x,labels)
            except ConvergenceWarning:
                entry.update(status='NOT EVALUABLE',reason='fixed dev-only probe failed convergence; no tuning/refit, R-NL1 unchanged');out[str(layer)][target]=entry;continue
            groups={}
            for kind,selected in [('multi_hop_test',test),('one_hop_descriptive',[p for p in pairs if p['kind']=='one_hop'])]:
                rows=[m for p in selected for m in p['members']];known=[m for m in rows if m['vectors'].get(layer)is not None];missing=len(rows)-len(known);classes=[];binary=None
                if known:
                    xx=np.asarray([m['vectors'][layer]for m in known],dtype=float);require(xx.ndim==2 and xx.shape[1]==x.shape[1]and np.isfinite(xx).all(),'finite test vectors, fixed dimension')
                    require(all(label(m)in fixed for m in known),'test labels within frozen fixed list')
                    probs=model.predict_proba(xx)
                    for j,value in enumerate(fixed):
                        yy=np.asarray([label(m)==value for m in known],dtype=int)
                        fitted=value in model.classes_;column=None if not fitted else list(model.classes_).index(value)
                        auc=None if not fitted or len(set(yy))<2 else float(roc_auc_score(yy,probs[:,column]))
                        classes.append(dict(class_index=j,trained=bool(fitted),AUROC=auc,n_positive=int(yy.sum()),n_negative=int((1-yy).sum())))
                    if target=='twin_identity':binary=classes[1]['AUROC']
                eligible=[c['AUROC']for c in classes if c['AUROC']is not None]
                groups[kind]=dict(planned_n=len(rows),n=len(known),missing_n=missing,unseen_target_n=sum(label(m)not in model.classes_ for m in known),classes=classes,binary_AUROC=binary,macro_ovr_AUROC=None if target=='twin_identity'or not eligible else float(np.mean(eligible)),n_evaluable_classes=len(eligible),n_trained_classes=len(model.classes_),n_fixed_classes=len(fixed),status='DESCRIPTIVE'if eligible else'NOT EVALUABLE')
            entry.update(status='DESCRIPTIVE',groups=groups);out[str(layer)][target]=entry
    babi=[p for p in pairs if p['kind']=='babi_qa2']
    return dict(babi_qa2_episode_cv=None if not babi else episode_cv(babi,fixed_name_list),primary='binary twin identity (which frozen recipient is current); AUROC',descriptive='current holder and previous holder, each multiclass over fixed names, macroOVR; absent/unseen classes explicit',split='first30 selected multi-hop pairs DEV, remaining TEST; pair members NEVER cross folds; one-hop transfer descriptive; QA2 separately episode-grouped CV',threshold_role='none of these probe metrics enters R-NL1',layers=out)


def episode_cv(pairs,fixed_name_list):
    """§242 QA2 descriptive probes; whole source episodes are held out together."""
    from sklearn.model_selection import GroupKFold
    require(all(p['kind']=='babi_qa2'and p.get('source_episode_id')is not None for p in pairs),'original CPU QA2 source episode IDs')
    out={}
    for layer in LAYERS:
        out[str(layer)]={}
        for target in ('twin_identity','current','previous'):
            label=lambda m:m['member']if target=='twin_identity'else m[target]
            fixed=[0,1]if target=='twin_identity'else fixed_name_list
            rows=[(m,p['source_episode_id'])for p in pairs for m in p['members']]
            known=[(m,e)for m,e in rows if m['vectors'].get(layer)is not None]
            groups=[e for _,e in known];n_episodes=len(set(groups));folds=[]
            report=dict(planned_n=len(rows),n_vectors=len(known),missing_vectors_n=len(rows)-len(known),n_source_episodes=len({e for _,e in rows}),n_episodes_with_vectors=n_episodes,n_folds=min(5,n_episodes),target=target)
            if n_episodes<2:
                report.update(status='NOT EVALUABLE',reason='fewer than2 observed source episodes; no episode CV',binary_AUROC=None,macro_ovr_AUROC=None);out[str(layer)][target]=report;continue
            x=np.asarray([m['vectors'][layer]for m,_ in known],dtype=float);y=np.asarray([label(m)for m,_ in known]);require(x.ndim==2 and np.isfinite(x).all()and all(v in fixed for v in y),'finite original QA2 vectors and frozen targets')
            predicted={v:{}for v in fixed}
            for fold,(train,test)in enumerate(GroupKFold(n_splits=min(5,n_episodes)).split(x,y,groups)):
                train_episodes={groups[i]for i in train};test_episodes={groups[i]for i in test};require(train_episodes.isdisjoint(test_episodes),'no source-episode leakage')
                info=dict(fold=fold,n_train=len(train),n_test=len(test),train_episodes=len(train_episodes),test_episodes=len(test_episodes),source_episode_overlap=0)
                if len(set(y[train]))<2:info['status']='NOT EVALUABLE: constant training target';folds.append(info);continue
                model=LogisticRegression(C=1.,max_iter=2000,random_state=0,solver='lbfgs')
                try:
                    with warnings.catch_warnings():warnings.simplefilter('error',ConvergenceWarning);model.fit(x[train],y[train])
                except ConvergenceWarning:info['status']='NOT EVALUABLE: fixed fit did not converge, no retuning';folds.append(info);continue
                scores=model.predict_proba(x[test])
                for j,value in enumerate(model.classes_):
                    for i,score in zip(test,scores[:,j]):predicted[value][int(i)]=float(score)
                info['status']='OUT_OF_EPISODE_PREDICTIONS';folds.append(info)
            classes=[]
            for j,value in enumerate(fixed):
                ids=sorted(predicted[value]);yy=[int(y[i]==value)for i in ids]
                auc=None if len(set(yy))<2 else float(roc_auc_score(yy,[predicted[value][i]for i in ids]))
                classes.append(dict(class_index=j,AUROC=auc,n_predictions=len(ids),missing_predictions_n=len(known)-len(ids),n_positive=sum(yy),n_negative=len(yy)-sum(yy)))
            eligible=[v['AUROC']for v in classes if v['AUROC']is not None]
            report.update(status='DESCRIPTIVE'if eligible else'NOT EVALUABLE',classes=classes,folds=folds,binary_AUROC=classes[1]['AUROC']if target=='twin_identity'else None,macro_ovr_AUROC=None if target=='twin_identity'or not eligible else float(np.mean(eligible)),n_evaluable_classes=len(eligible))
            out[str(layer)][target]=report
    return dict(scope='QA2 descriptive only; never enters R-NL1',grouping='ORIGINAL source episode, all twins and members together',folds='deterministic GroupKFold min(5, observed episodes); fewer than2 not evaluable',model='fixed E109 C1/lbfgs/max_iter2000/seed0; no scaling/tuning',layers=out)
