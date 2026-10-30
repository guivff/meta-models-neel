"""Judge-independent one-fit E137 probes, then immutable reuse in the main run."""
import argparse
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from . import adapter as a,probes
core=a.core;REQ=a.REQ


def paths():return a.GUARD.with_name('PROBES_ONCE.json'),a.GUARD.parent/'probes_once'


def available():
    guard,out=paths();REQ(not guard.exists()or(out/'ANALYSIS_SEAL.json').exists(),'probe phase in progress/failed; no second fit or guard reset')


def existing(inventory_sha,native_sha):
    guard,out=paths()
    if not guard.exists():return None
    available();s=core.verify(out/'ANALYSIS_SEAL.json',core.sha(out/'ANALYSIS_SEAL.json'))
    REQ(s['experiment']=='E137'and s['analysis_component']=='PROBES'and s['status']=='COMPLETE_ONCE'and s['inventory_sha256']==inventory_sha and s['native_output_sha256']==native_sha,'same frozen E137 inventory/native capture only')
    return core.read(out/'PROBE_RESULTS.json')


def native_metadata(spec):
    inv=core.read(spec['inventory_seal']);REQ(inv['native_output_sha256']==spec['native_output_sha256'],'same inventory-bound original native seal')
    seal=core.verify(spec['native_output_seal'],spec['native_output_sha256'])
    REQ(seal['experiment']=='E137'and seal['status']=='COMPLETE'and seal['labels_cpu_only']is True and seal['stages']['main_synthetic']=='COMPLETE','original complete E137 native main, no planning/partial')
    REQ('main_synthetic/INDEX.json'in seal['files'],'original native capture index')
    return seal


def native_vectors(spec,pairs,seal):
    """Literal sealed E133-runner INDEX pointers; no oracle/patch/judgment reads."""
    root=Path(spec['native_output_seal']).parent;prefix='main_synthetic/'
    index=core.read(root/(prefix+'INDEX.json'));rows=[x for x in index if x['kind']=='capture_answer'];by=core.unique(rows,'id')
    REQ(len(rows)==len(by)==2*len(pairs)and set(by)=={m['item_id']for p in pairs for m in p['members']},'all and only frozen original member captures')
    cache={};result=[]
    def member(name):
        name=prefix+name;REQ(name in seal['files'],'original capture member in outer E137 seal')
        if name not in cache:
            path=root/name;cache[name]=np.load(path,allow_pickle=False)if path.suffix=='.npy'else core.read(path)
        return cache[name]
    for pair in pairs:
        ms=[]
        for label in pair['members']:
            x=by[label['item_id']];record=member(x['member'])[x['record']]
            REQ(record['id']==label['item_id']and record['pair_id']==pair['pair_id']and record['member']==label['member']and record['family']==('one_hop'if pair['kind']=='one_hop'else'multi_hop'),'literal native pair/member/family role identity')
            REQ(set(x['layers'])=={str(l)for l in probes.LAYERS},'all6 original capture blocks')
            vv={}
            for l in probes.LAYERS:
                ptr=x['layers'][str(l)];array=member(ptr['member']);j=ptr['index']
                REQ(type(j)is int and array.ndim==2 and 0<=j<len(array)and array.dtype==np.float32,'literal original fp32 vector index')
                vector=array[j];REQ(np.isfinite(vector).all(),'finite original activation; no imputation')
                vv[l]=vector.astype(float).tolist()
            ms.append(dict(item_id=label['item_id'],member=label['member'],current=label['current'],previous=label['previous'],vectors=vv))
        result.append(dict(pair_id=pair['pair_id'],kind=pair['kind'],generation_index=pair['generation_index'],members=ms))
    return result


def fit(pairs,names,audit=None):
    result={};controls=[p for p in pairs if p['kind']=='one_hop']
    for design in('D1','D2'):
        xs=[p for p in pairs if p['kind']==design];view=deepcopy(xs+controls)
        for p in view:
            if p['kind']==design:p['kind']='multi_hop'
        private=[];report=probes.analyze(view,names,audit=private)
        if audit is not None:
            for record in private:record['subdesign']=design;audit.append(record)
        result[design]=dict(n_pairs=len(xs),eligible=len(xs)>=30,scope='D1 R-NL2 eligibility retained; probes do not enter R-NL2'if design=='D1'else'DESCRIPTIVE ONLY',probes=report)
    return dict(experiment='E137',analysis_component='PROBES',subdesigns=result,rule='unchanged first30 per-design DEV, remainder TEST; insufficient DEV remains NOT EVALUABLE; no alternative split',new_calls=0)


def claim(spec,commit):
    guard,out=paths();out=core.claim(dict(analysis=str(out),guard=str(guard),output_sha256=spec['native_output_sha256']),commit)
    core.write(out/'FIRST_OPENING.json',dict(utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,inventory_sha256=spec['inventory_sha256'],native_output_sha256=spec['native_output_sha256'],stage='before first vector loading/fit; metadata schema already inspected'))
    return out


def finish(spec,commit,out,pairs,names):
    audit=[];result=fit(pairs,names,audit);core.write(out/'PROBE_RESULTS.json',result);core.write(out/'BINDING.json',spec)
    private=out/'FIT_EVIDENCE.PRIVATE.json';core.write(private,audit);private.chmod(0o600)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E137',analysis_component='PROBES',status='COMPLETE_ONCE',source_commit=commit,inventory_sha256=spec['inventory_sha256'],native_output_sha256=spec['native_output_sha256'],private_sha256=core.sha(private),new_calls=0)
    return result


def ensure(spec,commit,pairs,names):
    prior=existing(spec['inventory_sha256'],spec['native_output_sha256'])
    if prior is not None:return prior
    out=claim(spec,commit);return finish(spec,commit,out,pairs,names)


def run(spec,commit):
    REQ(not paths()[0].exists(),'probe once guard consumed; no replay')
    pairs,names=a.metadata(spec);seal=native_metadata(spec);out=claim(spec,commit)
    vectors=native_vectors(spec,pairs,seal);finish(spec,commit,out,vectors,names)
    return out/'ANALYSIS_SEAL.json'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--spec',required=True);args=parser.parse_args();commit=a.committed();print(run(core.read(args.spec),commit))
if __name__=='__main__':main()
