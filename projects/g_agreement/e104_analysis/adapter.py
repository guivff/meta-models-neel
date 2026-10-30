"""E104 committed-source gate, sealed acquisition join and once-only inference."""
import argparse,hashlib,json,math,subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from .rules import ROWS,ARMS,analyze
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
require,read,sha,write=core.require,core.read,core.sha,core.write
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e104/ANALYSIS_ONCE.json')

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'changed pinned dependency '+name)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(blob).hexdigest()==sha(p),'uncommitted adapter '+p.name)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def dose(path,commit,digest):
    p=Path(path).resolve();require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'full dose commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==digest==sha(p),'committed dev-only dose identity')
    d=json.loads(blob);require(d['experiment']=='E104' and d['dev_count']==84 and d['seed']==20261029,'registered dev dose policy')
    selected=d['selected_doses'];validate_doses(selected);return selected

def validate_doses(selected):
    require(set(selected)=={f'{a}:{r}' for a in ARMS for r in ROWS},'four arm/row dose receipts')
    for key,v in selected.items():
        grid=(.5,1.,2.,4.,8.) if key.startswith('U:') else (.5,1.,2.,4.)
        counts=v['target_side_counts'];require(set(counts)=={str(x) for x in grid},'exact per-arm dose grid')
        require(all(type(n) is int and 0<=n<=84 for n in counts.values()),'84 dev flip counts')
        chosen=next((a for a in grid if counts[str(a)]/84>=.70),None)
        require(v['alpha']==chosen,'smallest eligible dev dose')

def inputs(s):
    selected=dose(s['dose_path'],s['dose_commit'],s['dose_sha256'])
    p=Path(s['input_seal']);seal=core.verify(p,s['input_sha256'])
    require(seal['experiment']=='E104' and seal['status']=='COMPLETE' and seal['labels_cpu_only'] is True and seal['dose_sha256']==s['dose_sha256'],'complete CPU acquisition bundle')
    require(seal['random_seed']==20261029 and seal['read_block']==44 and seal['reader']=='oracle','registered reader/seed')
    require(seal['U_hook']==dict(block=40,positions='eight_before_read',read_token_untouched=True) and seal['N_hook']==dict(block=44,positions='read_token',renormalized=True,random_renormalized=True),'registered arm hooks')
    require('RECORDS.json' in seal['files'],'sealed record index')
    sources=seal['source_seals'];ss=[core.verify(x['seal'],x['sha256']) for x in sources]
    records=read(p.parent/'RECORDS.json');core.unique(records);seen=set()
    for x in records:
        require(x['arm'] in ARMS and x['row'] in ROWS and x['reader']=='oracle' and x['split']=='test' and x['condition'] in ('steered','random'),'registered cells')
        require(x['alpha'] is not None and x['alpha']==selected[f'{x["arm"]}:{x["row"]}']['alpha'],'selected dev dose only')
        require(x['target'] in ('A','B') and set(x['values'])=={'A','B'} and x['contrast_target_sign'] in (-1,1),'CPU other-value orientation')
        require(set(x['measurements'])=={'text','pair_scores','norm_ratio','read_norm_ratio'},'exact raw measured fields')
        for field,ref in x.pop('measurements').items():
            require(field not in x,'measurements cannot be supplied twice')
            ix=ref['seal_index'];require(ref['member'] in ss[ix]['files'],'measurement member sealed')
            v=read(Path(sources[ix]['seal']).parent/ref['member'])
            for k in ref['keys']:v=v[k]
            x[field]=v
        require(isinstance(x['text'],str),'reader text')
        pairs=x.pop('pair_scores');require(pairs and all(len(v)==2 and all(math.isfinite(q) for q in v) for v in pairs),'finite registered behaviour pairs')
        # Binding names the frozen scorer. No first-token/full-sequence substitution.
        require(x['behaviour_scorer_sha256'] and x['candidate_count']==len(pairs),'frozen behaviour scorer/pair count')
        contrast=sum(a-b for a,b in pairs)/len(pairs);x['flipped']=contrast*x['contrast_target_sign']>0;x['contrast']=contrast
        for field in ('norm_ratio','read_norm_ratio'):require(math.isfinite(x[field]) and x[field]>0,'finite norm ratio')
        key=(x['arm'],x['row'],x['item_id'],x['condition']);require(key not in seen,'duplicate test cell');seen.add(key)
    for arm in ARMS:
        for row in ROWS:
            xs=[x for x in records if x['arm']==arm and x['row']==row]
            if selected[f'{arm}:{row}']['alpha'] is None:require(not xs,'no-dose arm must not produce test cells');continue
            st={x['item_id'] for x in xs if x['condition']=='steered'};ra={x['item_id'] for x in xs if x['condition']=='random'}
            require(len(xs)==168 and len(st)==84 and st==ra,'full84 paired test grid')
    return records,selected

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['export','analyze']);p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=read(a.spec);rows,selected=inputs(s)
    if a.action=='export':core.export(rows,s['blind'],s['private'],s['input_sha256'],commit);return
    scored,jhash=core.load_codes(dict(s,output_sha256=s['input_sha256'])) if rows else ([],None)
    original=core.unique(rows)
    require(set(original)=={x['id'] for x in scored},'exact judged grid')
    merged=[]
    for x in scored:
        o=original[x['id']];require({'id','item_id','arm','row','condition','text','target','values'}<=set(x),'private identity fields')
        require(set(x)<=set(o)|{'opaque_id','score','redacted'},'unexpected private fields')
        require(all(x[k]==o[k] for k in set(x)&set(o)),'private/acquisition mismatch')
        merged.append(dict(o,score=x['score'],redacted=x['redacted']))
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['input_sha256']),commit)
    result=analyze(merged,selected);write(out/'RESULTS.json',result)
    write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E104',status='COMPLETE_ONCE',code_commit=commit,judgment_sha256=jhash,input_sha256=s['input_sha256'],dose_sha256=s['dose_sha256'],authority='5e075c6a')
if __name__=='__main__':main()
