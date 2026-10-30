"""TH-2: frozen corpus-crossfit forecast and refitted hierarchical bootstrap (CPU only)."""
from __future__ import annotations
import argparse, itertools, json, os, time
from pathlib import Path
import numpy as np
import pandas as pd
from projects.g_agreement.r_bench import th2_models as M

READERS=['jlens','olens','nla','skip_a']
PAIRS=list(itertools.combinations(range(4),2))
BITS=((np.arange(16)[:,None]>>np.arange(4))&1)
OUT=Path('results/g_agreement/r/i2')

def load_rows(path):
    wide=pd.read_csv(path)
    if 'convention' in wide:return wide
    frames=[]
    for name,prefix in [('allmedian','err_'),('literal','literal_err_'),('poolmedian','pool_err_')]:
        q=wide.copy()
        for r in READERS:q['e_'+r]=q[prefix+r]
        if name=='poolmedian':q['eligible']=q.pool_eligible
        q=q.dropna(subset=['e_'+r for r in READERS])
        q['convention']=name
        frames.append(q)
    return pd.concat(frames,ignore_index=True)

def pair_counts(patterns):
    return np.stack([np.bincount(2*BITS[:,i]+BITS[:,j],weights=patterns,minlength=4) for i,j in PAIRS])

def prepare(rows):
    facts=[]
    for ds,g in rows.groupby('dataset',sort=True):
        f={'dataset':ds,'corpus':g.corpus_group.iloc[0], 'fold':int(g.fold.iloc[0]),'halves':{}}
        for half in ('calibration','endpoint'):
            q=g[g.half==half]
            codes=q[['e_'+r for r in READERS]].to_numpy(int)@ (1<<np.arange(4))
            f['halves'][half]=(q.text_hash.to_numpy(str),q.label.to_numpy(int),codes)
        facts.append(f)
    return facts

def suff(f,docweights=None):
    result=[]
    for label in (0,1):
        vals={}
        for half,(docs,ys,codes) in f['halves'].items():
            w=np.ones(len(docs)) if docweights is None else np.array([docweights[half].get(x,0) for x in docs])
            vals[half]=np.bincount(codes[ys==label],weights=w[ys==label],minlength=16)
        cal=vals['calibration']; end=vals['endpoint'];n=cal.sum()
        result.append({'dataset':f['dataset'],'corpus':f['corpus'],'fold':f['fold'],'label':label,
                       'p':(cal@BITS+.5)/(n+1), 'pairs':pair_counts(cal), 'end':end,'cal_n':n})
    return result

def draw_cells(facts,rng,scheme):
    cells=[]
    if scheme=='fact_item':
        batches=[[facts[i]] for i in rng.integers(len(facts),size=len(facts))]
    else:
        groups={c:[f for f in facts if f['corpus']==c] for c in sorted({f['corpus'] for f in facts})}
        names=list(groups)
        batches=[]
        for i in rng.integers(len(names),size=len(names)):
            group=groups[names[i]]
            batches.append([group[j] for j in rng.integers(len(group),size=len(group))])
    for group in batches:
        dw={}
        for half in ('calibration','endpoint'):
            docs=np.unique(np.concatenate([f['halves'][half][0] for f in group]))
            counts=rng.multinomial(len(docs),np.full(len(docs),1/len(docs)))
            dw[half]=dict(zip(docs,counts))
        for f in group:
            cells.extend(suff(f,dw))
    return cells

def prediction(cells,models=('factor','independence'),warm=None,diagnostic=False):
    p=np.array([c['p'] for c in cells]); pairs=np.array([c['pairs'] for c in cells]); end=np.array([c['end'] for c in cells])
    fold=np.array([c['fold'] for c in cells]); label=np.array([c['label'] for c in cells]);cn=np.array([c['cal_n'] for c in cells])
    if np.any((cn<=0)&(end.sum(1)>0)):raise ValueError('empty calibration cell with endpoint weight')
    preds={name:np.zeros((len(cells),16)) for name in models}; fits=[]
    if 'independence' in preds:preds['independence']=M.joint_independence(p)
    for k in sorted(set(fold)):
        for y in (0,1):
            tr=(fold!=k)&(label==y)&(cn>0); te=(fold==k)&(label==y)
            if not te.any():continue
            if not tr.any():raise ValueError('empty training fold')
            key=f'{k}:{y}'
            start=None if warm is None else warm.get(key)
            fit=M.fit_factor(p[tr],pairs[tr],start=start,multistart=True)
            if not fit['success']:raise ValueError('factor optimizer failed')
            if 'factor' in preds:
                preds['factor'][te]=M.joint_factor(p[te],fit['loadings'])
                if warm is None:
                    check=M.joint_factor(p[te],fit['loadings'],n_nodes=1024)
                    delta=float(np.max(np.abs(check-preds['factor'][te])))
                    margin_error=float(np.max(np.abs(preds['factor'][te]@BITS-p[te])))
                    if max(delta,margin_error)>1e-6:raise ValueError('factor quadrature accuracy')
                    fit['quad_max_delta']=delta;fit['marginal_max_error']=margin_error
            fits.append({'fold':int(k),'label':int(y),'model':'factor',**{x:float(a) for x,a in zip(READERS,fit['loadings'])},'nll':float(fit['nll']),'success':bool(fit['success']),'quad_max_delta':fit.get('quad_max_delta'),'marginal_max_error':fit.get('marginal_max_error')})
            if 'equal_factor' in preds:
                ff=M.fit_factor(p[tr],pairs[tr],equal=True)
                if not ff['success']:raise ValueError('equal-factor optimizer failed')
                preds['equal_factor'][te]=M.joint_factor(p[te],ff['loadings'])
                fits.append({'fold':int(k),'label':int(y),'model':'equal_factor',**{x:float(a) for x,a in zip(READERS,ff['loadings'])},'nll':float(ff['nll']),'success':bool(ff['success'])})
            if 'beta' in preds:
                fb=M.fit_beta(p[tr],pairs[tr])
                if not fb['success']:raise ValueError('beta optimizer failed')
                preds['beta'][te]=M.joint_beta(p[te],fb['rho'])
                fits.append({'fold':int(k),'label':int(y),'model':'beta','rho':float(fb['rho']),'nll':float(fb['nll']),'success':bool(fb['success'])})
            if 'unrestricted' in preds:
                fu=M.fit_unrestricted(p[tr],pairs[tr])
                if not fu['success']:raise ValueError('unrestricted optimizer failed')
                preds['unrestricted'][te], numeric=M.joint_unrestricted(p[te],fu['correlation'],return_info=True)
                if max(numeric['raw_sum_error'],numeric['marginal_error'])>1e-4:raise ValueError('unrestricted integration accuracy')
                fits.append({'fold':int(k),'label':int(y),'model':'unrestricted','correlation':json.dumps(np.asarray(fu['correlation']).tolist()),'nll':float(fu['nll']),'success':bool(fu['success']),'integration_raw_sum_error':numeric['raw_sum_error'],'integration_marginal_error':numeric['marginal_error']})
    for name,q in preds.items():
        if not np.isfinite(q).all() or (q<0).any() or np.max(np.abs(q.sum(1)-1))>1e-6:raise ValueError('invalid '+name+' probabilities')
    return preds,fits

def metrics(cells,preds):
    end=np.array([c['end'] for c in cells]);n=end.sum(1);tot=n.sum();obs=end[:,15].sum()
    if tot==0:raise ValueError('empty endpoints')
    base=(end*np.log(np.clip(preds['independence'],1e-300,1))).sum()/tot
    out=[]
    for name,q in preds.items():
        expected=n@q[:,15]; ll=(end*np.log(np.clip(q,1e-300,1))).sum()/tot
        out.append({'model':name,'n_items':int(tot),'observed_all_wrong':float(obs),'p_observed':obs/tot,'p_predicted':expected/tot,
                    'ratio':obs/expected,'log_score':ll,'gain':ll-base,'p_correct_observed':end[:,0].sum()/tot,'p_correct_predicted':n@q[:,0]/tot})
    return out

def point(rows,out):
    allmetrics=[];allfits=[];events=[];cellrows=[]
    for convention in sorted(rows.convention.unique()):
      for block in ('A','B'):
        sub=rows[(rows.convention==convention)&rows.eligible & ((rows.block_B) if block=='B' else True)]
        if sub.empty:continue
        facts=prepare(sub);cells=sum([suff(f) for f in facts],[])
        modelnames=('factor','independence','equal_factor','beta','unrestricted') if convention=='allmedian' else ('factor','independence')
        preds,fits=prediction(cells,modelnames)
        for x in metrics(cells,preds):allmetrics.append({'convention':convention,'block':block,'n_facts':len(facts),'n_corpora':len({f['corpus'] for f in facts}),**x})
        for x in fits:allfits.append({'convention':convention,'block':block,**x})
        e=np.array([c['end'] for c in cells]);n=e.sum(1)
        for model,q in preds.items():
          for k in (2,3,4):
            for subset in itertools.combinations(range(4),k):
                ix=BITS[:,list(subset)].all(1); obs=e[:,ix].sum();expected=n@q[:,ix].sum(1)
                events.append({'convention':convention,'block':block,'model':model,'order':k,'readers':'+'.join(READERS[i] for i in subset),
                               'n':int(n.sum()),'observed':int(obs),'p_observed':obs/n.sum(),'p_predicted':expected/n.sum(),'ratio':obs/expected})
          for j,c in enumerate(cells):
            cellrows.append({'convention':convention,'block':block,'dataset':c['dataset'],'corpus':c['corpus'],'fold':c['fold'],'label':c['label'],'model':model,
                             'n_cal':c['cal_n'],'n_endpoint':int(n[j]),'observed_all_wrong':int(e[j,15]),'p_all_wrong':q[j,15],
                             'joint_probabilities':json.dumps(q[j].tolist()),'marginals':json.dumps(c['p'].tolist())})
        print(f'point {convention} {block}: '+json.dumps(allmetrics[-len(preds):]),flush=True)
    pd.DataFrame(allmetrics).to_csv(out/'th2_metrics.csv',index=False)
    pd.DataFrame(allfits).to_csv(out/'th2_fits.csv',index=False)
    pd.DataFrame(events).to_csv(out/'th2_event_orders.csv',index=False)
    pd.DataFrame(cellrows).to_csv(out/'th2_predictions.csv',index=False)

_WORK=None

def init_worker(rowsfile,block,scheme,fitfile):
    global _WORK
    rows=load_rows(rowsfile);sub=rows[(rows.convention=='allmedian')&rows.eligible & ((rows.block_B) if block=='B' else True)]
    facts=prepare(sub)
    if Path(fitfile).exists():
        fits=pd.read_csv(fitfile);f=fits[(fits.convention=='allmedian')&(fits.block==block)&(fits.model=='factor')]
        warm={f'{int(x.fold)}:{int(x.label)}':np.array([getattr(x,r) for r in READERS]) for x in f.itertuples()}
    else:
        cells=sum([suff(f) for f in facts],[])
        _, fits=prediction(cells)
        warm={f"{x['fold']}:{x['label']}":np.array([x[r] for r in READERS]) for x in fits}
    _WORK=(facts,scheme,warm,block)

def bootstrap_one(i):
    facts,scheme,warm,block=_WORK
    rng=np.random.default_rng(np.random.SeedSequence([20261021,i,ord(block),0 if scheme=='corpus_fact_item' else 1]))
    try:
        cells=draw_cells(facts,rng,scheme);preds,fits=prediction(cells,warm=warm)
        m=metrics(cells,preds)[0]
        return {'replicate':i,'block':block,'scheme':scheme,'success':True,**m}
    except Exception as e:
        return {'replicate':i,'block':block,'scheme':scheme,'success':False,'error':str(e)}

def bootstrap(args):
    import multiprocessing as mp
    t=time.perf_counter(); path=args.out/f'th2_bootstrap_{args.block}_{args.scheme}.csv'
    old=pd.read_csv(path) if path.exists() else pd.DataFrame()
    done=set(old.replicate) if len(old) else set();todo=[i for i in range(args.n_boot) if i not in done]
    rows=old.to_dict('records')
    with mp.get_context('spawn').Pool(args.workers,initializer=init_worker,initargs=(args.out/'th2_rows.csv.gz',args.block,args.scheme,args.out/'th2_fits.csv')) as pool:
        for j,r in enumerate(pool.imap_unordered(bootstrap_one,todo,chunksize=2)):
            rows.append(r)
            if (j+1)%25==0:
                pd.DataFrame(rows).sort_values('replicate').to_csv(path,index=False)
                print(json.dumps({'block':args.block,'scheme':args.scheme,'done':len(rows),'elapsed_s':round(time.perf_counter()-t,1),'failed':sum(not x['success'] for x in rows)}),flush=True)
    pd.DataFrame(rows).sort_values('replicate').to_csv(path,index=False)


def intervals(out):
    rows=[]
    for block in ('A','B'):
        qs={}
        for scheme in ('corpus_fact_item','fact_item'):
            x=pd.read_csv(out/f'th2_bootstrap_{block}_{scheme}.csv');g=x[x.success]
            for metric in ('ratio','gain','p_observed','p_predicted'):
                for level in (.9,.95):
                    lo,hi=np.quantile(g[metric],[(1-level)/2,1-(1-level)/2]);rows.append({'block':block,'scheme':scheme,'metric':metric,'level':level,'low':lo,'high':hi,'n_valid':len(g),'n_failed':len(x)-len(g)})
                    qs.setdefault((metric,level),[]).append((lo,hi))
        for (metric,level),values in qs.items():rows.append({'block':block,'scheme':'envelope','metric':metric,'level':level,'low':min(x[0] for x in values),'high':max(x[1] for x in values)})
    pd.DataFrame(rows).to_csv(out/'th2_intervals.csv',index=False)

def main():
    a=argparse.ArgumentParser();a.add_argument('--stage',choices=['point','bootstrap','intervals'],required=True);a.add_argument('--out',type=Path,default=OUT)
    a.add_argument('--block',choices=['A','B'],default='A');a.add_argument('--scheme',choices=['corpus_fact_item','fact_item'],default='corpus_fact_item')
    a.add_argument('--n-boot',type=int,default=2000);a.add_argument('--workers',type=int,default=3);args=a.parse_args()
    if args.stage=='point':point(load_rows(args.out/'th2_rows.csv.gz'),args.out)
    elif args.stage=='bootstrap':bootstrap(args)
    else:intervals(args.out)
if __name__=='__main__':main()
