"""CPU-only sealed adapter primitives; no acquisition imports or calls."""
import hashlib,json,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
DRAWS,SEED=2000,20261027
require,read,write,sha,verify=core.require,core.read,core.write,core.sha,core.verify

def committed():
    for name,digest in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/name)==digest,'dependency changed: '+name)
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            data=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            require(hashlib.sha256(data).hexdigest()==sha(p),'uncommitted adapter '+p.name)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def load(entry,member):
    p=Path(entry['seal']);s=verify(p,entry['sha256'])
    require(member in s['files'],'unsealed requested member')
    return read(p.parent/member),s

def stat(values,other=None):return core.stats(values,other)
def ge(s,v):return None if s['estimate'] is None else round(s['estimate'],12)>=v
def le(s,v):return None if s['estimate'] is None else round(s['estimate'],12)<=v
def low(s,v):return None if s['CI95'] is None else s['CI95'][0]>v
def high(s,v):return None if s['CI95'] is None else s['CI95'][1]<v
def both(*xs):return False if False in xs else None if None in xs else True
def count(xs,n):
    p=sum(x is True for x in xs);u=sum(x is None for x in xs)
    return dict(status='MET' if p>=n else 'NOT EVALUABLE' if p+u>=n else 'NOT MET',passing=p,unknown=u,required=n)
def reserve(experiment,s,commit):
    # Guard is fixed across checkout paths; callers cannot choose a second guard.
    guard=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand')/experiment.lower()/'ANALYSIS_ONCE.json'
    binding=dict(analysis=s['analysis'],guard=str(guard),output_sha256=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest())
    return core.claim(binding,commit)

def finish(experiment,s,commit,result,out,plot=None):
    write(out/'RESULTS.json',result)
    if plot:plot(out)
    write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment=experiment,status='COMPLETE_ONCE',code_commit=commit,bootstrap_draws=DRAWS,seed=SEED)
    return out

def normalized(s,experiment):
    """Versioned CPU normalization contract with exact source references.

    Bundle record metadata must equal the frozen inventory. Each measured value
    must be read verbatim from a verified source seal via an explicit JSON path.
    The adapter, not the normalizer, computes scores and statistics.
    """
    entry=s['inventory'];p=Path(entry['seal']).resolve();commit=s['inventory_commit']
    require(len(commit)==40 and all(c in '0123456789abcdef' for c in commit),'full inventory commit')
    blob=subprocess.check_output(['git','show',commit+':'+str(p.relative_to(ROOT))],cwd=ROOT)
    require(hashlib.sha256(blob).hexdigest()==entry['sha256'],'inventory seal committed before use')
    inventory,inv=load(entry,'INVENTORY.json')
    require(inv.get('experiment')==experiment and inv.get('frozen_before_outputs') is True,'pre-output inventory receipt')
    records,bundle=load(s['data'],'RECORDS.json')
    require(bundle.get('experiment')==experiment and bundle.get('status')=='COMPLETE' and bundle.get('inventory_sha256')==s['inventory']['sha256'],'complete inventory-bound records')
    require(bundle.get('route_verified') is True and bundle.get('redaction_audit_complete') is True,'registered judge/privacy receipt')
    sources=bundle['source_seals'];seals=[verify(x['seal'],x['sha256']) for x in sources]
    expected=core.unique(inventory);actual=core.unique(records)
    require(set(expected)==set(actual),'exact frozen inventory; no subset')
    result=[]
    for identity,meta in expected.items():
        x=actual[identity];require(x['metadata']==meta,'frozen metadata changed')
        if experiment=='E103':fields={'own_response','mismatched_response'}
        elif meta['set']=='workspace':fields={'original_pass','retrained_pass'}
        elif meta['set']=='placebo':fields={a+'_'+f for a in ('original','retrained') for f in ('text','placebo_code')}
        else:fields={a+'_'+f for a in ('original','retrained') for f in ('text','code')}
        require(set(x['measurements'])==fields,'exact measured fields must come from sealed sources')
        values={}
        for field,ref in x['measurements'].items():
            require(field not in meta,'measurement cannot replace frozen metadata')
            ix=ref['seal_index'];require(ref['member'] in seals[ix]['files'],'unsealed measurement')
            value=read(Path(sources[ix]['seal']).parent/ref['member'])
            for key in ref['keys']:value=value[key]
            values[field]=value
        result.append(dict(meta,**values))
    return result,bundle,inv
