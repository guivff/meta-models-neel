"""Post-X1 descriptive CPU norm audit; no model loads or intervention outcomes."""
import json
from pathlib import Path
import numpy as np
from . import remainder_x1 as D

def summary(rows):
    out={}
    for metric in ('bridge_state_ratio','answer_state_ratio','answer_delta_over_bridge_delta','bridge_relative_delta','answer_relative_delta'):
        x=np.asarray([r[metric] for r in rows],float)
        assert np.isfinite(x).all() and (x>=0).all()
        out[metric]={'n':len(x),'quantiles':dict(zip(('min','p10','p25','median','p75','p90','max'),map(float,np.quantile(x,[0,.1,.25,.5,.75,.9,1])))), 'within':{str(t):{'count':int((abs(x-1)<=t).sum()),'fraction':float((abs(x-1)<=t).mean())} for t in (.05,.1,.2)}}
    return out

def main():
    root=D.ROOT/'cache/g_agreement/r/remainder/x1/pilot_20261020'
    states_path=root/'pulled'/D.DATA_REL/'natural'
    plan=D.read(D.OUT/'pilot_plan.json'); bank=plan['records']; checks=D.read(states_path/'checksums.json')
    states={}
    for r in bank:
        p=states_path/(r['id']+'.npz'); assert D.sha(p)==checks[p.name]
        with np.load(p,allow_pickle=False) as a: states[r['id']]={L:{s:np.asarray(a[f'L{L}_{s}'],dtype=np.float64) for s in ('bridge','answer')} for L in D.LAYERS}
    rows=[];meta=D.provenance(); byid={r['id']:r for r in bank}
    for r in bank:
        for j,did in enumerate(D.pair_candidates(r,bank)):
            for L in D.LAYERS:
                a=states[r['id']][L];b=states[did][L]
                delta={s:float(np.linalg.norm(b[s]-a[s])) for s in ('bridge','answer')}
                assert delta['bridge']>0
                row={'recipient':r['id'],'donor':did,'split':r['split'],'layer':L,'nominal':j==0,'pilot':r['id'] in plan['pilot_ids'],'recipient_bridge':r['bridge'],'donor_bridge':byid[did]['bridge'],**meta}
                row.update({s+'_state_ratio':float(np.linalg.norm(b[s])/np.linalg.norm(a[s])) for s in ('bridge','answer')})
                row.update({s+'_relative_delta':float(delta[s]/np.linalg.norm(a[s])) for s in ('bridge','answer')})
                row['answer_delta_over_bridge_delta']=delta['answer']/delta['bridge'];rows.append(row)
    result={'status':'DESCRIPTIVE_AFTER_X1_GATE_FAILURE','definitions':{'state_ratio':'norm(donor state) / norm(recipient state), same site','answer_delta_over_bridge_delta':'norm(donor answer - recipient answer) / norm(donor bridge - recipient bridge); the first X1 caliper gate','relative_delta':'norm(donor - recipient) / norm(recipient), same site'},'states':len(states),'inputs_checksums_sha256':D.sha(states_path/'checksums.json'),'groups':{},**meta}
    for L in D.LAYERS:
        result['groups'][str(L)]={name:summary([r for r in rows if r['layer']==L and pred(r)]) for name,pred in [('nominal_all_400',lambda r:r['nominal']),('nominal_pool',lambda r:r['nominal'] and r['split']=='pool'),('nominal_test',lambda r:r['nominal'] and r['split']=='test'),('nominal_pilot_20',lambda r:r['nominal'] and r['pilot']),('all_eligible_pairs',lambda r:True),('all_pilot_candidates',lambda r:r['pilot'])]}
    (root/'norm_rows.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
    D.save(D.OUT/'norm_distribution.json',result)
    print(json.dumps({L:{k:v for k,v in g['nominal_all_400'].items() if k in ('bridge_state_ratio','answer_state_ratio','answer_delta_over_bridge_delta')} for L,g in result['groups'].items()},indent=2))
if __name__=='__main__':main()
