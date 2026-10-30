"""E11: exact centered CPU PCA of sealed W3 h, reconstruction and residual."""
import time
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal, pca, image_fraction


def main():
    started=time.monotonic();base=ROOT/'results/g_agreement';out=base/'understand/e11'
    out.mkdir(exist_ok=False)
    cache=ROOT/'cache/g_agreement/blindspot/mechanism'
    bank=cache/'w34-collection-ebf6c121';target=bank/'target'
    residuals=cache/'w3-units/rk4veemwm0jf9i/w3-residuals'
    w1=base/'blindspot/w1/analysis';w3=base/'blindspot/mechanism/w3/analysis_rk4veemwm0jf9i'
    for d in [target,residuals,w3]:verify(d)
    verify(bank/'bank','INPUT_SEAL.json');verify(w1,'ANALYSIS_SEAL.json')
    lp=bank/'labels.DO_NOT_STAGE.jsonl'
    assert sha(lp)==read(bank/'bank/provenance.json')['labels_sha256']
    labels=rows(lp);ids=read(target/'items.order.json')
    assert ids==read(residuals/'ids.json')==[r['id'] for r in labels]
    selected={r['feature'] for r in read(w3/'metrics.residual.json')['rows']}
    ix=[i for i,l in enumerate(labels) if l['feature'] in selected and l['split']=='test']
    assert len(ix)==2100
    prov=read(residuals/'provenance.json')
    assert prov['target_score_seal_sha256']==sha(target/'SCORE_SEAL.json')
    assert prov['source_files']['projects/g_agreement/blindspot/ar_tests.py'].startswith('73a2c2fe')
    h=np.load(target/'acts44.npy',allow_pickle=False)[ix]
    recon=np.load(residuals/'recon.npy',allow_pickle=False)[ix]
    residual=np.load(residuals/'residual.npy',allow_pickle=False)[ix]
    assert np.array_equal(h-recon,residual)
    meta=read(w1/'probe_directions.json');arrays=np.load(w1/'probe_directions.npz',allow_pickle=False)
    dm=[r for r in meta['rows'] if r['layer']==44]
    directions=np.stack([arrays[r['array_prefix']+'__unit'] for r in dm])
    assert len(dm)==40 and all(r['fit_split']=='dev' for r in dm)
    pc={}
    for name,x in [('h',h),('reconstruction',recon),('residual',residual)]:
        print('E11 PCA',name,flush=True);pc[name]=pca(x,64)
    result=[]
    for i,r in enumerate(dm):
        result.append({'feature':r['feature'],'class':r['class'],'among_W3_25':r['feature'] in selected,
            **{name:{str(k):float(image_fraction(directions[i:i+1],p['basis'][:k])[0]) for k in [16,64]}
               for name,p in pc.items()}})
    alignment={}
    for k in [16,64]:
        cos=np.linalg.svd(pc['h']['basis'][:k]@pc['reconstruction']['basis'][:k].T,compute_uv=False)
        alignment[str(k)]={'principal_cosines':cos.tolist(),'mean_squared_principal_cosine':float(np.square(cos).mean()),
            'principal_angles_degrees':np.degrees(np.arccos(np.clip(cos,-1,1))).tolist()}
    summary={}
    for c in ['count-like','state-like','semantic']:
        rs=[r for r in result if r['class']==c and r['among_W3_25']]
        summary[c]={'n_rows':len(rs),**{n:{str(k):float(np.mean([r[n][str(k)] for r in rs])) for k in [16,64]} for n in pc}}
    output={'status':'EXPLORATORY','prediction':'Structure directions sit in residual and h top PCs but not reconstruction;meaning in all three.',
        'prediction_assessment':'No clean structure-specific dissociation at class level: reconstruction top-64 fractions are lower than h and residual for every class, including semantic rows;semantic h/residual fractions exceed count/state means. All40 directions and both k values reported.',
        'n_items':2100,'n_PCA_source_rows':25,'n_probe_directions':40,'centered_separately':True,'k':[16,64],
        'rows':result,'selected25_class_means':summary,'h_reconstruction_alignment':alignment,
        'variance_captured':{n:{str(k):float(p['variance_fraction'][:k].sum()) for k in [16,64]} for n,p in pc.items()},
        'source_seals':{str(p.relative_to(ROOT)):sha(p) for p in [target/'SCORE_SEAL.json',residuals/'SCORE_SEAL.json',w1/'ANALYSIS_SEAL.json',w3/'SCORE_SEAL.json']},
        'labels_sha256':sha(lp),'brief_sha256':sha(base/'understand/BRIEF_UNDERSTAND.bound.md'),
        'seconds':time.monotonic()-started,'GPU_hours':0}
    dump(out/'metrics.json',output)
    artifact=cache/'e11_PCA.npz'
    np.savez_compressed(artifact,**{n+'_'+key:p[key] for n,p in pc.items() for key in ['basis','eigenvalues','mean']})
    dump(out/'PCA_ARTIFACT.json',{'path':str(artifact),'sha256':sha(artifact)})
    lines=['# E11 — EXPLORATORY','',output['prediction'],'',
        output['prediction_assessment'],
        '', 'Centered PCA on all 2,100 W3 test items across the frozen 25 rows. Projections of all 40 W1 dev-fit directions are reported; class means below use the selected 25 only. No sign flips or refits.', '',
        '| Class | k | h | Reconstruction | Residual |','|---|---:|---:|---:|---:|']
    for c,s in summary.items():
        for k in [16,64]:lines.append(f"| {c} | {k} | {s['h'][str(k)]:.6f} | {s['reconstruction'][str(k)]:.6f} | {s['residual'][str(k)]:.6f} |")
    lines+=['','h/reconstruction mean squared principal cosine: '+', '.join(f"k={k}: {v['mean_squared_principal_cosine']:.6f}" for k,v in alignment.items())+'.','',
        '| Feature | Class | In W3 | h16 | h64 | recon16 | recon64 | residual16 | residual64 |','|---|---|---|---:|---:|---:|---:|---:|---:|']
    for r in result:lines.append('| '+ ' | '.join([r['feature'],r['class'],str(r['among_W3_25'])]+[f"{r[n][str(k)]:.6f}" for n in pc for k in [16,64]])+' |')
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    seal(out,['metrics.json','PCA_ARTIFACT.json','RESULTS.md'],'EXPLORATORY_E11_SEALED')
    print('E11 COMPLETE',round(output['seconds'],2),'seconds',summary,flush=True)


if __name__=='__main__':main()
