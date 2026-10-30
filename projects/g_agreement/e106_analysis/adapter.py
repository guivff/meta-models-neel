"""E106 sole CPU analysis; §215 and §221.3. No model or judging calls."""
import argparse, hashlib, math, subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from . import rules as r
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e106/ANALYSIS_ONCE.json')
REQ=core.require

def committed():
    for p,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/p)==h,'dependency changed')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.md','.json'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def statement(code,text):
    # This is the bank's whole trained-value-union judgment, not binary target S.
    REQ(set(code)=={'states_any_trained_value','evidence'},'placebo blind union code')
    v=code['states_any_trained_value'];e=code['evidence']
    REQ(v is None or type(v) is bool,'boolean statement or missing')
    REQ(isinstance(e,str) and bool(e)==(v is True),'statement evidence')
    REQ(core.normalize(e) in core.normalize(text),'verbatim statement evidence')
    return None if v is None else int(v)

def placebo(items):
    REQ(len(items)==200 and len({x['item_id'] for x in items})==200,'all200 paired placebos')
    out={}
    for cell in ('original','intervention'):
        values=[x[cell] for x in items];known=[x for x in values if x is not None]
        REQ(all(x in (0,1) for x in known),'statement indicators')
        yes=sum(known);missing=200-len(known)
        # The registered denominator is200, not a parseable-only denominator.
        out[cell]=dict(statement_rate=yes/200 if not missing else None,stating=yes,total=200,
            missing=missing,rate_bounds=[yes/200,(yes+missing)/200],
            parseable_descriptive=core.stats({x['item_id']:x[cell] for x in items}))
    return out

def gate(d):
    REQ(d['status']=='PASS' and d['steps']==10 and d['parity_byte_equal']==3,'feasibility gate')
    REQ(d['frozen_before_sha256']==d['frozen_after_sha256'] and d['adapter_tensors_changed']>0,'frozen base/trainable adapter')
    REQ(d['parity_before_optimizer'] is True and d['fresh_production_adapter'] is True,'pre-optimizer parity/fresh production')
    REQ(len(d['parity'])==3 and all(x['expected_sha256']==x['actual_sha256'] for x in d['parity']),'exact three parity fixtures')
    REQ(len(d['gate_losses'])==10 and all(math.isfinite(v) for v in d['gate_losses']),'ten finite dev steps')

def analyze(rows,dispositions,diagnostics):
    result=dict(experiment='E106',authority='§215 / §221 item3 clarification1',bootstrap=dict(draws=2000,seed=20261027,unit='paired item'),readers={})
    for reader in ('oracle','nla'):
        report={};xs=[x for x in rows if x['reader']==reader]
        for arm in ('P','T'):
            ds=dispositions[reader][arm];ys=[x for x in xs if x['arm']==arm]
            if ds['status']!='COMPLETE':
                REQ(not ys,'no partial failed-arm scores');report[arm]=dict(status=ds['status'],reason=ds['reason']);continue
            names=r.TRAIN+r.HELD+(r.CONTENT if arm=='T' else ())
            REQ({x['row'] for x in ys}==set(names)|({'placebo'} if arm=='T' else set()),'exact arm rows')
            per={k:r.paired([x for x in ys if x['row']==k]) for k in names}
            report[arm]=dict(status='COMPLETE',rows=per)
            if arm=='P':report[arm]['R-FX0']=dict(status='DESCRIPTIVE',comparison='prompt minus original per row');continue
            d=diagnostics[reader];gate(d['gate'])
            REQ(d['recipe']==dict(rank=16,lr=1e-4,steps=300,batch_size=16,seed=20261029),'fixed recipe')
            REQ(d['dev_only'] is True and d['equal_replay'] is True and d['test_optimizer_items']==0,'no test leakage')
            losses=d['losses'];REQ(len(losses)==300 and all(math.isfinite(x) for x in losses),'full finite loss trajectory')
            if reader=='oracle':REQ(d['oracle_e102_resolution_sha256'],'Oracle gate resolution')
            p=placebo([x for x in ys if x['row']=='placebo']);report[arm]['placebo']=p
            report[arm]['rules']=r.rules({k:per[k] for k in r.TRAIN},{k:per[k] for k in r.HELD},{k:per[k] for k in r.CONTENT},p['intervention']['statement_rate'],losses[-1]<losses[0],True)
            report[arm]['loss_comparison']=dict(first=losses[0],last=losses[-1])
        result['readers'][reader]=report
    return result

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit']
    REQ(len(commit)==40,'full pre-output inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed inventory')
    inv=core.verify(ip,s['inventory_sha256']);REQ(inv['experiment']=='E106' and inv['placebo_seed']==20261031,'original inventory')
    meta=core.unique(core.read(ip.parent/'INVENTORY.json'))
    for x in meta.values():
        REQ(x['reader'] in ('oracle','nla') and x['arm'] in ('P','T'),'registered reader/arm')
        allowed=r.TRAIN+r.HELD+(r.CONTENT+('placebo',) if x['arm']=='T' else ())
        REQ(x['row'] in allowed,'registered row')
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    REQ(seal['experiment']=='E106' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'terminal output binding')
    REQ(seal['route_verified'] is True and seal['privacy_verified'] is True and seal['labels_cpu_only'] is True,'route/privacy custody')
    REQ(set(seal['dispositions'])=={'oracle','nla'},'both reader dispositions')
    for reader,arms in seal['dispositions'].items():
        REQ(set(arms)=={'P','T'},'both arm dispositions')
        for arm,d in arms.items():
            REQ(d['status'] in ('COMPLETE','NOT RUN (feasibility)','NOT RUN (Oracle E102 gate unresolved)'),'registered disposition')
            if d['status']!='COMPLETE':REQ(arm=='T' and d['reason'] and d['source_ref'],'sealed feasibility reason')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'sealed source reference')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    for arms in seal['dispositions'].values():
        for d in arms.values():
            if d['status']!='COMPLETE':ref(d['source_ref'])
    expected={k for k,x in meta.items() if seal['dispositions'][x['reader']][x['arm']]['status']=='COMPLETE'}
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json'));REQ(set(ms)==expected,'all planned complete cells; no dropping')
    rows=[];keys=set()
    for ident in expected:
        x=meta[ident];key=(x['reader'],x['arm'],x['row'],x['item_id']);REQ(key not in keys,'duplicate paired item');keys.add(key)
        REQ(x['split']==('placebo' if x['row']=='placebo' else 'test'),'held-out evaluation')
        data=ms[ident];REQ(set(data['cells'])=={'original','intervention'},'paired cells')
        z={}
        for cell,refs in data['cells'].items():
            REQ(set(refs)=={'text','code'},'exact raw text/code pointers');text=ref(refs['text']);code=ref(refs['code'])
            z[cell]=statement(code,text) if x['row']=='placebo' else core.score(code,x['target_by_cell'][cell],text)
        rows.append(dict(x,**z))
    # Original expected IDs and availability are frozen before output, not inferred from observed cells.
    for reader in ('oracle','nla'):
        for arm in ('P','T'):
            names=r.TRAIN+r.HELD+(r.CONTENT+('placebo',) if arm=='T' else ())
            for row in names:
                n=sum(x['reader']==reader and x['arm']==arm and x['row']==row for x in meta.values())
                a=inv['availability'][reader][arm][row];REQ(n==a['count'] and 0<n<=(200 if row=='placebo' else 84),'frozen full availability')
                if n!=(200 if row=='placebo' else 84):REQ(row!='placebo' and a['reason'],'explicit original shortfall')
    REQ(inv['legacy_nla_holder_original_max_tokens']==128 and inv['new_max_tokens']==512,'retain legacy baseline mismatch')
    diag={k:ref(v) for k,v in seal['diagnostics'].items()}
    return rows,seal['dispositions'],diag

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=committed();s=core.read(args.spec)
    rows,dispositions,diagnostics=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(rows,dispositions,diagnostics)
    result['baseline_caveat']='NLA holder original128 tokens versus new512 retained; no baseline regeneration'
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E106',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'])
if __name__=='__main__':main()
