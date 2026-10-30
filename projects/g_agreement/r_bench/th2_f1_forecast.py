"""Registered TH-2-F1 corpus cross-fit, label-free prediction and refit bootstrap.

Only endpoint feature arrays enter ridge prediction. Endpoint labels/errors are
read for posterior diagnostics and accuracy AFTER the predictions are frozen.
"""
from __future__ import annotations
import argparse
import json
import os
import time
from pathlib import Path
import numpy as np
import pandas as pd
from projects.g_agreement.r_bench import th2_f1_models as M
from projects.g_agreement.r_bench import th2_models as M4

READERS = ['jlens', 'olens', 'nla', 'skip_a', 'probe', 'prompt_only']
FEATURES = ['po_margin', 'probe_margin', 'log_token_count', 'log_char_count', 'candidate_frequency_mean', 'candidate_frequency_difference']
OUT = Path('results/g_agreement/r/i2')


def weighted_tails(scores, weights, ids, fraction=.2):
    """Exactly fraction of positive weight at each tail, stable label-free ties."""
    scores, weights, ids = np.asarray(scores), np.asarray(weights, float), np.asarray(ids, str)
    if len(scores) != len(weights) or len(ids) != len(weights):
        raise ValueError('tail array length mismatch')
    if not np.isfinite(scores).all() or not np.isfinite(weights).all() or (weights < 0).any():
        raise ValueError('nonfinite scores/invalid weights')
    order = np.lexsort((ids, scores))
    w = weights[order]; cumulative = np.cumsum(w)
    budget = fraction * w.sum()
    lo = np.minimum(w, np.maximum(0., budget - (cumulative - w)))
    hi = np.minimum(w, np.maximum(0., cumulative - (w.sum() - budget)))
    low = np.zeros_like(weights); high = low.copy()
    low[order], high[order] = lo, hi
    return low, high


def fit_predict(trainfeatures, targets, trainweights, testfeatures, alpha=10.):
    """Weighted training-only imputation, standardization, fixed ridge, intercept.

    Returns predictions and coefficient diagnostics. Labels and IDs have no API
    path into this function. Missingness indicators are added before scaling;
    constant columns get coefficient zero.
    """
    x, t, w, z = (np.asarray(trainfeatures, float), np.asarray(targets, float),
                  np.asarray(trainweights, float), np.asarray(testfeatures, float))
    if x.ndim != 2 or z.ndim != 2 or x.shape[1] != z.shape[1]:
        raise ValueError('feature dimensions')
    if not np.isfinite(t).all() or not np.isfinite(w).all() or (w < 0).any() or w.sum() <= 0:
        raise ValueError('invalid targets/weights')
    if len(t) != len(x) or len(w) != len(x):
        raise ValueError('training lengths')
    missing = ~np.isfinite(x); zmissing = ~np.isfinite(z)
    available = np.sum(w[:, None] * ~missing, axis=0)
    fill = np.divide(np.sum(np.where(missing, 0., x) * w[:, None], axis=0), available,
                     out=np.zeros(x.shape[1]), where=available > 0)
    xx = np.concatenate([np.where(missing, fill, x), missing.astype(float)], axis=1)
    zz = np.concatenate([np.where(zmissing, fill, z), zmissing.astype(float)], axis=1)
    mean = np.average(xx, axis=0, weights=w)
    scale = np.sqrt(np.average((xx - mean) ** 2, axis=0, weights=w))
    active = scale > 1e-12
    scaled = (xx[:, active] - mean[active]) / scale[active]
    test_scaled = (zz[:, active] - mean[active]) / scale[active]
    intercept = float(np.average(t, weights=w))
    b = np.linalg.solve(scaled.T @ (scaled * w[:, None]) + alpha * np.eye(active.sum()),
                        scaled.T @ (w * (t - intercept)))
    coef = np.zeros(xx.shape[1]); coef[active] = b
    pred = intercept + test_scaled @ b
    if not np.isfinite(pred).all():
        raise ValueError('nonfinite ridge prediction')
    return pred, dict(coef=coef, mean=mean, scale=scale, fill=fill, active=active, intercept=intercept)


def feature_matrix(frame, model_fold, block):
    suffix = f'_B_fold{model_fold}' if block == 'B' else f'_fold{model_fold}'
    cols = FEATURES[:4] + ['freq_mean' + suffix, 'freq_diff' + suffix]
    return frame[cols].to_numpy(float)


def prepare(rows, block='A', convention='allmedian'):
    q = rows[rows.eligible.astype(bool)].copy()
    if block == 'B':
        q = q[q.block_B.astype(bool)]
    if convention == 'literal':
        for r in READERS[:4]:
            q['e_' + r] = q['literal_err_' + r]
    facts = []
    for ds, g in q.groupby('dataset', sort=True):
        f = dict(dataset=ds, corpus=str(g.corpus_group.iloc[0]), fold=int(g.fold.iloc[0]), halves={})
        for h in ['calibration', 'endpoint']:
            a = g[g.half == h].sort_values('item_id')
            bits = a[['e_' + r for r in READERS]].to_numpy(int)
            if not np.isin(bits, [0, 1]).all():
                raise ValueError('errors are not binary')
            f['halves'][h] = dict(ids=a.item_id.to_numpy(str), docs=a.text_hash.to_numpy(str),
                                  y=a.label.to_numpy(int), bits=bits, codes=bits @ (1 << np.arange(6)),
                                  x=[feature_matrix(a, k, block) for k in range(5)])
        facts.append(f)
    return facts


def occurrences(facts, rng=None):
    """Draw fresh corpus occurrences, fact occurrences, then shared document weights."""
    if rng is None:
        return [dict(fact=f, weights={h:np.ones(len(v['ids'])) for h,v in f['halves'].items()}, occurrence=i)
                for i,f in enumerate(facts)]
    groups = {c:[f for f in facts if f['corpus'] == c] for c in sorted({f['corpus'] for f in facts})}
    names = list(groups); result = []
    for ci in rng.integers(len(names), size=len(names)):
        group = groups[names[ci]]
        selected = [group[i] for i in rng.integers(len(group), size=len(group))]
        dw = {}
        for h in ['calibration', 'endpoint']:
            docs = np.unique(np.concatenate([f['halves'][h]['docs'] for f in selected]))
            counts = rng.multinomial(len(docs), np.full(len(docs), 1 / len(docs)))
            dw[h] = dict(zip(docs, counts))
        for f in selected:
            weights = {h:np.array([dw[h][d] for d in f['halves'][h]['docs']], float) for h in dw}
            result.append(dict(fact=f, weights=weights, occurrence=len(result)))
    return result


def sufficient(occs):
    cal, end, folds, labels = [], [], [], []
    for o in occs:
        f = o['fact']
        for y in [0, 1]:
            for h, target in [('calibration', cal), ('endpoint', end)]:
                a = f['halves'][h]; pick = a['y'] == y
                target.append(np.bincount(a['codes'][pick], weights=o['weights'][h][pick], minlength=64))
            folds.append(f['fold']); labels.append(y)
    cal, end = np.array(cal), np.array(end)
    n = cal.sum(axis=1)
    if np.any((n == 0) & (end.sum(axis=1) > 0)):
        raise ValueError('empty calibration class with endpoint mass')
    p = (cal @ M.BITS + .5) / (n[:, None] + 1.)
    return dict(cal=cal, end=end, p=p, pairs=M.pair_counts(cal), folds=np.array(folds),
                labels=np.array(labels), n=n)


def _weighted_corr(a, b, w):
    am, bm = np.average(a, weights=w), np.average(b, weights=w)
    va = np.average((a-am)**2, weights=w); vb = np.average((b-bm)**2, weights=w)
    return float(np.average((a-am)*(b-bm), weights=w)/np.sqrt(va*vb)) if va*vb > 0 else np.nan


def _accuracy_metric(predictions, method, global_quintiles=False, label=None):
    chunks=[]
    for p in predictions:
        w=p['weights']; score=p[method]; a=p['accuracy']
        # Primary quintiles are defined without labels. Class-specific summaries
        # restrict these same selected weights, never construct class-based ranks.
        low, high=weighted_tails(score,w,p['ids'])
        chunks.append((p,low,high))
    if global_quintiles:
        scores=np.concatenate([p[method] for p in predictions]); w=np.concatenate([p['weights'] for p in predictions])
        ids=np.concatenate([np.array([f"{p['occurrence']}:{x}" for x in p['ids']]) for p in predictions])
        low,high=weighted_tails(scores,w,ids); pos=0; chunks=[]
        for p in predictions:
            n=len(p['weights']); chunks.append((p,low[pos:pos+n],high[pos:pos+n]));pos+=n
    low_n=high_n=0.; low_correct=np.zeros(4); high_correct=np.zeros(4)
    for p,low,high in chunks:
        if label is not None:
            low=low*(p['y']==label); high=high*(p['y']==label)
        low_n+=low.sum();high_n+=high.sum()
        low_correct += low @ (1-p['bits'][:,:4]);high_correct += high @ (1-p['bits'][:,:4])
    if low_n<=0 or high_n<=0:
        raise ValueError('empty quintile')
    low_acc,high_acc=low_correct/low_n,high_correct/high_n
    out=dict(low_accuracy=float(low_acc.mean()),high_accuracy=float(high_acc.mean()),
             gap=float((low_acc-high_acc).mean()), low_n=float(low_n),high_n=float(high_n))
    for j,r in enumerate(READERS[:4]):
        out['gap_'+r]=float(low_acc[j]-high_acc[j])
    return out


def evaluate(occs, warm=None, descriptive=False, return_predictions=False):
    """Fit only calibration rows; make and freeze endpoint predictions first."""
    s=sufficient(occs); p=s['p']; folds=s['folds']; ys=s['labels']; n=s['n']
    fits=[]; coefs=[]; predictions=[]; warm_out={}
    matched=[]
    for k in range(5):
        tables=np.zeros((len(p),64)); table4=np.zeros((len(p),16)) if descriptive else None
        joint6=np.zeros((len(p),64)) if descriptive else None
        joint4=np.zeros((len(p),16)) if descriptive else None
        for y in [0,1]:
            tr=(folds!=k)&(ys==y)&(n>0); same=ys==y; te=(folds==k)&same
            if not tr.any():raise ValueError('empty outer training sample')
            key=f'{k}:{y}'
            fit=M.fit_factor(p[tr],s['pairs'][tr],start=None if warm is None else warm.get(key),multistart=True)
            if not fit['success']:raise ValueError('six-factor optimizer failed: '+str(fit))
            a=np.asarray(fit['loadings']);warm_out[key]=a
            if np.max(a[:4])<1e-6:raise ValueError('reader anchors all zero: difficulty orientation unidentified')
            q,d=M.joint_posterior(p[same],a)
            tables[same]=d
            count_error=s['cal'][tr]@M.BITS; total=s['cal'][tr].sum()
            sums=count_error.sum(axis=0)
            fr=dict(fold=k,label=y,n_cal=float(total),nll=float(fit['nll']),success=True,
                    **{r:float(v) for r,v in zip(READERS,a)})
            for j,r in enumerate(READERS):
                fr['n_error_'+r]=float(sums[j]);fr['n_correct_'+r]=float(total-sums[j])
            if descriptive:
                # Numerical check for probabilities and posterior expectations.
                qhi,dhi=M.joint_posterior(p[same],a,n_nodes=1024)
                mass=q>1e-10
                delta=float(np.max(np.abs(q-qhi)))
                ddelta=float(np.max(np.abs(d[mass]-dhi[mass])))
                if delta>1e-6 or ddelta>2e-5:raise ValueError(f'quadrature error {delta}, {ddelta}')
                fr['quad_prob_error']=delta;fr['quad_posterior_error']=ddelta
                joint6[same]=q
                cal4=np.stack([np.bincount(np.arange(64)%16,weights=x,minlength=16) for x in s['cal']])
                pair4=np.stack([np.stack([np.bincount(2*M4.BITS[:,i]+M4.BITS[:,j],weights=x,minlength=4) for i,j in M4.PAIRS]) for x in cal4])
                fit4=M4.fit_factor(p[tr,:4],pair4[tr],multistart=True)
                if not fit4['success']:raise ValueError('matched four-factor fit failed')
                _,d4=M.joint_posterior(p[same,:4],fit4['loadings']);table4[same]=d4
                joint4[te]=M4.joint_factor(p[te,:4],fit4['loadings'])
                for j,r in enumerate(READERS[:4]):fr['matched_four_'+r]=float(fit4['loadings'][j])
                # Pairwise calibration residuals use only training rows, not endpoints.
                pairprobs=M.pair_probabilities(p[tr],a[M.PAIR_I]*a[M.PAIR_J])
                predicted=np.sum(pairprobs*s['cal'][tr].sum(axis=1)[:,None,None],axis=0)
                actual=s['pairs'][tr].sum(axis=0)
                fr['pair_max_abs_residual']=float(np.max(np.abs(predicted-actual))/total)
            fits.append(fr)
        train=[];test=[]
        for i,o in enumerate(occs):
            f=o['fact'];h='endpoint' if f['fold']==k else 'calibration';a=f['halves'][h]
            # Endpoint posterior lookup is deliberately deferred until after g(X).
            target=None if f['fold']==k else tables[2*i+a['y'],a['codes']]
            rec=dict(i=i,o=o,a=a,x=a['x'][k],w=o['weights'][h],target=target)
            if descriptive and f['fold']!=k:
                rec['fourtarget']=table4[2*i+a['y'],a['codes']%16]
                rec['directtarget']=a['bits'][:,:4].mean(axis=1)
            (test if f['fold']==k else train).append(rec)
        if not test:continue
        X=np.concatenate([r['x'] for r in train]);w=np.concatenate([r['w'] for r in train]);Z=np.concatenate([r['x'] for r in test])
        methods={'predicted_difficulty':'target'}
        if descriptive:methods.update(four_target_prediction='fourtarget',direct_error_prediction='directtarget')
        forecasts={}
        for method,targetname in methods.items():
            target=np.concatenate([r[targetname] for r in train])
            forecast,cf=fit_predict(X,target,w,Z)
            forecasts[method]=forecast
            for j,name in enumerate(FEATURES+[x+'_missing' for x in FEATURES]):
                coefs.append(dict(fold=k,method=method,feature=name,coefficient=float(cf['coef'][j]),
                                  train_mean=float(cf['mean'][j]),train_sd=float(cf['scale'][j]),active=bool(cf['active'][j]),intercept=cf['intercept']))
        # All endpoint predictions above used features only. Now expose accuracy,
        # label-conditioned posterior and other diagnostic outcomes.
        start=0
        for r in test:
            o,a=r['o'],r['a'];end=start+len(a['ids'])
            rec=dict(dataset=o['fact']['dataset'],corpus=o['fact']['corpus'],fold=k,occurrence=o['occurrence'],
                     ids=a['ids'],docs=a['docs'],y=a['y'],bits=a['bits'],weights=r['w'],
                     posterior_difficulty=tables[2*r['i']+a['y'],a['codes']],accuracy=1-a['bits'][:,:4].mean(axis=1),
                     **{method:v[start:end] for method,v in forecasts.items()})
            if descriptive:
                rec['po_confidence']=-r['x'][:,0];rec['probe_confidence']=-r['x'][:,1]
            predictions.append(rec);start=end
        if descriptive:
            for i,o in enumerate(occs):
                if o['fact']['fold']!=k:continue
                for y in (0,1):
                    ix=2*i+y; en=s['end'][ix];nn=en.sum()
                    q4six=np.bincount(np.arange(64)%16,weights=joint6[ix],minlength=16)
                    q4=joint4[ix];qind=M4.joint_independence(p[ix,:4])[0]
                    en4=np.bincount(np.arange(64)%16,weights=en,minlength=16)
                    matched.append(dict(n=nn,observed_allwrong=en4[15],six_expected=nn*q4six[15],four_expected=nn*q4[15],ind_expected=nn*qind[15],
                                        six_log=float(en4@np.log(np.maximum(q4six,1e-300))),four_log=float(en4@np.log(np.maximum(q4,1e-300))),ind_log=float(en4@np.log(np.maximum(qind,1e-300)))))
    primary=_accuracy_metric(predictions,'predicted_difficulty')
    result={**primary}
    for y in (0,1):
        fy=[f for f in fits if f['label']==y]
        if len(fy)!=5:raise ValueError('not all five loading fits present')
        for r in READERS:result[f'loading_y{y}_{r}']=float(np.mean([f[r] for f in fy]))
    result['global_gap']=_accuracy_metric(predictions,'predicted_difficulty',global_quintiles=True)['gap']
    aa=np.concatenate([r['posterior_difficulty'] for r in predictions]);bb=np.concatenate([r['predicted_difficulty'] for r in predictions]);ww=np.concatenate([r['weights'] for r in predictions])
    variance=np.average((aa-np.average(aa,weights=ww))**2,weights=ww)
    result['posterior_r2']=float(1-np.average((aa-bb)**2,weights=ww)/variance)
    result['posterior_correlation']=_weighted_corr(aa,bb,ww)
    for feature in FEATURES:
        cf=[r['coefficient'] for r in coefs if r['method']=='predicted_difficulty' and r['feature']==feature]
        result['coefficient_'+feature]=float(np.mean(cf)) if len(cf)==5 else np.nan
    if descriptive:
        for method in ['four_target_prediction','direct_error_prediction','po_confidence','probe_confidence']:
            for name,val in _accuracy_metric(predictions,method).items():result[method+'_'+name]=val
        for y in (0,1):
            for name,val in _accuracy_metric(predictions,'predicted_difficulty',label=y).items():result[f'label{y}_'+name]=val
        a=np.concatenate([r['posterior_difficulty'] for r in predictions]);b=np.concatenate([r['predicted_difficulty'] for r in predictions]);ww=np.concatenate([r['weights'] for r in predictions])
        var=np.average((a-np.average(a,weights=ww))**2,weights=ww)
        result['posterior_r2']=float(1-np.average((a-b)**2,weights=ww)/var)
        result['posterior_correlation']=_weighted_corr(a,b,ww)
        m=pd.DataFrame(matched).sum();nn=m['n']
        for model in ['six','four','ind']:
            result[model+'_allwrong_ratio']=float(m.observed_allwrong/m[model+'_expected'])
            result[model+'_joint_gain']=float((m[model+'_log']-m.ind_log)/nn)
    return dict(metrics=result,fits=fits,coefs=coefs,predictions=predictions if return_predictions else None,warm=warm_out)


def run_point(rows,block='A',descriptive=True,convention='allmedian'):
    facts=prepare(rows,block,convention)
    if len(facts)<20 or set(f['fold'] for f in facts)!=set(range(5)):
        raise ValueError('UNDERPOWERED: insufficient eligible facts/folds')
    ans=evaluate(occurrences(facts),descriptive=descriptive,return_predictions=True)
    ans['metrics'].update(n_facts=len(facts),n_corpora=len({f['corpus'] for f in facts}),
                          n_calibration=sum(len(f['halves']['calibration']['ids']) for f in facts),
                          n_endpoint=sum(len(f['halves']['endpoint']['ids']) for f in facts))
    return ans


def point(rows,out):
    metrics=[];fits=[];coefs=[];preds=[]
    for block in ['A','B']:
        for convention in ['allmedian','literal']:
            ans=run_point(rows,block,descriptive=True,convention=convention)
            context=dict(block=block,convention=convention)
            metrics.append({**context,**ans['metrics']});fits.extend([{**context,**x} for x in ans['fits']]);coefs.extend([{**context,**x} for x in ans['coefs']])
            for p in ans['predictions']:
                low,high=weighted_tails(p['predicted_difficulty'],p['weights'],p['ids'])
                for i,item in enumerate(p['ids']):
                    row={**context,'dataset':p['dataset'],'item_id':item,'fold':p['fold'],'text_hash':p['docs'][i],
                         'label':p['y'][i],'accuracy':p['accuracy'][i],'low_quintile_weight':low[i],'high_quintile_weight':high[i]}
                    for c in ['predicted_difficulty','posterior_difficulty','four_target_prediction','direct_error_prediction','po_confidence','probe_confidence']:
                        row[c]=p[c][i]
                    for j,r in enumerate(READERS):row['e_'+r]=p['bits'][i,j]
                    preds.append(row)
            print(f'point {block} {convention}: '+json.dumps(ans['metrics']),flush=True)
    pd.DataFrame(metrics).to_csv(out/'th2_f1_metrics.csv',index=False)
    pd.DataFrame(fits).to_csv(out/'th2_f1_fits.csv',index=False)
    pd.DataFrame(coefs).to_csv(out/'th2_f1_coefficients.csv',index=False)
    pd.DataFrame(preds).to_csv(out/'th2_f1_predictions.csv.gz',index=False,compression={'method':'gzip','mtime':0})

_WORK=None

def init_worker(rowsfile,block,fitfile):
    global _WORK
    rows=pd.read_csv(rowsfile);facts=prepare(rows,block)
    ff=pd.read_csv(fitfile);ff=ff[(ff.block==block)&(ff.convention=='allmedian')]
    warm={f'{int(r.fold)}:{int(r.label)}':np.array([getattr(r,x) for x in READERS]) for r in ff.itertuples()}
    _WORK=facts,block,warm


def bootstrap_one(rep):
    facts,block,warm=_WORK;t0=time.monotonic();seed=20261023+(100000 if block=='B' else 0)+rep
    try:
        ans=evaluate(occurrences(facts,np.random.default_rng(seed)),warm=warm)
        return dict(block=block,replicate=rep,seed=seed,valid=True,error='',seconds=time.monotonic()-t0,**ans['metrics'])
    except Exception as exc:
        return dict(block=block,replicate=rep,seed=seed,valid=False,error=f'{type(exc).__name__}: {exc}',seconds=time.monotonic()-t0)


def bootstrap(rowsfile,out,reps=2000,workers=4,blocks=('A','B')):
    from concurrent.futures import ProcessPoolExecutor
    import multiprocessing as mp
    for block in blocks:
        path=out/f'th2_f1_bootstrap_{block}.csv';existing=[]
        if path.exists():existing=pd.read_csv(path).to_dict('records')
        done={int(x['replicate']) for x in existing};todo=[i for i in range(reps) if i not in done]
        values=existing
        with ProcessPoolExecutor(max_workers=workers,mp_context=mp.get_context('spawn'),initializer=init_worker,
                                 initargs=(str(rowsfile),block,str(out/'th2_f1_fits.csv'))) as pool:
            for r in pool.map(bootstrap_one,todo,chunksize=1):
                values.append(r)
                if len(values)%25==0:
                    pd.DataFrame(values).sort_values('replicate').to_csv(path,index=False)
                    print(f'bootstrap {block}: {len(values)}/{reps}, valid {sum(bool(x["valid"]) for x in values)}',flush=True)
        pd.DataFrame(values).sort_values('replicate').to_csv(path,index=False)


def intervals(out):
    point=pd.read_csv(out/'th2_f1_metrics.csv');fits=pd.read_csv(out/'th2_f1_fits.csv');ci=[];verdict=[]
    for block in ['A','B']:
        b=pd.read_csv(out/f'th2_f1_bootstrap_{block}.csv');valid=b[b.valid.astype(bool)];rate=len(valid)/len(b)
        p=point[(point.block==block)&(point.convention=='allmedian')].iloc[0]
        for col in valid:
            if col in ['replicate','seed','valid','seconds','block','error'] or col not in p:continue
            values=valid[col].dropna()
            if not len(values):continue
            q=np.quantile(values,[.025,.05,.95,.975])
            ci.append(dict(block=block,metric=col,point=p[col],lo95=q[0],lo90=q[1],hi90=q[2],hi95=q[3],valid=len(valid),n_finite=len(values),total=len(b)))
        cc={r['metric']:r for r in ci if r['block']==block}
        trust='UNDERPOWERED' if rate<.95 or len(b)<2000 else ('USABLE' if p.gap>=.15 and cc['gap']['lo95']>.05 else 'NOT DEMONSTRATED')
        row=dict(block=block,trust_verdict=trust,valid=len(valid),total=len(b))
        f=fits[(fits.block==block)&(fits.convention=='allmedian')]
        for instrument in ['probe','prompt_only']:
            for y in [0,1]:
                q=cc[f'loading_y{y}_{instrument}'];fy=f[f.label==y]
                enough=bool((fy['n_error_'+instrument]>=30).all() and (fy['n_correct_'+instrument]>=30).all())
                v='UNDERPOWERED' if not enough or rate<.95 or len(b)<2000 else ('NEAR ZERO' if q['lo90']>=-.10 and q['hi90']<=.10 else ('POSITIVE SHARED' if q['lo95']>.10 else 'UNDETERMINED'))
                row[f'{instrument}_y{y}']=v
        verdict.append(row)
    pd.DataFrame(ci).to_csv(out/'th2_f1_intervals.csv',index=False)
    pd.DataFrame(verdict).to_csv(out/'th2_f1_verdicts.csv',index=False)
    print(json.dumps(verdict),flush=True)


def main():
    pa=argparse.ArgumentParser();pa.add_argument('phase',choices=['point','bootstrap','intervals']);pa.add_argument('--rows',type=Path,default=OUT/'th2_f1_rows.csv.gz');pa.add_argument('--out',type=Path,default=OUT);pa.add_argument('--reps',type=int,default=2000);pa.add_argument('--workers',type=int,default=4);pa.add_argument('--blocks',nargs='+',default=['A','B']);a=pa.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    if a.phase=='point':point(pd.read_csv(a.rows),a.out)
    elif a.phase=='bootstrap':bootstrap(a.rows,a.out,a.reps,a.workers,a.blocks)
    else:intervals(a.out)

if __name__=='__main__':main()
