"""X1b-lite: raw paired bridge contrasts; norm adjustment is sensitivity only."""
from pathlib import Path
import argparse
import numpy as np
from . import remainder_x1b as D, remainder_x1b_collect as C, remainder_x1_analyze as A

TABLES=("flip_table","readback_table","rho_table","mahalanobis_gate","examples","summary","matching_table")


def adjusted_values(y_real,y_control,r_real,r_control):
    """Within-recipient regression, continuous ratio and real-arm interaction.
    Returns residual-preserving per-item standardized differences; mean equals fitted arm contrast.
    """
    y=np.asarray(y_real,float)-np.asarray(y_control,float)
    r=np.asarray(r_real,float);c=np.asarray(r_control,float)
    if not (y.shape==r.shape==c.shape) or not np.isfinite(np.r_[y,r,c]).all():raise ValueError('Adjustment input mismatch/nonfinite')
    if len(y)<4:raise ValueError('Adjustment insufficient rows')
    if max(r.min(),c.min())>min(r.max(),c.max()):raise ValueError('Adjustment lacks ratio overlap')
    center=np.mean((r+c)/2);x=np.column_stack([np.ones(len(y)),r-c,r-center])
    if np.linalg.matrix_rank(x)<x.shape[1]:raise ValueError('Adjustment rank deficient')
    beta=np.linalg.lstsq(x,y,rcond=None)[0]
    return y-beta[1]*(r-c)-beta[2]*(r-c)/2


def effect(rows,y_real,y_control,r_real,r_control,n=A.BOOT):
    raw=A.paired_effect(rows,np.asarray(y_real)-np.asarray(y_control),n)
    try:
        values=adjusted_values(y_real,y_control,r_real,r_control)
    except ValueError as e:return {'raw_primary':raw,'adjusted_sensitivity':{'status':'UNAVAILABLE','reason':str(e)},'comparison':'ADJUSTMENT_UNAVAILABLE'}
    arr=[np.asarray(x,float) for x in (y_real,y_control,r_real,r_control)];intervals={}
    for scheme in ('item','bridge','donor'):
        draws=[]
        for idx in A.draws(rows,scheme,n):
            try:draws.append(float(adjusted_values(*(x[idx] for x in arr)).mean()))
            except ValueError:draws.append(np.nan)
        intervals[scheme]=A.ci(draws)
    adjusted={'status':'OK','estimate':float(values.mean()),'wider_ci':A.envelope(list(intervals.values())),'intervals':intervals}
    def label(e):
        ci=e.get('wider_ci')
        return 'UNDEFINED' if ci is None else 'POSITIVE' if ci[0]>0 else 'NEGATIVE' if ci[1]<0 else 'INCONCLUSIVE'
    disagree=label(raw)!=label(adjusted) or np.sign(raw['estimate'])!=np.sign(adjusted['estimate'])
    return {'raw_primary':raw,'adjusted_sensitivity':adjusted,'comparison':'ADJUSTMENT_SENSITIVE' if disagree else 'AGREES'}


# Preserve §26 calculation, adding optional refit-within-draw norm sensitivity.
def ratio(rows,net,flipped,n=A.BOOT,margin_matched=False,adjustment=None):
    net=np.asarray(net);flipped=np.asarray(flipped,dtype=bool)
    if not rows or not flipped.any() or flipped.all():return {'status':'UNDEFINED','verdict':'MIXED','reason':'empty F or N','margin_matched':margin_matched}
    margins=np.asarray([r['natural_lo'] for r in rows]);cuts=np.quantile(margins,[1/3,2/3]);terciles=np.searchsorted(cuts,margins,side='right')
    usable=[t for t in (0,1,2) if np.any((terciles==t)&flipped) and np.any((terciles==t)&~flipped)]
    retained=np.isin(terciles,usable) if margin_matched else np.ones(len(rows),dtype=bool)
    def stats(idx):
        i=np.asarray(idx);i=i[retained[i]];f=flipped[i];x=net[i]
        if adjustment is not None:
            try:x=adjusted_values(*(np.asarray(v)[i] for v in adjustment))
            except ValueError:return np.array([np.nan]*3)
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
        arr=np.array([stats(i) for i in A.draws(rows,scheme,n,groups)]);samples[scheme]=arr
        intervals[scheme]={'N':A.ci(arr[:,0]),'F':A.ci(arr[:,1]),'rho':A.ci(arr[:,2],(.05,.95))}
        undefined=~np.isfinite(arr[:,2])
        pN=float(np.mean(~np.isfinite(arr[:,0])|(arr[:,0]<=0)));pF=float(np.mean(~np.isfinite(arr[:,1])|(arr[:,1]<=0)))
        pvals[scheme]={'written':max(pN,float(np.mean(undefined|(arr[:,2]<.5)))),
                       'use':max(pF,float(np.mean(undefined|(arr[:,2]>=.5)))), 'undefined_fraction':float(undefined.mean())}
    wide={k:A.envelope([v[k] for v in intervals.values()]) for k in ('N','F','rho')}
    # Conservative extension of §26: maximum p across all declared clustering schemes.
    ps={claim:max(v[claim] for v in pvals.values()) for claim in ('written','use')}
    return {'status':'OK' if wide['rho'] is not None else 'UNDEFINED','F_n':int(flipped.sum()),'N_n':int((~flipped).sum()),
            'N':None if not np.isfinite(point[0]) else float(point[0]),'F':None if not np.isfinite(point[1]) else float(point[1]),
            'rho':None if not np.isfinite(point[2]) else float(point[2]),'wider_ci':wide,'intervals':intervals,'p':ps,'schemes':pvals,
            'margin_matched':margin_matched,'tercile_cutpoints':cuts.tolist(),'retained_terciles':usable if margin_matched else [0,1,2],
            'retained_n':int(retained.sum()),'tercile_N_weights':{str(t):float(np.sum((terciles==t)&~flipped&retained)/max(1,np.sum(~flipped&retained))) for t in usable}}

def analyze(plan,root,primary_layer,out,n=A.BOOT):
    root=Path(root);out=Path(out)
    C.verify_measurement(root/'test');rows=D.read(root/'test/model_rows.json');readers=C.load_rows(root/'test/reader_rows.jsonl')
    C.assert_reader_completion(rows,readers,(primary_layer,));C.assert_model_coverage(rows,(primary_layer,))
    if any(r['layer']!=primary_layer or r['arm'] not in D.ARMS for r in rows):raise ValueError('Unexpected test layer/arm '+repr([(r['layer'],r['arm']) for r in rows if r['layer']!=primary_layer or r['arm'] not in D.ARMS]))
    model={(r['recipient'],r['arm']):r for r in rows if r['status']=='OK'}
    if len(model)!=sum(r['status']=='OK' for r in rows):raise ValueError('Duplicate model row')
    ids=sorted(i for i,a in model if a=='natural');L=primary_layer
    bridge_ids=[i for i in ids if all((i,a) in model for a in ('natural','bridge_patch','random_bridge'))]
    correct=[i for i in bridge_ids if model[i,'natural']['lo']>0]
    def base(which):return [{**model[i,'natural'],'natural_lo':model[i,'natural']['lo']} for i in which]
    def ratios(which,a,b):return ([model[i,a]['norm_ratio'] for i in which],[model[i,b]['norm_ratio'] for i in which])
    flips=[];readbacks=[];rhos=[];gates=[]
    for cohort,which in [('natural_correct',correct),('all_bridge_matched',bridge_ids)]:
        y=[[float(model[i,'natural']['lo']>0 and model[i,a]['lo']<0) for i in which] for a in ('bridge_patch','random_bridge')]
        flips.append({'cohort':cohort,'arm':'bridge_patch','control':'random_bridge','rates':{a:float(np.mean(v)) if v else None for a,v in zip(('bridge_patch','random_bridge'),y)},**effect(base(which),*y,*ratios(which,'bridge_patch','random_bridge'),n)})
    # Answer arms are descriptive; no inferential bypass/dissociation label.
    for arm in ('answer_patch','random_answer'):
        which=[i for i in ids if (i,arm) in model and model[i,'natural']['lo']>0]
        y=[model[i,arm]['lo']<0 for i in which]
        flips.append({'arm':arm,'status':'DESCRIPTIVE','n':len(which),'rate':float(np.mean(y)) if y else None,'wilson_ci':A.wilson(sum(y),len(y)),
                      'displacement_ratio':[{'recipient':i,'ratio':model[i,arm]['displacement_ratio']} for i in which]})
    for reader,sites in D.READERS.items():
      for site in sites:
        if site<=L:continue
        lookup={(r['recipient'],r['arm']):r for r in readers if r['reader']==reader and r['read_layer']==site and r['status']=='OK'}
        which=[i for i in correct if all((i,a) in lookup for a in ('natural','bridge_patch','random_bridge'))]
        rr=base(which);yr=[-lookup[i,'bridge_patch']['lo'] for i in which];yc=[-lookup[i,'random_bridge']['lo'] for i in which]
        norm=ratios(which,'bridge_patch','random_bridge');rate_ids=[i for i in which if lookup[i,'natural']['lo']>0]
        readbacks.append({'reader':reader,'read_layer':site,'arm':'bridge_patch','control':'random_bridge','naturally_correct_model_n':len(correct),'scorable_n':len(which),
                         'continuous_shift':effect(rr,yr,yc,*norm,n),
                         'switch_rates':{a:float(np.mean([lookup[i,a]['lo']<0 for i in rate_ids])) if rate_ids else None for a in ('bridge_patch','random_bridge')},
                         'switch':effect(base(rate_ids),[float(lookup[i,'bridge_patch']['lo']<0) for i in rate_ids],[float(lookup[i,'random_bridge']['lo']<0) for i in rate_ids],*ratios(rate_ids,'bridge_patch','random_bridge'),n)})
        for arm in ('answer_patch','random_answer'):
            kk=[i for i in ids if (i,arm) in lookup and (i,'natural') in lookup and model[i,'natural']['lo']>0 and lookup[i,'natural']['lo']>0]
            y=[lookup[i,arm]['lo']<0 for i in kk]
            readbacks.append({'reader':reader,'read_layer':site,'arm':arm,'status':'DESCRIPTIVE','n':len(kk),'switch_rate':float(np.mean(y)) if y else None,'wilson_ci':A.wilson(sum(y),len(y))})
        if site==D.READERS[reader][-1]:
            flipped=[model[i,'bridge_patch']['lo']<0 for i in which]
            for margin in (False,True):
                for adjusted in (False,True):
                    rhos.append({'reader':reader,'read_layer':site,'primary_reader':reader in ('olens','nla','skip_a'),'adjusted':adjusted,
                                 **ratio(rr,np.asarray(yr)-np.asarray(yc),flipped,n,margin,(yr,yc,*norm) if adjusted else None)})
    for margin in (False,True):
      for adjusted in (False,True):
        group=[r for r in rhos if r.get('margin_matched',margin)==margin and r['adjusted']==adjusted and r['primary_reader']]
        for claim in ('written','use'):
            for r,q in zip(group,A.bh([r.get('p',{}).get(claim,1.) for r in group])):r['q_'+claim]=q
    for r in rhos:r['verdict']=A.ratio_verdict(r,r.get('q_written',1),r.get('q_use',1)) if r['primary_reader'] else 'SECONDARY_NO_BH_VERDICT'
    for r in rhos:
        other=next(x for x in rhos if x['reader']==r['reader'] and x.get('margin_matched')==r.get('margin_matched') and x['adjusted']!=r['adjusted'])
        r['comparison']='ADJUSTMENT_SENSITIVE' if r['verdict']!=other['verdict'] else 'AGREES'
    states=C.load_states(root/'natural',plan);cached={}
    def state(row,site):
        path=root/'test'/row['state_file']
        if path not in cached:
            with np.load(path,allow_pickle=False) as blob:cached[path]={k:blob[k] for k in blob.files}
        return cached[path][f"{row['recipient']}_L{site}"]
    bank={r['id']:r for r in plan['records']}
    for site in (28,42,44):
        if site<=L:continue
        detector=D.Mahalanobis(np.stack([states[i][site]['answer'] for i in plan['detector_fit_ids']]))
        for arm in D.ARMS:
            kk=[i for i in ids if (i,arm) in model]
            if not kk:continue
            natural=detector.score(np.stack([state(model[i,'natural'],site) for i in kk]));patched=detector.score(np.stack([state(model[i,arm],site) for i in kk]))
            gates.append({'layer':L,'read_layer':site,'arm':arm,**A.gate(base(kk),natural,patched,n)})
        pi=plan['pilot_ids'];sp=plan['specificity_ids'];rr=[{'bridge':bank[i]['bridge'],'donor_bridge':bank[j]['bridge']} for i,j in zip(pi,sp)]
        gates.append({'layer':L,'read_layer':site,'arm':'natural_specificity',**A.gate(rr,detector.score(np.stack([states[i][site]['answer'] for i in pi])),detector.score(np.stack([states[i][site]['answer'] for i in sp])),n)})
    nonflipped=[i for i in correct if model[i,'bridge_patch']['lo']>=0]
    chosen=np.random.default_rng(0).choice(sorted(nonflipped),min(10,len(nonflipped)),replace=False).tolist()
    examples=[{'recipient':i,'natural':model[i,'natural'],'patched':model[i,'bridge_patch'],'readers':[r for r in readers if r['recipient']==i]} for i in chosen]
    F=len(correct)-len(nonflipped);N=len(nonflipped)
    summary={'status':'EXPLORATORY_FOLLOWUP_AFTER_X1_GATE_FAILURE','primary_layer':L,'F':F,'N':N,'quota':'MET' if F>=80 and N>=40 else 'UNDERPOWERED',
             'bridge_matched':len(bridge_ids),'test_total':len(ids),'answer_matched':sum((i,'random_answer') in model for i in ids),
             'raw_primary':True,'answer_arms':'DESCRIPTIVE_ONLY','draws':n,'seed':0}
    meta={**D.provenance(),'input_model_sha256':D.sha(root/'test/model_rows.json'),'input_reader_sha256':D.sha(root/'test/reader_rows.jsonl')}
    matching=[]
    for site,real,control in (('bridge','bridge_patch','random_bridge'),('answer','answer_patch','random_answer')):
        for template in sorted({bank[i]['template'] for i in ids}):
            cohort=[i for i in ids if bank[i]['template']==template];kk=[i for i in cohort if (i,control) in model]
            matching.append({'site':site,'template':template,'total':len(cohort),'matched':len(kk),'unmatched':len(cohort)-len(kk),
                             'mean_real_ratio':float(np.mean([model[i,real]['norm_ratio'] for i in kk])) if kk else None,
                             'mean_control_ratio':float(np.mean([model[i,control]['norm_ratio'] for i in kk])) if kk else None,
                             'mean_real_displacement':float(np.mean([model[i,real]['delta_norm'] for i in kk])) if kk and all('delta_norm' in model[i,real] for i in kk) else None,
                             'mean_control_displacement':float(np.mean([model[i,control]['delta_norm'] for i in kk])) if kk and all('delta_norm' in model[i,control] for i in kk) else None})
    for name,data in zip(TABLES,(flips,readbacks,rhos,gates,examples,summary,matching)):
        D.save(out/(name+'.json'),{'data':[{**r,**meta} for r in data] if isinstance(data,list) else data,**meta})
    return summary


def main():
    p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--plan',type=Path,default=D.OUT/'pilot_plan.json');p.add_argument('--out',type=Path,default=D.OUT/'tables');a=p.parse_args()
    root=a.run_dir/D.DATA_REL;layer=D.read(root/'layer_decision.json')['primary_layer']
    with D.write_guard([a.out/(name+suffix) for name in TABLES for suffix in ('.json','.json.partial')]):
        print(analyze(D.read(a.plan),root,layer,a.out))
if __name__=='__main__':main()
