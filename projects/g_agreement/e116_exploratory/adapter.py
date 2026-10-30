"""Post-hoc §228 note1; separate CPU-only once guard, primary immutable."""
import hashlib,subprocess
from pathlib import Path
import numpy as np
from common.stats import wilson,bootstrap_ci
from projects.g_agreement.e116_analysis import adapter as parent
from projects.g_agreement.e108_analysis.rules import loo_modes
from projects.g_agreement.understand.wmech2 import core as c
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
BASE=parent.GUARD.parent
PRIMARY='db01124ea4b03ed245aa0d0fc9ce1918ece7dbb92acbdea1644b3bf462479809'

def rate(vals):
    observed=[v for v in vals if v is not None];n=len(observed);k=sum(observed)
    p,lo,hi=wilson(k,n)
    return dict(planned=len(vals),kept=n,missing=len(vals)-n,hits=k,estimate=float(p) if n else None,CI95=[float(lo),float(hi)] if n else None)

def gain(xs,low):
    pairs=[x['hits'][60]-x['hits'][low] for x in xs if x['hits'][60] is not None and x['hits'][low] is not None]
    if pairs:p,lo,hi=bootstrap_ci(np.array(pairs,float),n_boot=5000,seed=0)
    return dict(planned=len(xs),paired=len(pairs),missing_pairs=len(xs)-len(pairs),estimate=float(p) if pairs else None,CI95=[float(lo),float(hi)] if pairs else None)

def reading(r):
    if r['estimate'] is None:return 'NOT EVALUABLE'
    if r['CI95'][0]>.25:return 'tracks specific choices'
    if r['estimate']<=.10:return 'predicts the prior'
    return 'intermediate; neither descriptive threshold met'

def analyze(xs,modes):
    immediate=[x for x in xs if x['arm']=='immediate'];c.require(len(immediate)==329,'original immediate329')
    split={}
    for name,flag in [('modal',1),('non_modal',0)]:
        group=[x for x in immediate if modes[x['id']]==flag]
        split[name]={str(b):rate([x['hits'][b] for x in group]) for b in (52,60)}
    c.require(sum(split[k]['52']['planned'] for k in split)==329,'complete modal partition')
    paired={arm:{'60_minus_'+str(b):gain([x for x in xs if arm=='all' or x['arm']==arm],b) for b in (52,44)} for arm in ('immediate','delayed','all')}
    diversity=[]
    for family in sorted({x['category'] for x in xs}):
        for b in (44,52,60):
            group=[x for x in xs if x['category']==family]
            diversity.append(dict(family=family,block=b,planned=len(group),judged=sum(x['hits'][b] is not None for x in group),distinct_named_members=None,status='NOT AVAILABLE: sealed hit-only judgments do not identify other named members'))
    return dict(experiment='E116 exploratory note1',role='post hoc exploratory appendix',primary_R_CH3='NOT MET (copied, unchanged)',modal_definition='Original E108 category-wide leave-one-out mode across both arms; lexical canonical-ID tie break; frozen picks, no bootstrap refit',immediate_subsets=split,always_mode_nonmodal_hit_rate=0,nonmodal60_reading=reading(split['non_modal']['60']),paired_depth_gains=paired,bootstrap=dict(draws=5000,seed=0,unit='same original item',missing='complete observed pairs only'),diversity=diversity,diversity_limitation='No new extraction, readout parsing or judging authorized/performed. Boolean hits cannot give total distinct named members. Requires existing sealed member extraction; absent is unknown.')

def main():
    receipt=c.read(HERE/'SOURCE_RECEIPT.json')
    for rel,h in receipt['files'].items():
        c.require(c.sha(ROOT/rel)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)).hexdigest()==h,'committed source')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    primary=BASE/'analysis_once';c.verify(primary/'ANALYSIS_SEAL.json',PRIMARY);guardhash=c.sha(parent.GUARD)
    s=c.read(primary/'BINDING.json');xs=parent.inputs(s)
    ep=Path(s['e108_analysis_seal']);c.verify(ep,s['e108_analysis_sha256'])
    old,_=parent.original_inputs(c.read(ep.parent/'BINDING.json'));old=[x for x in old if x['choice_status']=='ONE'];by=c.unique(old);modes=loo_modes(old)
    for x in xs:
        o=by[x['id']];c.require(x['arm']==o['arm'],'same arm');x['category']=o['category'];x['hits'][44]=o['hits']['oracle']
    c.require(len(xs)==376,'original376')
    out=c.claim(dict(analysis=str(BASE/'exploratory_note1_once'),guard=str(BASE/'EXPLORATORY_NOTE1_ONCE.json'),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',analyze(xs,modes));c.write(out/'BINDING.PRIVATE.json',s)
    c.require(c.sha(parent.GUARD)==guardhash,'primary guard unchanged');c.verify(primary/'ANALYSIS_SEAL.json',PRIMARY)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E116 exploratory note1',status='COMPLETE_ONCE',code_commit=commit,primary_seal_sha256=PRIMARY)
    print(c.sha(out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':main()
