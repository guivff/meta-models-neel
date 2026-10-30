"""One E94 CPU analysis, committed code required, exclusive output guard."""
import json,subprocess,time
from datetime import datetime,timezone
from collections import Counter
from sources94 import HERE,ROOT,CACHE,read,sha,write,load
from score94 import require,join,summarize

def analyse(rows):
    results={'experiment':'E94','descriptive':True,'no_new_readouts':True,'no_judging':True,'banks':{},'raw_categories':dict(Counter(r['bank']+'|'+r['reader']+'|'+r['raw_category'] for r in rows)), 'both_value_records':dict(Counter(r['bank']+'|'+r['reader'] for r in rows if r['both_values']))}
    pool=[]
    for bank in sorted({r['bank'] for r in rows}):
        mine=[r for r in rows if r['bank']==bank];paired,audit=join(mine)
        results['banks'][bank]={'pairing':audit,'metrics':summarize(paired),'strata':{}}
        for stratum in sorted({r['stratum'] for r in mine}):
            ps,au=join([r for r in mine if r['stratum']==stratum]);results['banks'][bank]['strata'][stratum]={'pairing':au,'metrics':summarize(ps)}
        if not bank.startswith('E67') and bank!='E76':pool+=paired
        if bank.startswith('E67'):results['banks'][bank]['interpretation']='CLAIM-LEVEL DIAGNOSTIC ONLY: identical supported class does not establish same judged value; excluded from H-A1.'
    results['pooled_value_grounded']=summarize(pool)
    results['pooling']='micro-average common-parseable value-bank units; E67 incompatible claim rubric separate, E76 placebo separate; no double counting E67 resampled E56/E57 originals in H-A1'
    return results

def main():
    started=time.monotonic();seal=read(HERE/'CODE_SEAL.json')
    for name,digest in seal['files'].items():
        require(sha(HERE/name)==digest,'code/plan drift')
        path=str((HERE/name).relative_to(ROOT));require(subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)==(HERE/name).read_bytes(),'commit before run')
    require(read(HERE/'E67_SCOPE.json')['status']=='RATIFIED','E67 class/scope ruling pending; do not consume once guard')
    plan=read(HERE/'INPUT_PLAN.json');require(sha(plan['private_sources'])==plan['private_sources_sha256'],'source ledger pin');data=read(plan['private_sources'])
    for path,digest in data['files'].items():require(sha(path)==digest,'source drift: '+path)
    # No categories have been loaded yet. Claim once before the first outcome join.
    out=HERE/'analysis_once_20261028';out.mkdir(exist_ok=False)
    write(out/'ONCE.json',{'experiment':'E94','created_utc':datetime.now(timezone.utc).isoformat(),'code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'input_plan_sha256':sha(HERE/'INPUT_PLAN.json'),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'invocations':1})
    rows=load(data);results=analyse(rows);results.update(unavailable=data['unavailable'],wall_seconds=time.monotonic()-started)
    # Private item classes retained for audit/reproduction only in cache; no text copied.
    private=CACHE/'ITEM_CLASSES.PRIVATE.json';require(not private.exists(),'existing private outcome artifact');write(private,rows);private.chmod(0o600)
    write(out/'RESULTS.json',results)
    lines=['# E94 reader agreement','','CPU only; no new readouts or judgments. Conditional precision excludes both-no-mention agreements. All comparisons use the same common-parseable items; missing and unmatched counts are in RESULTS.json. E67 is a separate claim diagnostic, not shared-value agreement.','','| Bank | Paired n | Agreement | Correct given decisive agreement | Ensemble coverage | Oracle accuracy | NLA accuracy |','|---|---:|---:|---:|---:|---:|---:|']
    blocks={k:v['metrics'] for k,v in results['banks'].items()};blocks['POOLED value-grounded']=results['pooled_value_grounded']
    for bank,m in blocks.items():
        fmt=lambda x:'N/E' if x is None else f'{x:.4f}'
        lines.append('| '+bank+' | '+str(m['n'])+' | '+' | '.join(fmt(v) for v in [m['agreement']['rate'],m['P_correct_given_agree_both_mention']['rate'],m['ensemble']['coverage']['rate'],m['readers']['oracle']['marginal_accuracy']['rate'],m['readers']['nla']['marginal_accuracy']['rate']])+' |')
    h=results['pooled_value_grounded']['H_A1'];lines+=['',f"H-A1 (pre-stated hypothesis, not a decision rule): **{h['status']}**, difference {h['difference']}; descriptive paired cluster-bootstrap 95% CI {h['CI95']}.",'','Unavailable paired banks:']+[f'- {k}: {v}' for k,v in data['unavailable'].items()]
    lines+=['','Per-bank/stratum confusion matrices, who is right on disagreements, reader precision/coverage, Wilson intervals and denominator audits are in RESULTS.json. Provisional scoring conventions and the incompatible E67 rubric are documented in METHOD.20261028.md. No sealed bank verdict is modified.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    write(out/'ANALYSIS_SEAL.json',{'experiment':'E94','status':'COMPLETE_ONCE','code_seal_sha256':sha(HERE/'CODE_SEAL.json'),'input_plan_sha256':sha(HERE/'INPUT_PLAN.json'),'item_classes_private_sha256':sha(private),'files':{n:sha(out/n) for n in ('RESULTS.json','REPORT.md','ONCE.json')}})
    print(json.dumps({'status':'COMPLETE_ONCE','bank_n':{k:v['metrics']['n'] for k,v in results['banks'].items()},'H_A1':h,'seal_sha256':sha(out/'ANALYSIS_SEAL.json')}))
if __name__=='__main__':main()
