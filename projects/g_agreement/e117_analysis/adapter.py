"""§228 E117, clarification1; original signed score and paired item bootstrap."""
import argparse,hashlib,subprocess
from pathlib import Path
from itertools import groupby
from collections import Counter
import numpy as np
from projects.g_agreement.understand.wmech2 import core as c
from projects.g_agreement.e100_analysis.rules import Bootstrap,DRAWS,SEED
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e117/ANALYSIS_ONCE.json'
BOOK=('nesting_depth','indent_level','page_range_digit');ROWS=BOOK+('fact_recall',)
ALPHAS=(1,2,4);ARMS=('T','W','R')


def degenerate(tokens,text,missing):
    c.require(isinstance(tokens,list) and all(type(t) is int for t in tokens),'original generated token IDs')
    if missing or not text.strip() or not tokens:return True
    return any(sum(1 for _ in run)>=4 for _,run in groupby(tokens)) or max(Counter(tokens).values())/len(tokens)>.5


def classify(rows):
    positive=[];low=[];unknown=[]
    for row in BOOK:
        eligible=[z for z in rows[row].values() if not z['excluded_degeneracy']]
        positive.append(any(z['T_minus_R']['estimate'] is not None and z['T_minus_R']['CI95'] is not None and z['W']['estimate'] is not None and round(z['T_minus_R']['estimate'],12)>=.30 and z['T_minus_R']['CI95'][0]>0 and z['W']['estimate']<=0 for z in eligible))
        low.append(bool(eligible) and all(z['T_minus_R']['estimate'] is not None and z['T_minus_R']['estimate']<=.10 for z in eligible))
        unknown.append(not eligible or any(z['T_minus_R']['estimate'] is None or z['T_minus_R']['CI95'] is None or z['W']['estimate'] is None for z in eligible))
    controls=[z for z in rows['fact_recall'].values() if not z['excluded_degeneracy']]
    moved=any(z['T_minus_R']['estimate'] is not None and round(z['T_minus_R']['estimate'],12)>=.30 for z in controls)
    control_unknown=not controls or any(z['T_minus_R']['estimate'] is None for z in controls)
    return dict(R_IR1='MET' if sum(positive)>=2 else 'NOT EVALUABLE' if any(unknown) else 'NOT MET',falsifier='MET' if sum(low)>=2 and moved else 'NOT EVALUABLE' if any(unknown) or control_unknown else 'NOT MET',rows_positive=sum(positive),rows_low_all_eligible_alpha=sum(low),control_moves=moved)


def analyze(items):
    c.unique(items);c.require(len(items)==336,'four original84-item rows')
    cells={};diagnostics={}
    for row in ROWS:
        xs=[x for x in items if x['row']==row];c.require(len(xs)==84,'84 per row')
        for alpha in ALPHAS:
            key=f'{row}:{alpha}'
            counts={arm:0 for arm in ARMS};norms={arm:[] for arm in ARMS}
            for arm in ARMS:
                cells[(row,'oracle',f'{alpha}_{arm}')]={}
                for x in xs:
                    z=x['arms'][alpha][arm];cells[(row,'oracle',f'{alpha}_{arm}')][x['id']]=z['score']
                    counts[arm]+=int(z['degenerate']);norms[arm].extend(z['norm_ratios'])
            diagnostics[key]=dict(degenerate_count=sum(counts.values()),total=252,fraction=sum(counts.values())/252,per_arm={arm:dict(degenerate=counts[arm],total=84,fraction=counts[arm]/84,norm_ratio_mean=float(np.mean(norms[arm])) if norms[arm] else None,norm_ratio_count=len(norms[arm])) for arm in ARMS})
    bootstrap=Bootstrap(cells);rows={}
    for row in ROWS:
        rows[row]={}
        for alpha in ALPHAS:
            key=f'{row}:{alpha}';d=diagnostics[key]
            rows[row][alpha]=dict(T=bootstrap.stat(row,f'{alpha}_T'),W=bootstrap.stat(row,f'{alpha}_W'),R=bootstrap.stat(row,f'{alpha}_R'),T_minus_R=bootstrap.stat(row,f'{alpha}_T',f'{alpha}_R'),degeneracy=d,excluded_degeneracy=d['fraction']>.20)
    return dict(experiment='E117',authority='§228 clarification1',rows=rows,rules=classify(rows),bootstrap=dict(draws=DRAWS,seed=SEED,unit='paired original item',source='original E100/E57 signed-statistic bootstrap'),degeneracy_policy='UNPARSEABLE/empty OR consecutive identical token run>=4 OR single-token fraction>.5; row×alpha pooled T/W/R >.20 excluded; scores still descriptive')


def inputs(s):
    ip=Path(s['inventory_seal']).resolve()
    from .inventory import load_inventory
    meta=load_inventory(s,ROOT,ROWS)
    bp=Path(s['binding_seal']);seal=c.verify(bp,s['binding_sha256'])
    c.require(seal['experiment']=='E117' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete original binding')
    for k in ('route_verified','privacy_verified','labels_cpu_only','original_E57_rubric_verified','dev_only_directions_verified','all_generated_positions_hook_verified','greedy'):
        c.require(seal[k] is True,k)
    sources=seal['source_seals'];ss=[c.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];c.require(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'original pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=c.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    ms=c.unique(c.read(bp.parent/'MEASUREMENTS.json'));c.require(set(ms)==set(meta),'no skipped items')
    out=[]
    for ident,x in ms.items():
        m=meta[ident];c.require(ref(x['source_id'])==ident and ref(x['source_row'])==m['row'],'original ID/row')
        target=ref(x['target_letter']);c.require(target in ('A','B'),'original true value')
        c.require(set(x['arms'])=={'1','2','4'},'all registered doses');arms={}
        for alpha in ALPHAS:
            a=x['arms'][str(alpha)];c.require(set(a)==set(ARMS),'all TWR arms');arms[alpha]={}
            for arm,z in a.items():
                c.require(ref(z['source_id'])==ident and ref(z['alpha'])==alpha and ref(z['arm'])==arm,'native source/dose/arm binding')
                code=ref(z['code']);text=ref(z['text']);tokens=ref(z['token_ids']);norms=ref(z['norm_ratios'])
                c.require(code is not None and code['id']==z['judgment_id'],'explicit original judgment or UNPARSEABLE disposition required')
                score=c.score(code,target,text)
                c.require(isinstance(norms,list) and all(type(v) in (int,float) and np.isfinite(v) and v>=0 for v in norms),'original norm ratios')
                arms[alpha][arm]=dict(score=score,degenerate=degenerate(tokens,text,score is None),norm_ratios=norms,judgment_id=z['judgment_id'],text_sha256=hashlib.sha256(text.encode()).hexdigest())
        out.append(dict(id=ident,row=m['row'],arms=arms))
    return out


def committed():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed original source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=c.read(a.spec)
    from .sensitivity import load_map,mask,report
    mapping=load_map(s);items=inputs(s);mask(items,mapping)
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',analyze(items));c.write(out/'REDACTION_SENSITIVITY.json',report(items,mapping));c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E117',status='COMPLETE_ONCE',code_commit=commit)
if __name__=='__main__':main()
