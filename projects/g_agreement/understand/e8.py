"""§95: frozen value-B recipients, signed dev-probe edits and gain conventions."""
import hashlib,json
from pathlib import Path
import numpy as np
from . import core as K
from projects.g_agreement.blindspot import protocol as P

ALPHAS=[0,.5,1,2,4,8]


def gains(scores,reference):
    values=np.asarray(scores,float)
    if values.shape!=(6,) or not np.isfinite(values).all():raise ValueError('six finite dose means required')
    crossing=[a for a,v in zip(ALPHAS,values) if v>=reference]
    return {'low_dose_gain':float(np.polyfit(ALPHAS[:3],values[:3],1)[0]),
        'all_dose_gain':float(np.polyfit(ALPHAS,values,1)[0]),
        'dose_reaching_A_median':crossing[0] if crossing else None,
        'crossing_status':'REACHED_MEASURED_GRID' if crossing else 'NOT_REACHED_AT_ALPHA8',
        'linear_range':[0,.5,1],'no_sign_flip':True}


def prepare():
    all_items,_,specs=K.load_w1();features=sorted(f for f,s in specs.items() if s['kind']=='binary')
    if len(features)!=40:raise ValueError('need all40 W1 binary rows')
    def select(items):
        indices=[]
        for f in features:
            eligible=[i for i,x in enumerate(items) if x['feature']==f and x['split']=='test' and x['value']==specs[f]['values'][1]]
            chosen=sorted(eligible,key=lambda i:hashlib.sha256(('E8-v1:'+items[i]['id']).encode()).hexdigest())[:40]
            if len(chosen)!=40 or len({items[i]['cluster'] for i in chosen})!=6:raise ValueError('need40 B items across6 clusters')
            indices.extend(chosen)
        return indices
    bank,frozen,plan=K.prepare('E8',features,select,{f:specs[f] for f in features},3600,
        {'alphas':ALPHAS,'prediction':'Oracle structure gain is lower than meaning gain; NLA attenuation is weaker',
         'edit':'h+alpha*(dev unit direction*dev class-mean projected gap), at each reader native site; no post-edit renormalization beyond native reader',
         'gain_definition':'OLS slope across fixed low-dose range alpha[0,0.5,1]; also report all-dose OLS and all points. No outcome-selected linear range.',
         'crossing_definition':'first measured grid dose whose mean recipient log-odds reaches W1 value-A test median; no interpolation/extrapolation; non-crossing explicit'})
    metadata=json.loads((K.W1/'probe_directions.json').read_text())['rows'];vectors=np.load(K.W1/'probe_directions.npz',allow_pickle=False)
    d={};scales=[]
    for r in metadata:
        if r['feature'] not in features:continue
        key=r['array_prefix'];u=vectors[key+'__unit'];gap=float(r['dev_class_mean_projection_gap'])
        if r['fit_split']!='dev' or not np.isclose(np.linalg.norm(u),1,atol=1e-5) or not np.isfinite(gap) or gap<=0:
            raise ValueError('invalid signed dev direction or class gap')
        d[key]=np.asarray(u*gap,dtype=np.float32)
        scales.append({'feature':r['feature'],'layer':r['layer'],'dev_gap':gap,'source_array':key+'__unit'})
    if len(d)!=80:raise ValueError('all80 native directions required')
    np.savez_compressed(bank/'directions.npz',**d)
    plan['direction_scales']=scales;plan['direction_source_seal_sha256']=P.sha(K.W1/'ANALYSIS_SEAL.json')
    # Frozen native value-A medians from existing sealed W1 scores; no new reader run.
    raw=[];lineage=[]
    for phase in ('target','nla'):
        root=P.ROOT/f'cache/g_agreement/blindspot/w1-assembled/{phase}'
        P.verify(root,'SCORE_SEAL.json');lineage.append(P.sha(root/'SCORE_SEAL.json'))
        raw.extend(P.rows(root/f'scores.{phase}.jsonl'))
    score={(r['id'],r['reader'],r['layer']):r for r in raw if r['arm']=='true'}
    references={}
    for f in features:
        ids=[x['id'] for x in all_items if x['feature']==f and x['split']=='test' and x['value']==specs[f]['values'][0]]
        if len(ids)!=42:raise ValueError('W1 A-reference population differs')
        for reader,site in K.READERS:
            cells=[score[i,reader,site] for i in ids]
            if any(r['status']!='COMPLETE' for r in cells):raise ValueError('incomplete A-reference scores')
            references[f+'__'+reader]={'A_median':float(np.median([np.mean(r['scores']) for r in cells])),'n_A':42}
    plan['A_reference_medians']=references;plan['A_reference_W1_score_seals']=lineage
    P.dump(bank/'plan.json',plan)
    names=list(json.loads((bank/'INPUT_SEAL.json').read_text())['files'])+['directions.npz']
    P.seal(bank,names,'EXPLORATORY_INPUTS_FROZEN')
    for n in ('plan.json','INPUT_SEAL.json'):(frozen/n).write_bytes((bank/n).read_bytes())
    return bank,frozen,plan
