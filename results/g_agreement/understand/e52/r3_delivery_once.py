"""R3-only delivery adapter; registered evaluator remains unchanged."""
import json
import subprocess
import time
from pathlib import Path
from build_basis import ROOT, HERE, sha, read, dump
from run_labels import verify
from comparison_once import evaluate_r3, CLAIM


def posthoc(r3):
    rows=r3['rows']
    groups={k:[r for r in rows if r['truth']==k] for k in ('REPORTED','MISSED')}
    hits={k:sum(r['correct'] for r in rr) for k,rr in groups.items()}
    rates={k:hits[k]/len(rr) if rr else None for k,rr in groups.items()}
    reported=groups['REPORTED']
    return {'label':'POST HOC; section169 dated note b5313eb1; no rule change',
        'constant_MISSED':{'correct':len(groups['MISSED']),'n':len(rows),'accuracy':len(groups['MISSED'])/len(rows)},
        'balanced_accuracy':sum(rates.values())/2 if all(v is not None for v in rates.values()) else None,
        'class_hit_rates':rates,'reported_correct':hits['REPORTED'],'reported_n':len(reported),
        'reported_rows':{r['row']:r['prediction'] for r in reported},
        'all_reported_correct':all(r['correct'] for r in reported) if reported else None,
        'beats_constant_MISSED':r3['accuracy']>len(groups['MISSED'])/len(rows)}


def main():
    request=read(HERE/'R3_DELIVERY_REQUEST_2026-10-27.json')
    verify(ROOT,read(HERE/'R3_DELIVERY_CODE_SEAL_2026-10-27.json')['files'])
    verify(ROOT,read(HERE/'COMPARISON_CODE_SEAL_2026-10-27.json')['files'])
    verify(ROOT,request['files'])
    source=ROOT/request['analysis_dir']; seal=read(source/'ANALYSIS_SEAL.json')
    assert seal['status']=='COMPLETE_ONCE'
    verify(source,seal['files'])
    for bank in ('E36','E49'):
        verify(HERE/'primary'/bank,read(HERE/'primary'/bank/'LABEL_SEAL.json')['files'])
    assert read(HERE/'primary/E36/R1_SANITY.json')['met'] is True
    forecast_path=HERE/'E49_JFORECAST.json'
    assert sha(forecast_path)==read(HERE/'E49_JFORECAST.sha256.json')['sha256']
    provenance=ROOT/request['provenance_dir']; output=read(provenance/'OUTPUT_SEAL.json')
    assert sha(provenance/'OUTPUT_SEAL.json')==seal['output_seal_sha256']
    assert sha(provenance/'GO_ACCEPTED.json')==output['files']['GO_ACCEPTED.json']
    go=read(provenance/'GO_ACCEPTED.json'); commit=go['forecast_commit']
    assert subprocess.check_output(['git','show',commit+':'+str(forecast_path.relative_to(ROOT))],cwd=ROOT)==forecast_path.read_bytes()
    epoch=int(subprocess.check_output(['git','show','-s','--format=%ct',commit],cwd=ROOT))
    assert epoch<=go['issued_epoch'] and go['release'] is True
    assert seal['bank_seal_sha256']==go['bank_seal_sha256']
    assert sha(HERE.parent/'e49/PRECALLS.json')==read(HERE/'COMPARISON_REQUEST_2026-10-27.json')['human_precalls_sha256']
    # Same global claim as the combined command: a later invocation cannot repeat R3.
    with CLAIM.open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','scope':'R3 only; R2 remains pending','epoch':time.time()},f)
    gates=read(source/'GATES.json'); native=read(source/'NATIVE_PRIMARY.json')
    assert set(native['rows'])==set(gates['qualified_rows'])==set(native['qualified_rows'])
    labels=read(HERE/'primary/E49/ROW_LABELS.json')['rows']
    forecasts=read(forecast_path)['rows']; predictions={x['row']:x['oracle_prediction'] for x in forecasts}
    assert predictions=={x['row']:'REPORTED' if x['label']=='IN-J' else 'NO FORECAST' if x['label']=='NO FORECAST' else 'MISSED' for x in labels}
    assert all(x.get('computational_reason') for x in forecasts if x['label']=='NO FORECAST')
    assert set(gates['rows'])==set(predictions)
    records=[]
    for label in labels:
        name=label['row']; g=gates['rows'][name]
        passes=g['probe']>=.90 and g['base']>=.85 and (label['class']=='content' or g['bow']<=.65)
        assert passes==(name in gates['qualified_rows'])
        n=native['rows'][name]['oracle'] if passes else None
        if n:
            counts=n['counts']; assert n['n']==84 and sum(counts.values())==84
            assert n['correct_mention_rate']==(counts['correct_only']+counts['both'])/84
            assert n['wrong_only_rate']==counts['wrong_only']/84
        records.append({'row':name,'class':label['class'],'probe_auroc':g['probe'],'base_text_auroc':g['base'],
            'bow_auroc':g['bow'],'correct_value_rate':n['correct_mention_rate'] if n else None,
            'wrong_only_rate':n['wrong_only_rate'] if n else None})
    human={x['name']:'REPORTED' if x['prediction']=='sayable' else 'MISSED' for x in read(HERE.parent/'e49/PRECALLS.json')['predictions']}
    r3=evaluate_r3(records,predictions,human,'scale_9_over_16')
    assert all(r['truth']==native['rows'][r['row']]['oracle']['forecast_truth'] for r in r3['rows'])
    extras=posthoc(r3)
    result={'experiment':'E52','status':'COMPLETE_ONCE_ONLY_R3','R3':r3,'post_hoc':extras,
        'R2':'PENDING_SEPARATE_ONCE_ONLY_INPUT_BINDING; not evaluated here',
        'falsifier':{'R3_part':r3['falsifier_low_accuracy'],'whole':False if r3['falsifier_low_accuracy'] is False else None},
        'forecast_sha256':sha(forecast_path),'analysis_seal_sha256':sha(source/'ANALYSIS_SEAL.json'),
        'request_sha256':sha(HERE/'R3_DELIVERY_REQUEST_2026-10-27.json'),
        'chronology':{'forecast_commit':commit,'forecast_commit_epoch':epoch,'go_issued_epoch':go['issued_epoch'],
            'evidence':'Final sealed E49 analysis validates GO before all E49 reader calls; no first-score timestamp invented.'}}
    out=HERE/'r3_169';out.mkdir(exist_ok=False);dump(out/'METRICS.json',result)
    s=r3['sensitivity_no_forecast_wrong']; b=extras['constant_MISSED']
    report=f"# E52 R3 — 2026-10-27\n\nRegistered R3: {'MET' if r3['met'] else 'NOT MET'}; {r3['correct']}/{r3['n_forecasted_gated']} = {r3['accuracy']:.1%}.\n\nSensitivity (all gated NO FORECAST wrong): {s['correct']}/{s['denominator']} = {s['accuracy']:.1%}; NO FORECAST={s['no_forecast_counted_wrong']}.\n\nPost hoc (§169 dated note b5313eb1): constant-MISSED baseline {b['correct']}/{b['n']} = {b['accuracy']:.1%}; balanced accuracy {extras['balanced_accuracy']:.1%}; REPORTED rows correctly forecast {extras['reported_correct']}/{extras['reported_n']}.\n\n"
    report+='; '.join(f"{k}: forecast {v}" for k,v in extras['reported_rows'].items())+'.\n\n'
    if not extras['beats_constant_MISSED']:report+='R3 is uninformative at this base rate: the forecast does not beat the constant-MISSED baseline.\n\n'
    report+='Registered rules and frozen forecasts unchanged. R2 is not evaluated by this command.\n'
    (out/'RESULTS.md').write_text(report)
    dump(out/'ANALYSIS_SEAL.json',{'files':{p.name:sha(p) for p in out.iterdir()},'code_seal_sha256':sha(HERE/'R3_DELIVERY_CODE_SEAL_2026-10-27.json')})
    print(report)

if __name__=='__main__':main()
