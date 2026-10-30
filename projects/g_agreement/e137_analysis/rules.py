"""§249/e02db7a11: unchanged full R-NL1 predicate on D1; separate descriptions."""
from copy import deepcopy
from projects.g_agreement.e133_analysis import rules as base,probes
from projects.g_agreement.e126_analysis.rules import all3,any3
from projects.g_agreement.e127_analysis.common import require
READS=base.READS;BLOCKS=base.BLOCKS;PATCHES=base.PATCHES
readout=base.readout

def readings(group,probe,eligible):
    rr=group['reader_rates'];ps=group['patches']
    metric=lambda l:probe['layers'][str(l)]['current'].get('groups',{}).get('multi_hop_test',{}).get('macro_ovr_AUROC')
    test=lambda v,threshold,upper=False:None if v is None else v<=threshold if upper else v>=threshold
    timing_probe=all3([test(metric(44),.70,True)]+[test(metric(l),.90)for l in (52,56,60)])
    later=any3([test(ps[b]['read_token']['estimate'],.50)for b in (52,56)])
    timing=all3([timing_probe,test(rr['44']['previous']['estimate'],.30),later,test(ps[44]['read_token']['estimate'],.15,True)])
    reporting=all3([test(metric(44),.90),test(rr['44']['current']['estimate'],.20,True),test(rr['60']['current']['estimate'],.50)])
    faithful=test(rr['44']['current']['estimate'],.70)
    status=lambda v:'NOT EVALUABLE'if v is None else'MET'if v else'NOT MET'
    return dict(a_timing=status(timing)if eligible else'DESCRIPTIVE ONLY: fewer than30 pairs',b_reporting=status(reporting)if eligible else'DESCRIPTIVE ONLY: fewer than30 pairs',c_faithful_early=status(faithful)if eligible else'DESCRIPTIVE ONLY: fewer than30 pairs',probe_current_macro_ovr={str(l):metric(l)for l in probes.LAYERS},scope='Pre-stated descriptions a/b/c; confirmatory R-NL2 separately retains ALL R-NL1 gates on D1 only')

def analyze(pairs,names,draws=2000,probe_results=None):
    require(len({p['pair_id']for p in pairs})==len(pairs),'unique original pair IDs')
    require(all(p['kind']in('D1','D2','one_hop')for p in pairs),'no pooled old E133 or QA2')
    controls=[p for p in pairs if p['kind']=='one_hop'];require(len(controls)<=16,'registered first16 qualifying one-hop controls')
    out={};audit=[]
    for design in('D1','D2'):
        original=[p for p in pairs if p['kind']==design];require(len(original)<=42,'original first42 per design')
        # Literal family view only. Original IDs/order/members/measurements remain unchanged.
        view=deepcopy(original+controls)
        for p in view:
            if p['kind']==design:p['kind']='multi_hop'
        result,private=base.analyze(view,draws);probe=probes.analyze(view,names)if probe_results is None else probe_results['subdesigns'][design]['probes']
        group=result['groups']['multi_hop'];eligible=len(original)>=30
        full=base.classify(group['reader_rates'],group['patches'],eligible)
        out[design]=dict(n_pairs=len(original),eligible=eligible,reader_patch=group,full_R_NL1_structure=full,readings=readings(group,probe,eligible),probes=probe,scope='CONFIRMATORY R-NL2 on D1 only'if design=='D1'else'DESCRIPTIVE ONLY')
        for row in private:
            if row['kind']=='multi_hop':row['kind']=design;audit.append(row)
        if design=='D1':onehop=result['groups']['one_hop']
    return dict(experiment='E137',R_NL2=out['D1']['full_R_NL1_structure']['R_NL1'],falsifier_descriptive=out['D1']['full_R_NL1_structure']['falsifier'],subdesigns=out,one_hop_descriptive=onehop,normalization='Unchanged per-prompt R then median; matched-pair bootstrap2000/seed20261027; both controls all5; confidence gates unchanged',confirmatory='ALL R-NL1 gates on D1 only, per e02db7a11 item2; D2 and readings a/b/c reported separately',probe_split='first30 qualifying pairs per design DEV, rest TEST; both members stay together; fixed E109 model/no tuning',missing_policy='original missing remains missing; no imputation/cohort shrink; fewer30 design not confirmatory',preference='NOT MEASURED'),audit
