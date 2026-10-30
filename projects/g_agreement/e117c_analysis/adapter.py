"""Prospective E117 part c CPU binding; never executes the original E117 grid."""
import argparse,hashlib,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core as c
from .analysis import ROWS,ARMS,extract,summarize,readings,fact_control
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e117/part_c/ANALYSIS_ONCE.json'


def inputs(s):
    ip=Path(s['inventory_seal']).resolve()
    c.require(hashlib.sha256(subprocess.check_output(['git','show',s['inventory_commit']+':'+str(ip.relative_to(ROOT))],cwd=ROOT)).hexdigest()==s['inventory_sha256'],'committed pre-output inventory seal')
    inv=c.verify(ip,s['inventory_sha256'])
    c.require(inv['experiment']=='E117' and inv['part']=='c' and inv['block']==44 and inv['reader']=='oracle' and inv['arms']==list(ARMS) and inv['items']==336,'registered part-c inventory')
    meta=c.unique(c.read(ip.parent/'INVENTORY.json'))
    c.require(len(meta)==336 and all(x['row']in ROWS and x['split']=='test' for x in meta.values()),'original E57 test census')
    c.require(all(sum(x['row']==r for x in meta.values())==84 for r in ROWS),'all84 per row')
    bp=Path(s['binding_seal']);b=c.verify(bp,s['binding_sha256'])
    c.require(b['experiment']=='E117' and b['part']=='c' and b['status']=='COMPLETE' and b['inventory_sha256']==s['inventory_sha256'],'complete part-c binding')
    for k in ('route_verified','privacy_verified','labels_cpu_only','original_E57_rubric_verified','same_E57_activations_and_read_token_verified','registered_targeted_and_sham_prompts_verified','sham_fact_absent_verified','native_Oracle_greedy_verified','source_plan_precedes_output_verified'):
        c.require(b[k]is True,k)
    sources=b['source_seals'];ss=[c.verify(x['seal'],x['sha256'])for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];c.require(type(i)is int and 0<=i<len(ss) and x['member']in ss[i]['files'],'exact sealed source pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=c.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    ms=c.unique(c.read(bp.parent/'MEASUREMENTS.json'));c.require(set(ms)==set(meta),'all and only original source items')
    out=[]
    for ident,m in meta.items():
        x=ms[ident];c.require(ref(x['source_id'])==ident and ref(x['source_row'])==m['row'] and ref(x['source_split'])=='test','original E57 source join')
        gold=ref(x['target_letter']);c.require(gold in ('A','B'),'original E57 true-value letter')
        c.require(set(x['arms'])==set(ARMS),'paired targeted and sham, no skipped cells');arms={}
        for arm,z in x['arms'].items():
            c.require(ref(z['source_id'])==ident and ref(z['arm'])==arm and ref(z['block'])==44,'native item/arm/read-site')
            c.require(ref(z['prompt'])==ref(m['prompts'][arm]),'exact frozen question prompt')
            text=ref(z['text']);code=ref(z['code'])
            c.require(code is None or code['id']==z['judgment_id'],'original rubric code identity')
            score=None if code is None else c.score(code,gold,text)
            arms[arm]=dict(score=score,yes=None if code is None or code['category']=='UNPARSEABLE' else extract(text))
        out.append(dict(id=ident,row=m['row'],arms=arms))
    return out


def committed():
    for f,h in c.read(HERE/'SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/f)==h and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)).hexdigest()==h,'committed source receipt')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=c.read(a.spec);items=inputs(s)
    summary=summarize(items);rules=readings(summary);control=fact_control(summary['rows']['fact_recall'])
    c.require(Path(s['analysis']).resolve()==GUARD.parent/'analysis_once','fixed separate part-c output')
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',dict(experiment='E117',part='c',status='DESCRIPTIVE',summary=summary,readings=rules,fact_recall_positive_control=control,caveat='Question prompt is outside the reader training distribution'))
    c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E117',part='c',status='COMPLETE_ONCE',code_commit=commit)

if __name__=='__main__':main()
