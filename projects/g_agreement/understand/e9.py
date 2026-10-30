"""§96 dependency-gated descriptive regressions; no imputation or new GPU work."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr
from projects.g_agreement.blindspot import protocol as P


def analyse(source,out):
    """Input contract: exact source receipts plus rows keyed by feature and reader.

    Columns: description_fidelity, image_fraction95, image_fraction99,
    next_token_relevance, probe_auroc, asked_auroc, low_dose_gain.
    Producer-specific mappings must be documented in source.provenance, not
    guessed from arbitrary metric names. Missing rows/fields are retained as NA.
    """
    source,out=Path(source),Path(out);data=json.loads(source.read_text())
    if not all(k in data.get('provenance',{}) for k in ('E1','E2','E4','E8','W1')):
        raise ValueError('need explicit E1,E2,E4,E8,W1 source receipts before regression')
    features=data.get('expected_features',[])
    if len(features)!=40 or len(set(features))!=40:raise ValueError('explicit40-row W1 feature universe required')
    observations=data['rows'];keys=[(r['feature'],r['reader']) for r in observations]
    if len(keys)!=len(set(keys)):raise ValueError('duplicate feature-reader rows')
    def finite(r,k):return isinstance(r.get(k),(int,float)) and np.isfinite(r[k])
    results=[]
    for reader in ('olens','nla','jlens'):
        observed={r['feature']:r for r in observations if r['reader']==reader}
        rows=[observed.get(f,{'feature':f,'reader':reader,'missing_reason':'dependency row absent'}) for f in features]
        for outcome in ('asked_auroc','low_dose_gain'):
            for variance in (95,99):
                predictors=['description_fidelity','image_fraction'+str(variance),'next_token_relevance','probe_auroc']
                correlations=[]
                for predictor in predictors:
                    valid=[r for r in rows if finite(r,predictor) and finite(r,outcome)]
                    x=[r[predictor] for r in valid];y=[r[outcome] for r in valid]
                    rho=float(spearmanr(x,y).statistic) if len(valid)>=3 and len(set(x))>1 and len(set(y))>1 else None
                    correlations.append({'predictor':predictor,'n':len(valid),'rho':rho})
                valid=[r for r in rows if all(finite(r,k) for k in predictors+[outcome])]
                entry={'reader':reader,'outcome':outcome,'image_variance':variance,'rank_correlations':correlations,
                    'n_total':len(rows),'n_complete_case':len(valid),'missing_features':[r['feature'] for r in rows if r not in valid]}
                if len(valid)<6:entry['regression_status']='INSUFFICIENT_COMPLETE_CASES'
                else:
                    x=np.array([[r[k] for k in predictors] for r in valid]);y=np.array([r[outcome] for r in valid])
                    scale=x.std(0);constant=scale==0;scale[constant]=1;x=(x-x.mean(0))/scale
                    design=np.column_stack([np.ones(len(x)),x]);coef,_,rank,_=np.linalg.lstsq(design,y,rcond=None)
                    entry.update(regression_status='RANK_DEFICIENT' if rank<len(coef) else 'DESCRIPTIVE_OLS',
                        design_rank=int(rank),standardized_predictor_coefficients=coef.tolist() if rank==len(coef) else None,
                        r_squared_in_sample=float(1-((y-design@coef)**2).sum()/((y-y.mean())**2).sum()) if np.var(y)>0 else None)
                results.append(entry)
    out.mkdir(parents=True,exist_ok=False)
    P.dump(out/'metrics.json',{'status':'DESCRIPTIVE','input_sha256':P.sha(source),'source_provenance':data['provenance'],
        'results':results,'limitations':'four numerical predictors for three conceptual families;95/99 image fractions in separate models; complete-case only; no missing=zero, sign flips or causal interpretation; no out-of-sample performance claim'})
    (out/'RESULTS.md').write_text('# E9 descriptive regressions\n\nPrediction: Oracle tracks describability, J tracks next-token relevance, NLA tracks presence with attenuation.\n\n'+
        '\n'.join(str(r) for r in results)+'\n\nE1/E4 may cover only25 rows while E9 requests40. Report missing coverage; do not extrapolate, impute or authorize extra compute.\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();analyse(a.source,a.out)
