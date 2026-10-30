"""E41 §147: dev-only CPU freeze; reuse E31(i)'s frozen estimator verbatim."""
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

P = load('e31_prepare', HERE.parent / 'e31/prepare.py')
A = load('e31_analyze', HERE.parent / 'e31/analyze.py')
BANK = HERE.parent / 'e36/cache/v2_25_2026-10-25'
TOKENIZER = Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json')
INPUTS = {
    str(BANK / 'items.input.jsonl'): '2d3b14226b76fb51b7afe83190b34fd03a2c9cb3ded6f3f867ac35cb3de10690',
    str(BANK / 'labels.DO_NOT_STAGE.jsonl'): '94f6244a8f89b0320408b77e06c84df2f94d9e0c250d84fa28c63fed8e21e50f',
    str(HERE.parent / 'e36/ROW_DEFINITIONS.json'): '2afa8e1202c0d7c181e6f95984b18bd59f99af81fc8cf8f27dcce02e8e38056c',
    str(TOKENIZER): '5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42',
    str(HERE.parent / 'e31/prepare.py'): '5e3ccd60df1e43a6abbbb424b36e20e9bb63cac1ca1876908650e37fef90acc0',
    str(HERE.parent / 'e31/analyze.py'): '81434ba9e95a4e726c971eb34ea19639b9275e396aadcac4a3d608d700665454',
}

def verify_inputs():
    for path, digest in INPUTS.items():
        P._check_hash(path, digest)

def items(split):
    # Filter immediately; no test text, tokens or labels enter the dev fitter.
    rows = [r for r in P.read_jsonl(BANK / 'items.input.jsonl') if r['split'] == split and r['feature'] in P.ROWS]
    labels = {r['id']: r for r in P.read_jsonl(BANK / 'labels.DO_NOT_STAGE.jsonl') if r['split'] == split and r['feature'] in P.ROWS}
    if len(rows) != 588 or len({r['id'] for r in rows}) != 588 or set(labels) != {r['id'] for r in rows}:
        raise ValueError('invalid seven-row split identity')
    for r in rows:
        label = labels[r['id']]
        if any(r[k] != label[k] for k in ('feature', 'split', 'cluster')):
            raise ValueError('label identity mismatch')
        r['value'] = label['value']
        r['meta'] = {'read_position': len(r['ids']) - 1}
    return rows

def decoder():
    from transformers import PreTrainedTokenizerFast
    return PreTrainedTokenizerFast(tokenizer_file=str(TOKENIZER))

def texts(rows, tok):
    return [tok.decode(P.suffix_ids(r, 'include_read'), skip_special_tokens=False,
                       clean_up_tokenization_spaces=False) for r in rows]

def main():
    verify_inputs()
    dev = items('dev')
    definitions = P.read(HERE.parent / 'e36/ROW_DEFINITIONS.json')['rows']
    out = HERE / 'freeze_2026-10-26'
    out.mkdir(exist_ok=False)
    (out / 'cache').mkdir()
    A.dump(out / 'STARTED.json', {'created_at': datetime.now(timezone.utc).isoformat(), 'scores_accessed': False})
    tok = decoder()
    models, cutoffs = {}, []
    for feature in P.ROWS:
        rows = [r for r in dev if r['feature'] == feature]
        values = definitions[feature]['values']
        if Counter(r['value'] for r in rows) != Counter({v: 42 for v in values}):
            raise ValueError('dev balance changed')
        text = texts(rows, tok)
        # Third argument is dev again: fit_row has no test-dependent fitting logic.
        model, probs, check = P.fit_row(text, [int(r['value'] == values[0]) for r in rows], text)
        np.testing.assert_allclose(probs, check, rtol=0, atol=1e-12)
        np.testing.assert_allclose(P.restored_probabilities(model, text), probs, rtol=0, atol=1e-12)
        cutoff = float(np.median(P.confidence(probs)))
        models[feature] = model
        cutoffs.append({'feature': feature, 'values': values, 'n_dev': len(rows), 'cutoff': cutoff,
                        'dev_strata': dict(Counter(P.assign_strata(probs, cutoff)))})
    A.dump(out / 'cache/models.json', models)
    A.dump(out / 'DEV_CUTOFFS.json', {'rows': cutoffs, 'margin': 'abs(p_A-p_B)', 'informative_operator': '>',
                                    'ties': 'uninformative', 'suffix': 'ids[-4:]', 'test_items_used': False})
    A.dump(out / 'PROVENANCE.json', {'experiment': 'E41', 'registration': '82cfeef4 §147',
        'recipe_freeze': '70ffb479', 'input_hashes': INPUTS, 'classifier_fits': 7,
        'test_scores_accessed': False, 'test_strata_computed': False, 'GPU_hours': 0,
        'freeze_source_sha256': P.sha(__file__), 'completed_at': datetime.now(timezone.utc).isoformat()})
    names = ['STARTED.json', 'cache/models.json', 'DEV_CUTOFFS.json', 'PROVENANCE.json']
    A.dump(out / 'CLASSIFIER_SEAL.json', {'complete': True, 'experiment': 'E41',
        'files': {n: P.sha(out / n) for n in names}})
    print(json.dumps({'status': 'DEV_ONLY_FROZEN', 'seal_sha256': P.sha(out / 'CLASSIFIER_SEAL.json'), 'rows': cutoffs}))

if __name__ == '__main__':
    main()
