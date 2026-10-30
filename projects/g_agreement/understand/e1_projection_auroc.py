"""Post-result DESCRIPTIVE E1 projection AUROCs; never reruns E1 fidelity analysis."""
import argparse
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .analyse import recon_data


def projection_auroc(projection,positive):
    p=np.asarray(projection,float);y=np.asarray(positive,bool)
    if len(p)!=len(y) or not np.isfinite(p).all() or set(y)!={False,True}:
        raise ValueError('finite two-class projection grid required')
    a=p[y,None];b=p[~y][None,:]
    return float(np.mean((a>b)+0.5*(a==b)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['inputs','preparation','w1','prefix','description','s2-texts','decoder','out']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    verify(a.inputs,'INPUT_SEAL.json');verify(a.w1,'ANALYSIS_SEAL.json');verify(a.s2_texts,'INPUT_SEAL.json')
    prep=read(a.preparation);lp=Path(prep['private_labels']['path'])
    if sha(lp)!=prep['private_labels']['sha256']:raise ValueError('frozen E1 label hash mismatch')
    pi,pr=recon_data(a.prefix);si,sr=recon_data(a.description);di,dr=recon_data(a.decoder)
    if pi!=[r['id'] for r in rows(a.inputs/'enactment.input.jsonl')]:raise ValueError('prefix order mismatch')
    if di!=[r['id'] for r in rows(a.inputs/'decoder.input.jsonl')]:raise ValueError('decoder order mismatch')
    if si!=[r['id'] for r in rows(a.s2_texts/'texts.input.jsonl')]:raise ValueError('description order mismatch')
    for path in [a.prefix,a.decoder]:
        if read(path/'provenance.json')['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('E1 lineage mismatch')
    if read(a.description/'provenance.json')['text_seal_sha256']!=sha(a.s2_texts/'INPUT_SEAL.json'):raise ValueError('S2 lineage mismatch')
    labels=rows(lp);meta=read(a.w1/'probe_directions.json')['rows'];directions=np.load(a.w1/'probe_directions.npz',allow_pickle=False)
    sets={'ar':{'enactment':(pi,pr),'description':(si,sr)},'nla':{'enactment':(di,dr),'description':(di,dr)}}
    features=sorted({r['feature'] for r in rows(a.inputs/'enactment.input.jsonl')});output=[]
    for feature in features:
        for reader,layer in [('ar',44),('nla',42)]:
            d=next(m for m in meta if m['feature']==feature and m['layer']==layer)
            u=directions[d['array_prefix']+'__unit'].astype(float)
            for arm in ['description','enactment']:
                selected=[r for r in labels if r['feature']==feature and r['arm']==arm]
                ids,x=sets[reader][arm];index={key:i for i,key in enumerate(ids)}
                projections=x[[index[r['id']] for r in selected]].astype(float)@u
                y=np.array([r['value'] for r in selected],bool)
                output.append({'feature':feature,'class':d['class'],'reader':reader,'layer':layer,
                    'frozen_arm_key':arm,'arm':'description' if arm=='description' else ('AR on the prefix' if reader=='ar' else 'NLA decoder on the prefix'),
                    'auroc':projection_auroc(projections,y),'n':len(y),'n_A':int(y.sum()),'n_B':int((~y).sum())})
    a.out.mkdir(exist_ok=False,parents=True)
    dump(a.out/'metrics.json',{'status':'DESCRIPTIVE_ADDED_AFTER_SEEING_E1_RESULTS','rows':output,
        'orientation':'value A positive; fixed dev-only native unit probe; no sign flips, normalization, refit or gap denominator',
        'definition':'P(projection_A > projection_B) + 0.5 P(tie)','CI':'No new CIs computed; requested descriptive AUROC point estimates only',
        'upstream_seals':{n:sha(path/'SCORE_SEAL.json') for n,path in [('prefix',a.prefix),('description',a.description),('decoder',a.decoder)]},
        'W1_analysis_seal_sha256':sha(a.w1/'ANALYSIS_SEAL.json'),'private_labels_sha256':sha(lp),'GPU_hours':0,'registered_E1_analysis_rerun':False})
    lines=['**DESCRIPTIVE — added after seeing E1 results (2026-10-24).** AUROC of the fixed native probe projection, value A positive, with ties counted as one half. No gap denominator, sign flip or probe refit. Both decoders and both frozen arms are included. These are point estimates; no new AUROC CIs were requested or computed. The original fidelity estimates and assessment are unchanged. High AUROC with low fidelity would indicate preserved ordering with a small projection contrast relative to the real-activation gap; AUROC alone does not validate reconstruction magnitude.','',
        '| Row | Class | AR description | AR on the prefix | NLA decoder description | NLA decoder on the prefix |',
        '|---|---|---:|---:|---:|---:|']
    index={(r['feature'],r['reader'],r['frozen_arm_key']):r for r in output}
    for feature in features:
        cells=[index[feature,r,arm] for r,arm in [('ar','description'),('ar','enactment'),('nla','description'),('nla','enactment')]]
        lines.append('| '+' | '.join([feature,cells[0]['class']]+[f"{r['auroc']:.6f}" for r in cells])+' |')
    lines+=['','Per row: description n = 40 (20 A / 20 B); prefix n = 84 (42 A / 42 B). Full precision, source seals and counts: `projection_auroc/metrics.json`.']
    (a.out/'DESCRIPTIVE.md').write_text('\n'.join(lines)+'\n')
    seal(a.out,['metrics.json','DESCRIPTIVE.md'],'DESCRIPTIVE_E1_PROJECTION_AUROC_ADDED_AFTER_RESULTS')
    print('DESCRIPTIVE E1 projection AUROC',len(output),'cells; no fidelity analysis rerun')


if __name__=='__main__':main()
