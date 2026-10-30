"""§240 E132 clarification1: E116 only, within-category grouped OOF analysis."""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression

from bind_c1 import bind, sha

HERE = Path(__file__).resolve().parent
SEED = 20261030
ARMS = ('prompt', 'readout', 'combined')
TOKEN_PATTERN = r'(?u)\b\w\w+\b'


def dump(p, x):
    Path(p).write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')


def member_id(word):
    return hashlib.sha256(word.encode()).hexdigest()[:20]


def fold_ids(rows):
    groups = sorted({r['template_group'] for r in rows})
    if len(groups) != 6:
        raise ValueError('requires all original six prompt templates')
    order = np.random.default_rng(SEED).permutation(len(groups))
    mapping = {groups[j]: f for f, part in enumerate(np.array_split(order, 5)) for j in part}
    assignment = np.array([mapping[r['template_group']] for r in rows])
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate original item')
    return assignment


def contains(text, pick):
    return pick.casefold() in text.casefold()


def predict_category(rows, fold, catalog, block, endpoint_view, arm):
    # This model is category-local: candidates never come from another category.
    analyzer = CountVectorizer(token_pattern=TOKEN_PATTERN).build_analyzer()
    banned = {token for word in catalog for token in analyzer(word)} if endpoint_view == 'B' else set()
    texts = []
    for r in rows:
        text = r['prompt'] if arm == 'prompt' else r['readouts'][str(block)] if arm == 'readout' else r['prompt']+'\n'+r['readouts'][str(block)]
        if not isinstance(text, str):
            raise ValueError('missing original text, no imputation')
        texts.append(text)
    probabilities = np.full((len(rows), len(catalog)), np.nan)
    unavailable, artifacts = [], []
    labels = np.array([r['pick'] for r in rows])
    for f in range(5):
        train, held = np.flatnonzero(fold != f), np.flatnonzero(fold == f)
        if not len(held):
            continue
        if not len(train):
            raise ValueError('empty category training population')
        v = CountVectorizer(token_pattern=TOKEN_PATTERN, lowercase=True, ngram_range=(1,1),
                            min_df=1, max_features=5000, stop_words=sorted(banned) or None)
        try:
            a = v.fit_transform([texts[i] for i in train]);b = v.transform([texts[i] for i in held])
        except ValueError as exc:
            if 'empty vocabulary' not in str(exc):
                raise
            a = b = None
        if banned and a is not None and set(v.vocabulary_) & banned:
            raise ValueError('candidate-mention feature leaked into B vocabulary')
        models = {}
        for j, c in enumerate(catalog):
            y = labels[train] == c
            if not y.any() or y.all():
                unavailable.append(dict(fold=f,member=member_id(c),reason='member_absent_from_train' if not y.any() else 'no_negative_training_class',heldout_items=len(held)))
                continue
            if a is None:
                models[c] = float(y.mean())
                probabilities[held,j] = y.mean()
            else:
                model = LogisticRegression(C=1., penalty='l2', solver='liblinear', max_iter=2000,
                                           tol=1e-4, random_state=SEED).fit(a,y.astype(int))
                if model.n_iter_.max() >= 2000:
                    raise ValueError('unconverged category fit')
                models[c] = model
                probabilities[held,j] = model.predict_proba(b)[:,1]
        artifacts.append(dict(fold=f,vectorizer=v if a is not None else None,models=models,
                              train_ids=[rows[i]['id'] for i in train],heldout_ids=[rows[i]['id'] for i in held]))
    return probabilities, unavailable, artifacts


def bootstrap_weights(rows, draws):
    # AUROC conditions on class counts; retain every category/pick stratum.
    strata = {}
    for i,r in enumerate(rows):
        strata.setdefault((r['category'],r['pick']),[]).append(i)
    rng = np.random.default_rng(SEED)
    weights = np.zeros((draws,len(rows)))
    for _, indices in sorted(strata.items()):
        ix=np.array(indices)
        sampled=rng.choice(ix,size=(draws,len(ix)),replace=True)
        for d in range(draws):weights[d]+=np.bincount(sampled[d],minlength=len(rows))
    return weights


def weighted_auc(y, scores, weights):
    pos=np.flatnonzero(y);neg=np.flatnonzero(~y)
    if not len(pos) or not len(neg):
        return np.full(len(weights),np.nan)
    matrix=(scores[pos,None]>scores[None,neg]).astype(float)+.5*(scores[pos,None]==scores[None,neg])
    a,b=weights[:,pos],weights[:,neg]
    den=a.sum(axis=1)*b.sum(axis=1)
    numerator=((a@matrix)*b).sum(axis=1)
    return np.divide(numerator,den,out=np.full(len(weights),np.nan),where=den>0)


def summarize(rows, predictions, endpoint_mask, nonmodal_only, draws=2000):
    selected=[i for i,r in enumerate(rows) if endpoint_mask[i] and (r['nonmodal'] or not nonmodal_only)]
    subset=[rows[i] for i in selected]
    if not subset:
        return dict(status='NOT_EVALUABLE',n=0,reason='empty endpoint')
    weights=np.vstack([np.ones(len(subset)),bootstrap_weights(subset,draws)])
    columns={a:[] for a in ARMS};categories={};excluded=[]
    for category in sorted({r['category'] for r in rows}):
        local=[i for i,r in enumerate(rows) if r['category']==category]
        data=predictions[category]
        positions={idx:j for j,idx in enumerate(local)}
        subset_ix=np.array([j for j,i in enumerate(selected) if rows[i]['category']==category],dtype=int)
        if not len(subset_ix):
            continue
        local_ix=np.array([positions[selected[j]] for j in subset_ix])
        labels=np.array([subset[j]['pick'] for j in subset_ix])
        cat_cols={a:[] for a in ARMS}
        for k,member in enumerate(data['catalog']):
            finite=np.ones(len(local_ix),bool)
            for arm in ARMS:finite &= np.isfinite(data[arm][local_ix,k])
            y=labels[finite]==member
            if not y.any() or y.all():
                excluded.append(dict(category=category,member=member_id(member),reason='no_positive_and_negative_common_OOF_endpoint',available_items=int(finite.sum())))
                continue
            for arm in ARMS:
                values=weighted_auc(y,data[arm][local_ix[finite],k],weights[:,subset_ix[finite]])
                columns[arm].append(values);cat_cols[arm].append(values)
        if cat_cols['prompt']:
            categories[category]=dict(n=int(len(subset_ix)),eligible_members=len(cat_cols['prompt']),
                auroc={a:float(np.mean(cat_cols[a],axis=0)[0]) for a in ARMS})
        else:
            categories[category]=dict(n=int(len(subset_ix)),eligible_members=0,auroc={a:None for a in ARMS})
    if not columns['prompt']:
        return dict(status='NOT_EVALUABLE',n=len(subset),reason='no evaluable category/member cells',categories=categories,unevaluable_cells=excluded)
    macro={a:np.mean(columns[a],axis=0) for a in ARMS}
    delta=macro['readout']-macro['prompt'];bad=~np.isfinite(delta[1:]);undefined=int(bad.sum())
    ci=None if undefined else list(map(float,np.quantile(delta[1:],[.025,.975])))
    verdict='NOT_EVALUABLE_CI' if ci is None else 'MET' if delta[0]>=.1 and ci[0]>0 else 'NOT_MET'
    intervals={a:(None if not np.isfinite(v[1:]).all() else list(map(float,np.quantile(v[1:],[.025,.975])))) for a,v in macro.items()}
    return dict(status='DEFINED',n=len(subset),eligible_member_cells=len(columns['prompt']),
         macro_ovr_auroc={a:float(v[0]) for a,v in macro.items()},item_bootstrap_95ci=intervals,
         readout_minus_prompt=float(delta[0]),paired_item_bootstrap_95ci=ci,
         undefined_bootstrap_draws=undefined,B_rule=verdict,prompt_derived_reading=bool(delta[0]<=.03),
         categories=categories,unevaluable_cells=excluded)


def analyze(rows, out=None, draws=2000):
    fold=fold_ids(rows);blocks=[b for b in (60,52,44) if all(str(b) in r['readouts'] for r in rows)]
    classes={c:sorted({r['pick'] for r in rows if r['category']==c}) for c in sorted({r['category'] for r in rows})}
    results={'experiment':'E132','exploratory':True,'E107':'NOT_APPLICABLE_ITEM_SPECIFIC_LABEL_NO_CROSS_ITEM_PRIVATE_VARIATION',
             'n':len(rows),'nonmodal':sum(r['nonmodal'] for r in rows),'primary_block':60,
             'bootstrap':dict(draws=draws,seed=SEED,unit='paired item within category/pick strata, fixed OOF'),
             'fold_counts':{str(f):int(sum(fold==f)) for f in range(5)},'blocks':{}}
    allpred={};allmodels={}
    for block in blocks:
        results['blocks'][str(block)]={};allpred[str(block)]={}
        for view in ('A','B'):
            predictions={};missing=[];models={}
            for c,catalog in classes.items():
                ix=[i for i,r in enumerate(rows) if r['category']==c];xs=[rows[i] for i in ix]
                data={'catalog':catalog}
                for arm in ARMS:
                    p,u,a=predict_category(xs,fold[ix],catalog,block,view,arm)
                    data[arm]=p
                    missing += [dict(category=c,arm=arm,**z) for z in u]
                    models[(c,arm)]=a
                predictions[c]=data
            if out is not None:
                joblib.dump(models,out/f'MODELS_{block}_{view}.joblib')
            allmodels[(block,view)]=models
            allpred[str(block)][view]=predictions
            mask=np.array([contains(r['readouts'][str(block)],r['pick']) == (view=='A') for r in rows])
            result={scope:summarize(rows,predictions,mask,scope=='nonmodal',draws) for scope in ('all','nonmodal')}
            result['unevaluable_training_member_folds']=missing
            results['blocks'][str(block)][view]=result
    headline=results['blocks']['60']['B']['nonmodal']
    results['headline']=dict(block=60,endpoint='B',scope='nonmodal',**headline)
    # The registered rule is tested only on B. A remains descriptive.
    for block in results['blocks'].values():
        for report in block['A'].values():
            if isinstance(report,dict) and 'B_rule' in report:report['B_rule']='NOT_APPLICABLE_ENDPOINT_A_DESCRIPTIVE'
    return results,allpred,fold,allmodels


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--spec',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    code=json.loads((HERE/'CODE_SEAL_C1.json').read_text())
    for n,h in code['files'].items():
        if sha(HERE/n)!=h:raise ValueError('committed source hash differs')
    rows,custody=bind(json.loads(args.spec.read_text()))
    lock=HERE/'cache/E132_C1_ONCE.json';lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'spec_sha256':sha(args.spec),'code_seal':sha(HERE/'CODE_SEAL_C1.json'),'out':str(args.out.resolve())},f)
    args.out.mkdir(parents=True,exist_ok=False)
    dump(args.out/'SOURCE_BINDING.PRIVATE.json',custody)
    dump(args.out/'COHORT.PRIVATE.json',rows)
    result,pred,fold,_=analyze(rows,args.out)
    joblib.dump(pred,args.out/'OOF.PRIVATE.joblib')
    dump(args.out/'FOLDS.PRIVATE.json',[dict(id=r['id'],fold=int(fold[i])) for i,r in enumerate(rows)])
    dump(args.out/'METRICS.json',result)
    dump(args.out/'ANALYSIS_SEAL.json',{'experiment':'E132','status':'COMPLETE_ONCE','files':{p.name:sha(p) for p in args.out.iterdir() if p.is_file()}})


if __name__=='__main__':main()
