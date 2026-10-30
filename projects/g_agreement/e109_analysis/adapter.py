"""Source-pinned CPU E109 once-only transport. Private joins never published."""
import argparse,hashlib,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
from .analysis import analyze,ROWS,LAYERS,READS
from .sensitivity import sensitivity
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e109/ANALYSIS_ONCE.json')
E104_SEAL='01d8d5a17b7bbea1d2df27982ef10c897156093430967d8da442e0a5137cbe1e'
E104_PRIVATE='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4'
REQ=core.require

def committed():
    for p,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/p)==h,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT);REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit'];REQ(len(commit)==40,'full inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'pre-output inventory commitment')
    inv=core.verify(ip,s['inventory_sha256']);REQ(inv['experiment']=='E109','inventory experiment')
    meta=core.read(ip.parent/'INVENTORY.json');REQ(set(meta)==set(ROWS),'both rows')
    ep=Path(s['e104_analysis_seal']);core.verify(ep,E104_SEAL);old=core.read(ep.parent/'RESULTS.json')
    pp=Path(s['e104_private']);REQ(core.sha(pp)==E104_PRIVATE,'original E104 cohort join');prior=core.read(pp)
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    REQ(seal['experiment']=='E109' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete bound E109')
    REQ(seal['route_verified'] is True and seal['privacy_verified'] is True and seal['labels_cpu_only'] is True,'frozen route/privacy')
    REQ(seal['hook']==dict(block=40,positions='eight_before_read',read_token_untouched=True),'E104 U hook')
    REQ(seal['d40_sha256']==inv['d40_sha256'] and seal['d40_sha256'],'original d40 binding')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(ss) and x['member'] in ss[i]['files'],'sealed pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=np.load(p,allow_pickle=False) if p.suffix=='.npy' else core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    ms=core.read(op.parent/'MEASUREMENTS.json');REQ(set(ms)==set(ROWS),'exact measured rows')
    data={}
    for row in ROWS:
        m=meta[row];pr={x['item_id']:x for x in prior if x['arm']=='U' and x['row']==row and x['condition']=='steered'}
        REQ(len(pr)==84 and set(m['test_ids'])==set(pr),'original E104 test items')
        REQ(m['alpha']==(8 if row=='fact_recall' else 2),'sealed dose')
        REQ(len(set(m['dev_ids']))==84 and set(m['dev_ids']).isdisjoint(m['test_ids']),'84 dev only')
        REQ(all(m['target_letters'][j]==pr[i]['target'] for j,i in enumerate(m['test_ids'])),'original CPU target letters')
        REQ(all(m['targets'][j]==(1 if pr[i]['target']=='A' else 0) for j,i in enumerate(m['test_ids'])),'A=1 B=0 target orientation')
        layers={};REQ(set(ms[row])=={str(l) for l in LAYERS},'five layer inventory')
        for l in LAYERS:
            z=ms[row][str(l)];REQ(set(z)==({'dev','test','oracle'} if l in READS else {'dev','test'}),'exact layer fields')
            REQ(set(z['dev'])==set(z['test'])=={'unhooked','steered','random'},'all capture conditions')
            # All dev captures are retained/verified; only unhooked dev is fit.
            dev={c:ref(v) for c,v in z['dev'].items()};test={c:ref(v) for c,v in z['test'].items()}
            REQ(all(np.asarray(x).ndim==2 and len(x)==84 and np.isfinite(x).all() for x in list(dev.values())+list(test.values())),'complete finite capture')
            layer=dict(dev_unhooked=dev['unhooked'],test=test)
            if l in READS:
                REQ(set(z['oracle'])=={'steered','random'},'paired Oracle conditions');scores={}
                for c,refs in z['oracle'].items():
                    REQ(len(refs)==84 and [x['item_id'] for x in refs]==m['test_ids'],'exact original item order')
                    scores[c]=[core.score(ref(x['code']),m['target_letters'][j],ref(x['text'])) for j,x in enumerate(refs)]
                layer['oracle']=scores
            layers[l]=layer
        data[row]=dict(m,cohort=[i for i,x in pr.items() if x['flipped']],layers=layers)
    REQ('redaction_audit' in seal,'original affected-ID audit pointer required')
    audit=ref(seal['redaction_audit']);REQ(audit['all_affected_mapped'] is True and audit['original_text_preserved'] is True,'exact affected-ID/source mapping')
    affected=audit['affected_readouts']
    REQ(len(affected)==seal['redacted_readout_count'],'full redacted record count')
    return data,{r:old['arms']['U'][r]['difference']['estimate'] for r in ROWS},affected

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=committed();s=core.read(args.spec)
    data,old,affected=inputs(s);out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(data,old);core.write(out/'RESULTS.json',result);core.write(out/'REDACTION_SENSITIVITY.json',sensitivity(data,result,old,affected));core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E109',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'],e104_analysis_sha256=E104_SEAL)
if __name__=='__main__':main()
