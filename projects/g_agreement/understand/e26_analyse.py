"""Once-only registered E26 CPU analysis after complete integrator pull; never loads AR."""
import argparse
import time
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .e26 import PLAN, validate_inputs
from .e26_bank import FEATURES
from .e26_metrics import raw_scores, item_measures, summarize


def evaluate(recon, records, banks, templates):
    if recon.shape != (836,5120) or not np.isfinite(recon).all():
        raise ValueError('complete finite raw reconstructions required')
    index={r['id']:i for i,r in enumerate(records)}; result={}
    for feature in FEATURES:
        folder=banks/feature; verify(folder,'BANK_SEAL.json')
        c=rows(folder/'candidates.DO_NOT_STAGE.jsonl')
        public=rows(folder/'candidates.input.jsonl')
        for private,public_row in zip(c,public,strict=True):
            if any(private[k]!=v for k,v in public_row.items()):
                raise ValueError('private/public candidate alignment mismatch')
        items=rows(folder/'items.DO_NOT_STAGE.jsonl')
        ids=read(folder/'ids.json')
        if ids!=[r['id'] for r in items] or len(ids)!=80:
            raise ValueError('sealed item alignment mismatch')
        values=templates[feature]['values']
        truth=[values.index(r['value']) for r in items]
        if truth.count(0)!=40 or truth.count(1)!=40: raise ValueError('40 per value required')
        x=recon[[index[r['id']] for r in c]]; h=np.load(folder/'acts44.npy',allow_pickle=False)
        if h.shape!=(80,5120) or not np.isfinite(h).all(): raise ValueError('finite sealed block44 states required')
        scores=raw_scores(x,h)
        metrics=item_measures(scores,[r['category'] for r in c],[r.get('value',-1) for r in c],truth)
        result[feature]=summarize(metrics,n_boot=2000,seed=20261025)
    states=sum(result[f]['R1'] and result[f]['R2'] for f in FEATURES[:-1])
    sentiment=result['prose_sentiment']['R1'] and result['prose_sentiment']['R2']
    return {'rows':result, 'states_joint_R1_R2':int(states), 'states_prediction_met':states>=4,
            'sentiment_prediction_met':bool(sentiment), 'prediction_met':bool(states>=4 and sentiment),
            'interpretation':'EXPLORATORY; raw cosine; sentiment own-value continuations = category (b) only'}


def render(result):
    status='MET' if result['prediction_met'] else 'NOT MET'
    lines=['# E26 — EXPLORATORY', '',
           'Prediction: R1 and R2 jointly hold on at least four of five state rows; sentiment also satisfies R1 and ranks descriptions below own-value continuations.', '',
           f"Prediction **{status}**: joint R1/R2 on {result['states_joint_R1_R2']}/5 state rows; sentiment prediction {'MET' if result['sentiment_prediction_met'] else 'NOT MET'}.", '',
           'Raw cosine as E21, tag 44. Item bootstrap: 2,000 resamples, seed 20261025. Sentiment omits E15 category (a) under §120 clarification 1; its own-value continuations are category (b).', '',
           '| Row | M1 [95% CI] | Best true-description rank [CI] | Own-continuation rank [CI] | M2 difference [CI] | M3 [CI] | R1 | R2 |',
           '|---|---|---|---|---|---|---|---|']
    def fmt(m):
        return f"{m['estimate']:.4f} [{m['ci95'][0]:.4f}, {m['ci95'][1]:.4f}]"
    for f,r in result['rows'].items():
        cells=[fmt(r[k]) for k in ('M1','best_true_description_median_rank','own_continuation_median_rank','M2_rank_difference','M3')]
        lines.append('| '+f+' | '+' | '.join(cells)+f" | {r['R1']} | {r['R2']} |")
    lines+=['', 'R1: M1 ≥ 0.65 and CI lower > 0.50. R2: best-description median rank minus own-continuation median rank > 0, with CI lower > 0. Exact cosine ties have average ranks and fractional membership at the top-10 boundary. Own-continuation rank is the median of within-item medians; M2 uses a paired item bootstrap. These conventions were frozen before scoring.', '']
    return '\n'.join(lines)


def analyse(a):
    plan=read(ROOT/PLAN); records=validate_inputs(a.inputs,plan['input_seal_sha256'])
    collection=verify(a.collection)
    if collection['status']!='E26_COMPLETE':raise ValueError('complete collection required')
    run=read(a.collection/'run.json')
    if run['status']!='COMPLETE' or run['input_seal_sha256']!=plan['input_seal_sha256']:
        raise ValueError('collection provenance mismatch')
    if run['candidate_banks_sha256']!=sha(a.banks/'PREPARATION.json') or sha(a.inputs/'BANKS.json')!=sha(a.banks/'PREPARATION.json'):
        raise ValueError('local bank provenance mismatch')
    for file,digest in run['source_files'].items():
        path=(ROOT/file).resolve()
        if not path.is_relative_to(ROOT.resolve()) or sha(path)!=digest: raise ValueError('source pin mismatch')
    prep=read(a.banks/'PREPARATION.json')
    for r in prep['rows']:
        verify(a.banks/r['feature'],'BANK_SEAL.json')
        if sha(a.banks/r['feature']/'BANK_SEAL.json')!=r['bank_seal_sha256']:raise ValueError('local bank seal mismatch')
    verify(a.w1/'w1-bank-v2','INPUT_SEAL.json')
    if sha(a.w1/'w1-bank-v2/INPUT_SEAL.json')!=prep['source_pins']['W1_bank_seal']:raise ValueError('W1 provenance mismatch')
    if read(a.collection/'ids.json')!=[r['id'] for r in records]:raise ValueError('reconstruction order mismatch')
    # An existing directory or attempt marker stops repeat analysis; failed attempts require review.
    a.out.mkdir(parents=True,exist_ok=False)
    with (a.out/'ANALYSIS_ONCE.json').open('x') as f:f.write('{"status":"STARTED_ONCE"}\n')
    started=time.monotonic()
    result=evaluate(np.load(a.collection/'recon.npy',allow_pickle=False),records,a.banks,
                    read(a.w1/'w1-bank-v2/templates.json'))
    dump(a.out/'metrics.json',result);(a.out/'RESULTS.md').write_text(render(result))
    dump(a.out/'ANALYSIS_RUN.json',{'status':'COMPLETE_ONCE','authority_commit':'4384b1ad',
        'wall_seconds':time.monotonic()-started,'GPU_hours':0,'input_seal_sha256':plan['input_seal_sha256'],
        'collection_seal_sha256':sha(a.collection/'SCORE_SEAL.json'),
        'banks_sha256':sha(a.banks/'PREPARATION.json'),'source_commit':run['source_commit'],
        'seed':20261025,'bootstrap_resamples':2000})
    seal(a.out,[p.name for p in a.out.iterdir() if p.is_file()],'E26_REGISTERED_ANALYSIS_ONCE')
    print('HANDOFF E26',a.out/'RESULTS.md',sha(a.out/'SCORE_SEAL.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','banks','collection','w1','out'):p.add_argument('--'+name,type=Path,required=True)
    analyse(p.parse_args())
