"""CPU RS-5 analysis. No collection, network, model forward, or source-cache writes."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy.stats import rankdata

ROOT = Path(__file__).resolve().parents[3]
CACHE = ROOT / 'cache/g_agreement/r'
OUT = CACHE / 'remainder/r1'
RESULTS = ROOT / 'results/g_agreement/r/remainder/r1'
SEED = 20261020
READERS = ('jlens', 'olens', 'nla', 'skip_a', 'probe')
R5_DIRS = ('d_cm_L38', 'd_probe_L38', 'd_jlens_L38', 'd_jlens38_L38', 'd_olens_L38', 'd_skip_a_L38') + tuple(f'd_rand{i}_L38' for i in range(10))
DEFECT = {'139_news_class_Politics', '140_news_class_Technology', '141_news_class_Entertainment', '97_news_class', '145_disease_class_digestive system diseases', '146_disease_class_cardiovascular diseases', '101_disease_class'}
METRICS = ('auroc', 'tpr', 'fpr', 'auroc_minus_chance', 'tpr_minus_fpr', 'content_auroc', 'detection_minus_content')


def seed(key):
    return int.from_bytes(hashlib.sha256(f'{SEED}|{key}'.encode()).digest()[:4], 'big')


def provenance():
    return {'pod': 'cpu-mac', 'git_sha': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
            'code_sha': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'seed': SEED}


def rows(path):
    with path.open() as f:
        for line in f:
            if line.strip():
                yield json.loads(line)


def read_unique(path):
    out = {}
    for r in rows(path):
        if r['key'] in out:
            raise ValueError(f'duplicate key: {path}: {r["key"]}')
        out[r['key']] = r
    return list(out.values())


def load_swap_model_rows(*paths):
    """Keep measured LO rows; completion records are a distinct instrument.

    Poetry completion and model-LO files can share keys. Completion text must
    never overwrite a measured model row or count as a model-LO smoke cell.
    """
    out = {}
    for path in paths:
        for row in read_unique(path):
            fields = ('lo_bridge', 'lo_answer') if row['part'] == 'khop' else ('lo_rhyme',)
            if not any(field in row for field in fields) and 'completion' in row:
                continue
            if any(field not in row or not np.isfinite(row[field]) for field in fields):
                raise ValueError(f'SMOKE FAILED: missing/nonfinite model LO in {path}: {row["key"]}')
            if row['key'] in out:
                raise ValueError(f'duplicate model-LO key across sources: {row["key"]}')
            out[row['key']] = row
    return list(out.values())


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''):
            h.update(b)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')


def clean(x):
    if isinstance(x, dict): return {k:clean(v) for k,v in x.items()}
    if isinstance(x, (tuple,list)): return [clean(v) for v in x]
    if isinstance(x, np.ndarray): return clean(x.tolist())
    if isinstance(x, (float,np.floating)): return float(x) if np.isfinite(x) else None
    if isinstance(x, np.integer): return int(x)
    return x


def corpus(ds):
    try: n=int(ds.split('_')[0])
    except ValueError: return ds
    for c,a,b in [('headlines',21,24),('wikidata',56,64),('geo',114,128),('bigram_phrase',65,85),('code',158,163),('glue',87,91),('hist_fig',5,7),('context_type',133,135)]:
        if a <= n <= b: return c
    return ds


def direction_group(d):
    if d.startswith('d_rand'): return 'random'
    return {'d_cm_L38':'class_mean','d_cm':'class_mean','d_probe_L38':'probe','d_jlens_L38':'J_lens','d_jlens38_L38':'J_lens_at_edit_site','d_olens_L38':'Oracle_gradient','d_skip_a_L38':'skip_gradient'}.get(d,d)


def detection_stats(natural, edited, content=None, labels=None):
    """Vectorized rows of bootstrap replicates; high score means edited."""
    natural=np.atleast_2d(natural); edited=np.atleast_2d(edited)
    n=natural.shape[1]
    ranks=rankdata(np.concatenate([natural,edited],axis=1),axis=1,method='average')
    auc=(ranks[:,n:].sum(1)-n*(n+1)/2)/(n*n)
    # At most floor(.05*n) natural scores may strictly exceed the threshold.
    cutoff=np.sort(natural,axis=1)[:,max(0,n-int(np.floor(.05*n))-1)]
    tpr=(edited>cutoff[:,None]).mean(1); fpr=(natural>cutoff[:,None]).mean(1)
    ca=np.full(len(auc),np.nan)
    if content is not None and labels is not None:
        content=np.atleast_2d(content); labels=np.atleast_2d(labels)
        pos=labels.sum(1); neg=n-pos
        rr=rankdata(content,axis=1,method='average')
        np.divide((rr*labels).sum(1)-pos*(pos+1)/2,pos*neg,out=ca,where=(pos*neg)>0)
    return np.column_stack([auc,tpr,fpr,auc-.5,tpr-fpr,ca,auc-ca])


def specificity(natural, reps=100, key=''):
    natural=np.asarray(natural); rng=np.random.default_rng(seed('specificity|'+key)); out=[]
    for _ in range(reps):
        perm=rng.permutation(len(natural)); h=len(perm)//2
        a=natural[perm[:h]]; b=natural[perm[h:]]
        cutoff=np.sort(a)[max(0,len(a)-int(np.floor(.05*len(a)))-1)]
        ranks=rankdata(np.r_[a,b]); nb=len(b)
        auc=(ranks[len(a):].sum()-nb*(nb+1)/2)/(len(a)*nb)
        out.append([auc,float(np.mean(b>cutoff))])
    return np.mean(out,axis=0)


@dataclass
class Cell:
    source: str
    dataset: str
    direction: str
    alpha: float
    layer: int
    pair: str
    reader: str
    detector: str
    ids: list[str]
    natural: np.ndarray
    edited: np.ndarray
    flips: np.ndarray
    content: np.ndarray | None = None
    labels: np.ndarray | None = None
    model_accuracy: float | None = None
    original_accuracy: float | None = None

    def meta(self):
        return {k:getattr(self,k) for k in ('source','dataset','direction','alpha','layer','pair','reader','detector')} | {'direction_type':direction_group(self.direction),'n':len(self.ids),'corpus':corpus(self.dataset)}


def require_coverage(actual, expected):
    missing=sorted(set(expected)-set(actual))
    if missing: raise RuntimeError('SMOKE FAILED: missing '+repr(missing[:15])+f' ({len(missing)} cells)')


def r5_readback_audit(selection, conditions):
    missing = []
    for ds, sel in sorted(selection.items()):
        root = CACHE / 'r5/readback' / ds
        index_path = root / 'index.json'
        wanted = list(sel['item_ids'])
        if index_path.exists():
            index = json.loads(index_path.read_text())
            ids = index['item_ids']
            if len(ids) != len(set(ids)) or set(ids) != set(wanted) or index.get('read_layer') != 42:
                raise RuntimeError(f'SMOKE FAILED: invalid R5 readback index {index_path}')
        else:
            ids = wanted
        for direction, alpha in conditions:
            path = root / f'{direction}_a{alpha}.npy'
            if not path.exists() or not index_path.exists():
                missing.append({'dataset': ds, 'direction': direction, 'alpha': alpha, 'missing_ids': wanted})
                continue
            values = np.load(path, mmap_mode='r')
            if values.ndim != 2 or len(values) != len(ids) or not np.isfinite(values).all():
                raise RuntimeError(f'SMOKE FAILED: malformed R5 readback {path}')
    return missing


def source_audit():
    sr=read_unique(CACHE/'r5/steer.jsonl'); rr=read_unique(CACHE/'r5/readers.jsonl')
    sel=json.loads((ROOT/'results/g_agreement/r/r5_selection.json').read_text())['datasets']
    ds=sorted(set(sel)-DEFECT)
    cond=[('natural',0.)]+[(d,a) for d in R5_DIRS for a in (.5,1.,2.)]
    actual={(r['dataset'],r['direction'],r['alpha']) for r in sr}
    expected={(d,a,b) for d in ds for a,b in cond}
    require_coverage(actual,expected)
    expected_r={(d,a,b,reader) for d,a,b in expected for reader in READERS}
    require_coverage({(r['dataset'],r['direction'],r['alpha'],r['reader']) for r in rr},expected_r)
    counts=Counter((r['dataset'],r['direction'],r['alpha']) for r in sr)
    if any(counts[k]!=len(sel[k[0]]['item_ids']) for k in expected): raise RuntimeError('SMOKE FAILED: R5 incomplete item coverage')
    swaps=load_swap_model_rows(CACHE/'swap/swap.jsonl', CACHE/'swap/swap_poetry.jsonl')
    swr=read_unique(CACHE/'swap/swap_readers.jsonl')
    cov={(r['part'],r['layer'],r['arm']) for r in swaps}
    expected_s={(p,L,a) for p in ('khop','poetry') for L in (24,28,32,36,40,44) for a in (('d_swap','d_answer','d_cm','d_logit','d_rand0','d_rand1','d_rand2') if p=='khop' else ('d_swap','d_logit','d_rand0','d_rand1','d_rand2'))}
    expected_s|={(p,None,'natural') for p in ('khop','poetry')}
    require_coverage(cov,expected_s)
    missing_states=[]; n_states=0
    for p,L,a in sorted(expected_s,key=str):
        tag='natural' if a=='natural' else f'L{L}_{a}'
        f=CACHE/f'swap/readback/{p}/{tag}.npy'; j=f.with_suffix('.json')
        expected_ids={r['item'] for r in swaps if (r['part'],r['layer'],r['arm'])==(p,L,a)}
        if not f.exists() or not j.exists():
            missing_states.append({'part':p,'layer':L,'arm':a,'missing_ids':sorted(expected_ids),'reason':'missing file'}); continue
        ids=json.loads(j.read_text()); x=np.load(f,mmap_mode='r')
        if len(ids)!=len(set(ids)) or x.shape[0]!=len(ids): raise RuntimeError(f'SMOKE FAILED: malformed state index {f}')
        orphan=set(ids)-expected_ids
        if orphan: raise RuntimeError(f'SMOKE FAILED: orphan SWAP states {orphan}')
        n_states+=len(ids)
        if expected_ids-set(ids): missing_states.append({'part':p,'layer':L,'arm':a,'missing_ids':sorted(expected_ids-set(ids)),'reason':'known lost readbacks'})
    r5_missing = r5_readback_audit({d: sel[d] for d in ds}, cond)
    # Reader output exists for khop only; poetry native-reader cells are explicitly blocked.
    actual_s={(r['part'],r['layer'],r['arm'],r['reader'],r['pair']) for r in swr}
    expected_sr={(p,L,a,reader,pair) for p,L,a in expected_s if p=='khop' for reader in READERS[:-1] for pair in (('bridge',) if reader=='nla' else ('bridge','answer'))}
    require_coverage(actual_s,expected_sr)
    report={'r5_facts':len(ds),'r5_model_rows':len(sr),'r5_reader_rows':len(rr),'r5_source_cells':len(expected),'r5_reader_cells':len(expected_r),
        'r5_readback_present':(CACHE/'r5/readback').exists(),'r5_missing_state_rows':sum(len(r['missing_ids']) for r in r5_missing),'r5_missing_states':r5_missing,
        'swap_model_rows':len(swaps),'swap_reader_rows':len(swr),'swap_readback_states':n_states,'swap_missing_states':missing_states,
        'swap_poetry_reader_rows':sum(r['part']=='poetry' for r in swr),'source_row_smoke':'PASS',
        'strict_full_design_smoke':'FAIL: missing R5 readbacks, 22 lost khop readbacks, all poetry readbacks and reader rows',
        'source_provenance':'R5 source rows lack pod/git/code stamps. SWAP provenance is documented in swap/PROVENANCE.json, including unrecoverable original phase-A code hash; analysis stamps do not repair this.'}
    report['strict_full_design_smoke'] = ('FAIL: missing original readbacks or poetry reader cells'
        if r5_missing or missing_states or not report['swap_poetry_reader_rows'] else 'PASS')
    return sr,rr,swaps,swr,report


def confidence_cells(sr,rr,swaps,swr):
    out=[]; model={(r['dataset'],r['item_id'],r['direction'],r['alpha']):r for r in sr if r['dataset'] not in DEFECT}
    groups=defaultdict(list); natural={}
    for r in rr:
        if r['dataset'] in DEFECT or r.get('unscorable') or not np.isfinite(r['lo']): continue
        if r['direction']=='natural': natural[r['dataset'],r['reader'],r['item_id']]=r
        else: groups[r['dataset'],r['reader'],r['direction'],r['alpha']].append(r)
    for (ds,reader,d,a),rs in sorted(groups.items()):
        rs=sorted(rs,key=lambda r:r['item_id']); ids=[r['item_id'] for r in rs]
        nr=[natural[ds,reader,i] for i in ids]
        n=np.array([r['lo'] for r in nr]); e=np.array([r['lo'] for r in rs]); y=np.array([r['label'] for r in rs])
        flips=np.array([(model[ds,i,d,a]['lo']>0)!=(model[ds,i,'natural',0.]['lo']>0) for i in ids])
        for det,nn,ee in [('abs_lo_high',abs(n),abs(e)),('abs_lo_low',-abs(n),-abs(e)),('paired_lo_shift',abs(n-np.roll(n,1)),abs(e-n))]:
            out.append(Cell('r5',ds,d,a,38,'label',reader,det,ids,nn,ee,flips,e,y))
    model={(r['part'],r['item'],r['layer'],r['arm']):r for r in swaps}; groups=defaultdict(list); natural={}
    for r in swr:
        if r.get('unscorable') or not np.isfinite(r['lo']): continue
        if r['arm']=='natural': natural[r['part'],r['reader'],r['pair'],r['item']]=r
        else: groups[r['part'],r['reader'],r['pair'],r['layer'],r['arm']].append(r)
    for (part,reader,pair,L,d),rs in sorted(groups.items()):
        rs=sorted(rs,key=lambda r:r['item']);ids=[r['item'] for r in rs]
        n=np.array([natural[part,reader,pair,i]['lo'] for i in ids]);e=np.array([r['lo'] for r in rs])
        mr=[model[part,i,L,d] for i in ids]; mn=[model[part,i,None,'natural'] for i in ids]
        flips=np.array([(r[f'lo_{pair}']>0)!=(n0[f'lo_{pair}']>0) for r,n0 in zip(mr,mn)])
        ma=float(np.mean((e>0)==np.array([r[f'lo_{pair}']>0 for r in mr])))
        for det,nn,ee in [('abs_lo_high',abs(n),abs(e)),('abs_lo_low',-abs(n),-abs(e)),('paired_lo_shift',abs(n-np.roll(n,1)),abs(e-n))]:
            ds='re_khop2_bridge' if part=='khop' else 'x27_wsb_poetry'
            out.append(Cell('swap',ds,d,1.,L,pair,reader,det,ids,nn,ee,flips,model_accuracy=ma,original_accuracy=float(np.mean(e>0))))
    return out


class PoolGeometry:
    """Exact fixed-ridge Mahalanobis, memory O(n_pool*d + n_pool**2)."""
    def __init__(self,X,k=5):
        self.X=np.asarray(X,dtype=np.float64); self.mu=self.X.mean(0); self.Z=self.X-self.mu
        self.k=min(k,len(X)); self.lam=max(float(np.mean(self.Z.var(0,ddof=1)))*.1,1e-8)
        n=len(X); self.inv=np.linalg.inv(self.Z@self.Z.T+(n-1)*self.lam*np.eye(n))
        self.norm=(self.X*self.X).sum(1)

    def score(self,H,Q=None):
        H=np.asarray(H,dtype=np.float64);z=H-self.mu;cross=z@self.Z.T
        md=np.sqrt(np.maximum(((z*z).sum(1)-((cross@self.inv)*cross).sum(1))/self.lam,0))
        d2=np.maximum((H*H).sum(1)[:,None]+self.norm[None,:]-2*H@self.X.T,0)
        knn=np.sqrt(np.partition(d2,self.k-1,axis=1)[:,:self.k]).mean(1)
        norm=np.linalg.norm(H,axis=1)
        out={'mahalanobis':md,'knn':knn,'norm':norm}
        if Q is not None: out['j_energy']=((H@Q)**2).sum(1)/np.maximum(norm**2,1e-12)
        return out


def j_basis():
    f=OUT/'j42_rank384.npy'
    if f.exists(): return np.load(f)
    import torch
    from sklearn.utils.extmath import randomized_svd
    path=ROOT/'cache/g_agreement/s3/jlens/Qwen3.6-27B_jacobian_lens_n1000.pt'
    if not path.exists(): return None
    obj=torch.load(path,map_location='cpu',weights_only=False,mmap=True)
    jac=obj.get('J',obj.get('jacobians'))
    J=(jac[42] if not isinstance(jac,dict) or 42 in jac else jac['42']).float().numpy()
    _,s,Vt=randomized_svd(J,n_components=384,n_iter=4,random_state=SEED)
    Q=Vt.T.copy();np.save(f,Q)
    write_json(OUT/'j_basis.json',{'method':'randomized_svd input right-singular vectors','rank':384,'n_iter':4,'seed':SEED,
        'layer':42,'source':str(path),'captured_frobenius_fraction':float(np.sum(s*s)/np.sum(J*J)),**provenance()})
    return Q


def r5_state_cells(sr, Q):
    out = []
    by = defaultdict(list)
    for row in sr:
        if row['dataset'] not in DEFECT:
            by[row['dataset']].append(row)
    for ds, model_rows in sorted(by.items()):
        root = CACHE / 'r5/readback' / ds
        if not (root/'index.json').exists() or not (root/'natural_a0.0.npy').exists():
            continue
        index = json.loads((root/'index.json').read_text())
        ids = index['item_ids']
        source = CACHE/'states'/ds
        pool_index = json.loads((source/'index.json').read_text())
        H = np.load(source/'chat_L42.npy', mmap_mode='r')
        pool = H[np.asarray(pool_index['splits']) == 'pool']
        geometry = PoolGeometry(pool)
        natural = geometry.score(np.load(root/'natural_a0.0.npy'), Q)
        model = {(r['item_id'], r['direction'], r['alpha']): r for r in model_rows}
        for path in sorted(root.glob('*.npy')):
            direction, alpha = path.stem.rsplit('_a', 1)
            alpha = float(alpha)
            if direction == 'natural': continue
            edited = geometry.score(np.load(path), Q)
            flips = np.array([(model[i, direction, alpha]['lo'] > 0) !=
                              (model[i, 'natural', 0.]['lo'] > 0) for i in ids])
            for detector in edited:
                out.append(Cell('r5', ds, direction, alpha, 38, 'label', 'state', detector,
                                ids, natural[detector], edited[detector], flips))
    return out


def state_cells(swaps,Q):
    out=[];model={(r['part'],r['item'],r['layer'],r['arm']):r for r in swaps}
    for part,ds in [('khop','re_khop2_bridge'),('poetry','x27_wsb_poetry')]:
        root=CACHE/'states'/ds;idx=json.loads((root/'index.json').read_text());H=np.load(root/'chat_L42.npy',mmap_mode='r')
        pool=H[np.array(idx['splits'])=='pool'].astype(np.float64);geom=PoolGeometry(pool)
        rd=CACHE/'swap/readback'/part
        if not (rd/'natural.json').exists() or not (rd/'natural.npy').exists():
            continue  # Explicit blocked cells are listed in source_audit; no imputation.
        ni=json.loads((rd/'natural.json').read_text()); N=np.load(rd/'natural.npy');nm={i:j for j,i in enumerate(ni)}
        ns=geom.score(N,Q)
        for f in sorted(rd.glob('L*.npy')):
            L,d=f.stem.split('_',1); L=int(L[1:]);ids=json.loads(f.with_suffix('.json').read_text());E=np.load(f)
            es=geom.score(E,Q);sel=np.array([nm[i] for i in ids]);pair='answer' if d=='d_answer' else ('bridge' if part=='khop' else 'rhyme')
            flips=np.array([(model[part,i,L,d][f'lo_{pair}']>0)!=(model[part,i,None,'natural'][f'lo_{pair}']>0) for i in ids])
            for det in es:
                out.append(Cell('swap',ds,d,1.,L,pair,'state',det,ids,ns[det][sel],es[det],flips))
    return out


def estimate(cells,B):
    rng=np.random.default_rng(SEED); results=[]; boot=[]; specificity_cache={}; t=time.time()
    with (OUT/'paired_scores.jsonl').open('w') as sink:
        prov=provenance()
        for k,c in enumerate(cells):
            n=len(c.ids); rs=np.random.default_rng(seed(c.dataset+'|'+str(n)))
            idx=rs.integers(0,n,(B,n))
            val=detection_stats(c.natural,c.edited,c.content,c.labels)[0]
            bb=detection_stats(c.natural[idx],c.edited[idx],None if c.content is None else c.content[idx],None if c.labels is None else c.labels[idx])
            skey=(c.dataset,c.reader,c.detector,tuple(c.ids),tuple(c.natural))
            if skey not in specificity_cache: specificity_cache[skey]=specificity(c.natural,key=c.dataset+c.reader+c.detector)
            spec=specificity_cache[skey]
            r=c.meta()|{'flip_rate':float(c.flips.mean()),'specificity_null_auroc':float(spec[0]),'specificity_null_fpr':float(spec[1]),'model_answer_agreement':c.model_accuracy,'original_label_accuracy':c.original_accuracy,**prov}
            for j,m in enumerate(METRICS):
                r[m]=val[j];r[m+'_ci']=np.nanquantile(bb[:,j],[.025,.975]).tolist() if np.isfinite(bb[:,j]).any() else [None,None]
            r['useful_at_this_dose']=bool(val[1]>=.5 and r['tpr_ci'][0]>.3) if c.flips.mean()>=.5 else None
            results.append(r);boot.append(bb.astype(np.float32))
            sink.write(json.dumps(clean(c.meta()|{'item_ids':c.ids,'natural_scores':c.natural,'edited_scores':c.edited,'model_flips':c.flips.astype(int),'content':c.content,'labels':c.labels,**prov}),allow_nan=False)+'\n')
            if (k+1)%1000==0: print(f'cells {k+1}/{len(cells)} elapsed={time.time()-t:.0f}s',flush=True)
    return results,boot


def aggregate(results,boots,B):
    groups=defaultdict(list)
    for i,r in enumerate(results):
        key=tuple(r[k] for k in ('source','direction_type','alpha','layer','pair','reader','detector'))
        groups[key].append(i)
    summaries=[]
    for key,inds in groups.items():
        by_fact=defaultdict(list)
        for i in inds: by_fact[results[i]['dataset']].append(i)
        facts=sorted(by_fact); points=[]; draws=[]
        for f in facts:
            ii=by_fact[f];points.append(np.array([[results[i][m] for m in METRICS] for i in ii]).mean(0));draws.append(np.array([boots[i] for i in ii]).mean(0))
        points=np.array(points);draws=np.array(draws); point=points.mean(0);item=draws.mean(0)
        rng=np.random.default_rng(seed('|'.join(map(str,key))));cs=defaultdict(list)
        for j,f in enumerate(facts): cs[corpus(f)].append(j)
        cn=sorted(cs);cluster=[]
        for b in range(B):
            ids=[]
            for ci in rng.integers(0,len(cn),len(cn)):
                fs=cs[cn[ci]];ids.extend(rng.choice(fs,len(fs),replace=True))
            cluster.append(draws[ids,b,:].mean(0))
        cluster=np.array(cluster)
        rr=dict(zip(('source','direction_type','alpha','layer','pair','reader','detector'),key))|{'n_facts':len(facts),'n_corpora':len(cn),'n_items':sum(results[by_fact[f][0]]['n'] for f in facts),'random_directions_per_fact':len(inds)/len(facts),'flip_rate':float(np.mean([results[i]['flip_rate'] for i in inds])),**provenance()}
        for j,m in enumerate(METRICS):
            ic=np.nanquantile(item[:,j],[.025,.975]) if np.isfinite(item[:,j]).any() else np.array([np.nan,np.nan]);cc=np.nanquantile(cluster[:,j],[.025,.975]) if np.isfinite(cluster[:,j]).any() else np.array([np.nan,np.nan])
            rr[m]=point[j];rr[m+'_item_ci']=ic;rr[m+'_corpus_ci']=cc;rr[m+'_ci']=[min(ic[0],cc[0]),max(ic[1],cc[1])]
        rr['specificity_null_auroc']=np.mean([results[i]['specificity_null_auroc'] for i in inds]);rr['specificity_null_fpr']=np.mean([results[i]['specificity_null_fpr'] for i in inds])
        rr['inference_limit']='single-source-corpus; no between-corpus inference' if len(cn)==1 else 'corpus → fact → paired item bootstrap'
        summaries.append(rr)
    return summaries


def write_report(audit,results,summary,B):
    fmt=lambda x:f'{x:.3f}' if x is not None and np.isfinite(x) else 'undefined'
    ci=lambda r,m:f'{fmt(r[m])} [{fmt(r[m+"_ci"][0])}, {fmt(r[m+"_ci"][1])}]'
    primary=[r for r in summary if r['source']=='r5' and r['direction_type'] in ('class_mean','probe','J_lens','Oracle_gradient','random') and r['reader']!='probe']
    qualifying=[r for r in results if r['flip_rate']>=.5]
    r5qual=[r for r in qualifying if r['source']=='r5']
    lines=['# R1 — RS-5 detectability','',f'CPU analysis completed 2026-10-20. {B:,} paired-item and corpus → fact → item bootstrap draws; every interval below is the envelope of both 95% intervals. No pod or judge spend.','',
        f'**R5 useful-detector verdict: {"UNDEFINED" if not r5qual else "see qualifying_doses.json"}.** {len(r5qual)} detector cells have an observed dose that flips the model on at least 50% of items. R5 is missing {audit["r5_missing_state_rows"]:,} readbacks on this Mac; Mahalanobis, kNN, norm and J-space energy require their original state files. Reader-confidence analysis covers all {audit["r5_reader_rows"]:,} existing rows from {audit["r5_facts"]} facts.','',
        '**Completeness.** The source-row arm smoke passed. The strict full-design audit is recorded in audit.json; R5 has '+str(audit['r5_missing_state_rows'])+' missing readbacks; SWAP is missing '+str(sum(len(r['missing_ids']) for r in audit['swap_missing_states']))+' readback rows (22 khop L24 and all 1,488 poetry readbacks); poetry reader scores are absent. This is a completed analysis of available data, not a complete RS-5 experiment. Original state files must be pulled from the volume to finish R5 geometry; this analysis never regenerates them.','',
        '**Interpretation.** High-|LO| and low-|LO| are separate fixed detectors. LO shift uses the same item’s unedited reference and a distinct-natural-item difference null; it is not deployable without that reference. Content AUROC in R5 remains the original dataset label and is descriptive after edits. SWAP original-label accuracy is not content truth after an edit; model-answer agreement is reported separately. Do not interpret detection as faithful content reading.','',
        '## R5 confidence detection, by direction and dose','', 'Each cell is the equally weighted mean over facts (random directions also averaged within fact). AUROC is versus natural controls; ΔAUROC is relative to chance 0.5. The full table, including confidence orientation, probe pseudo-reader, skip gradient and J-lens edit-site direction, is in `summary.json`.','',
        '| direction | dose | reader | low-confidence AUROC [95% CI] | ΔAUROC [95% CI] | TPR@5% FPR [95% CI] | content AUROC [95% CI] | detection − content [95% CI] |','|---|---:|---|---|---|---|---|---|']
    for r in primary:
        if r['detector']=='abs_lo_low':lines.append(f'| {r["direction_type"]} | {r["alpha"]} | {r["reader"]} | {ci(r,"auroc")} | {ci(r,"auroc_minus_chance")} | {ci(r,"tpr")} | {ci(r,"content_auroc")} | {ci(r,"detection_minus_content")} |')
    lines+=['','## SWAP layer 24: state detectors and native confidence','','SWAP has one corpus per reported part; item intervals cannot establish corpus generality. The geometry readback is L42; layer below is the edit site. Pool geometry never fits the test readbacks. Top-384 J energy uses a fixed approximate SVD of J42. Comparators at all layers and all arms are in `summary.json`.','',
        '| part / pair | arm | detector | AUROC [95% CI] | ΔAUROC [95% CI] | TPR@5% FPR [95% CI] | ΔTPR vs natural FPR [95% CI] |','|---|---|---|---|---|---|---|']
    for r in summary:
        if r['source']=='swap' and r['layer']==24 and (r['direction_type'] in ('d_swap','class_mean','random')) and (r['reader']=='state' or r['detector']=='abs_lo_low' and r['pair']=='bridge'):
            lines.append(f'| {r["pair"]} | {r["direction_type"]} | {r["reader"]}:{r["detector"]} | {ci(r,"auroc")} | {ci(r,"auroc_minus_chance")} | {ci(r,"tpr")} | {ci(r,"tpr_minus_fpr")} |')
    lines+=['','## Specificity and limits','','Natural-vs-natural checks use 100 fixed random half-splits. Their mean null AUROC and held-out false-positive rate are saved for every detector/condition in `summary.json`; these resample the same finite natural bank and are not an independent validation set. With 32 natural R5 states, a 5% ROC operating point allows one false positive; a half-split has only 16 calibration items, so its threshold is the maximum and its expected held-out FPR can exceed 5%. TPR confidence intervals include re-estimation of the threshold.','',
        'No direction or dose was selected using detectability. Useful-at-dose flags are conditional on the model-flip criterion and on the observed candidate doses; thresholds are preregistered but the original R5/SWAP aggregates were public before this analysis. Per-fact values and all useful-at-lowest-dose flags are in the cache. Source row provenance is incomplete: analysis pod/git/code stamps and source hashes are present, but the original missing stamps are not invented.','',
        'The confidence-vs-content comparison does not make a useful-detector claim when no dose reaches the model-flip gate. A high score for one confidence orientation is not selected over the other. The random and class-mean controls are essential: a generic response to any activation edit is not specific to report-flipping edits.','',
        '## Reproduction','', '`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.remainder_r1 --smoke`','',
        '`OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m projects.g_agreement.r_bench.remainder_r1 --run --bootstrap 1000`','',
        'Plan: `PLAN.md`; audit: `audit.json`; full small aggregate table: `summary.json`; per-cell metrics and paired score vectors: `cache/g_agreement/r/remainder/r1/`. A strict completeness check is `--smoke --strict` and intentionally exits nonzero until the missing original artifacts are available.','']
    (RESULTS/'REPORT.md').write_text('\n'.join(lines))


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--smoke',action='store_true');ap.add_argument('--strict',action='store_true');ap.add_argument('--run',action='store_true');ap.add_argument('--bootstrap',type=int,default=1000);a=ap.parse_args(argv)
    if not (a.smoke or a.run): ap.error('choose --smoke or --run')
    OUT.mkdir(parents=True,exist_ok=True);RESULTS.mkdir(parents=True,exist_ok=True)
    start=time.time();sr,rr,swaps,swr,audit=source_audit();audit.update(provenance())
    write_json(RESULTS/'audit.json',audit);print('SMOKE PASSED: all source-row arms × conditions covered; strict state audit '+audit['strict_full_design_smoke']+' (see audit.json)',flush=True)
    if a.strict and audit['strict_full_design_smoke'] != 'PASS':
        raise RuntimeError('SMOKE FAILED: full-design artifacts missing; see audit.json')
    if not a.run:return 0
    files=[CACHE/p for p in ['r5/steer.jsonl','r5/readers.jsonl','swap/swap.jsonl','swap/swap_poetry.jsonl','swap/swap_readers.jsonl']]
    manifest={str(p.relative_to(ROOT)):sha(p) for p in files}
    for readback_root in (CACHE/'swap/readback', CACHE/'r5/readback'):
        for p in readback_root.rglob('*'):
            if p.is_file():manifest[str(p.relative_to(ROOT))]=sha(p)
    for ds in ('re_khop2_bridge','x27_wsb_poetry'):
        for name in ('index.json','chat_L42.npy'):
            p=CACHE/'states'/ds/name
            if p.exists(): manifest[str(p.relative_to(ROOT))]=sha(p)
    for p in [ROOT/'results/g_agreement/r/r5_selection.json',ROOT/'cache/g_agreement/s3/jlens/Qwen3.6-27B_jacobian_lens_n1000.pt']:
        if p.exists():manifest[str(p.relative_to(ROOT))]=sha(p)
    write_json(OUT/'input_hashes.json',manifest)
    print('Building confidence cells',flush=True);cells=confidence_cells(sr,rr,swaps,swr)
    print('Building J42 basis and pool geometry',flush=True);Q=j_basis();cells+=r5_state_cells(sr,Q)+state_cells(swaps,Q)
    print(f'Analyzing {len(cells)} detector cells',flush=True);results,boots=estimate(cells,a.bootstrap)
    print('Corpus bootstrap aggregation',flush=True);summary=aggregate(results,boots,a.bootstrap)
    with (OUT/'cell_metrics.jsonl').open('w') as f:
        for r in results:f.write(json.dumps(clean(r),allow_nan=False)+'\n')
    # The lowest qualifying dose is selected separately per fact/direction/reader/detector, never from detection.
    grouped=defaultdict(list)
    for r in results:
        if r['flip_rate']>=.5:grouped[tuple(r[k] for k in ('source','dataset','direction','layer','pair','reader','detector'))].append(r)
    qualifying=[min(rs,key=lambda r:r['alpha']) for rs in grouped.values()]
    write_json(OUT/'qualifying_doses.json',clean(qualifying));write_json(RESULTS/'summary.json',clean(summary));write_report(audit,results,summary,a.bootstrap)
    write_json(RESULTS/'run.json',{'status':'AVAILABLE_DATA_COMPLETE_FULL_DESIGN_INCOMPLETE','wall_seconds':time.time()-start,'pod_hours':0,'judge_cost':0,'bootstrap':a.bootstrap,'cells':len(cells),'summaries':len(summary),'qualifying_r5_detector_cells':sum(r['source']=='r5' for r in qualifying),'qualifying_swap_detector_cells':sum(r['source']=='swap' for r in qualifying),**provenance()})
    changed=[p for p,h in manifest.items() if sha(ROOT/p) != h]
    if changed: raise RuntimeError('Source files changed during analysis: '+repr(changed))
    print(f'Completed available-data analysis in {time.time()-start:.1f}s; R5 qualifying detector cells={sum(r["source"]=="r5" for r in qualifying)}',flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
