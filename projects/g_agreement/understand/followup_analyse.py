"""CPU-only post-seal E1b/E12 metrics, with frozen dev/test and paired cluster bootstrap."""
import argparse
from dataclasses import asdict
from pathlib import Path
import numpy as np
from .cpu import ROOT,read,rows,dump,sha,verify,seal
from .analyse import fidelity_ratio,analysis_output,recon_data

SEED=20261023
BOOT=2000


def labels_for(a,tag):
    receipt=read(ROOT/f'results/g_agreement/understand/{tag}/PACKED_INPUT_RECEIPT.json')
    private=Path(receipt['private_bank_path'])/'items.DO_NOT_STAGE.jsonl'
    if sha(private)!=receipt['private_items_sha256']:raise ValueError('frozen W1 label-bearing item hash mismatch')
    return {r['id']:r for r in rows(private)}


def window_scores(dev_text,dev_y,test_text):
    """No test text enters vocabulary, IDF, coefficient fitting or hyperparameter selection."""
    import warnings
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning
    vectorizer=TfidfVectorizer(analyzer='char',ngram_range=(1,4),lowercase=False,min_df=1,
        norm='l2',use_idf=True,smooth_idf=True,sublinear_tf=False)
    x=vectorizer.fit_transform(dev_text)
    classifier=LogisticRegression(C=1.,penalty='l2',solver='lbfgs',max_iter=2000,tol=1e-4,random_state=SEED)
    with warnings.catch_warnings():
        warnings.simplefilter('error',ConvergenceWarning);classifier.fit(x,np.asarray(dev_y,int))
    return classifier.decision_function(vectorizer.transform(test_text)),len(vectorizer.vocabulary_)


def e1b(a):
    import common,sklearn
    from mats.metrics import auroc_ci
    verify(a.inputs,'INPUT_SEAL.json');verify(a.collection)
    if not read(a.collection/'SCORE_SEAL.json')['status'].endswith('_COMPLETE'):raise ValueError('E1b collection incomplete')
    verify(a.collection/'continuations');verify(a.w1,'ANALYSIS_SEAL.json');verify(a.e1);verify(a.e1/'projection_auroc')
    cont=rows(a.collection/'continuations/continuations.jsonl');items=rows(a.inputs/'items.input.jsonl')
    if [r['id'] for r in cont]!=[r['id'] for r in items] or len(cont)!=4200 or any(len(r['ids'])!=16 for r in cont):raise ValueError('complete 4200continuation grid required')
    if read(a.collection/'continuations/provenance.json')['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('continuation lineage mismatch')
    ids,recon=recon_data(a.collection/'ar');test=read(a.inputs/'test_ids.json');dev=read(a.inputs/'dev_ids.json')
    if ids!=test or len(test)!=2100 or len(dev)!=2100 or set(test)&set(dev):raise ValueError('frozen dev/test split mismatch')
    rp=read(a.collection/'ar/provenance.json')
    if rp['continuation_seal_sha256']!=sha(a.collection/'continuations/SCORE_SEAL.json') or rp['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('AR continuation lineage mismatch')
    # Labels join only after every continuation, reconstruction and input seal above passed.
    labels=labels_for(a,'e1b');texts={r['id']:r['text'] for r in cont};meta=read(a.w1/'probe_directions.json')['rows'];directions=np.load(a.w1/'probe_directions.npz',allow_pickle=False)
    old=read(a.e1/'metrics.json')['rows'];oldauc=read(a.e1/'projection_auroc/metrics.json')['rows'];w1=read(a.w1/'metrics.json')['rows'];index={key:i for i,key in enumerate(ids)}
    output=[];predictions=[]
    for feature in sorted({r['feature'] for r in items}):
        ti=[key for key in test if labels[key]['feature']==feature];di=[key for key in dev if labels[key]['feature']==feature]
        assert len(ti)==len(di)==84
        if {labels[k]['cluster'] for k in ti}&{labels[k]['cluster'] for k in di}:raise ValueError('template leakage across dev/test')
        definition=next(m for m in meta if m['feature']==feature and m['layer']==44)
        # Direction export fixes value A; the W1 template file supplies its exact name.
        bank=Path(read(ROOT/'results/g_agreement/understand/e1b/PACKED_INPUT_RECEIPT.json')['private_bank_path'])
        positive=read(bank/'templates.json')[feature]['values'][0]
        y=np.array([labels[k]['value']==positive for k in ti]);dy=np.array([labels[k]['value']==positive for k in di]);groups=[labels[k]['cluster'] for k in ti]
        scores,vocabulary=window_scores([texts[k] for k in di],dy,[texts[k] for k in ti])
        proj=recon[[index[k] for k in ti]].astype(float)@directions[definition['array_prefix']+'__unit'].astype(float)
        fidelity=fidelity_ratio(proj,y,definition['test_class_mean_projection_gap'])
        old_f={r['arm']:r for r in old if r['feature']==feature and r['reader']=='ar'}
        old_a={r['frozen_arm_key']:r for r in oldauc if r['feature']==feature and r['reader']=='ar'}
        oracle=next(r['true'] for r in w1 if r['feature']==feature and r['reader']=='olens' and r['layer']==44)
        output.append({'feature':feature,'class':definition['class'],'window_ceiling':asdict(auroc_ci(scores,y,groups,n_boot=BOOT,seed=SEED)),
            'AR_continuation_fidelity':fidelity,'AR_continuation_projection_auroc':asdict(auroc_ci(proj,y,groups,n_boot=BOOT,seed=SEED)),
            'AR_on_prefix_fidelity':old_f['enactment'],'AR_description_fidelity':old_f['description'],
            'AR_on_prefix_projection_auroc_POST_RESULT':old_a['enactment'],'AR_description_projection_auroc_POST_RESULT':old_a['description'],
            'Oracle_W1_auroc':oracle,'vocabulary_dev_only':vocabulary,'n_dev':len(di),'n_test':len(ti)})
        predictions += [{'id':key,'feature':feature,'window_score':float(s),'AR_probe_projection':float(p)} for key,s,p in zip(ti,scores,proj)]
    analysis_output(a.out)
    dump(a.out/'metrics.json',{'status':'EXPLORATORY_E1B','rows':output,'sklearn_version':sklearn.__version__,
        'primary_AR_measure':'test projection AUROC; §102 04:50CEST amendment, frozen template-cluster bootstrap',
        'secondary_AR_measure':'signed E1 real-gap fidelity ratio, unchanged normalization',
        'bootstrap':{'window_and_AR_auroc':'2000templateclusters,testonly,fixeddevfit;seed20261023','fidelity':'exactE1 2000withinvalueitembootstrap;seed20261024,fixedrealgap'},
        'upstream_seals':{'input':sha(a.inputs/'INPUT_SEAL.json'),'collection':sha(a.collection/'SCORE_SEAL.json'),'W1':sha(a.w1/'ANALYSIS_SEAL.json'),'E1':sha(a.e1/'SCORE_SEAL.json')},'GPU_hours':0})
    from .followup_packed import jsonl
    jsonl(a.out/'predictions.jsonl',predictions)
    lines=['**Prediction (§102):** Continuation-revealing structure rows and meaning rows have high window ceiling and AR fidelity; non-revealing count rows have low values on both. Oracle remains low on the revealing structure rows.','',
        '**Assessment:** All 25 rows are reported below. The qualitative “high/low” prediction has no registered numeric cutoff; assess its pattern from the paired estimates and CIs, without adding a threshold. The integrator must add a plain-language held/partly-held/did-not-hold assessment after reviewing this complete table.','',
        'EXPLORATORY. Primary AR metric is test projection AUROC (§102 04:50 CEST amendment); gap fidelity is secondary. Window model: character 1–4-gram TF–IDF, L2 logistic C=1, fixed dev templates only; no test tuning. This is a model-specific text predictability baseline, not an information-theoretic ceiling. Prefix and description fidelity are the unchanged sealed E1 values. Their projection AUROCs were added after seeing E1 results.','',
        '| Row | Class | Window AUROC [95% CI] | AR continuation projection AUROC — PRIMARY [95% CI] | AR continuation fidelity — SECONDARY [95% CI] | AR on prefix fidelity | AR description fidelity | Oracle W1 AUROC |',
        '|---|---|---|---|---|---:|---:|---:|']
    for r in output:
        def auc(v):return f"{v['auroc']:.4f} [{v['lo']:.4f}, {v['hi']:.4f}]"
        f=r['AR_continuation_fidelity'];fv='undefined' if f['fidelity'] is None else f"{f['fidelity']:.4f} [{f['ci95'][0]:.4f}, {f['ci95'][1]:.4f}]"
        lines.append('| '+' | '.join([r['feature'],r['class'],auc(r['window_ceiling']),auc(r['AR_continuation_projection_auroc']),fv,str(r['AR_on_prefix_fidelity']['fidelity']),str(r['AR_description_fidelity']['fidelity']),str(r['Oracle_W1_auroc']['auroc'])])+' |')
    (a.out/'RESULTS.md').write_text('\n'.join(lines)+'\n');seal(a.out,['metrics.json','predictions.jsonl','RESULTS.md'],'EXPLORATORY_E1B_CPU_ANALYSIS_SEALED')


def paired_auroc_contrasts(scores,y,groups,n_boot=BOOT):
    from mats.metrics import auroc_labels,cluster_bootstrap
    s={k:np.asarray(v,float) for k,v in scores.items()};y=np.asarray(y,bool)
    out={};boots={}
    for arm in ['text_only','text_wrong_activation','activation_only']:
        stat=lambda ix:auroc_labels(s['text_activation'][ix],y[ix])-auroc_labels(s[arm][ix],y[ix])
        lo,hi,samples=cluster_bootstrap(stat,groups,n_boot=n_boot,seed=SEED,return_samples=True)
        out['b_minus_'+{'text_only':'c','text_wrong_activation':'d','activation_only':'a'}[arm]]={'difference':float(stat(np.arange(len(y)))),'ci95':[float(lo),float(hi)]}
        boots[arm]=samples
    return out,boots


def e12(a):
    import common
    from mats.metrics import auroc_ci
    verify(a.inputs,'INPUT_SEAL.json');verify(a.collection);verify(a.w1,'ANALYSIS_SEAL.json')
    oracle_primary=getattr(a,'oracle_primary',False)
    if oracle_primary:
        # §99 f70894e1 permits the sealed, complete Oracle grid from the incomplete pack.
        # Check the original parent and both phase seals without changing any collection file.
        for phase in ['olens_native','olens_context']:
            if read(a.collection/'run.json')['paths'].get(phase,{}).get('complete') is not True:raise ValueError('Oracle path incomplete')
            verify(a.collection/(phase.replace('_','-')+'-units'))
    elif not read(a.collection/'SCORE_SEAL.json')['status'].endswith('_COMPLETE'):raise ValueError('E12 collection incomplete')
    items=rows(a.inputs/'items.input.jsonl');templates=read(a.inputs/'templates.json');reader_scores={};native_status=read(a.collection/'PREFIX_PREFLIGHT.json')
    scope=['olens'] if oracle_primary else (['nla'] if getattr(a,'reader_scope','all')=='nla' else ['olens','nla'])
    for name in scope:
        path=a.collection/name
        if not path.exists():
            if name=='olens' or scope==['nla'] or not isinstance(native_status.get(name),dict):raise ValueError('missing reader without preflight record')
            continue
        verify(path)
        if read(path/'provenance.json')['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('E12 lineage mismatch')
        rs=rows(path/'scores.jsonl');expected={(r['id'],arm) for r in items for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
        if len(rs)!=len(expected) or {(r['id'],r['arm']) for r in rs}!=expected:raise ValueError('incomplete four-arm grid')
        reader_scores[name]={(r['id'],r['arm']):r for r in rs}
    # Only after all score seals pass do labels and the sealed W1 baseline join.
    labels=labels_for(a,'e12');receipt=read(ROOT/'results/g_agreement/understand/PREPARATION.json');assembled=Path(receipt['W1_readonly_root'])/'w1-assembled'
    baseline={}
    for part,filename in [('target','scores.target.jsonl'),('nla','scores.nla.jsonl')]:
        verify(assembled/part)
        baseline.update({(r['id'],r['reader']):r for r in rows(assembled/part/filename) if r['arm']=='true'})
    output=[];class_boots={}
    for name,index in reader_scores.items():
        for feature,spec in sorted(templates.items()):
            keys=[r['id'] for r in items if r['feature']==feature];y=np.array([labels[k]['value']==spec['values'][0] for k in keys]);groups=[labels[k]['cluster'] for k in keys]
            scores={arm:np.array([index[k,arm]['score'] for k in keys]) for arm in ['activation_only','text_activation','text_only','text_wrong_activation']}
            contrasts,boots=paired_auroc_contrasts(scores,y,groups)
            ref=np.array([baseline[k,name]['scores'] for k in keys],float);now=np.array([index[k,'activation_only']['scores'] for k in keys],float)
            if ref.shape!=now.shape or ref.shape!=(84,2):raise ValueError('baseline phrasing mismatch')
            baseline_auc=asdict(auroc_ci(ref.mean(1),y,groups,n_boot=BOOT,seed=SEED))
            output.append({'reader':name,'feature':feature,'class':spec['class'],'arms':{arm:asdict(auroc_ci(v,y,groups,n_boot=BOOT,seed=SEED)) for arm,v in scores.items()},
                'contrasts':contrasts,'W1_reproduction':{'max_abs_phrasing_score_difference':float(np.max(np.abs(now-ref))),'mean_abs_phrasing_score_difference':float(np.mean(np.abs(now-ref))),'W1_auroc':baseline_auc,'a_minus_W1_auroc':float(asdict(auroc_ci(scores['activation_only'],y,groups,n_boot=BOOT,seed=SEED))['auroc']-baseline_auc['auroc']),'exclusion_tolerance':None}})
            class_boots.setdefault((name,spec['class']),[]).append((scores,y,groups))
    classes=[]
    for (name,cls),rowboots in class_boots.items():
        rr=[r for r in output if r['reader']==name and r['class']==cls];contrasts={}
        from mats.metrics import cluster_bootstrap,auroc_labels
        rng=np.random.default_rng(SEED);draws=[]
        for scores,y,groups in rowboots:
            # Independent within-row template resamples; the same draw is used for every arm/contrast.
            seed=int(rng.integers(0,2**32));current={}
            for arm in ['text_only','text_wrong_activation','activation_only']:
                stat=lambda ix:auroc_labels(scores['text_activation'][ix],y[ix])-auroc_labels(scores[arm][ix],y[ix])
                current[arm]=cluster_bootstrap(stat,groups,n_boot=BOOT,seed=seed,return_samples=True)[2]
            draws.append(current)
        for arm,key in [('text_only','b_minus_c'),('text_wrong_activation','b_minus_d'),('activation_only','b_minus_a')]:
            samples=np.mean([v[arm] for v in draws],axis=0)
            contrasts[key]={'difference':float(np.mean([r['contrasts'][key]['difference'] for r in rr])),'ci95':np.quantile(samples,[.025,.975]).tolist()}
        classes.append({'reader':name,'class':cls,'n_rows':len(rr),'contrasts_equal_row_mean':contrasts,'mean_arm_auroc':{arm:float(np.mean([r['arms'][arm]['auroc'] for r in rr])) for arm in rr[0]['arms']}})
    analysis_output(a.out);dump(a.out/'metrics.json',{'status':'EXPLORATORY_E12','analysis_scope':'PRIMARY_ORACLE_ONLY_f70894e1' if oracle_primary else ('NLA_ONLY_RETRY_f70894e1' if scope==['nla'] else 'COMPLETE_AVAILABLE_READERS'),'rows':output,'classes':classes,'native_prefix_status':native_status,'GPU_hours':0,'upstream_seals':{'inputs':sha(a.inputs/'INPUT_SEAL.json'),'collection':sha(a.collection/'SCORE_SEAL.json'),'W1':sha(a.w1/'ANALYSIS_SEAL.json')}})
    lines=['**Prediction (§99):** On structure rows, text alone is above chance and b ≈ c ≈ d; on meaning rows b > d.','',
        '**Assessment:** The complete four-arm estimates and paired contrasts follow. No equivalence margin or pass threshold is registered; the integrator must add the plain-language prediction assessment after reviewing all rows.','',
        'EXPLORATORY. Prefix arms are outside both readers’ training distribution. Text-only leaves the placeholder’s own embedding/residual untouched. Frozen W1 donors are opposite-value, matched within template; no redraw. Native W1 score and AUROC reproduction differences are reported without tolerance-based exclusions. NLA unavailability is explicit; KV-olens is not tested.','',
        '| Reader | Row | Class | a | b | c | d | b−c [95% CI] | b−d [95% CI] | b−a [95% CI] |',
        '|---|---|---|---:|---:|---:|---:|---|---|---|']
    for r in output:
        def fmt(c):return f"{c['difference']:.4f} [{c['ci95'][0]:.4f}, {c['ci95'][1]:.4f}]"
        lines.append('| '+' | '.join([r['reader'],r['feature'],r['class']]+[f"{r['arms'][arm]['auroc']:.4f}" for arm in ['activation_only','text_activation','text_only','text_wrong_activation']]+[fmt(r['contrasts'][k]) for k in ['b_minus_c','b_minus_d','b_minus_a']])+' |')
    lines+=['','Class means/CIs and every native W1 reproduction difference: `metrics.json`. Prefix support: '+str(native_status)]
    (a.out/'RESULTS.md').write_text('\n'.join(lines)+'\n');seal(a.out,['metrics.json','RESULTS.md'],'EXPLORATORY_E12_CPU_ANALYSIS_SEALED')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('experiment',choices=['e1b','e12'])
    for name in ['inputs','collection','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--w1',type=Path,default=ROOT/'results/g_agreement/blindspot/w1/analysis');p.add_argument('--e1',type=Path,default=ROOT/'results/g_agreement/understand/e1')
    p.add_argument('--oracle-primary',action='store_true',help='§99 f70894e1: analyse only complete sealed Oracle paths from an incomplete pack')
    p.add_argument('--reader-scope',choices=['all','nla'],default='all',help='NLA-only completion from §99 f70894e1; metrics unchanged')
    a=p.parse_args()
    if a.oracle_primary and a.reader_scope!='all':p.error('--oracle-primary and --reader-scope are exclusive')
    if a.experiment!='e12' and (a.oracle_primary or a.reader_scope!='all'):p.error('reader scope applies only to E12')
    {'e1b':e1b,'e12':e12}[a.experiment](a)


if __name__=='__main__':main()
