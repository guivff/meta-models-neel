"""DESCRIPTIVE text-only shortcut checks; never read reader scores or activations.

Fixed before running: native Qwen token-count unigrams, L2 logistic C=1,
leave-one-template-cluster-out CV over all frozen items (dev+test), pooled OOF
AUROC with present positive; threshold >=0.8. Vocabulary is fitted within folds.
This separate diagnostic cannot change any registered decision or denominator.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time

import numpy as np
import sklearn
from sklearn.feature_extraction import DictVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import LeaveOneGroupOut

from . import protocol as P

THRESHOLD = 0.8
PADDING = re.compile(r'^(?:pad )*')
METHOD = {
    'features': 'raw native Qwen token-ID unigram counts; no normalization, ngrams or metadata',
    'padding': 'maximal leading repetition of the literal string pad<space>; excludes separator and carrier',
    'vocabulary': 'DictVectorizer fitted on training clusters only, separately for every fold/view/row',
    'classifier': 'LogisticRegression C=1, solver=lbfgs, L2 default, fit_intercept=True, tol=1e-8, max_iter=2000',
    'cv': 'LeaveOneGroupOut by template cluster; matched pair members always stay together',
    'population': 'all 168 frozen items per row, combining original dev/test for this separate diagnostic only',
    'auroc': 'pooled held-out decision_function predictions; present=1; fixed sign, no reversal',
    'threshold': THRESHOLD,
    'flag': 'possible shortcut if padding-only OR full-prefix OOF AUROC >=0.8',
    'padding_flag': 'padding artefact possible only if padding-only OOF AUROC >=0.8',
    'registered_verdict': 'unchanged; no registered metrics, gates, denominators or score joins modified',
    'uncertainty': 'descriptive OOF point estimates and fold AUROCs; no confidence intervals computed',
    'seed': P.SEED,
}


def padding_text(text):
    return PADDING.match(text).group()


def grouped_predictions(token_bags, y, groups):
    """Return exactly one prediction per item from a model excluding its cluster."""
    y, groups = np.asarray(y), np.asarray(groups)
    predictions = np.full(len(y), np.nan)
    assigned = np.zeros(len(y), dtype=int)
    folds = []
    for train, test in LeaveOneGroupOut().split(np.zeros(len(y)), y, groups):
        if set(groups[train]) & set(groups[test]):
            raise ValueError('cluster leakage')
        if len(set(y[train])) != 2 or len(set(y[test])) != 2:
            raise ValueError('both values required in every training and held-out fold')
        vectorizer = DictVectorizer()
        x_train = vectorizer.fit_transform([token_bags[i] for i in train])
        x_test = vectorizer.transform([token_bags[i] for i in test])
        if x_train.shape[1] == 0:
            # No padding at all: an intercept-only constant score is chance.
            score = np.zeros(len(test))
        else:
            classifier = LogisticRegression(C=1.0, solver='lbfgs', fit_intercept=True,
                tol=1e-8, max_iter=2000, random_state=P.SEED)
            classifier.fit(x_train, y[train])
            if classifier.n_iter_.max() >= classifier.max_iter:
                raise RuntimeError('classifier did not converge')
            score = classifier.decision_function(x_test)
        predictions[test] = score
        assigned[test] += 1
        folds.append({'held_out_cluster': str(groups[test[0]]),
            'train_clusters': sorted(set(groups[train].tolist())),
            'n_train': len(train), 'n_test': len(test),
            'vocabulary_size': x_train.shape[1], 'auroc': float(roc_auc_score(y[test], score))})
    if not np.all(assigned == 1) or not np.isfinite(predictions).all():
        raise ValueError('incomplete or duplicate OOF predictions')
    return predictions, folds


def flags(padding_auc, full_auc):
    return {'status': 'possible shortcut' if max(padding_auc, full_auc) >= THRESHOLD else 'not flagged',
            'padding_possible_shortcut': padding_auc >= THRESHOLD,
            'full_prefix_possible_shortcut': full_auc >= THRESHOLD,
            'padding_artefact_possible': padding_auc >= THRESHOLD}


def run(bank, freeze, out):
    started = time.monotonic()
    bank, freeze, out = Path(bank), Path(freeze), Path(out)
    if out.exists():
        raise ValueError('refusing to overwrite an existing descriptive run')
    seal = P.verify(bank, 'INPUT_SEAL.json')
    manifest = json.loads((bank/'manifest.json').read_text())
    if manifest['experiment'] != 'W1b':
        raise ValueError('expected W1b bank')
    for path in freeze.iterdir():
        if path.read_bytes() != (bank/path.name).read_bytes():
            raise ValueError('freeze differs from bank: '+path.name)
    item_path = bank/'items.DO_NOT_STAGE.jsonl'
    if P.sha(item_path) != manifest['files'][item_path.name]:
        raise ValueError('unsealed full item text')
    items = P.rows(item_path)
    selected = manifest['selection_receipt']['section79_features']
    if set(selected) != {it['feature'] for it in items}:
        raise ValueError('selected row mismatch')
    tokenizer_path = Path(manifest['tokenizer'])
    if P.sha(tokenizer_path/'tokenizer.json') != manifest['tokenizer_sha256']:
        raise ValueError('tokenizer hash mismatch')
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(tokenizer_path, local_files_only=True)
    rows, all_predictions = [], []
    for feature in selected:
        subset = [it for it in items if it['feature'] == feature]
        if len(subset) != 168 or len({it['cluster'] for it in subset}) != 12:
            raise ValueError('unexpected row size or clusters')
        y = np.array([int(it['value'] == 'present') for it in subset])
        if Counter(it['value'] for it in subset) != {'present':84,'absent':84}:
            raise ValueError('invalid frozen values')
        groups = [it['cluster'] for it in subset]
        row = {'feature':feature, 'n':len(subset), 'n_clusters':len(set(groups)),
               'status_scope':'DESCRIPTIVE', 'confirmation_status':'PENDING REGISTERED SCORE ANALYSIS'}
        oof = {}
        for view in ('padding_only','full_prefix'):
            texts = [padding_text(it['text']) if view == 'padding_only' else it['text'] for it in subset]
            encoded = [tok(text, add_special_tokens=False)['input_ids'] for text in texts]
            if view == 'full_prefix' and encoded != [it['ids'] for it in subset]:
                raise ValueError('full prefix retokenization mismatch')
            bags = [Counter(str(token) for token in ids) for ids in encoded]
            predictions, folds = grouped_predictions(bags, y, groups)
            row[view] = {'auroc':float(roc_auc_score(y,predictions)), 'folds':folds}
            oof[view] = predictions
        row.update(flags(row['padding_only']['auroc'], row['full_prefix']['auroc']))
        rows.append(row)
        for i,it in enumerate(subset):
            all_predictions.append({'id':it['id'], 'feature':feature, 'cluster':it['cluster'],
                'original_split':it['split'], 'value':it['value'],
                **{view:float(predictions[i]) for view,predictions in oof.items()}})
    out.mkdir(parents=True, exist_ok=False)
    report = {'status':'DESCRIPTIVE', 'at_utc':datetime.now(timezone.utc).isoformat(),
        'method':METHOD, 'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'manifest_sha256':P.sha(bank/'manifest.json'), 'items_sha256':P.sha(item_path),
        'tokenizer_sha256':manifest['tokenizer_sha256'],
        'source_sha256':P.sha(Path(__file__)), 'sklearn_version':sklearn.__version__,
        'rows':rows, 'possible_shortcut_rows':[r['feature'] for r in rows if r['status']=='possible shortcut'],
        'padding_artefact_possible_rows':[r['feature'] for r in rows if r['padding_artefact_possible']],
        'reader_scores_read':False, 'registered_analysis_run':False,
        'wall_seconds':time.monotonic()-started, 'gpu_hours':0,
        'interpretation':[
            'Prediction from full text is expected when the text directly defines the value; this alone does not identify a padding artefact.',
            'A padding-only flag identifies a possible nuisance cue, not proof that a reader/probe uses that cue.',
            'Absence of a flag does not exclude nonlinear or relational padding shortcuts.',
            'After registered results exist, join this sidecar by feature in the descriptive write-up; flag confirmations with padding_artefact_possible separately. Keep registered verdict unchanged.'
        ]}
    P.dump(out/'metrics.json',report)
    P.jsonl(out/'oof_predictions.jsonl',all_predictions)
    lines = ['# §84 text-only shortcut check — DESCRIPTIVE', '',
        'Registered §84 verdict unchanged. Reader scores and activations were not read.', '',
        'Native Qwen token-count unigrams; fixed L2 logistic C=1; leave-one-cluster-out CV',
        'over all 168 items/row (12 clusters, including original dev and test). Vocabulary',
        'fit on training clusters only. Pooled OOF AUROC; present positive; flag at ≥0.8.', '',
        '| Row | n | Padding-only AUROC | Full-prefix AUROC | Status | Padding artefact possible |',
        '|---|---:|---:|---:|---|---|']
    for r in rows:
        lines.append(f"| {r['feature']} | {r['n']} | {r['padding_only']['auroc']:.3f} | {r['full_prefix']['auroc']:.3f} | {r['status']} | {'yes' if r['padding_artefact_possible'] else 'not flagged'} |")
    lines += ['', 'Full-prefix prediction alone does not establish a padding artefact. Padding-only',
        'prediction is a nuisance warning, not causal evidence of reader reliance. No flag',
        'does not rule out nonlinear/relational shortcuts. Confirmation statuses are pending;',
        'the descriptive write-up must merge these flags by feature after registered analysis.', '',
        'All OOF predictions, fold memberships, fold AUROCs and exact provenance are saved',
        'alongside this table. No hyperparameter search, sign reversal or scope selection.']
    (out/'TABLE.md').write_text('\n'.join(lines)+'\n')
    P.dump(out/'DESCRIPTIVE_SEAL.json',{'status':'DESCRIPTIVE_TEXT_ONLY',
        'files':{name:P.sha(out/name) for name in ('metrics.json','oof_predictions.jsonl','TABLE.md')}})
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for option in ('bank','freeze','out'):
        p.add_argument('--'+option,type=Path,required=True)
    a = p.parse_args()
    result = run(a.bank,a.freeze,a.out)
    print(json.dumps({'status':result['status'],'possible_shortcut_rows':result['possible_shortcut_rows'],
        'padding_artefact_possible_rows':result['padding_artefact_possible_rows'],'wall_seconds':result['wall_seconds']},indent=2))
