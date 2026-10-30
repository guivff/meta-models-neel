"""CPU finalization of the fixed E106 dev dataset after sealed NLA gate/teachers."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from .production import verified_gate
from projects.g_agreement.e96.reconstructor_check import write,digest
from projects.g_agreement.e96.prepare_smoke_inputs import verify


def finalize(selection,teachers,gate,out,manifest):
    if out.exists():raise FileExistsError(out)
    verified_gate(gate);verify(selection,'INPUT_SEAL.json');verify(teachers,'OUTPUT_SEAL.json')
    seal=json.loads((teachers/'OUTPUT_SEAL.json').read_text())
    if seal['gate_seal_sha256']!=digest(gate/'OUTPUT_SEAL.json') or seal['input_seal_sha256']!=digest(selection/'INPUT_SEAL.json'):raise ValueError('teacher lineage')
    report=json.loads((teachers/'REPORT.json').read_text())
    if report['status']!='COMPLETE' or report['items']!=252 or report['reader']!='nla' or report['original_adapter_sha256']!='b54e23e4e36dbd04023b307e3abfd4618b5db2b31b8e7c650a957ebb1c90c358':raise ValueError('complete original-NLA dev teachers')
    if report['decoding']!={'do_sample':False,'batch':8,'max_new_tokens':512,'stop':'</explanation>'}:raise ValueError('frozen teacher decoding')
    pairs=json.loads((selection/'DEV_PAIRS.json').read_text());a=np.load(selection/'acts42.npy',allow_pickle=False)
    if len(pairs)!=504 or a.shape!=(504,5120) or not np.isfinite(a).all() or any(p['split']!='dev' for p in pairs) or len({p['key'] for p in pairs})!=504:raise ValueError('504unique dev vectors')
    targets={p['key'] for p in pairs if p['role']=='target'};replay={p['key'] for p in pairs if p['role']=='replay'}
    if len(targets)!=252 or len(replay)!=252 or targets&replay:raise ValueError('equal disjoint target/replay inventory')
    records=[r for f in sorted(teachers.glob('TEACHER_*.json')) for r in json.loads(f.read_text())]
    if len(records)!=252 or {r['key'] for r in records}!=replay or any(r['split']!='dev' or r['role']!='replay' or not isinstance(r.get('raw'),str) or not r['raw'] for r in records):raise ValueError('exact252dev replay teacher texts; no test substitution')
    lookup={r['key']:r['raw'] for r in records};training=[]
    for p in pairs:
        text='<explanation>\n'+p['text']+'\n</explanation>' if p['role']=='target' else lookup[p['key']]
        training.append({'key':p['key'],'split':'dev','role':p['role'],'text':text})
    out.mkdir(parents=True);write(out/'TRAINING.json',training);np.save(out/'acts42.npy',a,allow_pickle=False)
    write(out/'INPUT_SEAL.json',{'status':'FINAL_DEV_TRAINING_DATASET_READY','files':{p.name:digest(p) for p in sorted(out.iterdir())},'gate_seal_sha256':digest(gate/'OUTPUT_SEAL.json'),'teacher_output_seal_sha256':digest(teachers/'OUTPUT_SEAL.json'),'selection_seal_sha256':digest(selection/'INPUT_SEAL.json')})
    write(manifest,{'experiment':'E106','reader':'nla','status':'FINAL_DEV_TRAINING_DATASET_READY','input_seal_sha256':digest(out/'INPUT_SEAL.json'),'directory':str(out.resolve()),'target_items':252,'replay_items':252,'dev_only':True,'test_optimizer_items':0,'files':json.loads((out/'INPUT_SEAL.json').read_text())['files'],'gate_seal_sha256':digest(gate/'OUTPUT_SEAL.json'),'teacher_output_seal_sha256':digest(teachers/'OUTPUT_SEAL.json'),'first_output_utc':report['first_output_utc']})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('selection','teachers','gate','out','manifest'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();finalize(**vars(a))
