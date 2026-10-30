"""§71 CPU-only reuse of the sealed S2 reconstruction batch for all40W1 rows.

No model imports/forwards, reconstruction recollection, or direction fitting.
The fidelity/bootstrap and decision implementation is the immutable ar_tests.py.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import time
import numpy as np
from . import ar_tests as AR, protocol as P

APPROVED_AR = '73a2c2fe6a7f6be5cf93abda0c7fadcf505abc32f2d346e635b068d11d6c7d3b'


def sealed_s2(texts, reconstruction, text_labels):
    AR._verify(texts, 'INPUT_SEAL.json', ['texts.input.jsonl','definitions.json','provenance.json'])
    AR._verify(reconstruction, 'SCORE_SEAL.json', ['recon.npy','ids.json','provenance.json'])
    definitions = AR._read(texts/'definitions.json')
    records = P.rows(texts/'texts.input.jsonl')
    if records != AR.freeze_text_records(definitions)[0]:
        raise ValueError('S2 text grid differs from frozen definitions')
    provenance = AR._read(reconstruction/'provenance.json')
    if (provenance.get('stage') != 'S2'
        or provenance.get('whitener_sha256') != '178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'):
        raise ValueError('S2 stage/official whitener provenance mismatch')
    if provenance['text_seal_sha256'] != P.sha(texts/'INPUT_SEAL.json'):
        raise ValueError('S2 reconstruction/text seal mismatch')
    if AR._read(reconstruction/'ids.json') != [r['id'] for r in records]:
        raise ValueError('S2 reconstruction ID/order mismatch')
    rec = AR._tensor(np.load(reconstruction/'recon.npy',allow_pickle=False),'S2 reconstructions')
    if len(rec) != len(records):
        raise ValueError('S2 reconstruction coverage mismatch')
    if P.sha(text_labels) != AR._read(texts/'provenance.json')['labels_sha256']:
        raise ValueError('S2 text label hash mismatch')
    labels = P.rows(text_labels)
    if labels != AR.freeze_text_records(definitions)[1]:
        raise ValueError('S2 text labels differ from frozen grid')
    return records, labels, definitions, rec


def run(a):
    started = time.perf_counter()
    if P.sha(AR.__file__) != APPROVED_AR:
        raise ValueError('P3-approved ar_tests.py bytes changed')
    items,h = AR._target(a.bank,a.target)
    seal = P.verify(a.w1,'ANALYSIS_SEAL.json')
    if not {'metrics.json','probe_directions.json','probe_directions.npz'} <= set(seal['files']):
        raise ValueError('W1 analysis seal missing directions/metrics')
    metrics, meta = AR._read(a.w1/'metrics.json'), AR._read(a.w1/'probe_directions.json')
    if (metrics['input_seal_sha256'] != P.sha(a.bank/'INPUT_SEAL.json')
        or P.sha(a.target/'SCORE_SEAL.json') not in metrics['reader_seals'] or meta['fit_split'] != 'dev'):
        raise ValueError('W1 bank/target/direction lineage mismatch')
    records, text_labels, definitions, rec = sealed_s2(a.texts,a.reconstruction,a.text_labels)
    expected = AR.definitions_from_bank(a.bank)
    if len(expected) != 40 or any(definitions.get(f) != d for f,d in expected.items()):
        raise ValueError('S2 must contain all40exact W1 binary definitions')
    labels = AR._labels(a.bank,a.labels,items)
    cells = {r['feature']:r for r in metrics['rows'] if r['reader']=='olens' and r['layer']==44}
    if len(cells) != 40 or set(cells) != set(expected):
        raise ValueError('W1 Oracle cell coverage mismatch')
    rows = []
    with np.load(a.w1/'probe_directions.npz',allow_pickle=False) as arrays:
        for f,definition in sorted(expected.items()):
            cell = cells[f]; matches = [r for r in meta['rows'] if r['feature']==f and r['layer']==44]
            if len(matches) != 1:
                raise ValueError('missing/duplicate W1 raw44 direction')
            dm = matches[0]
            if (dm['fit_split'] != 'dev' or dm['orientation_flipped'] is not False
                or dm['positive_value'] != definition['values'][0] or dm['negative_value'] != definition['values'][1]):
                raise ValueError('W1 direction fitting/orientation mismatch')
            direction = AR._tensor(arrays[dm['array_prefix']+'__unit'],'raw44 direction',1)
            coef = AR._tensor(arrays[dm['array_prefix']+'__coef'],'raw44 coefficient',1)
            if not np.isclose(float(direction.norm()),1,atol=1e-5) or not np.allclose(coef/coef.norm(),direction,rtol=1e-5,atol=1e-6):
                raise ValueError('raw unit direction disagrees with raw coefficient')
            idx = AR._test_indices(items,labels,f)
            ti = [i for i,r in enumerate(records) if r['feature']==f]
            if len(ti) != 40:
                raise ValueError('need20texts per value for each W1 row')
            y = [labels[items[i]['id']]['value']==definition['values'][0] for i in idx]
            row = {'feature':f,'row_class':definition['row_class'],'evaluable':cell['status']=='EVALUABLE',
                'W1_gate':cell['status'],'probe_auroc':cell['probe_auroc'],
                'oracle_auroc':cell['true']['auroc'] if cell['true'] else None,
                'exported_test_class_mean_projection_gap':dm['test_class_mean_projection_gap']}
            try:
                result = AR.fidelity(rec[ti],[text_labels[i] for i in ti],h[idx],y,direction)
            except ValueError as e:
                if 'degenerate real class-mean gap' not in str(e): raise
                result = {'status':'NOT EVALUABLE','fidelity':None,'reason':str(e)}
            if result['fidelity'] is not None and not np.isclose(result['denominator'],dm['test_class_mean_projection_gap'],rtol=1e-5,atol=1e-5):
                raise ValueError('real test class-mean gap disagrees with W1 export')
            rows.append({**row,**result})
    a.out.mkdir(parents=True,exist_ok=False)
    P.dump(a.out/'metrics.w2.json',{'rows':rows,'W2':AR.w2_decision(rows),'w1_status':metrics['w1']['status'],
        'inference_scope':'REGISTERED_SECTION71_CPU_REUSE','n_W1_rows':40,'n_W1_texts_reused':1600,
        'correlation_denominator':'all W1-evaluable rows with defined fidelity;all40rows reported',
        'reconstruction_score_seal_sha256':P.sha(a.reconstruction/'SCORE_SEAL.json'),
        'w1_analysis_seal_sha256':P.sha(a.w1/'ANALYSIS_SEAL.json')})
    P.dump(a.out/'run.json',{'step':'W2_CPU','wall_s':time.perf_counter()-started,'gpu_hours':0,'model_forwards':0,
        'ar_tests_sha256':P.sha(AR.__file__),'source_sha256':P.sha(__file__),'seed':P.SEED})
    P.seal(a.out,['metrics.w2.json','run.json'],'SCORES_SEALED_W2_CPU')
    print('HANDOFF W2: '+AR._read(a.out/'metrics.w2.json')['W2']['status']+'; CPU; '+str(a.out/'metrics.w2.json'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for field in ('bank','target','w1','texts','reconstruction','labels','text-labels','out'):
        p.add_argument('--'+field,type=Path,required=True)
    run(p.parse_args())


if __name__=='__main__': main()
