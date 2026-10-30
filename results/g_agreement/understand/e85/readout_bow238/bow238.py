"""E85 §238.2.2: CPU-only, dev-fit word-unigram models, then frozen test.

Run once: python bow238.py --spec CPU_INPUTS.json --out IGNORED_OUTPUT_DIRECTORY
CPU_INPUTS: labels {path,sha256}; sources [{root,seal,sha256,members:[relative paths]}].
Each source seal has files[path]=sha256. Members contain native Oracle JSON lists
with unit_id, reader='oracle', repeat=0 and text. Labels stay in original CPU key.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parent
LABEL_SHA = '5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44'
SEED = 20261030
BOOTSTRAPS = 2000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def reading(auc):
    if auc >= .80:
        return 'CARRIED_IN_WORDS'
    if auc <= .60:
        return 'HIDDEN_STATE_TO_OUTPUT_BOTTLENECK'
    return 'INTERMEDIATE'


def validate_rows(rows):
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError('duplicate readout/item id')
    counts = {}
    quartets = {}
    for row in rows:
        if row['split'] not in ('dev', 'test') or row['genre'] not in (0, 1) or row['addressed'] not in (0, 1):
            raise ValueError('invalid original cell')
        if not isinstance(row['text'], str):
            raise ValueError('missing readout text; no imputation')
        key = (row['split'], row['genre'], row['addressed'])
        counts[key] = counts.get(key, 0) + 1
        quartets.setdefault(row['quartet'], []).append(row)
    expected = {(s, g, a): n for s, n in [('dev', 50), ('test', 100)] for g in (0, 1) for a in (0, 1)}
    if counts != expected:
        raise ValueError('requires exact 200 DEV + 400 TEST native Oracle texts, four balanced cells')
    for group in quartets.values():
        if len(group) != 4 or len({r['split'] for r in group}) != 1 or len({(r['genre'], r['addressed']) for r in group}) != 4:
            raise ValueError('incomplete/mixed original quartet')


def checked(path, expected):
    path = Path(path)
    if sha(path) != expected:
        raise ValueError('source checksum mismatch')
    return json.loads(path.read_text())


def load_rows(spec):
    if spec['labels']['sha256'] != LABEL_SHA:
        raise ValueError('requires original frozen E85 label key')
    labels = checked(spec['labels']['path'], LABEL_SHA)
    key = {r['public_id']: r for r in labels}
    if len(key) != 600:
        raise ValueError('original label key must contain 600 unique items')
    found = {}
    for source in spec['sources']:
        root = Path(source['root']).resolve()
        seal = checked(root / source['seal'], source['sha256'])
        for relative in source['members']:
            path = (root / relative).resolve()
            if root not in path.parents:
                raise ValueError('source member outside sealed root')
            records = checked(path, seal['files'][relative])
            if not isinstance(records, list):
                raise ValueError('expected original batch list, not a rewritten export')
            for r in records:
                if r['reader'] != 'oracle' or r['repeat'] != 0 or r['unit_id'] not in key:
                    raise ValueError('requires native Oracle repeat0 original source IDs')
                item_id = r['unit_id']
                if item_id in found:
                    raise ValueError('duplicate native item; no generation selection/deduplication')
                if not isinstance(r['text'], str):
                    raise ValueError('missing text, no substitution')
                label = key[item_id]
                found[item_id] = dict(id=item_id, text=r['text'], split=label['split'],
                                      genre=label['genre'], addressed=label['addressed'],
                                      quartet=label['matched_set'])
    rows = sorted(found.values(), key=lambda r: r['id'])
    validate_rows(rows)  # Fails before a lock/fit if DEV native text is absent.
    return rows


def fit_dev(dev):
    if not dev or any(r['split'] != 'dev' for r in dev):
        raise ValueError('fit requires DEV only')
    vectorizer = CountVectorizer(lowercase=True, ngram_range=(1, 1), min_df=1,
                                 token_pattern=r'(?u)\b\w\w+\b')
    x = vectorizer.fit_transform([r['text'] for r in dev])
    models = {}
    for target in ('addressed', 'genre'):
        models[target] = LogisticRegression(C=1.0, penalty='l2', solver='liblinear',
                                           max_iter=2000, tol=1e-4, random_state=SEED).fit(x, [r[target] for r in dev])
        if not np.array_equal(models[target].classes_, [0, 1]) or models[target].n_iter_.max() >= 2000:
            raise ValueError('invalid classes or unconverged fit')
    return vectorizer, models


def words(vectorizer, model, n=20):
    pairs = list(zip(vectorizer.get_feature_names_out(), model.coef_[0]))
    positive = sorted((p for p in pairs if p[1] > 0), key=lambda p: (-p[1], p[0]))[:n]
    negative = sorted((p for p in pairs if p[1] < 0), key=lambda p: (p[1], p[0]))[:n]
    return {side: [{'word': str(w), 'weight': float(v)} for w, v in values]
            for side, values in [('positive_class', positive), ('negative_class', negative)]}


def score_test(vectorizer, models, test, bootstraps=BOOTSTRAPS):
    if not test or any(r['split'] != 'test' for r in test):
        raise ValueError('evaluation requires TEST only')
    x = vectorizer.transform([r['text'] for r in test])
    groups = sorted({r['quartet'] for r in test})
    indices = [np.array([i for i, r in enumerate(test) if r['quartet'] == g]) for g in groups]
    rng = np.random.default_rng(SEED)
    draws = [np.concatenate([indices[j] for j in rng.integers(len(groups), size=len(groups))])
             for _ in range(bootstraps)]
    result = {}
    for target in ('addressed', 'genre'):
        y = np.array([r[target] for r in test])
        p = models[target].predict_proba(x)[:, 1]
        auc = float(roc_auc_score(y, p))
        boots = [roc_auc_score(y[ix], p[ix]) for ix in draws]
        result[target] = {'auroc': auc, 'quartet_bootstrap_95ci': list(map(float, np.quantile(boots, [.025, .975]))),
                          'positive_class': 1, 'top_weights_dev_only': words(vectorizer, models[target])}
    result['addressed']['registered_reading'] = reading(result['addressed']['auroc'])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    code_seal = json.loads((HERE / 'CODE_SEAL.json').read_text())
    for member, digest in code_seal['files'].items():
        if sha(HERE / member) != digest:
            raise ValueError('frozen code/contract differs')
    spec = json.loads(args.spec.read_text())
    rows = load_rows(spec)
    # Canonical owner lock: do not retry/refit under another output directory.
    lock = HERE / 'cache' / 'E85_BOW238_ONCE.json'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('x') as f:
        json.dump({'spec_sha256': sha(args.spec), 'code_seal_sha256': sha(HERE / 'CODE_SEAL.json'),
                   'output': str(args.out.resolve())}, f)
    args.out.mkdir(parents=True, exist_ok=False)
    dev = [r for r in rows if r['split'] == 'dev']
    test = [r for r in rows if r['split'] == 'test']
    vectorizer, models = fit_dev(dev)
    joblib.dump((vectorizer, models), args.out / 'FROZEN_DEV_MODELS.joblib')
    dump(args.out / 'DEV_FIT_SEAL.json', {'model_sha256': sha(args.out / 'FROZEN_DEV_MODELS.joblib'),
          'dev_ids_sha256': hashlib.sha256(json.dumps([r['id'] for r in dev]).encode()).hexdigest(),
          'contract_sha256': sha(HERE / 'PROTOCOL.json'), 'spec_sha256': sha(args.spec)})
    # Only after model+vocabulary freeze: transform/score TEST, never refit.
    result = score_test(vectorizer, models, test)
    dump(args.out / 'METRICS.json', result)
    dump(args.out / 'SOURCE_BINDING.json', {'spec_sha256': sha(args.spec), 'code_seal_sha256': sha(HERE / 'CODE_SEAL.json'),
          'n_dev': len(dev), 'n_test': len(test), 'empty_text_dev': sum(not r['text'] for r in dev),
          'empty_text_test': sum(not r['text'] for r in test)})
    dump(args.out / 'ANALYSIS_SEAL.json', {'experiment': 'E85_READOUT_BOW238',
          'files': {p.name: sha(p) for p in args.out.iterdir() if p.is_file()}, 'status': 'COMPLETE_ONCE'})


if __name__ == '__main__':
    main()
