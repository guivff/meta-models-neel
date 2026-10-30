"""Single registered E44 analysis; no new E39 analysis or model calls."""
import argparse
import math
from pathlib import Path
import numpy as np
import contract as C
from operational_gates import validate_operational_gates
from release_gate import verify_release_receipt

def eligibility(reference):
    if reference.get('experiment')!='E39' or reference.get('status')!='COMPLETE_ANALYSIS':raise ValueError('sealed complete E39 analysis required')
    by={(x['row'],x['arm']):x for x in reference['cells']}
    if len(by)!=54 or len(reference['cells'])!=54:raise ValueError('complete E39 reference required')
    eligible=[]
    for row in C.STRUCTURE:
        l,s=by[row,'L'],by[row,'S']
        for cell in (l,s):
            if ([x['step'] for x in cell['asked']]!=[0,25,50,100,200,400,800]
                    or any(not math.isfinite(x['auroc']) or not 0<=x['auroc']<=1 for x in cell['asked'])):
                raise ValueError('complete finite E39 reference checkpoints required')
        valid=max(x['auroc'] for x in s['asked'])<=.60 and l['asked'][0]['auroc']<=.65
        if reference['row_eligibility'][row]['interpretable']!=valid:raise ValueError('E39 eligibility summary inconsistent')
        if valid:eligible.append(row)
    return eligible

def evaluate_rules(curves,eligible):
    if set(curves)!=set(C.ROWS) or any(set(v)!=set(C.CHECKPOINTS) or any(not math.isfinite(x) or not 0<=x<=1 for x in v.values()) for v in curves.values()):
        raise ValueError('all 25 rows and four finite AUROCs required')
    if len(eligible)!=len(set(eligible)) or not set(eligible)<=set(C.STRUCTURE):raise ValueError('invalid reference cohort')
    median=float(np.median([curves[r][400] for r in C.CONTENT]));content_ok=median>=.90
    fast=[r for r in eligible if any(curves[r][s]>=.80 for s in (0,25,100))]
    low=[r for r in eligible if curves[r][400]<=.65]
    reasons=[]
    if len(eligible)<8:reasons.append('fewer_than_8_E39_interpretable_structure_rows')
    if not content_ok:reasons.append('content_median_below_0.90_at400')
    return {'eligible_rows':eligible,'content_check':{'met':content_ok,'median_auroc_at400':median,'threshold':.90},
        'not_evaluable_reasons':reasons,
        'R1':{'met':None if reasons else len(fast)/len(eligible)>=.50,'rows':fast,'n':len(fast),'denominator':len(eligible)},
        'R2':{'met':None if reasons else len(low)>len(eligible)/2,'rows':low,'n':len(low),'denominator':len(eligible)}}

def validate_collection(inputs,collection):
    inputs,collection=Path(inputs),Path(collection)
    binding=C.read(C.HERE/'BOUND_INPUT.json')
    C.verify(inputs)
    if C.sha(inputs/'INPUT_SEAL.json')!=binding['input_seal_sha256']:raise ValueError('bound input differs')
    source=C.read(C.HERE/'SOURCE_MANIFEST.json')
    C.verify(C.ROOT,str((C.HERE/'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    seal=C.verify(collection,'OUTPUT_SEAL.json')
    actual={p.relative_to(collection).as_posix() for p in collection.rglob('*') if p.is_file()}
    if actual!=set(seal['files'])|{'OUTPUT_SEAL.json'}:raise ValueError('exact sealed output coverage required')
    a=C.read(collection/'assignment.json');run=C.read(collection/'RUN_RECEIPT.json')
    if (run.get('status')!='COMPLETE_FULL_ASSIGNED_GRID' or run.get('experiment')!='E44'
            or a.get('source_manifest_sha256')!=C.sha(C.HERE/'SOURCE_MANIFEST.json')
            or a.get('input_seal_sha256')!=binding['input_seal_sha256']
            or a.get('plan_sha256')!=C.sha(C.HERE/'PLAN.json')
            or run.get('plan_sha256')!=C.sha(C.HERE/'PLAN.json')
            or run.get('test_labels_opened') is not False or a.get('pod_count')!=1 or a.get('previous_gpu_seconds')!=0
            or not 0<run.get('gpu_seconds_provider',math.inf)<=a.get('allocated_gpu_seconds',0)<=C.CAP):
        raise ValueError('complete original E44 run and budget required')
    validate_operational_gates(collection,run,a)
    if C.sha(collection/'E39_RELEASE_GATE.json')!=a['release_gate_sha256']:raise ValueError('release gate binding differs')
    verify_release_receipt(collection/'E39_RELEASE_GATE.json')
    dev=C.rows(inputs/'dev.jsonl')
    if C.read(collection/'SCHEDULE.json')!=C.training_schedule(dev):raise ValueError('pooled content-only schedule changed')
    training=C.rows(collection/'train.jsonl')
    if [r['step'] for r in training]!=list(range(1,401)) or any(not math.isfinite(r['loss']) for r in training):raise ValueError('exact400 finite optimizer steps required')
    test=C.rows(inputs/'test.jsonl');scoremap={}
    if len(test)!=2100 or len({r['id'] for r in test})!=2100:raise ValueError('complete test population required')
    for step in C.CHECKPOINTS:
        folder=collection/f'step_{step}';s=C.verify(folder,'CHECKPOINT_SEAL.json')
        if set(s['files'])!={r+'.jsonl' for r in C.ROWS}|{'adapter.pt'}:raise ValueError('complete25row checkpoint and adapter required')
        for row in C.ROWS:
            records=C.rows(folder/(row+'.jsonl'));ids={r['id'] for r in test if r['feature']==row}
            if len(records)!=84 or len(ids)!=84 or {r['id'] for r in records}!=ids or any(len(r['scores'])!=2 or not all(math.isfinite(x) for x in r['scores']) for r in records):
                raise ValueError('complete finite paired log-odds grid required')
            scoremap[row,step]={r['id']:float(np.mean(r['scores'])) for r in records}
    return test,scoremap

def analysis(inputs,collection,e39_analysis,out):
    inputs,collection,e39_analysis,out=map(Path,(inputs,collection,e39_analysis,out))
    if out.exists():raise FileExistsError('immutable analysis')
    test,scoremap=validate_collection(inputs,collection)
    C.verify(e39_analysis,'ANALYSIS_SEAL.json')
    reference=C.read(e39_analysis/'METRICS.json')
    if reference.get('analysis_plan_sha256')!='43cf46d872efc6719a1373a81f7bd0ef6b1f1aa53b71b10858593ac3adb5275d':raise ValueError('original E39 analysis plan required')
    eligible=eligibility(reference)
    # Open private labels only after both sealed collections and complete grid validate.
    if C.sha(inputs/'test.labels.DO_NOT_STAGE.jsonl')!=C.read(C.HERE/'BOUND_INPUT.json')['private_test_labels_sha256']:raise ValueError('private test key changed')
    raw=C.rows(inputs/'test.labels.DO_NOT_STAGE.jsonl');labels={r['id']:r for r in raw}
    if len(raw)!=2100 or set(labels)!={r['id'] for r in test}:raise ValueError('exact label coverage required')
    import sys
    sys.path.insert(0,str(C.ROOT));import common
    from mats.metrics import auroc_labels
    cells=[];curves={};refs={(x['row'],x['arm']):x for x in reference['cells']}
    for row in C.ROWS:
        ids=sorted(r['id'] for r in test if r['feature']==row)
        if any(labels[k]['feature']!=row or labels[k]['y'] not in (0,1) for k in ids):raise ValueError('row/label mismatch')
        y=np.array([labels[k]['y'] for k in ids]);groups=np.array([labels[k]['cluster'] for k in ids]);clusters=sorted(set(groups))
        if sum(y)!=42:raise ValueError('balanced frozen row required')
        scores=np.array([[scoremap[row,s][k] for k in ids] for s in C.CHECKPOINTS]);values=[float(auroc_labels(x,y)) for x in scores]
        rng=np.random.default_rng(C.SEED);draws=[np.concatenate([np.flatnonzero(groups==g) for g in rng.choice(clusters,len(clusters),replace=True)]) for _ in range(2000)]
        boot=np.array([[auroc_labels(x[t],y[t]) for x in scores] for t in draws]);ci=np.quantile(boot,[.025,.975],axis=0)
        curves[row]=dict(zip(C.CHECKPOINTS,values))
        ref=refs.get((row,'L'))
        cells.append({'row':row,'arm':'C','asked':[{'step':s,'auroc':values[i],'ci95':ci[:,i].tolist()} for i,s in enumerate(C.CHECKPOINTS)],
            'E39_L_reference':ref['asked'] if ref else None,'E39_step0_reference':ref['asked'][0] if ref else None})
    result={'experiment':'E44','status':'COMPLETE_ANALYSIS','exploratory':True,'cells':cells,**evaluate_rules(curves,eligible),
        'plan_sha256':C.sha(C.HERE/'PLAN.json'),'input_seal_sha256':C.sha(inputs/'INPUT_SEAL.json'),
        'output_seal_sha256':C.sha(collection/'OUTPUT_SEAL.json'),'e39_analysis_seal_sha256':C.sha(e39_analysis/'ANALYSIS_SEAL.json'),
        'bootstrap_seed':C.SEED,'bootstrap_replicates':2000,'E39_analysis_rerun':False}
    out.mkdir(parents=True,exist_ok=False);C.dump(out/'METRICS.json',result)
    verdict=lambda x:'MET' if x is True else 'NOT MET' if x is False else 'NOT EVALUABLE'
    (out/'RESULTS.md').write_text('# E44 registered exploratory results\n\nR1: '+verdict(result['R1']['met'])+'\n\nR2: '+verdict(result['R2']['met'])+'\n\nContent median at400: '+str(result['content_check']['median_auroc_at400'])+'\n\nE39 interpretable structure rows: '+str(len(eligible))+'\n\nNot-evaluable reasons: '+(', '.join(result['not_evaluable_reasons']) or 'none')+'\n')
    C.seal(out,'ANALYSIS_SEAL.json');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','collection','e39-analysis','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=analysis(a.inputs,a.collection,a.e39_analysis,a.out);print('E44 COMPLETE_ANALYSIS')
