"""§238 clarification4: prospective CPU-only grouped five-fold OOF analysis.
Run once from original owner checkout: python cv238.py --spec INPUTS.json --out CACHE_DIR
Original dev-fit source/guard is preserved and never invoked.
"""
import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
SEED = 20261030
LABEL_SHA = '5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44'
OUTPUT_SHA = '0e630fceabae4b7095ae8b4a670d06e609ed3935b7a7a50f3343b97e4f036551'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def dump(p, x):
    Path(p).write_text(json.dumps(x, indent=2, sort_keys=True) + '\n')


def load_source(spec):
    labels_path = Path(spec['labels'])
    if sha(labels_path) != LABEL_SHA:
        raise ValueError('original E85 label seal mismatch')
    key = {r['public_id']: r for r in json.loads(labels_path.read_text()) if r['split'] == 'test'}
    root = Path(spec['native_root'])
    seal_path = root / 'OUTPUT_SEAL.json'
    if sha(seal_path) != OUTPUT_SHA:
        raise ValueError('original native output seal mismatch')
    seal = json.loads(seal_path.read_text())
    records, members = {}, {}
    for relative, expected in sorted(seal['files'].items()):
        if not relative.startswith('oracle/') or not relative.endswith('.json'):
            continue
        p = (root / relative).resolve()
        if root.resolve() not in p.parents or sha(p) != expected:
            raise ValueError('Oracle member path/checksum mismatch')
        members[relative] = expected
        batch = json.loads(p.read_text())
        if not isinstance(batch, list):
            raise ValueError('original Oracle batch must be a list')
        for r in batch:
            item = r['unit_id']
            if item not in key or item in records or r['reader'] != 'oracle' or r['repeat'] != 0:
                raise ValueError('unexpected/duplicate/non-native item')
            if not isinstance(r['text'], str):
                raise ValueError('missing readout: do not impute')
            label = key[item]
            records[item] = dict(id=item, text=r['text'], quartet=label['matched_set'],
                                 genre=label['genre'], addressed=label['addressed'])
    if set(records) != set(key) or len(records) != 400:
        raise ValueError('requires original complete400 TEST native Oracle corpus')
    rows = [records[k] for k in sorted(records)]
    validate(rows, 100)
    return rows, members


def validate(rows, expected_groups):
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('duplicate item')
    groups = {}
    for r in rows:
        groups.setdefault(r['quartet'], []).append(r)
    if len(groups) != expected_groups:
        raise ValueError('wrong group count')
    for group in groups.values():
        if len(group) != 4 or {(r['genre'], r['addressed']) for r in group} != {(g,a) for g in (0,1) for a in (0,1)}:
            raise ValueError('incomplete original quartet')


def folds(rows):
    groups = sorted({r['quartet'] for r in rows})
    if len(groups) % 5:
        raise ValueError('requires five equally sized folds')
    # Each group has both genres and labels: grouping the whole quartet makes
    # every fold exactly stratified for genre and addressed, without splitting twins.
    order = np.random.default_rng(SEED).permutation(len(groups))
    assignments = {groups[j]: f for f, part in enumerate(np.array_split(order, 5)) for j in part}
    return np.array([assignments[r['quartet']] for r in rows])


def fit_train(rows):
    v = CountVectorizer(lowercase=True, ngram_range=(1,1), min_df=1,
                        token_pattern=r'(?u)\b\w\w+\b')
    x = v.fit_transform([r['text'] for r in rows])
    models = {}
    for target in ('addressed', 'genre'):
        m = LogisticRegression(C=1., penalty='l2', solver='liblinear',
                               max_iter=2000, tol=1e-4, random_state=SEED)
        m.fit(x, [r[target] for r in rows])
        if not np.array_equal(m.classes_, [0,1]) or m.n_iter_.max() >= 2000:
            raise ValueError('invalid/unconverged training model')
        models[target] = m
    return v, models


def reading(auc):
    if auc >= .8:
        return 'CARRIED_IN_WORDS'
    if auc <= .6:
        return 'HIDDEN_STATE_TO_OUTPUT_BOTTLENECK'
    return 'INTERMEDIATE'


def analyze(rows, out=None, bootstrap=2000):
    fold = folds(rows)
    predictions = {k: np.full(len(rows), np.nan) for k in ('addressed', 'genre')}
    coefficients = {k: {} for k in predictions}
    vocabulary_by_fold, model_seals = [], []
    for f in range(5):
        train_ix, held_ix = np.flatnonzero(fold != f), np.flatnonzero(fold == f)
        train, held = [rows[i] for i in train_ix], [rows[i] for i in held_ix]
        v, models = fit_train(train)
        vocabulary_by_fold.append(set(v.vocabulary_))
        if out is not None:
            path = out / f'FOLD_{f}_MODELS.joblib'
            joblib.dump((v, models), path)
            receipt = {'fold': f, 'model_sha256': sha(path),
                       'training_ids_sha256': hashlib.sha256(json.dumps([r['id'] for r in train]).encode()).hexdigest(),
                       'held_out_ids_sha256': hashlib.sha256(json.dumps([r['id'] for r in held]).encode()).hexdigest()}
            dump(out / f'FOLD_{f}_FIT_SEAL.json', receipt)  # precedes held-out transform/predict
            model_seals.append(receipt)
        x = v.transform([r['text'] for r in held])
        for target, model in models.items():
            predictions[target][held_ix] = model.predict_proba(x)[:,1]
            for word, weight in zip(v.get_feature_names_out(), model.coef_[0]):
                coefficients[target][word] = coefficients[target].get(word, 0.) + float(weight) / 5.
    if any(not np.isfinite(p).all() for p in predictions.values()):
        raise ValueError('incomplete OOF coverage')
    groups = sorted({r['quartet'] for r in rows})
    group_ix = [np.array([i for i,r in enumerate(rows) if r['quartet']==g]) for g in groups]
    rng = np.random.default_rng(SEED)
    draws = [np.concatenate([group_ix[j] for j in rng.integers(len(groups), size=len(groups))]) for _ in range(bootstrap)]
    result = {'status':'COMPLETE_ONCE', 'exploratory':True, 'n':len(rows), 'quartets':len(groups),
              'folds':5, 'seed':SEED, 'bootstrap_resamples':bootstrap,
              'bootstrap_unit':'original matched item quartet, all four cells together',
              'empty_existing_readouts':sum(not r['text'] for r in rows),
              'weights':'mean of five training-fold coefficients, absent-fold word coefficient=0; no full-corpus refit'}
    for target,p in predictions.items():
        y = np.array([r[target] for r in rows])
        auc = float(roc_auc_score(y,p))
        boots = [roc_auc_score(y[ix],p[ix]) for ix in draws]
        weights = coefficients[target]
        positive = sorted(((w,c) for w,c in weights.items() if c>0),key=lambda p:(-p[1],p[0]))[:20]
        negative = sorted(((w,c) for w,c in weights.items() if c<0),key=lambda p:(p[1],p[0]))[:20]
        result[target] = {'oof_auroc':auc,'item_bootstrap_95ci':list(map(float,np.quantile(boots,[.025,.975]))),
                          'positive_class':1,'top_positive':[{'word':w,'weight':c} for w,c in positive],
                          'top_negative':[{'word':w,'weight':c} for w,c in negative]}
    result['addressed']['registered_reading'] = reading(result['addressed']['oof_auroc'])
    return result, predictions, fold, vocabulary_by_fold, model_seals


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    code = json.loads((HERE/'CV_CODE_SEAL.json').read_text())
    for name,digest in code['files'].items():
        if sha(HERE/name)!=digest:
            raise ValueError('frozen CV source differs')
    rows,members=load_source(json.loads(args.spec.read_text()))
    lock=HERE/'cache/E85_BOW238_CV_ONCE.json'
    lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as handle:
        json.dump({'spec_sha256':sha(args.spec),'code_seal_sha256':sha(HERE/'CV_CODE_SEAL.json'),'output':str(args.out.resolve())},handle)
    args.out.mkdir(parents=True,exist_ok=False)
    result,pred,fold,_,model_seals=analyze(rows,args.out)
    dump(args.out/'METRICS.json',result)
    dump(args.out/'OOF.PRIVATE.json',[dict(id=r['id'],quartet=r['quartet'],fold=int(fold[i]),genre=r['genre'],addressed=r['addressed'],
         addressed_probability=float(pred['addressed'][i]),genre_probability=float(pred['genre'][i])) for i,r in enumerate(rows)])
    dump(args.out/'SOURCE_BINDING.json',{'original_labels_sha256':LABEL_SHA,'original_output_seal':OUTPUT_SHA,
         'source_members':members,'spec_sha256':sha(args.spec),'code_seal_sha256':sha(HERE/'CV_CODE_SEAL.json'),'fold_model_seals':model_seals})
    dump(args.out/'ANALYSIS_SEAL.json',{'experiment':'E85_READOUT_BOW238_CV','status':'COMPLETE_ONCE','files':{p.name:sha(p) for p in args.out.iterdir() if p.is_file()}})


if __name__=='__main__':
    main()
