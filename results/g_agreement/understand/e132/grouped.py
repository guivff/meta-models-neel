"""E132 synthetic-tested grouped-CV primitives. No real labels, model load or CLI.
Target convention and E116 Oracle block must be bound before real execution.
"""
from collections import defaultdict
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import roc_auc_score

SEED = 20261030
CAPACITY = 5000


def joint_groups(rows):
    """Connected components: same original item OR same original template.

    Both identities must come from frozen metadata, not readout/label inference.
    Dataset prefixing is a source-binding responsibility.
    """
    parent = list(range(len(rows)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def merge(i, j):
        a, b = find(i), find(j)
        parent[max(a, b)] = min(a, b)

    seen = {}
    for i, r in enumerate(rows):
        for field in ('item_group', 'template_group'):
            value = r[field]
            if not isinstance(value, str) or not value:
                raise ValueError('requires frozen item/template group identity')
            key = field, value
            if key in seen:
                merge(i, seen[key])
            else:
                seen[key] = i
    return np.array([find(i) for i in range(len(rows))])


def make_folds(rows, labels):
    groups = joint_groups(rows)
    if len(np.unique(groups)) < 5:
        raise ValueError('NOT EVALUABLE: fewer than five joint item/template groups')
    splitter = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    assignment = np.full(len(rows), -1)
    for f, (_, held) in enumerate(splitter.split(np.zeros(len(rows)), labels, groups)):
        assignment[held] = f
    if np.any(assignment < 0):
        raise ValueError('incomplete fold coverage')
    for g in np.unique(groups):
        if len(set(assignment[groups == g])) != 1:
            raise ValueError('item/template leakage')
    return assignment


def model():
    return LogisticRegression(C=1., penalty='l2', solver='liblinear',
                              max_iter=2000, tol=1e-4, random_state=SEED)


def oof(rows, labels, assignments, text_field, declared_classes):
    """OVR binary estimators, matched 5,000-word capacity across text sources.

    Classes are supplied by the future frozen target contract. No automatic
    conversion of item-specific entities to arbitrary binary labels.
    Missing training classes produce unavailable predictions, not zeros.
    """
    labels = np.asarray(labels)
    probabilities = np.full((len(rows), len(declared_classes)), np.nan)
    vocabularies = []
    for f in range(5):
        train, held = np.flatnonzero(assignments != f), np.flatnonzero(assignments == f)
        if not len(train) or not len(held):
            raise ValueError('empty fold')
        if any(not isinstance(rows[i][text_field], str) for i in np.r_[train, held]):
            raise ValueError('missing original text: no imputation')
        v = CountVectorizer(lowercase=True, ngram_range=(1,1), min_df=1,
                            max_features=CAPACITY, token_pattern=r'(?u)\b\w\w+\b')
        a = v.fit_transform([rows[i][text_field] for i in train])
        b = v.transform([rows[i][text_field] for i in held])
        vocabularies.append(set(v.vocabulary_))
        for j, c in enumerate(declared_classes):
            y = (labels[train] == c).astype(int)
            if len(np.unique(y)) < 2:
                continue
            m = model().fit(a, y)
            if m.n_iter_.max() >= 2000:
                raise ValueError('unconverged fit')
            probabilities[held, j] = m.predict_proba(b)[:,1]
    return probabilities, vocabularies


def auc(labels, probabilities, classes, convention):
    """No choosing the target convention from real performance."""
    labels = np.asarray(labels)
    probabilities = np.asarray(probabilities)
    if convention == 'binary':
        if len(classes) != 2 or len(set(labels)) != 2:
            return None
        p = probabilities[:, 1]
        return float(roc_auc_score(labels == classes[1], p)) if np.isfinite(p).all() else None
    if convention == 'macro_ovr':
        values = []
        for j, c in enumerate(classes):
            y = labels == c
            if len(np.unique(y)) < 2 or not np.isfinite(probabilities[:,j]).all():
                return None
            values.append(roc_auc_score(y, probabilities[:,j]))
        return float(np.mean(values)) if values else None
    raise ValueError('target/AUROC convention must be explicitly frozen')


def paired_endpoint_difference(labels, readout, prompt, classes, convention,
                               endpoint, item_groups, draws=2000):
    """Same endpoint items, labels and resamples for both predictors."""
    labels = np.asarray(labels)
    mask = np.asarray(endpoint, dtype=bool)
    readout, prompt = np.asarray(readout), np.asarray(prompt)
    a, b = auc(labels[mask], readout[mask], classes, convention), auc(labels[mask], prompt[mask], classes, convention)
    if a is None or b is None:
        return {'status':'NOT_EVALUABLE', 'n':int(mask.sum()), 'reason':'undefined target classes/predictions'}
    group = np.asarray(item_groups)
    groups = sorted(set(group[mask]))
    indices = [np.flatnonzero(mask & (group == g)) for g in groups]
    rng = np.random.default_rng(SEED)
    delta, undefined = [], 0
    for _ in range(draws):
        ix = np.concatenate([indices[j] for j in rng.integers(len(indices), size=len(indices))])
        ra, pa = auc(labels[ix], readout[ix], classes, convention), auc(labels[ix], prompt[ix], classes, convention)
        if ra is None or pa is None:
            undefined += 1
        else:
            delta.append(ra-pa)
    ci = None if undefined else list(map(float, np.quantile(delta,[.025,.975])))
    difference = a-b
    verdict = 'NOT_EVALUABLE_CI' if ci is None else ('MET' if difference >= .1 and ci[0] > 0 else 'NOT_MET')
    return dict(status='DEFINED',n=int(mask.sum()),readout_auroc=a,prompt_auroc=b,
                difference=difference,paired_item_bootstrap_95ci=ci,
                undefined_bootstrap_draws=undefined,registered_B_rule=verdict,
                low_difference_reading=bool(difference <= .03))
