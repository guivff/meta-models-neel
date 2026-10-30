"""Gated CPU E130 analysis. No model, API, GPU, acquisition or E125 imports."""
import hashlib
import json
from pathlib import Path
import random
import subprocess
from datetime import datetime, timezone
import numpy as np
from . import kernel as k
from projects.g_agreement.e130.gates import e130_admit

GUARD = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wlens/cache/g_agreement/understand/e130/analysis')
LABEL_SHA = '5ed311882f9b06f208776d1636567267570ed33bbf83b39d5da9732559975a44'
INPUT_SHA = '01086c34e01657dceac68b003abffde9115a6bfd206f4343a88101f42836c24d'
RUNNER_SHA = '5edd2a127195f8dc2516a8ddee978f229d47ee86b58590ac8cf962ec8355c324'
DEADLINE = datetime(2026,10,30,17,tzinfo=timezone.utc)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n')


def claim(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as f:
        json.dump(value, f, sort_keys=True, allow_nan=False)
        f.write('\n')


def verified_seal(root, name, digest):
    root = Path(root)
    k.require(sha(root/name) == digest, 'exact sealed artifact '+name)
    seal = read(root/name)
    for name, digest in seal['files'].items():
        k.require(Path(name).name == name and sha(root/name) == digest, 'sealed member '+name)
    return seal



def verified_outer(pin, inner_pin):
    """Bind Q's nested transport seal to the unchanged native acquisition seal."""
    path = Path(pin['path']); root = path.parent
    k.require(sha(path) == pin['sha256'], 'exact Q outer seal')
    outer = read(path)
    k.require(outer['experiment'] == 'E130' and outer['status'] == 'COMPLETE'
              and outer['source_sha256'] == RUNNER_SHA and outer['input_sha256'] == INPUT_SHA
              and outer['outputs_unopened'] is True, 'complete original Q transport')
    for name, digest in outer['files'].items():
        member = Path(name)
        k.require(not member.is_absolute() and '..' not in member.parts
                  and sha(root/member) == digest, 'Q sealed transport member')
    name = outer['inner_seal']
    k.require((root/name).resolve() == Path(inner_pin['path']).resolve()
              and outer['files'][name] == inner_pin['sha256'], 'exact native inner seal lineage')
    return outer


def tokens_check(rows, order, dev):
    roster = {(r['id'], r['condition']): r for r in rows}
    expected = {(i, 'span_32') for i in order['dev']} | {(i, c) for i in order['test'] for c in ('ol_readout','ol_readout_shuffled')}
    k.require(len(rows) == len(roster) == 1000 and set(roster) == expected, 'complete token roster')
    k.require([r['id'] for r in dev] == order['dev'], 'original DEV span order')
    for r in dev:
        t = roster[r['id'], 'span_32']
        k.require(t['split'] == 'dev' and t['ids'] == r['ids'] and len(t['ids']) == 32, 'original DEV span IDs')
    rng = random.Random(20261031)
    for i in order['test']:
        a, b = (roster[i, c] for c in ('ol_readout','ol_readout_shuffled'))
        ids = a['ids']; expected = list(ids)
        k.require(a['split'] == b['split'] == 'test' and 0 < len(ids) <= 256 and all(type(x) is int and x >= 0 for x in ids), 'valid TEST token IDs')
        for _ in range(10):
            rng.shuffle(expected)
            if expected != ids:
                break
        k.require(b['ids'] == expected, 'exact sealed-order seed20261031 token shuffle')


def index_check(index, order):
    expected = {(i, 'span_32') for i in order['dev']} | {(i, c) for i in order['test'] for c in ('ol_readout','ol_readout_shuffled')}
    k.require(len(index) == 1000 and {(r['id'],r['condition']) for r in index} == expected, '1000 complete distinct rebuild rows')
    files = {}; slots = set()
    for r in index:
        name = r['file']
        k.require(Path(name).name == name and name.endswith('.npy') and type(r['index']) is int and r['index'] >= 0, 'safe original batch row')
        k.require(r['split'] == ('dev' if r['condition'] == 'span_32' else 'test'), 'condition split')
        k.require((name,r['index']) not in slots, 'unique batch row')
        slots.add((name,r['index']))
        files.setdefault(name, []).append(r)
    for rs in files.values():
        k.require(len({r['condition'] for r in rs}) == 1 and {r['index'] for r in rs} == set(range(len(rs))), 'unmixed complete condition batch')
    return files


def load_condition(root, index, order, condition):
    ids = order['dev' if condition == 'span_32' else 'test']
    rows = {r['id']: r for r in index if r['condition'] == condition}
    arrays = {}
    for r in rows.values():
        if r['file'] not in arrays:
            x = np.load(Path(root)/r['file'], allow_pickle=False)
            n = sum(v['file'] == r['file'] for v in rows.values())
            k.require(x.shape == (n,5120) and x.dtype == np.float32 and np.isfinite(x).all(), 'lossless finite original batch')
            arrays[r['file']] = x
    return np.stack([arrays[rows[i]['file']][rows[i]['index']] for i in ids])


def run(plan_path):
    """Final plan must be committed after real delivery and before this sole claim."""
    k.require(datetime.now(timezone.utc) <= DEADLINE, 'analysis/review deadline')
    plan_path = Path(plan_path).resolve(); plan = read(plan_path)
    repo = Path(subprocess.check_output(['git','rev-parse','--show-toplevel'], text=True).strip())
    rel = str(plan_path.relative_to(repo))
    k.require(subprocess.check_output(['git','show','HEAD:'+rel]) == plan_path.read_bytes(), 'committed final exact plan')
    receipt = read(Path(__file__).with_name('SOURCE_RECEIPT.json'))
    for name, digest in receipt['files'].items():
        path = Path(__file__).parent/name
        k.require(sha(path) == digest and subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(repo))]) == path.read_bytes(), 'committed tested analysis source')
    k.require(plan['experiment'] == 'E130' and plan['status'] == 'FINAL_BOUND' and plan['analysis_source_receipt_sha256'] == sha(Path(__file__).with_name('SOURCE_RECEIPT.json')), 'final bound E130 source')
    for pin in plan['pins'].values():
        k.require(Path(pin['path']).is_absolute() and sha(pin['path']) == pin['sha256'], 'exact original binding member')
    pins = {name: Path(v['path']) for name,v in plan['pins'].items()}
    k.require(plan['pins']['labels']['sha256'] == LABEL_SHA and plan['pins']['runner_source_seal']['sha256'] == RUNNER_SHA, 'original E85 CPU labels and executed source')
    inputseal = verified_seal(pins['input_seal'].parent, pins['input_seal'].name, INPUT_SHA)
    admission = read(pins['operator_admission'])
    e130_admit(admission, INPUT_SHA, inputseal['sealed_at_utc'], datetime.fromisoformat(plan['actual_creation_utc'].replace('Z','+00:00')))
    k.require(admission['adapter_commit'] == plan['preoutput_adapter_commit'], 'same admitted preoutput adapter')
    k.require(subprocess.check_output(['git','show',plan['preoutput_adapter_commit']+':projects/g_agreement/e130_analysis/SOURCE_RECEIPT.json']) == Path(__file__).with_name('SOURCE_RECEIPT_PREOUTPUT.json').read_bytes(), 'actual original adapter commit')
    custody = read(pins['custody'])
    k.require(custody['experiment'] == 'E130' and custody['status'] == 'VERIFIED_COMPLETE' and custody['operator'] == 'Track Q'
              and custody['input_sha256'] == INPUT_SHA and custody['executed_source_seal_sha256'] == RUNNER_SHA
              and custody['output_seal_sha256'] == plan['pins']['outer_output_seal']['sha256']
              and custody['preoutput_adapter_commit'] == plan['preoutput_adapter_commit']
              and custody['adapter_preceded_first_output'] is True and custody['outputs_held_until_adapter'] is True, 'original Q custody/admitted chronology')
    verified_outer(plan['pins']['outer_output_seal'], plan['pins']['output_seal'])
    root = pins['output_seal'].parent
    seal = verified_seal(root, pins['output_seal'].name, plan['pins']['output_seal']['sha256'])
    k.require(seal['experiment'] == 'E130' and seal['status'] == 'COMPLETE' and seal['tag'] == 44 and seal['variant'] == ['li','ln'] and seal['seed'] == 20261031
              and all(seal[x] is False for x in ('labels_included','probe_fit','probe_score','alignment_fit','whitening_applied')), 'complete original no-fit E130 output')
    order = dict(dev=[x['id'] for x in read(pins['input_seal'].parent/'DEV_SPANS.json')], test=read(pins['input_seal'].parent/'TEST_ORDER.json'))
    index = read(root/'INDEX.json'); batches = index_check(index, order)
    k.require({'INDEX.json','TOKEN_ROWS.json','TIMING.json','ONCE.json'} | set(batches) <= set(seal['files']), 'every consumed original output member sealed')
    tokens_check(read(root/'TOKEN_ROWS.json'), order, read(pins['input_seal'].parent/'DEV_SPANS.json'))
    labels = k.label_binding(order, read(pins['labels']))
    out = Path(plan['private_output']).resolve()
    k.require(not out.exists() and not out.is_relative_to(repo/'results'), 'fresh private CPU output outside tracked results')
    claim(GUARD/'ONCE.json', dict(experiment='E130', plan_sha256=sha(plan_path), output_seal_sha256=sha(pins['output_seal'])))
    out.mkdir(parents=True, exist_ok=False)
    dev = load_condition(root,index,order,'span_32')
    models = {}; controls = {}; private = {}; fit_files = {}
    for factor in k.FACTORS:
        y = labels['dev'][factor]
        cvpred, folds = k.cv(dev,y,labels['dev']['groups'])
        controls[factor] = k.summary(y, {'true_span_oof':cvpred})
        model = k.fit(dev,y); models[factor] = model
        name = factor+'_FROZEN.npz'
        np.savez(out/name, w=model.w.numpy(), b=model.b, mu=model.mu.numpy(), sd=model.sd.numpy())
        fit_files[name] = sha(out/name)
        private[factor] = dict(dev_oof_scores=cvpred.tolist(), dev_folds=folds)
    write(out/'FIT_SEAL.json', dict(experiment='E130', files=fit_files, source_receipt_sha256=sha(Path(__file__).with_name('SOURCE_RECEIPT.json')), test_arrays_opened=False))
    claim(GUARD/'TEST_ONCE.json', dict(experiment='E130', fit_seal_sha256=sha(out/'FIT_SEAL.json')))
    intact = load_condition(root,index,order,'ol_readout')
    shuffled = load_condition(root,index,order,'ol_readout_shuffled')
    result = dict(experiment='E130', status='COMPLETE_ONCE', credit='Suraj exp24 protocol, source23d5a972', factors={})
    for factor in k.FACTORS:
        y = labels['test'][factor]
        pred = dict(intact=k.score(models[factor],intact), shuffled=k.score(models[factor],shuffled))
        transferred = k.summary(y,pred)
        # Explicitly descriptive TEST readout-only grouped CV, after primary probe freeze.
        cvpred, folds = k.cv(intact,y,labels['test']['groups'])
        control = controls[factor]['scores']['true_span_oof']['AUROC']
        result['factors'][factor] = dict(frozen_probe=transferred, true_span_positive_control=controls[factor],
             readout_only_grouped_cv=k.summary(y,dict(readout_oof=cvpred)), interpretation=k.reading(control,transferred) if factor == 'addressed' else 'GENRE_DESCRIPTIVE_CONTROL_ONLY')
        private[factor].update(test_scores={c:v.tolist() for c,v in pred.items()}, test_readout_oof=cvpred.tolist(), test_readout_folds=folds)
    result['R_EC1'] = result['factors']['addressed']['interpretation']
    result['caveats'] = ['Descriptive E130 arrangement test; naming premise from sealed E85 0/176, not recomputed.',
                         'Complete exact input binder after capture, before CPU claim; preoutput kernel separately pinned.',
                         'DEV200 true-span rebuild reference, frozen all-DEV probe; TEST400 readout-only CV separately descriptive.',
                         'No E125 rerun or changed verdict; no causal-access or organic-awareness claim.']
    write(out/'PREDICTIONS.PRIVATE.json',private)
    write(out/'RESULTS.json',result)
    write(out/'ANALYSIS_SEAL.json',dict(experiment='E130', plan_sha256=sha(plan_path), files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
    return out


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser(); p.add_argument('--plan',required=True)
    print(run(p.parse_args().plan))
