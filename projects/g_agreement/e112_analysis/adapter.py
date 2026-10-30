"""E112 §225: CPU-only paired comparison with immutable E80c cells."""
import argparse, hashlib, math, random, subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.understand.e80_analysis.score80 import passed
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e112/ANALYSIS_ONCE.json'
REQ=core.require
ARMS=('none','J','random','PCA_k')

def projection(p):
    shares=p['cumulative_variance'];k=p['k'];j=p['J_variance_share']
    REQ(type(k) is int and 1<=k<=len(shares),'valid frozen k')
    REQ(all(math.isfinite(x) and 0<=x<=1 for x in shares) and shares==sorted(shares),'cumulative shares')
    REQ(round(j,4)==.1431,'E80c all518 J share, not posthoc cohort share')
    REQ(shares[k-1]>=j and (k==1 or shares[k-2]<j),'smallest variance-matching k')
    REQ(p['n']==518 and p['basis_block']==44 and p['centred'] is True,'original all518 centred basis')
    REQ(p['same_e80c_mu_and_basis'] is True,'original mu and basis custody')
    return k

def paired(rows):
    keep=[x for x in rows if x['J'] is not None and x['PCA_k'] is not None]
    n=len(keep);out=dict(n=len(rows),n_complete=n,n_missing=len(rows)-n,R_X5='NOT EVALUABLE',falsifier='NOT EVALUABLE')
    if not n:return out
    vals=[float(x['PCA_k'])-float(x['J']) for x in keep]
    jf=sum(not x['J'] for x in keep)/n;pf=sum(not x['PCA_k'] for x in keep)/n
    rng=random.Random(20261028)
    draws=sorted(sum(vals[rng.randrange(n)] for _ in range(n))/n for _ in range(2000))
    ci=[draws[50],draws[1949]];d=sum(vals)/n
    out.update(J_fall=jf,PCA_k_fall=pf,J_minus_PCA_k=dict(estimate=d,ci95=ci))
    if n==len(rows) and n>=2:
        out.update(R_X5='MET' if d>=.10 and ci[0]>0 else 'NOT MET',falsifier='MET' if pf>=jf else 'NOT MET')
    return out

def analyze(rows):
    REQ(len(rows)==518 and len({x['id'] for x in rows})==518,'exact518 source items')
    for x in rows:
        REQ(set(x['cells'])=={'oracle','nla'},'both readers')
        for cells in x['cells'].values():
            REQ(set(cells)==set(ARMS),'exact arm grid')
            REQ(all(v is None or type(v) is bool for v in cells.values()),'pass booleans or explicit missing')
    cohort=[x for x in rows if x['cells']['oracle']['none'] is True]
    REQ(len(cohort)==184,'sealed Oracle none-pass184 cohort')
    old=[x['cells']['oracle']['J'] for x in cohort]
    REQ(all(v is not None for v in old) and round(sum(not v for v in old)/184,3)==.576,'sealed original J fall')
    result=dict(experiment='E112',bootstrap=dict(draws=2000,seed=20261028,unit='paired source item'),cohort='sealed Oracle none-pass184',sealed_J_fall=sum(not v for v in old)/184,readers={})
    for reader in ('oracle','nla'):
        cells=[x['cells'][reader] for x in cohort]
        result['readers'][reader]=dict(role='confirmatory' if reader=='oracle' else 'exploratory',pooled=paired(cells),per_family={f:paired([x['cells'][reader] for x in cohort if x['family']==f]) for f in sorted({x['family'] for x in cohort})},arm_falls={a:dict(n=sum(x[a] is not None for x in cells),fall=sum(not x[a] for x in cells if x[a] is not None)/sum(x[a] is not None for x in cells) if any(x[a] is not None for x in cells) else None) for a in ARMS})
    result['R_X5']=result['readers']['oracle']['pooled']['R_X5'];result['falsifier']=result['readers']['oracle']['pooled']['falsifier']
    return result

def committed():
    for f,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/f)==h,'pinned dependency')
    for p in HERE.iterdir():
        if p.is_file():REQ(hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)).hexdigest()==core.sha(p),'source committed')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def ruling_admission(s,inventory):
    # ba760009e admits a post-output copy; no historical field is rewritten.
    REQ(inventory['experiment']=='E112' and inventory['pre_output']=='MISSING','honest copy-only inventory')
    proof=s['trackq_verification'];source=s['source_seals'][s['inventory']['seal_index']]
    REQ(source['sha256']==proof['inventory']['seal'],'verified copy seal binding')
    core.verify(source['seal'],source['sha256'])
    root=Path(source['seal']).parent
    REQ(core.sha(root/'INVENTORY.json')==proof['inventory']['inventory'] and core.sha(root/'PROVENANCE.json')==proof['inventory']['provenance'],'copy/provenance hashes')
    for field in ('route','privacy','labels_cpu_only','source_order','pre_output_commits'):
        REQ(proof[field]['ok'] is True,'current independent '+field+' verification')
    if 'r5_review_seal' not in s:
        review=core.read(HERE/'R5_REVIEW_BINDING.json')
        blob=subprocess.check_output(['git','show',review['commit']+':'+review['member']],cwd=ROOT)
        REQ(hashlib.sha256(blob).hexdigest()==review['sha256'],'original committed R5 review')
        text=blob.decode();section=text.split(review['section'],1)[1].split('\n## ',1)[0]
        REQ(review['approval_phrase'] in section,'existing R5 provenance approval')
        for field in ('inventory','provenance'):
            REQ(review[field+'_sha256']==proof['inventory'][field] and review[field+'_sha256'] in section,'R5 exact copied field hashes')
    else:
        review=core.verify(s['r5_review_seal'],s['r5_review_sha256'])
        REQ(review['reviewer']=='R-5' and review['status']=='PROVENANCE_VERIFIED' and review['inventory_sha256']==proof['inventory']['inventory'] and review['provenance_sha256']==proof['inventory']['provenance'],'R5 reviewed exact copied provenance before guard')
        REQ(review['projection_sha256']==core.sha(Path(s['source_seals'][s['projection']['seal_index']]['seal']).parent/s['projection']['member']),'reviewed original projection')


def inputs(s):
    seals=[core.verify(x['seal'],x['sha256']) for x in s['source_seals']];cache={}
    def ref(r):
        i=r['seal_index'];REQ(type(i) is int and 0<=i<len(seals) and r['member'] in seals[i]['files'],'sealed source member')
        p=Path(s['source_seals'][i]['seal']).parent/r['member']
        if p not in cache:cache[p]=core.read(p)
        v=cache[p]
        for key in r['keys']:v=v[key]
        return v
    inventory=ref(s['inventory']);plan=ref(s['projection']);projection(plan)
    ruling=s.get('inventory_construction','').startswith('POST_OUTPUT_COPY_ONLY')
    if ruling:
        ruling_admission(s,inventory)
        names=('projection',)
    else:
        REQ(inventory['experiment']=='E112' and inventory['pre_output'] is True,'pre-output frozen inventory')
        names=('inventory','projection')
        for field in ('route_verified','privacy_verified','labels_cpu_only','source_order_verified','pre_output_commits_verified'):
            REQ(inventory[field] is True,field)
    for name in names:
        REQ(len(s[name+'_commit'])==40,'full pre-output commit')
        r=s[name];blob=subprocess.check_output(['git','show',s[name+'_commit']+':'+s[name+'_commit_member']],cwd=ROOT)
        source=Path(s['source_seals'][r['seal_index']]['seal']).parent/r['member']
        REQ(hashlib.sha256(blob).hexdigest()==core.sha(source),'exact pre-output committed member')
    REQ(inventory['reader_blocks']==dict(oracle=44,nla=42),'registered sites')
    ids=inventory['item_ids'];REQ(len(ids)==len(set(ids))==518,'frozen518 inventory')
    old=ref(s['e80c_analysis']);REQ(old['oracle']['pooled']['n_pass_none']==184 and round(old['oracle']['pooled']['falls']['J_ablated'],3)==.576,'original analysis prerequisite')
    measurements=ref(s['measurements']);REQ([x['id'] for x in measurements]==ids,'exact original item ordering')
    rows=[]
    for x in measurements:
        packet=ref(x['packet']);REQ(packet['id']==x['id'],'original item packet')
        cells={}
        for reader in ('oracle','nla'):
            cells[reader]={}
            for arm in ARMS:
                z=x['cells'][reader][arm]
                REQ(z['experiment']==('E112' if arm=='PCA_k' else 'E80' if arm=='none' else 'E80c'),'reuse original arms')
                cells[reader][arm]=passed(ref(z['judgment']),packet,ref(z['text']))
        rows.append(dict(id=x['id'],family=packet['family'],cells=cells))
    if ruling and isinstance(s['diagnostics'],str):
        REQ(s['diagnostics'].startswith('NOT AVAILABLE'),'explicit unavailable diagnostics')
        return rows,plan,dict(status=s['diagnostics'],imputed=False)
    diagnostics=ref(s['diagnostics'])
    for reader in ('oracle','nla'):
        REQ(set(diagnostics[reader])==set(ARMS),'all arm diagnostics')
        for arm,z in diagnostics[reader].items():
            REQ(len(z['norm_ratios'])==518 and all(math.isfinite(v) and v>=0 for v in z['norm_ratios']),'original per-item norm ratios')
            REQ(math.isfinite(z['variance_removed']) and 0<=z['variance_removed']<=1,'measured variance removed')
    return rows,plan,diagnostics

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=core.read(a.spec)
    rows,plan,diagnostics=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=core.sha(a.spec)),commit)
    result=analyze(rows);result['projection']=plan;result['diagnostics']=diagnostics
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E112',status='COMPLETE_ONCE',code_commit=commit,spec_sha256=core.sha(a.spec))
if __name__=='__main__':main()
