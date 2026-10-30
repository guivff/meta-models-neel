"""CPU-only transfer of immutable timings across an admission-only source fix.

No new timing measurement is claimed. Source maps must match in every runtime,
acquisition, scorer, input and dependency member, apart from the explicit cap
arithmetic and this offline helper/tests. Original receipts remain untouched.
"""
import argparse,copy
from pathlib import Path
from .contract import read,write,sha
from .timing import _measured

ALLOWED={f'projects/g_agreement/e101/{n}' for n in (
    'timing.py','test_timing217.py','rebind_timing217.py','test_rebind_timing217.py')}


def transfer(profile,old_source,new_source,out):
    r=read(profile);old=read(old_source);new=read(new_source)
    if r['source_sha256']!=sha(old_source) or old['experiment']!=new['experiment']:
        raise ValueError('original measured source and same experiment required')
    _measured(r)
    if r['status']!='TIMING_ONLY_NOT_SCIENCE' or r['margin']!=1.25:
        raise ValueError('discarded measured profile required')
    changed={p for p in old['files'].keys()|new['files'].keys() if old['files'].get(p)!=new['files'].get(p)}
    if not changed or not changed<=ALLOWED:raise ValueError('source change outside admission-only allowlist')
    owner=read(profile.parent/'ASSIGNMENT.json')
    if (owner['source_sha256']!=r['source_sha256'] or owner['input_sha256']!=r['input_sha256']
        or owner['gpu_type']!=r['gpu_type'] or owner['experiment']!=new['experiment']):
        raise ValueError('original custody experiment/input/source/hardware binding')
    proof=dict(status='CPU_SOURCE_EQUIVALENCE_NOT_NEW_TIMING',original_profile_sha256=sha(profile),
               original_assignment_sha256=sha(profile.parent/'ASSIGNMENT.json'),
               original_source_sha256=sha(old_source),new_source_sha256=sha(new_source),
               changed_source_members=sorted(changed),measurements_unchanged=True,GPU_calls=0)
    derived=copy.deepcopy(r);derived['source_sha256']=sha(new_source);derived['source_rebinding']=proof
    derived_owner=dict(owner,source_sha256=sha(new_source),profile_rebinding='CPU_DERIVED_NOT_POD_ASSIGNMENT')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'MEASURED_PROFILE.json',derived);write(out/'ASSIGNMENT.json',derived_owner)
    write(out/'ORIGINAL_PROFILE.json',r);write(out/'ORIGINAL_ASSIGNMENT.json',owner);write(out/'SOURCE_EQUIVALENCE.json',proof)
    return proof

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('profile','old-source','new-source','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();print(transfer(a.profile,a.old_source,a.new_source,a.out))
