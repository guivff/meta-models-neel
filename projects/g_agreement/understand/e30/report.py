"""E30 registered, once-only post-seal analysis; no row exclusion or sign fitting."""
import argparse
import hashlib
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
import common
from mats.metrics import auroc_labels,auroc_ci,cluster_bootstrap
from projects.g_agreement.blindspot import protocol as P
from .inputs import load,read,RESULTS
from .run import INPUT_SHA,DONORS_SHA

SEED=20261025
N_BOOT=2000
GRID=tuple((f,a) for f in ['baseline','value_words'] for a in ['matched','random','opposite'])+(('value_words','base_text'),)


def analyse(records,data,labels,n_boot=N_BOOT):
    items=data['items'];expected={(r['id'],f,a) for r in items for f,a in GRID}
    actual={(r['id'],r['family'],r['arm']) for r in records}
    if len(records)!=len(expected) or actual!=expected:raise ValueError('complete unique seven-arm grid required')
    truth={r['id']:r for r in labels}
    if len(truth)!=len(labels) or set(truth)!={r['id'] for r in items}:raise ValueError('private truth coverage')
    lookup={(r['id'],r['family'],r['arm']):r for r in records};byid={r['id']:r for r in items}
    for r in records:
        item=byid[r['id']]
        if r['feature']!=item['feature'] or truth[r['id']]['feature']!=item['feature']:raise ValueError('row mismatch')
        pairs=np.asarray(r['pair_scores'],float)
        if pairs.shape!=(2,) or not np.isfinite(pairs).all() or not np.isclose(r['score'],pairs.mean(),rtol=0,atol=1e-5):raise ValueError('pair mean/finiteness mismatch')
        expected_donor=None if r['arm']=='base_text' else r['id'] if r['arm']=='matched' else data['donors'][r['arm']][r['id']]
        if r['donor_id']!=expected_donor:raise ValueError('score donor not frozen map')
    refs={r['id']:r for r in data['reference']}
    cells=[]
    for feature in data['scope']['all_rows']:
        ids=[r['id'] for r in items if r['feature']==feature]
        y=np.array([truth[k]['y'] for k in ids]);groups=np.array([truth[k]['cluster'] for k in ids])
        if set(y)!={0,1} or len(set(groups))!=6:raise ValueError('binary truth/six clusters required')
        scores={(f,a):np.array([lookup[k,f,a]['score'] for k in ids]) for f,a in GRID}
        measures={f+'/'+a:asdict(auroc_ci(scores[f,a],y,groups,n_boot=n_boot,seed=SEED)) for f,a in GRID}
        base=measures['baseline/matched']['auroc'];value=measures['value_words/matched']['auroc']
        reference=auroc_labels([np.mean(refs[k]['scores']) for k in ids],y)
        delta=value-base
        ci=cluster_bootstrap(lambda ix:auroc_labels(scores['value_words','matched'][ix],y[ix])-auroc_labels(scores['baseline','matched'][ix],y[ix]),groups,n_boot=n_boot,seed=SEED)
        null_pass=all(.4-1e-12<=measures[f+'/random']['auroc']<=.6+1e-12 for f in ['baseline','value_words'])
        secondary={f:None if measures[f+'/matched']['auroc']<.7-1e-12 else measures[f+'/opposite']['auroc']<=.4+1e-12 for f in ['baseline','value_words']}
        cells.append({'feature':feature,'n':len(ids),'measures':measures,'sealed_w1_auroc':reference,
                      'R0':abs(base-reference)<=.03+1e-12,'random_control_pass':null_pass,
                      'status':'CONTROL_PASSED' if null_pass else 'CONTROL_FAILED',
                      'opposite_reversal_pass':secondary,'delta':delta,'delta_ci95':list(ci),
                      'R1_raw':delta>=.15-1e-12 and ci[0]>0,'R1':bool(delta>=.15-1e-12 and ci[0]>0) if null_pass else None,
                      'R3_raw':abs(delta)<=.05+1e-12})
    byrow={c['feature']:c for c in cells};structure=[byrow[f] for f in data['scope']['primary_structure_rows']];content=[byrow[f] for f in data['scope']['primary_content_rows']]
    if len(structure)!=16 or len(content)!=9:raise ValueError('fixed16/9primary denominator')
    median=float(np.median([c['measures']['value_words/matched']['auroc'] for c in structure]));count=sum(c['R1_raw'] for c in structure)
    r0=all(c['R0'] for c in cells)
    raw='REFRAME_DESCRIPTIONS_VS_VALUE_WORDS' if median>=.7-1e-12 and count>=8 else 'BLIND_SPOT_STANDS' if median<=.6+1e-12 and count<=3 else 'INTERMEDIATE'
    r2='INVALID_R0' if not r0 else 'UNINTERPRETABLE_CONTROL_FAILED' if not all(c['random_control_pass'] for c in structure) else raw
    r3=None if not r0 or not all(c['random_control_pass'] for c in content) else all(c['R3_raw'] for c in content)
    return {'experiment':'E30','status':'VALID_R0' if r0 else 'INVALID_R0','R0':r0,'R2':r2,'R2_raw_descriptive':raw,
            'R3':r3,'structure_median':median,'R1_raw_count_of16':count,'control_failed_rows':[c['feature'] for c in cells if not c['random_control_pass']],
            'n_records':len(records),'bootstrap':{'n':n_boot,'seed':SEED,'unit':'W1 template cluster; paired same resamples for difference'},
            'control_policy':'No failed rows removed or replaced; raw endpoints retained. Primary null gates interpretation. Secondary opposite reversal is reported separately.',
            'cells':cells}


def generate(scores,inputs,labels,out):
    scores,inputs,labels,out=map(Path,(scores,inputs,labels,out))
    lock=out.with_name(out.name+'.lock')
    if out.exists():raise FileExistsError('analysis output exists')
    lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:f.write('E30 analysis started; never rerun implicitly\n')
    seal=P.verify(scores,'SCORE_SEAL.json')
    if seal['status']!='SCORES_SEALED_EXPLORATORY_E30' or read(scores/'RUN_STATUS.json')['status']!='COMPLETE':raise ValueError('complete sealed scores required')
    if P.sha(inputs/'INPUT_SEAL.json')!=INPUT_SHA:raise ValueError('input pin')
    data=load(inputs);prov=read(scores/'provenance.json')
    if prov['input_seal_sha256']!=INPUT_SHA or prov['donors_sha256']!=DONORS_SHA:raise ValueError('score lineage mismatch')
    own=str(Path(__file__).resolve().relative_to(P.ROOT))
    if prov['source_files'].get(own)!=registered_source_sha():raise ValueError('analysis differs from scored source freeze')
    if P.sha(labels)!=data['provenance']['labels_sha256']:raise ValueError('private truth hash mismatch')
    reference_path=RESULTS/'E15_REFERENCE.json'
    reference_key=str(reference_path.relative_to(P.ROOT))
    if prov['source_files'].get(reference_key)!=P.sha(reference_path):raise ValueError('E15 reference pin')
    result=analyse(P.rows(scores/'scores.jsonl'),data,P.rows(labels))
    e15=read(reference_path)
    for cell in result['cells']:
        cell['w1_class']=e15['w1_classes'][cell['feature']]
        cell['E15_descriptive_reference']=e15['rows'].get(cell['feature'],{'status':'NOT_REGISTERED_IN_E15'})
    result['E15_reference_provenance']={k:v for k,v in e15.items() if k not in ['rows','w1_classes']}
    result['provenance']={'score_seal_sha256':P.sha(scores/'SCORE_SEAL.json'),'input_seal_sha256':INPUT_SHA,'analysis_sha256':P.sha(Path(__file__))}
    out.mkdir();P.dump(out/'summary.json',result)
    lines=['Prediction: a partial value-word effect, short of R2’s reframing threshold.','',f"R0: {result['R0']}; R2: {result['R2']}; R3: {result['R3']}.",f"Primary structure median: {result['structure_median']:.4f}; raw R1 count: {result['R1_raw_count_of16']}/16.",'','Control-failed rows: '+(', '.join(result['control_failed_rows']) or 'none')+'.','',
           'W1’s baseline and the new value-word candidates are both bullets. This is a descriptions-versus-value-words comparison. All rows and controls remain in summary.json; failed controls are not dropped. Three optional LaTeX rows are descriptive extras, outside the fixed16/9primary denominators.','',
           '| Row | W1 descriptive | Value words | Δ (95% CI) | Random control |','|---|---:|---:|---|---|']
    for c in result['cells']:
        m=c['measures'];lines.append(f"| {c['feature']} | {m['baseline/matched']['auroc']:.4f} | {m['value_words/matched']['auroc']:.4f} | {c['delta']:+.4f} [{c['delta_ci95'][0]:+.4f}, {c['delta_ci95'][1]:+.4f}] | {c['status']} |")
    lines+=['','E15 comparison (descriptive; no new threshold):','', '| Row | E30 raw R1 | E15 Oracle continuation AUROC |','|---|---|---:|']
    for c in result['cells']:
        ref=c['E15_descriptive_reference'];value=ref.get('true')
        if c['w1_class']!='semantic':lines.append(f"| {c['feature']} | {c['R1_raw']} | {value['auroc'] if value else ref['status']} |")
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    P.dump(out/'ANALYSIS_SEAL.json',{'status':'E30_ANALYSIS_SEALED','files':{n:P.sha(out/n) for n in ['summary.json','RESULTS.md']}})
    return result

def registered_source_sha():
    # §138 item 1: verify the original capture pin after reversing ONLY this correction.
    data=Path(__file__).read_bytes()
    start=data.index(b'\ndef registered_source_sha():')
    end=data.index(b"\nif __name__=='__main__':",start)
    data=data[:start]+data[end:]
    data=data.replace(b'import argparse\nimport hashlib',b'import argparse',1)
    data=data.replace(b'atol=1e-5',b'atol=1e-10',1)
    data=data.replace(b'registered_source_sha()',b'P.sha(Path(__file__))')
    return hashlib.sha256(data).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['scores','inputs','labels','out']:p.add_argument('--'+n,type=Path,required=True)
    r=generate(**vars(p.parse_args()));print(json.dumps({k:r[k] for k in ['status','R0','R2','R3']}))
