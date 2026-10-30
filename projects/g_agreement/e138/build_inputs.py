"""CPU-only packaging of existing sealed vectors/protocols; never model outputs."""
import json,hashlib,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e138.runner import transform,norm_match,pair_other

def build():
    R=Path(__file__).resolve().parents[3];OUT=R.parent/'outputs/e138-inputs-v1'
    E127=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e127-inputs-v2')
    CAP=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/analysis402_verified/E127/measured_a2/out')
    E100=R/'results/g_agreement/understand/e100/vectors/artifacts'
    def read(p):return json.loads(p.read_text())
    def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    def write(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    def verify(r,n,h):
     assert sha(r/n)==h, str(r/n)
     s=read(r/n)
     for f,v in s['files'].items():assert sha(r/f)==v,'sealed member '+f
     return s
    verify(E127/'inputs','INPUT_SEAL.json','964b5fc3f7e9e638496b987207cb8eb2ea6af7c54018b764c35452ea5b8462dd')
    verify(E127/'cpu_only','LABEL_SEAL.json','549fa110f6f0f0276dda18b428b26de9c921e9fd97bced195f754a017ebe99c0')
    cs=verify(CAP,'OUTPUT_SEAL.json','a30e638090bbd6b8a90f98153c5a153363f05b06d62672c4a42304a13f914d78');assert cs['status']=='COMPLETE'
    verify(E100,'VECTOR_SEAL.json','dd1ff8dc2ec742e001d8d0e59b700b33fa904680d420d9fb9350088f752317b0')
    verify(E100/'public','INPUT_SEAL.json','2ec88f115d3a507675e8fed6674cc3edf417ce587dd2d5220f1005329cd69573')
    labels=read(E127/'cpu_only/LABELS.PRIVATE.json');labelby={x['base_id']:x for x in labels}
    items=[x for x in read(E127/'inputs/items.json')if x['condition']=='none'];assert len(items)==84
    join=[x for x in read(E100/'cpu_only/JOIN.DO_NOT_STAGE.json')if x['row']=='fact_recall'];assert len(join)==84
    jby={x['source_item_id']:x for x in join};assert set(jby)=={labelby[x['base_id']]['original_source_id']for x in items}
    # E104 source identity proof uses complete tokens/readindex/orderedcandidate IDs.
    parent=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e104U_test_bind/fact_recall')
    verify(parent,'INPUT_SEAL.json','1e91a33f801d1eff72641fee56fa718957c65f57a7667fea5b5145a8db77b04a')
    old={x['base_id']:x for x in read(parent/'items.json')if x['condition']=='steered'}
    for x in items:
     l=labelby[x['base_id']];o=old[l['original_base_id']];assert all(x[k]==o[k]for k in ['ids','read_index','candidate_ids'])
     assert l['old_value']==jby[l['original_source_id']]['source_value']
    # Reproduce original E100 map only as a binding check; actual map is copied.
    pairs=read(E100/'public/pairings/fact_recall.json');check=pair_other([x['id']for x in join],[x['true_label']for x in join])
    assert [p['donor_slot']for p in pairs]==check
    assert all(p['id']==x['id']and p['donor_id']==x['donor_id']for p,x in zip(pairs,join))
    index=[x for x in read(CAP/'CAPTURE_INDEX.json')if x['source_layer']==44];by={x['id']:x for x in index};assert len(by)==252
    members={};vectors=[];pointers=[]
    for x in items:
     p=by[x['id']];name=p['member'];assert name in cs['files']and name.endswith('_44.npy')
     if name not in members:members[name]=np.load(CAP/name,allow_pickle=False)
     v=members[name][p['vector_index']].copy();assert v.shape==(5120,)and np.isfinite(v).all();vectors.append(v)
     pointers.append(dict(item=x,source_member=name,source_vector_index=p['vector_index'],source_member_sha256=cs['files'][name],labels=labelby[x['base_id']],e100=jby[labelby[x['base_id']]['original_source_id']]))
    h=np.stack(vectors).astype(np.float32);slot={p['labels']['original_source_id']:i for i,p in enumerate(pointers)}
    donor=[slot[p['e100']['donor_source_item_id']]for p in pointers]
    assert all(i!=j for i,j in enumerate(donor))
    b=transform(h,h[donor],'transplant');assert np.array_equal(b,h[donor])
    norms=np.linalg.norm(h.astype(np.float64),axis=1);target=np.full(84,np.median(norms))
    z=np.random.default_rng(20261027).standard_normal((84,5120)).astype(np.float32)
    c=norm_match(z,target)
    OUT.mkdir(exist_ok=False);pub=OUT/'inputs';cpu=OUT/'cpu_only';pub.mkdir();cpu.mkdir();records=[];private=[]
    for arm,vs in [('b',b),('c',c)]:
     for i,p in enumerate(pointers):
      ident=hashlib.sha256(('E138:'+p['item']['id']+':'+arm).encode()).hexdigest()
      records.append(dict(id=ident,vector_index=len(records)))
      private.append(dict(id=ident,condition=arm,recipient_source=p['labels']['original_source_id'],donor_source=p['e100']['donor_source_item_id'],recipient_old=p['e100']['source_value'],donor_old=p['e100']['donor_value'],original_E104_base_id=p['labels']['original_base_id'],clean_capture_pointer={k:p[k]for k in ['source_member','source_vector_index','source_member_sha256']},donor_capture_pointer={k:pointers[donor[i]][k]for k in ['source_member','source_vector_index','source_member_sha256']}))
    write(pub/'items.json',records);np.save(pub/'vectors.npy',np.concatenate([b,c]),allow_pickle=False)
    write(pub/'MANIFEST.json',dict(experiment='E138',source_items=84,readouts=168,oracle_block=44,dimension=5120,labels_on_pod=False,order='original E104 recipient order; b then c',pairing_protocol='E100 original frozen mapping seed20261028',random_protocol='E76 float32 Gaussian seed20261027, bank median clean84 norm, original norm_match',original_clean_output_sha256=sha(CAP/'OUTPUT_SEAL.json')))
    write(pub/'INPUT_SEAL.json',dict(experiment='E138',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()}))
    write(cpu/'POINTERS.PRIVATE.json',private)
    write(cpu/'CPU_SEAL.json',dict(experiment='E138',input_sha256=sha(pub/'INPUT_SEAL.json'),source_cpu_seals=[sha(E127/'cpu_only/LABEL_SEAL.json'),sha(E100/'VECTOR_SEAL.json')],files={p.name:sha(p)for p in cpu.iterdir()}))
    for p in cpu.iterdir():p.chmod(0o600)
    with tarfile.open(OUT/'inputs.tar.gz','w:gz',compresslevel=1)as t:
     for p in sorted(pub.iterdir()):t.add(p,arcname=p.name)
    x=dict(experiment='E138',public_root=str(pub),input_sha256=sha(pub/'INPUT_SEAL.json'),archive=str(OUT/'inputs.tar.gz'),archive_sha256=sha(OUT/'inputs.tar.gz'),CPU_only_root=str(cpu),CPU_only_seal_sha256=sha(cpu/'CPU_SEAL.json'),source_items=84,readouts=168,donor_seed=20261028,gaussian_seed=20261027,donor_protocol_path='results/g_agreement/understand/e100/vectors/math100.py::pair_other',norm_protocol_path='results/g_agreement/understand/e76/common76.py::norm_match',clean_source_root=str(CAP),clean_output_seal_sha256=sha(CAP/'OUTPUT_SEAL.json'),E104_input_sha256=sha(parent/'INPUT_SEAL.json'),E100_vector_seal_sha256=sha(E100/'VECTOR_SEAL.json'),all84_source_bindings='PASS full tokens/read/orderedpairs/originalsourceIDs',all84_donor_bindings='PASS original frozen seed/mapping; oppositeclass/samefactrow',placebo_norm_reference='median of ALL84 clean block44 raw norms, E76 bankmedian protocol',source_readouts_opened=0,model_calls=0,GPU_calls=0)
    write(R/'results/g_agreement/understand/e138/INPUT_BINDING.json',x);print(json.dumps(x,indent=2))

if __name__=="__main__":build()
