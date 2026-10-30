"""§224 E111: exactly two E109 unhooked-dev block44 probe fits. CPU only.
Reuses E109's fixed fit function. Never opens test captures or reader judgments.
"""
import hashlib,json,os,platform,subprocess,time
from pathlib import Path
import numpy as np
from projects.g_agreement.e109_analysis.analysis import fit
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[4]
ROWS=('fact_recall','language_plan')
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
def select(index,inventory,row):
    m=inventory[row];ids=m['dev_ids'];labels=m['dev_labels']
    assert len(ids)==len(set(ids))==len(labels)==84 and set(ids).isdisjoint(m['test_ids'])
    assert labels.count(0)==labels.count(1)==42
    selected=[x for x in index if x['row']==row and x['split']=='dev' and x['condition']=='unhooked']
    by={x['base_id']:x for x in selected}
    assert len(selected)==len(by)==84 and set(by)==set(ids),'exact original unhooked84 dev ids'
    return [by[i] for i in ids],np.array(labels,dtype=int)
def dump_probe(path,model):
    np.savez(path,w=model.coef_[0],b=model.intercept_[0],classes=model.classes_,n_iter=model.n_iter_)
def main():
    start=time.monotonic();p=read(HERE/'FIT_PLAN.json')
    for f,h in p['pins'].items():assert sha(f)==h,f
    for f in [HERE/'fit_probes.py',HERE/'FIT_PLAN.json']:
        blob=subprocess.check_output(['git','show','HEAD:'+str(f.relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest()==sha(f),'commit plan/code before fit'
    root=Path(p['capture_root']);seal=read(root/'OUTPUT_SEAL.json')
    assert seal['experiment']=='E109' and seal['status']=='COMPLETE' and sha(root/'OUTPUT_SEAL.json')==p['capture_seal_sha256']
    for n,h in seal['files'].items():assert sha(root/n)==h,'sealed original member '+n
    invseal=read(p['inventory_seal']);assert sha(Path(p['inventory_seal']).parent/'INVENTORY.json')==invseal['files']['INVENTORY.json']
    inv=read(Path(p['inventory_seal']).parent/'INVENTORY.json');index=read(root/'CAPTURE_INDEX.json')
    selected={r:select(index,inv,r) for r in ROWS};cache={};data={};bindings={}
    for row,(items,y) in selected.items():
        vectors=[];refs=[]
        for x in items:
            ref=x['layers']['44'];meta=x['metadata'];job=read(root/meta['member'])[meta['record_index']]
            assert all(job[k]==x[k] for k in ('id','base_id','row','split','condition'))
            assert job['hook_installed'] is False and job['injection_sites']==[],'actually unhooked dev'
            assert job['read_index']>=0
            name=ref['member'];assert name in seal['files'] and meta['member'] in seal['files']
            if name not in cache:cache[name]=np.load(root/name,allow_pickle=False)
            a=cache[name];assert a.dtype==np.float32 and a.ndim==2 and a.shape[1]==5120
            vectors.append(a[ref['vector_index']]);refs.append(dict(base_id=x['base_id'],capture_id=x['id'],member=name,sha256=seal['files'][name],vector_index=ref['vector_index'],metadata_member=meta['member'],metadata_sha256=seal['files'][meta['member']],record_index=meta['record_index'],read_index=job['read_index']))
        a=np.stack(vectors);assert a.shape==(84,5120) and np.isfinite(a).all();data[row]=(a,y);bindings[row]=refs
    output=HERE/'weights';assert not output.exists()
    guard=ROOT/'cache/g_agreement/understand/e111/e109_dev44/ONCE.json';guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:json.dump(dict(plan_sha256=sha(HERE/'FIT_PLAN.json')),f)
    output.mkdir(exist_ok=False);models=[]
    for row in ROWS:
        x,y=data[row];model=fit(x,y) # one unmodified E109 fit per row, no held-out/outcome evaluation
        assert model.coef_.shape==(1,5120) and model.classes_.tolist()==[0,1] and np.isfinite(model.coef_).all()
        dest=output/(row+'_probe.npz');dump_probe(dest,model)
        ids=inv[row]['dev_ids'];labeljoin=[dict(id=i,label=int(v)) for i,v in zip(ids,y)]
        models.append(dict(row=row,origin='E109',e109_probe_available=True,block=44,fit_split='unhooked_dev',test_used_for_fit=False,positive_class=1,classes=[0,1],class_letter_mapping={'0':'B','1':'A'},preprocessing='none',feature_scale=None,weights_path=str(dest),weights_sha256=sha(dest),coefficient_array='w',intercept_array='b',coefficients_sha256=digest(model.coef_[0].tolist()),dev_ids=ids,n_dev=84,n_per_class={'0':42,'1':42},labels_order_sha256=digest(labeljoin),training_source_sha256=digest(bindings[row]),recipe_sha256=sha(ROOT/'projects/g_agreement/e109_analysis/analysis.py'),fit_parameters=model.get_params(),n_iter=model.n_iter_.tolist()))
    private=guard.parent/'DEV_BINDINGS.PRIVATE.json';write(private,dict(label_order={r:[dict(id=i,label=y) for i,y in zip(inv[r]['dev_ids'],inv[r]['dev_labels'])] for r in ROWS},capture_refs=bindings))
    import sklearn
    write(HERE/'PROBE_MANIFEST.json',dict(experiment='E111',source_experiment='E109',status='COMPLETE_ONCE',capture_seal_sha256=sha(root/'OUTPUT_SEAL.json'),inventory_seal_sha256=sha(p['inventory_seal']),plan_sha256=sha(HERE/'FIT_PLAN.json'),probes=models,private_training_binding_path=str(private),private_training_binding_sha256=sha(private),fit_count=2,scaling='none; raw coefficient w, no sd',bootstrap_or_test_statistics=False,python=platform.python_version(),sklearn=sklearn.__version__,numpy=np.__version__,wall_seconds=time.monotonic()-start,gpu_hours=0))
    write(HERE/'PROBE_SEAL.json',dict(experiment='E111',status='COMPLETE_ONCE',source_experiment='E109',files={str(f.relative_to(HERE)):sha(f) for f in [HERE/'PROBE_MANIFEST.json',HERE/'FIT_PLAN.json',HERE/'fit_probes.py',*output.iterdir()]}))
    print(json.dumps({x['row']:x['weights_sha256'] for x in models},indent=2))
if __name__=='__main__':main()
