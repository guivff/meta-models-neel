"""E133 CPU probe-only phase, independent of judge completion; one global fit guard."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from . import adapter as a,probes
core=a.core;REQ=a.REQ


def paths():return a.GUARD.with_name('PROBES_ONCE.json'),a.GUARD.parent/'probes_once'


def available():
    guard,out=paths()
    REQ(not guard.exists()or(out/'ANALYSIS_SEAL.json').exists(),'probe phase in progress/failed; no second fit or guard reset')


def existing(inventory_sha,native_sha):
    guard,out=paths()
    if not guard.exists():return None
    available();s=core.verify(out/'ANALYSIS_SEAL.json',core.sha(out/'ANALYSIS_SEAL.json'))
    REQ(s['experiment']=='E133'and s['analysis_component']=='PROBES'and s['status']=='COMPLETE_ONCE'and s['inventory_sha256']==inventory_sha and s['native_output_sha256']==native_sha,'same original screened cohort/native activations; no reused foreign probe')
    return core.read(out/'PROBE_RESULTS.json')


def claim(spec,commit):
    guard,out=paths();out=core.claim(dict(analysis=str(out),guard=str(guard),output_sha256=spec['native_output_sha256']),commit)
    core.write(out/'FIRST_OPENING.json',dict(utc=datetime.now(timezone.utc).isoformat(),code_commit=commit,inventory_sha256=spec['inventory_sha256'],native_output_sha256=spec['native_output_sha256'],stage='probe phase before fit; operator clock only'))
    return out


def finish(spec,commit,out,pairs,names):
    result=probes.analyze(pairs,names);core.write(out/'PROBE_RESULTS.json',result);core.write(out/'BINDING.json',spec)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E133',analysis_component='PROBES',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=spec['inventory_sha256'],native_output_sha256=spec['native_output_sha256'],new_calls=0)
    return result


def ensure(spec,commit,pairs,names):
    """Full analysis reuses an earlier completed fit, or claims the SAME probe-only guard."""
    prior=existing(spec['inventory_sha256'],spec['native_output_sha256'])
    if prior is not None:return prior
    out=claim(spec,commit);return finish(spec,commit,out,pairs,names)


def vector_metadata(spec):
    s=core.verify(spec['probe_input_seal'],spec['probe_input_sha256'])
    REQ(s['experiment']=='E133'and s['status']=='COMPLETE'and s['labels_cpu_only']is True and s['inventory_sha256']==spec['inventory_sha256']and s['layers']==list(probes.LAYERS),'complete original frozen probe cohort and all6sites')
    REQ(s['native_output_sha256']==spec['native_output_sha256']and any(x['sha256']==spec['native_output_sha256']for x in s['source_seals']),'original COMPLETE native activation source')
    for x in s['source_seals']:
        original=core.verify(x['seal'],x['sha256']);REQ(original['experiment']=='E133'and original['status']in('COMPLETE','COMPLETE_ONCE'),'no partial/unrelated activation source')
    return s


def vectors(spec,inventory,s):
    sources=s['source_seals'];seals=[core.verify(x['seal'],x['sha256'])for x in sources];cache={}
    def ref(p):
        i=p['seal_index'];REQ(type(i)is int and 0<=i<len(seals)and p['member']in seals[i]['files'],'original vector/identity pointer')
        key=(i,p['member'])
        if key not in cache:
            file=Path(sources[i]['seal']).parent/p['member'];cache[key]=np.load(file,allow_pickle=False)if file.suffix=='.npy'else core.read(file)
        x=cache[key];REQ(isinstance(p['keys'],list)and all(type(k)in(int,str)for k in p['keys']),'literal original vector keys')
        for k in p['keys']:x=x[k]
        return x
    ms=core.unique(core.read(Path(spec['probe_input_seal']).parent/'VECTORS.PRIVATE.json'),'pair_id');REQ(set(ms)=={p['pair_id']for p in inventory},'all frozen screened pairs, no reader-based selection')
    pairs=[]
    for p in inventory:
        z=ms[p['pair_id']];REQ(len(z['members'])==2,'both original members');members=[]
        for j,(label,m)in enumerate(zip(p['members'],z['members'])):
            vv={};REQ(set(m['vectors'])=={str(l)for l in probes.LAYERS},'all6original activation sites')
            for layer in probes.LAYERS:
                cell=m['vectors'][str(layer)];i=ref(cell['identity'])
                REQ(i['pair_id']==p['pair_id']and i['item_id']==label['item_id']and i['member']==j and i['kind']==p['kind']and i['mode']=='vector'and i['block']==layer,'exact original pair/item/member/site')
                if p['kind']=='babi_qa2':REQ(i['source_episode_id']==p['source_episode_id'],'original QA2 episode')
                v=ref(cell['vector']);vv[layer]=None if v is None else np.asarray(v,dtype=float).tolist()
            members.append(dict(member=j,current=label['current'],previous=label['previous'],vectors=vv))
        pairs.append(dict(pair_id=p['pair_id'],kind=p['kind'],generation_index=p['generation_index'],source_episode_id=p.get('source_episode_id'),members=members))
    return pairs


def run(spec,commit):
    a.protocol();guard,out=paths();REQ(not guard.exists(),'probe once guard consumed; no repeat')
    inventory=a.metadata(spec);s=vector_metadata(spec);out=claim(spec,commit)
    pairs=vectors(spec,inventory['pairs'],s);finish(spec,commit,out,pairs,inventory['fixed_name_list'])
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=a.committed();print(run(core.read(args.spec),commit))

if __name__=='__main__':main()
