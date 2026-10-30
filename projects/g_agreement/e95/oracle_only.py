"""CPU-only E95 notes 3/4: complete reader stages only; no acquisition."""
import argparse
import hashlib
import subprocess
import types
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.understand.e87_analysis import e87_analysis as e87

ROOT=Path(__file__).resolve().parents[3]
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e95/ANALYSIS_ONCE.json'
REASON='NOT RUN (operational): no complete matched NLA real and placebo stage; operational note 3'


def stage(manifest, planned, reader='oracle'):
    c.require(reader in ('oracle','nla') and manifest['reader']==reader and manifest['status']=='COMPLETE','complete planned reader stage only')
    actual=manifest['cells']
    def keys(xs):
        ks=[(x['id'],x['arm'],x['layer'],tuple(x['positions'])) for x in xs]
        c.require(len(ks)==len(set(ks)),'duplicate stage cell')
        return set(ks)
    c.require(keys(actual)==keys(planned),'all and only planned real/placebo position/layer cells')
    c.require({x['arm'] for x in actual}=={'real','placebo'},'matched placebo floor required')


def row_stat(cells,row,layers,reader='oracle'):
    # Original E87 function/code and bootstrap, with the frozen row's achieved layer grid.
    scope=dict(e87.row_stat.__globals__,ORACLE_LAYERS=tuple(layers))
    selected={(r,'oracle',a,l):v for (r,rd,a,l),v in cells.items() if rd==reader}
    return types.FunctionType(e87.row_stat.__code__,scope)(selected,row)


def summarize_reader(plan,judgments,join,reader='oracle'):
    c.require(all(x['reader']==reader for x in join),'one reader per registered map')
    c.unique(judgments); c.unique(join)
    cells,first=e87.grid(judgments,join)
    result=[]
    for row in plan['rows']:
        key=row['key']; item=dict(bank=row['bank'],row=row['row'],key=key)
        if row['status']=='NOT RUN':
            c.require(bool(row['reason']),'explicit missing stage reason')
            item.update(status='NOT RUN (operational)',reason=row['reason']);result.append(item);continue
        if not row['statement_score_registered']:
            item.update(status='NOT EVALUABLE (no statement score)');result.append(item);continue
        c.require(row['status']=='COMPLETE' and row['layers'],'frozen row grid')
        actual={(a,l):set(v) for (r,rd,a,l),v in cells.items() if r==key}
        expected={(a,l):set(row['items'][a]) for a in ('real','placebo') for l in row['layers']}
        c.require(actual==expected,'exact per-row original item/layer/arm inventory')
        stats=row_stat(cells,key,row['layers'],reader)
        item.update(status='DESCRIPTIVE',statistics=stats,J_fraction=row['J_fraction'],single_site_verdict=row['single_site_verdict'])
        # A source-bound registered verdict boundary is mandatory; never choose one from outputs.
        rule=plan['verdict_rule'];c.require(rule['operator'] in ('>=','>') and rule['authority'],'registered verdict definition')
        d=stats['D'];threshold=rule['threshold']
        item['map_verdict']=None if not np.isfinite(d) else ('REPORTED' if (d>=threshold if rule['operator']=='>=' else d>threshold) else 'MISSED')
        positions=first.get((key,reader),[])
        item['first_mention_position']=dict(n=len(positions),median=float(np.median(positions)) if positions else None)
        result.append(item)
    eligible=[r for r in result if r['status']=='DESCRIPTIVE']
    complete=bool(eligible) and all(r['map_verdict'] is not None and r['single_site_verdict'] in ('REPORTED','MISSED') and r['J_fraction'] is not None for r in eligible) and plan['E62_median'] is not None
    hm=dict(status='NOT EVALUABLE',eligible_rows=len(eligible),authority='H-M1 descriptive; not confirmatory')
    if complete:
        agree=sum(r['map_verdict']==r['single_site_verdict'] for r in eligible)/len(eligible)
        violation=any(r['J_fraction']<plan['E62_median'] and r['statistics']['D']>=.30 for r in eligible)
        hm.update(status='MET' if agree>=.80 and not violation else 'NOT MET',agreement=agree,low_J_readable=violation)
    return dict(experiment='E95',reader=reader,rows=result,H_M1=hm)


def summarize(plan,judgments,join):
    c.require(all(x['reader'] in ('oracle','nla') for x in join),'registered readers only')
    c.unique(judgments);c.unique(join)
    c.require({x['id'] for x in judgments}=={x['id'] for x in join},'complete original judgments')
    reports={};coverage={}
    for reader in ('oracle','nla'):
        rows=[r for r in plan['rows'] if r.get('reader','oracle')==reader]
        js=[x for x in join if x['reader']==reader];ids={x['id'] for x in js}
        c.require(not js or rows,'no unplanned reader inputs')
        rp=dict(plan,rows=rows)
        reports[reader]=summarize_reader(rp,[j for j in judgments if j['id'] in ids],js,reader)
        coverage[reader]=[dict(shard=r.get('stage'),row=r['key'],status=r['status'],reason=r.get('reason')) for r in rows]
    result=reports['oracle']
    result['NLA']=reports['nla'] if coverage['nla'] else dict(status='NOT RUN (operational)',reason=REASON)
    result['coverage']=coverage
    return result


def inputs(spec):
    seal=c.verify(spec['binding_seal'],spec['binding_sha256']);root=Path(spec['binding_seal']).parent
    c.require(seal['experiment']=='E95' and seal['status']=='COMPLETE','complete binding')
    for name in ('route_verified','privacy_verified','labels_cpu_only','stage_custody_verified'):
        c.require(seal[name] is True,name)
    for source in seal['sources']:c.verify(source['seal'],source['sha256'])
    plan=c.read(root/'PLAN.json')
    c.require(hashlib.sha256(subprocess.check_output(['git','show',spec['plan_commit']+':'+spec['plan_path']],cwd=ROOT)).hexdigest()==c.sha(root/'PLAN.json'),'pre-output committed plan')
    manifests=c.read(root/'STAGES.json')
    c.require(set(manifests)==set(plan['stages']),'all shard dispositions')
    for ident,expected in plan['stages'].items():
        m=manifests[ident]
        if m['status']=='NOT RUN':
            c.require(m['reason'] and not m.get('cells'),'no partial stage use')
            c.require(all(r['status']=='NOT RUN' for r in plan['rows'] if r['stage']==ident),'missing stage rows explicitly not run')
        else:stage(m,expected,plan.get('stage_readers',{}).get(ident,'oracle'))
        reader=plan.get('stage_readers',{}).get(ident,'oracle')
        c.require(reader in ('oracle','nla') and m['reader']==reader,'frozen reader stage identity')
        c.require(all(r.get('reader','oracle')==reader and r['status']==m['status'] for r in plan['rows'] if r['stage']==ident),'row coverage follows stage manifest only')
    join=c.read(root/'JOIN.PRIVATE.json');judgments=c.read(root/'JUDGMENTS.json')
    admitted=[(x['id'],m['reader']) for m in manifests.values() if m['status']=='COMPLETE' for x in m['cells']]
    c.require(len(admitted)==len({i for i,_ in admitted}),'distinct original grouped IDs across stages/readers')
    allowed=dict(admitted)
    c.require(all(allowed.get(x['id'])==x['reader'] for x in join),'join reader matches complete stage')
    c.require({x['id'] for x in join}==set(allowed),'no omitted/partial/extra grouped readout')
    return plan,judgments,join


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    receipt=c.read(ROOT/'projects/g_agreement/e95/ORACLE_ONLY_SOURCE_RECEIPT.json')
    for f,h in receipt['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed scientific source')
    spec=c.read(args.spec);plan,judgments,join=inputs(spec)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    out=c.claim(dict(analysis=spec['analysis'],guard=str(GUARD),output_sha256=spec['binding_sha256']),commit)
    result=summarize(plan,judgments,join)
    # JSON null for undefined scientific values, never fabricated zeros.
    def clean(x):
        if isinstance(x,float) and not np.isfinite(x):return None
        if isinstance(x,dict):return {k:clean(v) for k,v in x.items()}
        if isinstance(x,list):return [clean(v) for v in x]
        return x
    c.write(out/'RESULTS.json',clean(result));c.write(out/'BINDING.json',spec)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E95',status='COMPLETE_ONCE',code_commit=commit)

if __name__=='__main__':main()
