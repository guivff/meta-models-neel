"""CPU-only existing E109 probe application and exact read-token vector delivery."""
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
REQ=core.require


def margins(vectors,w,b,old_letters):
    x=np.asarray(vectors);w=np.asarray(w);b=np.asarray(b)
    REQ(x.ndim==2 and w.shape==(x.shape[1],)and b.shape==()and len(old_letters)==len(x),'frozen probe/vector shape')
    REQ(np.isfinite(x).all()and np.isfinite(w).all()and np.isfinite(b),'finite original vectors/weights/intercept')
    REQ(all(v in('A','B')for v in old_letters),'explicit original-fact class orientation')
    # Original unscaled class1=A,class0=B decision function; no normalization/refit.
    return (x.astype(float)@w+float(b))*np.array([1 if v=='A'else-1 for v in old_letters])


def export(plan):
    out=Path(plan['output']);REQ(not out.exists(),'delivery already exists; do not repeat')
    main=Path(plan['e133_analysis_seal']);core.verify(main,plan['e133_analysis_sha256'])
    binding=core.verify(plan['binding_seal'],plan['binding_sha256']);bp=Path(plan['binding_seal']).parent
    inv=core.verify(plan['inventory_seal'],plan['inventory_sha256']);meta=core.read(Path(plan['inventory_seal']).parent/'INVENTORY.json')['fact_recall']
    REQ(meta['alpha']==8 and len(set(meta['test_ids']))==84,'original84 fact alpha8 test cohort')
    REQ(core.sha(plan['e104_private'])==plan['e104_private_sha256'],'original E104 private cohort')
    prior=core.read(plan['e104_private']);rows=[x for x in prior if x['arm']=='U'and x['row']=='fact_recall'and x['condition']=='steered'];by=core.unique(rows,'item_id')
    ids=meta['test_ids'];REQ(set(by)==set(ids)and len(rows)==84,'exact original E10484; no filtering')
    REQ(all(by[i]['target']==t for i,t in zip(ids,meta['target_letters'])),'original steered OTHER-value targets')
    old=['B'if t=='A'else'A'for t in meta['target_letters']]
    probe=core.verify(plan['probe_seal'],plan['probe_sha256']);pr=Path(plan['probe_seal']).parent
    pm=core.read(pr/'PROBE_MANIFEST.json');p=next(x for x in pm['probes']if x['row']=='fact_recall')
    REQ(p['block']==44 and p['preprocessing']=='none'and p['classes']==[0,1]and p['class_letter_mapping']=={'0':'B','1':'A'}and p['fit_split']=='unhooked_dev'and p['test_used_for_fit']is False,'frozen own E109 dev44 unscaled class mapping')
    weights=pr/'weights/fact_recall_probe.npz';REQ(core.sha(weights)==p['weights_sha256'],'original probe bytes')
    wp=np.load(weights,allow_pickle=False);w,b=wp['w'],wp['b'];REQ(wp['classes'].tolist()==[0,1],'original fitted classes')
    sources=binding['source_seals'];seals=[core.verify(z['seal'],z['sha256'])for z in sources]
    capture=seals[0];root=Path(sources[0]['seal']).parent;index=core.read(root/'CAPTURE_INDEX.json')
    REQ(sources[0]['sha256']==pm['capture_seal_sha256'],'same original probe-training/capture acquisition')
    mm=core.read(bp/'MEASUREMENTS.json')['fact_recall']['44']['test'];arrays={};refs={};cache={}
    for cond in('unhooked','steered'):
        z=mm[cond];si=z['seal_index'];REQ(not z['keys']and z['member']in seals[si]['files'],'original complete84 capture array')
        matrix=np.load(Path(sources[si]['seal']).parent/z['member'],allow_pickle=False)
        REQ(matrix.shape==(84,5120)and matrix.dtype==np.float32 and np.isfinite(matrix).all(),'original fp32 read-token84 vectors')
        selected=[x for x in index if x['row']=='fact_recall'and x['split']=='test'and x['condition']==cond];native=core.unique(selected,'base_id');REQ(set(native)==set(ids)and len(selected)==84,'original vector ID order/cohort')
        rr=[]
        for j,i in enumerate(ids):
            x=native[i];v=x['layers']['44'];m=x['metadata'];REQ(v['member']in capture['files']and m['member']in capture['files'],'sealed original vector+metadata')
            if v['member']not in cache:cache[v['member']]=np.load(root/v['member'],allow_pickle=False)
            if m['member']not in cache:cache[m['member']]=core.read(root/m['member'])
            job=cache[m['member']][m['record_index']];REQ(all(job[k]==x[k]for k in('id','base_id','row','split','condition'))and job['read_index']>=0,'exact original read-token identity')
            REQ(x['alpha']==8 if cond=='steered'else not job['hook_installed'],'alpha8 or actually clean unhooked')
            REQ(np.array_equal(matrix[j],cache[v['member']][v['vector_index']]),'normalized sealed matrix exactly matches native same-ID vector')
            rr.append(dict(item_id=i,native_id=x['id'],vector=v,metadata=m,read_index=job['read_index']))
        arrays[cond]=matrix;refs[cond]=rr
    values={c:margins(x,w,b,old)for c,x in arrays.items()}
    out.mkdir(parents=True,mode=0o700)
    for c in arrays:
        np.save(out/(c+'_vectors44.PRIVATE.npy'),arrays[c]);np.save(out/(c+'_old_fact_margins44.PRIVATE.npy'),values[c])
    core.write(out/'IDENTITIES.PRIVATE.json',dict(item_ids=ids,original_fact_letters=old,steered_target_letters=meta['target_letters'],source_refs=refs))
    core.write(out/'SOURCE_BINDING.PRIVATE.json',dict(plan=plan,probe_class_mapping=p['class_letter_mapping'],margin_definition='(2*original_fact_class-1)*(h44@w+b); unscaled original frozen probe; original fact is opposite E104 other-value steering target',vector_definition='exact original fp32 read-token vectors; no normalization/displacement computed',fit_calls=0))
    for f in out.iterdir():f.chmod(0o600)
    core.seal(out,'DELIVERY_SEAL.json',experiment='E109',purpose='248C original84 fact probe margins and raw read-token vectors',n_items=84,conditions=['unhooked','steered_alpha8'],block=44,new_fits=0,new_calls=0)
    (out/'DELIVERY_SEAL.json').chmod(0o600)
    return out/'DELIVERY_SEAL.json'
