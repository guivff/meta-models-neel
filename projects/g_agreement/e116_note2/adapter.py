"""E116 exploratory note2: post hoc, CPU only, separate once guard."""
import hashlib,subprocess
from pathlib import Path
import numpy as np
from common.stats import bootstrap_ci
from projects.g_agreement.e116_exploratory.adapter import rate
from projects.g_agreement.e116_analysis import adapter as parent
from projects.g_agreement.e108_analysis.rules import loo_modes
from projects.g_agreement.understand.wmech2 import core as c
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;BASE=parent.GUARD.parent
PRIMARY='db01124ea4b03ed245aa0d0fc9ce1918ece7dbb92acbdea1644b3bf462479809'
NOTE1='4533330ea8a2f90cede483b60941e3867aaf61466247a7a1c1111afc5ca16cfb'

def summarize(group):
    outside=rate([x['outside'] for x in group]);pairs=[float(x['hits'][60])-float(x['outside']) for x in group if x['outside'] is not None]
    if pairs:p,lo,hi=bootstrap_ci(np.array(pairs),n_boot=5000,seed=0)
    gain=dict(status='AVAILABLE' if pairs else 'NOT AVAILABLE',planned=len(group),paired=len(pairs),missing=len(group)-len(pairs),estimate=float(p) if pairs else None,CI95=[float(lo),float(hi)] if pairs else None)
    outside['status']='AVAILABLE' if outside['kept'] else 'NOT AVAILABLE'
    return dict(outside_hit=outside,oracle60_minus_outside=gain,hit_rates={str(b):rate([x['hits'][b] for x in group]) for b in (44,52,60)})

def select(xs,modes):
    c.unique(xs);group=[x for x in xs if x['arm']=='immediate' and modes[x['id']]==0]
    for x in group:
        c.require(set(x['hits'])=={44,52,60},'all original depths')
        c.require(all(v is None or type(v) is bool for v in [*x['hits'].values(),x['outside']]),'sealed bool/null only')
    paired=[x for x in group if x['hits'][60] is not None]
    return group,paired

def main():
    for rel,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/rel)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)).hexdigest()==h,'committed source receipt')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    c.verify(BASE/'analysis_once/ANALYSIS_SEAL.json',PRIMARY);c.verify(BASE/'exploratory_note1_once/ANALYSIS_SEAL.json',NOTE1)
    guards={p:c.sha(p) for p in [parent.GUARD,BASE/'EXPLORATORY_NOTE1_ONCE.json']}
    s=c.read(BASE/'analysis_once/BINDING.json');xs=parent.inputs(s)
    ep=Path(s['e108_analysis_seal']);c.verify(ep,s['e108_analysis_sha256']);old,_=parent.original_inputs(c.read(ep.parent/'BINDING.json'));old=[x for x in old if x['choice_status']=='ONE'];by=c.unique(old);modes=loo_modes(old)
    for x in xs:
        o=by[x['id']];c.require(o['arm']==x['arm'],'same item arm');x['hits'][44]=o['hits']['oracle'];x['outside']=o['hits']['outside']
    all_nonmodal,group=select(xs,modes);c.require(len(all_nonmodal)==111 and len(group)==110,'frozen note1 nonmodal cohort with observed block60')
    out=c.claim(dict(analysis=str(BASE/'exploratory_note2_once'),guard=str(BASE/'EXPLORATORY_NOTE2_ONCE.json'),output_sha256=s['binding_sha256']),commit)
    result=dict(experiment='E116 exploratory note2',authority='f011cc183',role='POST HOC EXPLORATORY',primary_R_CH3='NOT MET; unchanged',cohort='110 immediate non-modal items with observed Oracle60; original E108 leave-one-out mode, no refit',matched110=summarize(group),all111_nonmodal_depth_rates={str(b):rate([x['hits'][b] for x in all_nonmodal]) for b in (44,52)},bootstrap=dict(draws=5000,seed=0,unit='original item',order='original sealed E116 measurement order',missing='paired observed outside/Oracle60 only'),caveat='No new decision rule; no primary or note1 replay. Outside baseline is from original sealed E108 per-item judgments.')
    c.write(out/'RESULTS.json',result);c.write(out/'BINDING.PRIVATE.json',s)
    c.write(out/'COHORT.PRIVATE.json',dict(item_ids=[x['id'] for x in group],nonmodal_item_ids=[x['id'] for x in all_nonmodal]))
    for p,h in guards.items():c.require(c.sha(p)==h,'earlier guard unchanged')
    c.verify(BASE/'analysis_once/ANALYSIS_SEAL.json',PRIMARY);c.verify(BASE/'exploratory_note1_once/ANALYSIS_SEAL.json',NOTE1)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E116 exploratory note2',status='COMPLETE_ONCE',code_commit=commit,primary_seal_sha256=PRIMARY,note1_seal_sha256=NOTE1)
    print(c.sha(out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':main()
