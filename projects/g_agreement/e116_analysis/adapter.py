"""§228 E116: original E108 cohort and hit-rate bootstrap at blocks52/60."""
import argparse,hashlib,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.e108_analysis import adapter as original
from projects.g_agreement.e108_analysis.rules import interval,mean,DRAWS,SEED
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e116/ANALYSIS_ONCE.json'
BLOCKS=(52,60)


def classify(immediate):
    ready=all(immediate[b]['estimate'] is not None for b in BLOCKS)
    late=any(z['estimate'] is not None and z['CI95'] is not None and z['estimate']>.66 and z['CI95'][0]>.66 for z in immediate.values())
    low=ready and all(immediate[b]['estimate']<=.48 for b in BLOCKS)
    return dict(R_CH3='MET' if late else 'NOT MET' if ready and all(immediate[b]['CI95'] is not None for b in BLOCKS) else 'NOT EVALUABLE',not_at_read_token_by60=low if ready else None,mode_baseline=.66,outside_baseline=.48,descriptive=True)


def analyze(items):
    c.unique(items);out={}
    for arm,n in [('immediate',329),('delayed',47)]:
        xs=sorted([x for x in items if x['arm']==arm],key=lambda x:x['id']);c.require(len(xs)==n,'original retained arm census')
        out[arm]={}
        for b in BLOCKS:
            c.require(all(set(x['hits'])==set(BLOCKS) for x in xs),'both blocks required')
            vals=np.array([x['hits'][b] for x in xs],float)
            c.require(all(x['hits'][b] is None or type(x['hits'][b]) is bool for x in xs),'sealed bool or missing')
            out[arm][b]=dict(interval(np.arange(n),lambda ix:mean(vals[ix])),total=n,kept=int(np.isfinite(vals).sum()),missing=int(np.isnan(vals).sum()))
    return dict(experiment='E116',authority='§228',arms=out,rules=classify(out['immediate']),NLA='NOT RUN (registered Oracle-only scope)',bootstrap=dict(draws=DRAWS,seed=SEED,unit='original E108 item'),baseline_source='E108 sealed values, copied without refit/replay')


def original_inputs(binding):
    """Resolve original committed inventory in its own checkout, without editing binding."""
    ip=Path(binding['inventory_seal']).resolve()
    root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ip.parent,text=True).strip()).resolve()
    c.require(ip.is_relative_to(root),'inventory belongs to original checkout')
    previous=original.ROOT
    try:
        original.ROOT=root
        return original.inputs(binding)
    finally:
        original.ROOT=previous


def inputs(s):
    # Reuse only E108 normalization, never E108 analysis/bootstrap/guard.
    ep=Path(s['e108_analysis_seal']);es=c.verify(ep,s['e108_analysis_sha256'])
    c.require(es['experiment']=='E108' and es['status']=='COMPLETE_ONCE','original E108 terminal analysis')
    c.require('BINDING.json' in es['files'],'original sealed E108 SPEC')
    old,_=original_inputs(c.read(ep.parent/'BINDING.json'))
    cohort={x['id']:x for x in old if x['choice_status']=='ONE'}
    c.require(sum(x['arm']=='immediate' for x in cohort.values())==329 and sum(x['arm']=='delayed' for x in cohort.values())==47,'original retained376')
    bp=Path(s['binding_seal']);seal=c.verify(bp,s['binding_sha256'])
    c.require(seal['experiment']=='E116' and seal['status']=='COMPLETE','complete E116 binding')
    for key in ('route_verified','privacy_verified','labels_cpu_only','original_prompt_and_read_token_verified','frozen_e108_rubric_verified','greedy'):
        c.require(seal[key] is True,key)
    sources=seal['source_seals'];ss=[c.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];c.require(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'sealed source reference')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=c.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    ms=c.unique(c.read(bp.parent/'MEASUREMENTS.json'));c.require(set(ms)==set(cohort),'same retained E108 IDs, no new/drop items')
    out=[]
    for ident,x in ms.items():
        o=cohort[ident];c.require(ref(x['choice'])==o['choice'] and ref(x['source_id'])==ident,'original greedy pick and item')
        c.require(set(x['blocks'])=={'52','60'},'two exact blocks')
        hits={}
        for b in BLOCKS:
            z=x['blocks'][str(b)];c.require(ref(z['source_id'])==ident and ref(z['block'])==b,'capture/readout identity')
            hits[b]=ref(z['hit']);c.require(hits[b] is None or type(hits[b]) is bool,'original hit or explicit missing')
        out.append(dict(id=ident,arm=o['arm'],hits=hits))
    return out


def committed():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed original source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=c.read(a.spec);items=inputs(s)
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',analyze(items));c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E116',status='COMPLETE_ONCE',code_commit=commit)

if __name__=='__main__':main()
