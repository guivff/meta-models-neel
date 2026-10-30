"""E108 sealed normalized source joins; no generation, judging or prior analysis replay."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import analyze
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,write,sha=core.require,core.read,core.write,core.sha
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e108/ANALYSIS_ONCE.json')

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'changed dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest()==sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit']
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'full inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed inventory')
    inv=core.verify(ip,s['inventory_sha256']);require(inv['experiment']=='E108','inventory experiment')
    require('INVENTORY.json' in inv['files'],'inventory member')
    metadata=read(ip.parent/'INVENTORY.json');by=core.unique(metadata)
    from .rules import CATEGORIES,ARMS
    native=[x for x in metadata if x['kind']=='native'];placebo=[x for x in metadata if x['kind']=='placebo']
    require(len(native)==1008 and len(placebo)==84,'1008 prompts plus84 placebo vectors')
    for cat in CATEGORIES:
        sets=[]
        for arm in ARMS:
            xs=[x for x in native if x['category']==cat and x['arm']==arm]
            require(len(xs)==42 and len({x['prompt_id'] for x in xs})==42,'42 prompts per category-arm')
            sets.append({x['prompt_id'] for x in xs})
        require(sets[0]==sets[1],'same42 prompts in both arms')
    require(all(x['category'] in CATEGORIES and x['arm'] in ARMS for x in native),'exact category-arm grid')
    op=Path(s['output_seal']);seal=core.verify(op,s['output_sha256'])
    require(seal['experiment']=='E108' and seal['status']=='COMPLETE' and seal['inventory_sha256']==s['inventory_sha256'],'complete bound bank')
    require(seal['route_verified'] is True and seal['redaction_audit_complete'] is True and seal['ground_truth_blind'] is True,'route/privacy/blind ground truth')
    require(seal['outside_generation']==dict(model='google/gemini-3.1-flash-lite',provider='google-vertex/global',temperature=0,max_tokens=256,ZDR=True,data_collection='deny',fallbacks=False),'E107 outside route')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources]
    require('MEASUREMENTS.json' in seal['files'],'sealed measurement pointers')
    measurements=core.unique(read(op.parent/'MEASUREMENTS.json'));require(set(measurements)==set(by),'exact full inventory')
    cache={}
    def resolve(ref):
        ix=ref['seal_index'];require(type(ix) is int and 0<=ix<len(ss),'source index')
        require(ref['member'] in ss[ix]['files'],'sealed original source')
        key=(ix,ref['member'])
        if key not in cache:cache[key]=read(Path(sources[ix]['seal']).parent/ref['member'])
        value=cache[key]
        for k in ref['keys']:value=value[k]
        return value
    items=[];floors=[]
    for ident,meta in by.items():
        data={k:resolve(v) for k,v in measurements[ident]['fields'].items()}
        require(set(data)==({'hits','ground_truth','J_fraction','choice_token_offset'} if meta['kind']=='native' else {'hits'}),'exact source fields')
        hits=data['hits'];require(set(hits)==({'oracle','nla','outside'} if meta['kind']=='native' else {'oracle','nla'}),'full scored system grid')
        require(all(v is None or type(v) is bool for v in hits.values()),'yes/no/missing; no guessed coding')
        if meta['kind']=='placebo':floors.append(dict(meta,hits=hits));continue
        gt=data['ground_truth'];require(gt['status'] in ('ONE','NONE','MULTIPLE','UNPARSEABLE'),'ground truth disposition')
        require((isinstance(gt['canonical_member'],str) and bool(gt['canonical_member'])) if gt['status']=='ONE' else gt['canonical_member'] is None,'canonical chosen member')
        j=data['J_fraction'];require(j is None or type(j) in (int,float) and 0<=j<=1,'J fraction in unit interval')
        offset=data['choice_token_offset'];require(offset is None or type(offset) is int and offset>=0,'choice emission offset')
        items.append(dict(meta,choice_status=gt['status'],choice=gt['canonical_member'],J_fraction=j,hits=hits,choice_token_offset=offset))
    return items,floors

def first_output_provenance(path):
    from datetime import datetime, timezone
    p=Path(path);ns=p.stat().st_mtime_ns
    return dict(first_output_utc=datetime.fromtimestamp(ns/1e9,timezone.utc).isoformat(),
                first_output_evidence=dict(member=p.name,sha256=sha(p),mtime_ns=ns))

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=read(a.spec);items,floors=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    result=analyze(items,floors)
    result['delayed_offset_check']=dict(under3=sum(x['arm']=='delayed' and x['choice_status']=='ONE' and x['choice_token_offset'] is not None and x['choice_token_offset']<3 for x in items),missing=sum(x['arm']=='delayed' and x['choice_status']=='ONE' and x['choice_token_offset'] is None for x in items),action='reported; no unregistered exclusion')
    write(out/'RESULTS.json',result);write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E108',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'],inventory_sha256=s['inventory_sha256'],**first_output_provenance(out/'RESULTS.json'))
if __name__=='__main__':main()
