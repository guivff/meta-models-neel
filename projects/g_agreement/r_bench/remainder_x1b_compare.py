"""Descriptive cross-runtime capture comparison; never supplies intervention states."""
from pathlib import Path
import argparse
import numpy as np
from projects.g_agreement.r_bench import remainder_x1b as D


def metrics(a,b,name):
    a=np.asarray(a,dtype=np.float64);b=np.asarray(b,dtype=np.float64)
    if a.shape!=b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():raise ValueError('Invalid comparison vector: '+name)
    na=np.linalg.norm(a);nb=np.linalg.norm(b)
    if na==0 or nb==0:raise ValueError('Zero comparison vector: '+name)
    return {'cosine':float(np.dot(a.ravel(),b.ravel())/(na*nb)), 'relative_l2':float(np.linalg.norm(b-a)/na)}


def compare(old,new,manifest,plan):
    old=Path(old);new=Path(new);manifest=Path(manifest)
    if D.sha(manifest)!=D.read(D.OUT/'capture_reuse.json')['pulled_manifest_sha256']:raise ValueError('Original manifest differs: '+str(manifest))
    files=D.read(manifest)['files'];checks=D.read(new/'checksums.json')
    ids=sorted({p['recipient'] for p in plan['pairs'] if p['split']=='pilot'})
    if len(ids)!=D.PILOT_N:raise ValueError('Pilot recipient count differs: '+str(ids))
    old_encoded=D.read(old/'encoded.json');new_encoded=D.read(new/'encoded.json');rows=[]
    for iid in ids:
        name=iid+'.npz';a=old/name;b=new/name
        entry=[v for k,v in files.items() if k.endswith('/natural/'+name)]
        if len(entry)!=1 or D.sha(a)!=entry[0]['sha256'] or a.stat().st_size!=entry[0]['bytes']:raise ValueError('A100 checksum differs: '+name)
        if D.sha(b)!=checks.get(name):raise ValueError('H100 checksum differs: '+name)
        if old_encoded[iid]!=new_encoded[iid]:raise ValueError('Token/position mismatch: '+iid)
        with np.load(a,allow_pickle=False) as aa,np.load(b,allow_pickle=False) as bb:
            keys=set(aa.files)-{'provenance_json'}
            if keys!=set(bb.files)-{'provenance_json'}:raise ValueError('State keys differ: '+iid)
            for key in sorted(keys):
                rows.append({'item':iid,'state':key,**metrics(aa[key],bb[key],iid+'/'+key),'a100_sha256':D.sha(a),'h100_sha256':D.sha(b),**D.provenance()})
    groups={}
    for key in sorted({r['state'] for r in rows}):
        part=[r for r in rows if r['state']==key]
        groups[key]={metric:{'min':float(np.min(v)), 'median':float(np.median(v)), 'max':float(np.max(v))} for metric in ('cosine','relative_l2') for v in [[r[metric] for r in part]]}
    return {'status':'DESCRIPTIVE','relative_l2_denominator':'A100 norm','selection':'20 frozen pilot recipients, no outcome selection','used_for_layer_choice':False,'rows':rows,'summary':groups,**D.provenance()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--a100',type=Path,required=True);p.add_argument('--h100',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    with D.write_guard(paths=[args.out,args.out.with_name(args.out.name+'.partial')]):
        D.save(args.out,compare(args.a100,args.h100,args.manifest,D.read(D.OUT/'pilot_plan.json')))

if __name__=='__main__':main()
