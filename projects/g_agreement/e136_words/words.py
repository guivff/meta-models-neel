"""Prospective §247 E85-words estimator; CPU only, source loader separate."""
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
SEED=20261030

def assignments(rows):
    tasks=sorted({r['base_task'] for r in rows})
    if len(tasks)!=20:raise ValueError('exact20TEST base tasks')
    order=np.random.default_rng(SEED).permutation(len(tasks))
    return {tasks[j]:f for f,part in enumerate(np.array_split(order,5)) for j in part}

def predictor_text(row,exclude=True):
    """Same per-item metadata ban in training and heldout, independent of cue label."""
    if not exclude:return row['text']
    names=('correct','wrong','fact_sentence')
    if any(not isinstance(row.get(k),str) or not row[k].strip() for k in names):
        raise ValueError('frozen true/distractor/fact metadata required; no inferred exclusions')
    analyzer=CountVectorizer(lowercase=True,ngram_range=(1,1),token_pattern=r'(?u)\b\w\w+\b').build_analyzer()
    banned={token for k in names for token in analyzer(row[k])}
    return ' '.join(token for token in analyzer(row['text']) if token not in banned)

def analyze(rows,draws=2000,*,exclude=True):
    if len(rows)!=160 or len({r['id'] for r in rows})!=160:raise ValueError('exact160 uniqueTESTreadouts percue')
    pairs={}
    for r in rows:
        if not isinstance(r['text'],str) or r['split']!='test':raise ValueError('TEST text only, no imputation')
        pairs.setdefault(r['pair_id'],[]).append(r)
    if len(pairs)!=80 or any(len(v)!=2 or {r['label'] for r in v}!={0,1} or len({r['base_task'] for r in v})!=1 for v in pairs.values()):raise ValueError('complete80matchedpairs')
    folds=assignments(rows);pred=np.full(160,np.nan);models=[];weights={};foldaudit=[]
    for f in range(5):
        train=[r for r in rows if folds[r['base_task']]!=f];held_ix=[i for i,r in enumerate(rows) if folds[r['base_task']]==f];held=[rows[i] for i in held_ix]
        if {r['base_task'] for r in train}&{r['base_task'] for r in held}:raise ValueError('task leak')
        v=CountVectorizer(lowercase=True,ngram_range=(1,1),min_df=1,token_pattern=r'(?u)\b\w\w+\b')
        y=np.array([r['label'] for r in train]);empty=False
        try:x=v.fit_transform([predictor_text(r,exclude) for r in train])
        except ValueError as e:
            if 'empty vocabulary' not in str(e):raise
            empty=True
        if empty:
            model=None;pred[held_ix]=float(y.mean());models.append((None,None))
        else:
            model=LogisticRegression(C=1.,penalty='l2',solver='liblinear',max_iter=2000,tol=1e-4,random_state=SEED).fit(x,y)
            if model.n_iter_.max()>=2000:raise ValueError('nonconvergence')
            pred[held_ix]=model.predict_proba(v.transform([predictor_text(r,exclude) for r in held]))[:,1];models.append((v,model))
            for word,w in zip(v.get_feature_names_out(),model.coef_[0]):weights[word]=weights.get(word,0.)+float(w)/5
        foldaudit.append(dict(fold=f,train_ids=[r['id'] for r in train],held_ids=[r['id'] for r in held],empty_training_vocabulary=empty))
    if not np.isfinite(pred).all():raise ValueError('completeOOF')
    y=np.array([r['label'] for r in rows]);point=float(roc_auc_score(y,pred))
    def ci(key):
        groups=sorted({r[key] for r in rows});ix=[np.array([i for i,r in enumerate(rows) if r[key]==g]) for g in groups];rng=np.random.default_rng(SEED)
        vals=[]
        for _ in range(draws):
            sample=np.concatenate([ix[j] for j in rng.integers(len(groups),size=len(groups))]);vals.append(roc_auc_score(y[sample],pred[sample]))
        return list(map(float,np.quantile(vals,[.025,.975])))
    primary=ci('pair_id');cluster=ci('base_task')
    result=dict(n=160,pairs=80,base_tasks=20,oof_auroc=point,item_bootstrap_95ci=primary,base_task_bootstrap_95ci_descriptive=cluster,carried_component='MET' if point>=.8 and primary[0]>.7 else 'NOT MET',seed=SEED,bootstrap_draws=draws,bootstrap_conditional_on_fitted_folds=True,top_positive=sorted([(w,c) for w,c in weights.items() if c>0],key=lambda z:(-z[1],z[0]))[:20],top_negative=sorted([(w,c) for w,c in weights.items() if c<0],key=lambda z:(z[1],z[0]))[:20],empty_fold_vocabularies=sum(r['empty_training_vocabulary'] for r in foldaudit))
    result['candidate_fact_exclusion']=exclude
    result['role']='PRIMARY_EXCLUDED' if exclude else 'DESCRIPTIVE_UNEXCLUDED'
    if not exclude:result['descriptive_threshold_component']=result.pop('carried_component')
    return result,pred,models,foldaudit
