"""X1 paired tables, downstream Mahalanobis gate and the registered SWAP-U ratio."""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path
import numpy as np
from sklearn.metrics import roc_auc_score
from projects.g_agreement.r_bench import remainder_x1 as D
from projects.g_agreement.r_bench import remainder_x1_collect as C

BOOT=2000


def ci(x,q=(.025,.975)):
    x=np.asarray(x);valid=x[np.isfinite(x)]
    return np.quantile(valid,q).tolist() if len(valid)>=.95*len(x) and len(valid) else None


def envelope(intervals):
    return [min(x[0] for x in intervals),max(x[1] for x in intervals)] if intervals and all(x is not None for x in intervals) else None


def draws(rows,scheme,n=BOOT,groups=None):
    """Pairs stay intact; entity clustering preserves all recipients sharing the entity."""
    rng=np.random.default_rng(0);N=len(rows)
    if not N:return
    if scheme=='item':
        if groups is None:
            for _ in range(n):yield rng.integers(N,size=N)
        else:
            strata=[np.where(np.asarray(groups)==v)[0] for v in sorted(set(groups))]
            for _ in range(n):yield np.concatenate([rng.choice(ids,len(ids),replace=True) for ids in strata])
    else:
        by=defaultdict(list)
        for i,r in enumerate(rows):by[r['bridge' if scheme=='bridge' else 'donor_bridge']].append(i)
        keys=sorted(by)
        for _ in range(n):yield np.concatenate([by[keys[j]] for j in rng.integers(len(keys),size=len(keys))])


def paired_effect(rows,values,n=BOOT):
    values=np.asarray(values,dtype=float)
    if len(rows)!=len(values):raise ValueError('Effect rows misaligned')
    if not rows:return {'n':0,'estimate':None,'wider_ci':None}
    intervals={s:ci([values[i].mean() for i in draws(rows,s,n)]) for s in ('item','bridge','donor')}
    return {'n':len(rows),'estimate':float(values.mean()),**{s+'_ci':v for s,v in intervals.items()},'wider_ci':envelope(list(intervals.values()))}


def wilson(success,total):
    if total==0:return None
    z=1.959963984540054;p=success/total;den=1+z*z/total
    centre=(p+z*z/(2*total))/den;half=z*np.sqrt(p*(1-p)/total+z*z/(4*total**2))/den
    return [float(centre-half),float(centre+half)]


def dissociated(fa,fc,bc,ba):
    cis=[x.get('wider_ci') for x in (fa,fc,bc,ba)]
    if any(c is None for c in cis):return 'UNDEFINED'
    return 'DISSOCIATED' if cis[0][0]>.2 and cis[1][0]>.2 and cis[2][1]<.1 and cis[3][0]>.2 else 'NOT_DISSOCIATED'


def ratio(rows,net,flipped,n=BOOT,margin_matched=False):
    net=np.asarray(net);flipped=np.asarray(flipped,dtype=bool)
    if not rows or not flipped.any() or flipped.all():return {'status':'UNDEFINED','verdict':'MIXED','reason':'empty F or N'}
    margins=np.asarray([r['natural_lo'] for r in rows]);cuts=np.quantile(margins,[1/3,2/3]);terciles=np.searchsorted(cuts,margins,side='right')
    usable=[t for t in (0,1,2) if np.any((terciles==t)&flipped) and np.any((terciles==t)&~flipped)]
    retained=np.isin(terciles,usable) if margin_matched else np.ones(len(rows),dtype=bool)
    def stats(idx):
        i=np.asarray(idx);i=i[retained[i]];f=flipped[i];x=net[i]
        if not len(i) or not f.any() or f.all():return np.array([np.nan]*3)
        N=x[~f].mean();F=x[f].mean()
        if margin_matched:
            parts=[];weights=[]
            for t in usable:
                ft=(terciles[i]==t)&f;nt=(terciles[i]==t)&~f
                if not ft.any() or not nt.any():continue
                parts.append(x[ft].mean());weights.append(nt.sum())
            if not weights:return np.array([np.nan]*3)
            F=np.average(parts,weights=weights)
        return np.array([N,F,N/F if F>0 else np.nan])
    point=stats(np.arange(len(rows)));samples={};intervals={};pvals={}
    for scheme in ('item','bridge','donor'):
        # §26: item resampling within F/N (and margin tercile for sensitivity).
        groups=[str(int(f))+'_'+str(t) if margin_matched else str(int(f)) for f,t in zip(flipped,terciles)]
        arr=np.array([stats(i) for i in draws(rows,scheme,n,groups)]);samples[scheme]=arr
        intervals[scheme]={'N':ci(arr[:,0]),'F':ci(arr[:,1]),'rho':ci(arr[:,2],(.05,.95))}
        undefined=~np.isfinite(arr[:,2])
        pN=float(np.mean(~np.isfinite(arr[:,0])|(arr[:,0]<=0)));pF=float(np.mean(~np.isfinite(arr[:,1])|(arr[:,1]<=0)))
        pvals[scheme]={'written':max(pN,float(np.mean(undefined|(arr[:,2]<.5)))),
                       'use':max(pF,float(np.mean(undefined|(arr[:,2]>=.5)))), 'undefined_fraction':float(undefined.mean())}
    wide={k:envelope([v[k] for v in intervals.values()]) for k in ('N','F','rho')}
    # Conservative extension of §26: maximum p across all declared clustering schemes.
    ps={claim:max(v[claim] for v in pvals.values()) for claim in ('written','use')}
    return {'status':'OK' if wide['rho'] is not None else 'UNDEFINED','F_n':int(flipped.sum()),'N_n':int((~flipped).sum()),
            'N':None if not np.isfinite(point[0]) else float(point[0]),'F':None if not np.isfinite(point[1]) else float(point[1]),
            'rho':None if not np.isfinite(point[2]) else float(point[2]),'wider_ci':wide,'intervals':intervals,'p':ps,'schemes':pvals,
            'margin_matched':margin_matched,'tercile_cutpoints':cuts.tolist(),'retained_terciles':usable if margin_matched else [0,1,2],
            'retained_n':int(retained.sum()),'tercile_N_weights':{str(t):float(np.sum((terciles==t)&~flipped&retained)/max(1,np.sum(~flipped&retained))) for t in usable}}


def bh(p):
    a=np.asarray(p);order=np.argsort(a);q=np.ones(len(a));running=1.
    for j in range(len(a)-1,-1,-1):
        running=min(running,float(a[order[j]])*len(a)/(j+1));q[order[j]]=running
    return q.tolist()


def ratio_verdict(r,qwritten=1.,quse=1.):
    if r.get('status')!='OK':return 'MIXED'
    N,F,rho=(r['wider_ci'][k] for k in ('N','F','rho'))
    if any(v is None for v in (N,F,rho)):return 'MIXED'
    if N[0]>0 and rho[0]>=.5 and qwritten<=.1:return 'READS WRITTEN'
    if F[0]>0 and rho[1]<.5 and quse<=.1:return 'TRACKS USE'
    return 'MIXED'


def gate(rows,natural,patched,n=BOOT):
    natural=np.asarray(natural);patched=np.asarray(patched)
    def auc(idx):
        return float(roc_auc_score(np.r_[np.zeros(len(idx)),np.ones(len(idx))],np.r_[natural[idx],patched[idx]]))
    point=auc(np.arange(len(rows)));intervals={s:ci([auc(i) for i in draws(rows,s,n)]) for s in ('item','bridge','donor')}
    wide=envelope(list(intervals.values()))
    return {'n':len(rows),'auroc':point,'auroc_minus_chance':point-.5,'orientation_free_auroc':max(point,1-point),
            **{s+'_ci':v for s,v in intervals.items()},'wider_ci':wide,'auroc_minus_chance_wider_ci':[v-.5 for v in wide] if wide else None,
            'point_gate':point<=.6,'low_detectability_ci_supported':wide is not None and wide[1]<=.6}


def analyze(plan,root,primary_layer,out,n=BOOT):
    root=Path(root);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    C.verify_measurement(root/'test')
    rows=D.read(root/'test/model_rows.json');readers=C.load_rows(root/'test/reader_rows.jsonl')
    C.assert_reader_completion(rows,readers);C.assert_model_coverage(rows)
    model={(r['recipient'],r['layer'],r['arm']):r for r in rows if r['status']=='OK'}
    if len(model)!=sum(r['status']=='OK' for r in rows):raise ValueError('Duplicate model rows')
    flips=[];read_tables=[];rho_rows=[];decisions=[];gates=[];examples=[]
    state_cache={}
    def state(r,L):
        file=r['state_file']
        if file not in state_cache:
            with np.load(root/'test'/file,allow_pickle=False) as data:state_cache[file]={k:data[k] for k in data.files}
        return state_cache[file][f"{r['recipient']}_L{L}"]
    natural_states=C.load_states(root/'natural',plan)
    for L in D.LAYERS:
        ids=sorted({r['recipient'] for r in rows if r['layer']==L and r['arm']=='natural' and r['status']=='OK'})
        core=[i for i in ids if all((i,L,a) in model for a in D.ARMS if a!='class_mean')]
        if len(core)!=len(ids):raise ValueError('Incomplete natural arm cohort')
        correct=[i for i in core if model[i,L,'natural']['lo']>0]
        base=[{**model[i,L,'natural'],'natural_lo':model[i,L,'natural']['lo']} for i in correct]
        flip_effect={}
        for arm in D.ARMS:
            eligible=[r for r in base if (r['recipient'],L,arm) in model]
            for control in (['random_bridge','random_answer'] if arm=='answer_patch' else ['random_bridge']):
                a=np.array([model[r['recipient'],L,arm]['lo']<0 for r in eligible],float)
                b=np.array([model[r['recipient'],L,control]['lo']<0 for r in eligible],float)
                effect=paired_effect(eligible,a-b,n);flip_effect[arm,control]=effect
                flips.append({'layer':L,'arm':arm,'control':control,'natural_correct_only':True,'successes':int(a.sum()),'rate':float(a.mean()) if len(a) else None,
                              'wilson_ci':wilson(int(a.sum()),len(a)),**effect})
        for arm in D.ARMS:
            eligible=[model[i,L,'natural'] for i in core if (i,L,arm) in model]
            a=np.array([r['lo']>0 and model[r['recipient'],L,arm]['lo']<0 for r in eligible],float)
            b=np.array([r['lo']>0 and model[r['recipient'],L,'random_bridge']['lo']<0 for r in eligible],float)
            flips.append({'layer':L,'arm':arm,'control':'random_bridge','natural_correct_only':False,'successes':int(a.sum()),
                          'rate':float(a.mean()) if len(a) else None,'wilson_ci':wilson(int(a.sum()),len(a)),**paired_effect(eligible,a-b,n)})
        for site in (28,42,44):
            if site<=L:continue
            detector=D.Mahalanobis(np.stack([natural_states[i][site]['answer'] for i in plan['detector_fit_ids']]))
            for arm in D.ARMS:
                eligible=[i for i in core if (i,L,arm) in model]
                if not eligible:continue
                rr=[model[i,L,'natural'] for i in eligible]
                a=detector.score(np.stack([state(model[i,L,'natural'],site) for i in eligible]));b=detector.score(np.stack([state(model[i,L,arm],site) for i in eligible]))
                gates.append({'layer':L,'read_layer':site,'arm':arm,**gate(rr,a,b,n)})
            # Both sets held out from the detector. Pair by fixed seed order, not by distances.
            pi=plan['pilot_ids'];sp=plan['specificity_ids'];bank={r['id']:r for r in plan['records']}
            rr=[{'bridge':bank[i]['bridge'],'donor_bridge':bank[j]['bridge']} for i,j in zip(pi,sp)]
            a=detector.score(np.stack([natural_states[i][site]['answer'] for i in pi]));b=detector.score(np.stack([natural_states[i][site]['answer'] for i in sp]))
            gates.append({'layer':L,'read_layer':site,'arm':'natural_specificity',**gate(rr,a,b,n)})
        bank={r['id']:r for r in plan['records']};means=D.class_means(plan,natural_states,L)
        for arm in D.ARMS:
            site='answer' if arm in ('answer_patch','random_answer') else 'bridge'
            eligible=[i for i in core if (i,L,arm) in model]
            if not eligible:continue
            det=D.Mahalanobis(np.stack([natural_states[i][L][site] for i in plan['detector_fit_ids']]))
            original=[];patched=[];rr=[]
            for i in eligible:
                row=model[i,L,arm];v=natural_states[i][L][site];original.append(v);rr.append(row)
                if arm=='natural':new=v
                elif arm=='class_mean':
                    delta=means[bank[row['donor']]['bridge']]-means[bank[i]['bridge']]
                    new=v+delta*(row['norm_a']/np.linalg.norm(delta))
                else:
                    donor=row[arm+'_donor'] if arm.startswith('random_') else row['donor']
                    new=natural_states[donor][L][site]
                patched.append(new)
            gates.append({'layer':L,'read_layer':L,'site':site,'arm':arm,'descriptive_patch_site':True,
                          **gate(rr,det.score(np.stack(original)),det.score(np.stack(patched)),n)})
        for reader,sites in D.READERS.items():
          for site in sites:
            if site<=L:continue
            matches=[r for r in readers if r['reader']==reader and r['layer']==L and r['read_layer']==site and r['status']=='OK']
            lookup={(r['recipient'],r['arm']):r for r in matches}
            if len(lookup)!=len(matches):raise ValueError('Duplicate reader rows')
            keep=[r for r in base if all((r['recipient'],a) in lookup for a in D.ARMS if a!='class_mean')]
            switch_effect={}
            for arm in D.ARMS:
                valid=[r for r in keep if (r['recipient'],arm) in lookup]
                rate_rows=[r for r in valid if lookup[r['recipient'],'natural']['lo']>0]
                for control in (['random_bridge','random_answer'] if arm=='answer_patch' else ['random_bridge']):
                    a=np.array([lookup[r['recipient'],arm]['lo']<0 for r in rate_rows],float);b=np.array([lookup[r['recipient'],control]['lo']<0 for r in rate_rows],float)
                    effect=paired_effect(rate_rows,a-b,n);switch_effect[arm,control]=effect
                    shift=[lookup[r['recipient'],control]['lo']-lookup[r['recipient'],arm]['lo'] for r in valid]
                    read_tables.append({'layer':L,'reader':reader,'read_layer':site,'arm':arm,'control':control,
                                        'switch_rate':float(a.mean()) if len(a) else None,'switch_wilson_ci':wilson(int(a.sum()),len(a)),
                                        'switch_difference':effect,'continuous_net_shift':paired_effect(valid,shift,n),
                                        'mean_natural_lo':float(np.mean([lookup[r['recipient'],'natural']['lo'] for r in valid])) if valid else None,
                                        'mean_patched_lo':float(np.mean([lookup[r['recipient'],arm]['lo'] for r in valid])) if valid else None,
                                        'naturally_correct_answer_n':len(base),'complete_reader_n':len(keep)})
            decisions.append({'layer':L,'reader':reader,'read_layer':site,'primary':L==primary_layer and reader=='olens',
                              'verdict':dissociated(flip_effect['bridge_patch','random_bridge'],flip_effect['answer_patch','random_bridge'],
                                                   switch_effect['answer_patch','random_bridge'],switch_effect['bridge_patch','random_bridge']),
                              'answer_site_control_verdict':dissociated(flip_effect['bridge_patch','random_bridge'],flip_effect['answer_patch','random_answer'],
                                                   switch_effect['answer_patch','random_answer'],switch_effect['bridge_patch','random_bridge'])})
            if L==primary_layer and site==D.READERS[reader][-1]:
                net=[lookup[r['recipient'],'random_bridge']['lo']-lookup[r['recipient'],'bridge_patch']['lo'] for r in keep]
                f=[model[r['recipient'],L,'bridge_patch']['lo']<0 for r in keep]
                for matched in (False,True):rho_rows.append({'reader':reader,'read_layer':site,'layer':L,'primary_reader':reader in ('olens','nla','skip_a'),**ratio(keep,net,f,n,matched)})
        if L==primary_layer:
            nonflipped=[i for i in correct if model[i,L,'bridge_patch']['lo']>=0]
            chosen=sorted(np.random.default_rng(0).choice(sorted(nonflipped),min(10,len(nonflipped)),replace=False).tolist())
            for i in chosen:examples.append({'recipient':i,'natural':model[i,L,'natural'],'patched':model[i,L,'bridge_patch'],
                                             'readers':[r for r in readers if r['recipient']==i and r['layer']==L and r['arm'] in ('natural','bridge_patch','random_bridge')]})
    for matched in (False,True):
        group=[r for r in rho_rows if r.get('margin_matched')==matched and r['primary_reader']]
        for claim in ('written','use'):
            for r,q in zip(group,bh([r.get('p',{}).get(claim,1.) for r in group])):r['q_'+claim]=q
    for r in rho_rows:r['verdict']=ratio_verdict(r,r.get('q_written',1.),r.get('q_use',1.)) if r['primary_reader'] else 'SECONDARY_NO_BH_VERDICT'
    primary=[r for r in rows if r['layer']==primary_layer and r['arm']=='bridge_patch' and r['status']=='OK' and model[r['recipient'],primary_layer,'natural']['lo']>0]
    F=sum(r['lo']<0 for r in primary);N=sum(r['lo']>=0 for r in primary)
    summary={'primary_layer':primary_layer,'F':F,'N':N,'quota_status':'MET' if F>=80 and N>=40 else 'UNDERPOWERED',
             'scientific_status':'EXPLORATORY_SINGLE_BANK','draws':n,'seed':0,'examples_n':len(examples),'dissociation':decisions,
             'gate':[g for g in gates if g['layer']==primary_layer and g['read_layer']==42 and g['arm']=='bridge_patch']}
    meta={**D.provenance(),'plan_sha256':D.digest(plan),'input_model_rows_sha256':D.sha(root/'test/model_rows.json'),
          'input_reader_rows_sha256':D.sha(root/'test/reader_rows.jsonl'),'input_capture_checksums_sha256':D.sha(root/'natural/checksums.json')}
    for name,table in [('flip_table',flips),('readback_table',read_tables),('rho_table',rho_rows),('mahalanobis_gate',gates),('examples',examples),('summary',summary)]:
        D.save(out/(name+'.json'),{'data':[{**r,**meta} for r in table] if isinstance(table,list) else table,**meta})
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--plan',type=Path,default=D.OUT/'pilot_plan.json');p.add_argument('--out',type=Path,default=D.OUT/'tables');a=p.parse_args()
    decision=D.read(a.run_dir/D.DATA_REL/'layer_decision.json')
    print(analyze(D.read(a.plan),a.run_dir/D.DATA_REL,decision['primary_layer'],a.out))

if __name__=='__main__':main()
