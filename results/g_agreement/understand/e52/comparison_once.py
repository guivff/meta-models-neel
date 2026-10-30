"""E52 once-only R2/R3 comparison, strictly after E49's sealed analysis."""
from pathlib import Path
import json
import math
import subprocess
import time
import sys
from build_basis import ROOT,HERE,CACHE,sha,read,dump
from run_labels import verify
from core import rule_r2

REQUEST=HERE/'COMPARISON_REQUEST_2026-10-27.json'
CLAIM=CACHE/'COMPARISON_ONCE.json'

def at(doc,pointer):
    if not isinstance(pointer,str) or not pointer.startswith('/'):raise ValueError('explicit JSON pointer required')
    value=doc
    for key in pointer[1:].split('/'):
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value

def evaluate_r3(rows,forecast,human,mode):
    if len(rows)!=16 or len({r['row'] for r in rows})!=16:
        raise ValueError('all16 E49 rows required')
    if set(forecast)!={r['row'] for r in rows} or set(human)!=set(forecast):raise ValueError('forecast/baseline row coverage')
    gated=[];excluded=[];missing=[]
    for r in rows:
        passes=r['probe_auroc']>=.90 and r['base_text_auroc']>=.85 and (r['class']=='content' or r['bow_auroc']<=.65)
        if passes:
            if forecast[r['row']]=='NO FORECAST':
                missing.append(r['row']);continue
            if forecast[r['row']] not in ('REPORTED','MISSED'):raise ValueError('unknown forecast value')
            true='REPORTED' if r['correct_value_rate']>=.10 and r['correct_value_rate']>r['wrong_only_rate'] else 'MISSED'
            gated.append({'row':r['row'],'truth':true,'prediction':forecast[r['row']],
                'correct':forecast[r['row']]==true,'human_prediction':human[r['row']],'human_correct':human[r['row']]==true})
        else:excluded.append(r['row'])
    n=len(gated);correct=sum(r['correct'] for r in gated)
    if mode!='scale_9_over_16':raise ValueError('clarification3 requires scaled gated-row accuracy')
    evaluable=n>=8
    low=correct/n<=9/16 if evaluable else None
    total=n+len(missing)
    return {'status':'EVALUABLE' if evaluable else 'NOT EVALUABLE','met':correct/n>=.75 if evaluable else None,'correct':correct,'n_gated':total,'n_forecasted_gated':n,'accuracy':correct/n if n else None,
        'minimum_forecasted_gated_rows':8,'not_evaluable_reason':None if evaluable else 'fewer than8 forecasted gated E49 rows; descriptive only',
        'gated_no_forecast_rows':missing,'sensitivity_no_forecast_wrong':{'correct':correct,'denominator':total,'accuracy':correct/total if total else None,'no_forecast_counted_wrong':len(missing)},
        'human_correct':sum(r['human_correct'] for r in gated),'human_accuracy':sum(r['human_correct'] for r in gated)/n if n else None,
        'rows':gated,'excluded_rows':excluded,'falsifier_low_accuracy':low,'truth':'native Oracle correct-value rate >=0.10 and >wrong-only rate; forced choice not used'}

def comparison(request):
    verify(ROOT,read(HERE/'COMPARISON_CODE_SEAL_2026-10-27.json')['files'])
    if read(HERE/'primary/E36/R1_SANITY.json')['met'] is not True:raise ValueError('R1 failed; no outcome comparison')
    for bank in ('W1','E36','E49'):
        verify(HERE/bank,read(HERE/bank/'LABEL_SEAL.json')['files'])
        verify(HERE/'primary'/bank,read(HERE/'primary'/bank/'LABEL_SEAL.json')['files'])
    forecast=read(HERE/'E49_JFORECAST.json')
    if sha(HERE/'E49_JFORECAST.json')!=read(HERE/'E49_JFORECAST.sha256.json')['sha256']:raise ValueError('prospective forecast changed')
    delivery=read(ROOT/request['verified_inputs'])
    if (delivery.get('issuer')!='integrator' or delivery.get('status')!='VERIFIED_FINAL_ANALYSES'
            or delivery.get('E49_analysis_complete') is not True):raise ValueError('final verified E49 analysis required')
    timing=delivery['timing']
    committed=subprocess.check_output(['git','show',timing['forecast_commit']+':'+str((HERE/'E49_JFORECAST.json').relative_to(ROOT))],cwd=ROOT)
    if committed!=(HERE/'E49_JFORECAST.json').read_bytes():raise ValueError('forecast commit bytes differ')
    epoch=int(subprocess.check_output(['git','show','-s','--format=%ct',timing['forecast_commit']],cwd=ROOT))
    if not epoch==timing['forecast_commit_epoch']<=timing['first_reader_score_epoch']<=timing['reader_unseal_epoch']:
        raise ValueError('prospective chronology violated')
    e49seal=delivery['e49_analysis_seal'];sealpath=Path(e49seal['path'])
    if sha(sealpath)!=e49seal['sha256']:raise ValueError('E49 analysis seal differs')
    verify(sealpath.parent,read(sealpath)['files'])
    docs={};docmeta=delivery['documents']
    for key,d in docmeta.items():
        path=Path(d['path']);seal=Path(d['seal_path'])
        if (sha(path)!=d['sha256'] or sha(seal)!=d['seal_sha256'] or read(seal)['files'][d['member']]!=d['sha256']
                or (seal.parent/d['member']).resolve()!=path.resolve()):raise ValueError('source analysis document not sealed')
        docs[key]=read(path)
    def number(ref,bank):
        if ref is None:return None
        if bank=='E49' and Path(docmeta[ref['document']]['seal_path']).resolve()!=sealpath.resolve():raise ValueError('E49 outcomes must come from its final analysis')
        x=at(docs[ref['document']],ref['pointer'])
        if type(x) not in (int,float) or not math.isfinite(x) or not 0<=x<=1:raise ValueError('finite rate/AUROC required')
        return x
    joined={}
    for bank in ('W1','E36','E49'):
        labels=read(HERE/bank/'ROW_LABELS.json')['rows'];meta=delivery['banks'][bank]
        if set(meta)!={x['row'] for x in labels}:raise ValueError('complete bank outcomes required')
        joined[bank]=[]
        for x in labels:
            r=meta[x['row']]
            if r.get('reader')!='oracle' or r.get('layer')!=44 or r.get('split')!='test':raise ValueError('native Oracle block44 test measure required')
            native=number(r.get('unprompted_mention_rate'),bank);forced=number(r.get('forced_choice_auroc'),bank)
            if native is None and r.get('no_sealed_readouts_available') is not True:raise ValueError('forced-choice fallback only when no readouts exist')
            if native is None and (bank=='E49' or forced is None):raise ValueError('required outcome missing')
            record={'row':x['row'],'class':x['class'],'E1536':x['enrichment']['1536']['enrichment'] if bank!='E49' else None,'probe_auroc':number(r['probe_auroc'],bank),
                'unprompted_mention_rate':native,'forced_choice_auroc':forced}
            if bank=='E49':
                record.update(bow_auroc=number(r['bow_auroc'],bank),base_text_auroc=number(r['base_text_auroc'],bank),
                    correct_value_rate=number(r['correct_value_rate'],bank),wrong_only_rate=number(r['wrong_only_rate'],bank))
                if record['correct_value_rate'] is None or record['wrong_only_rate'] is None:raise ValueError('R3 requires native correct-value and wrong-only rates')
            joined[bank].append(record)
    r2={bank:rule_r2(joined[bank]) for bank in ('W1','E36')}
    precall=HERE.parent/'e49/PRECALLS.json'
    if sha(precall)!=request['human_precalls_sha256']:raise ValueError('original blind pre-calls changed')
    human={x['name']:'REPORTED' if x['prediction']=='sayable' else 'MISSED' for x in read(precall)['predictions']}
    predictions={x['row']:x['oracle_prediction'] for x in forecast['rows']}
    labelmap={x['row']:x['label'] for x in read(HERE/'primary/E49/ROW_LABELS.json')['rows']}
    if any(x['prediction'] not in ('sayable','unsayable') for x in read(precall)['predictions']):raise ValueError('unknown original blind pre-call')
    if any(x['label']=='NO FORECAST' and not x.get('computational_reason') for x in forecast['rows']):raise ValueError('NO FORECAST needs a computational reason')
    if predictions!={k:'NO FORECAST' if v=='NO FORECAST' else 'REPORTED' if v=='IN-J' else 'MISSED' for k,v in labelmap.items()}:raise ValueError('forecast must follow frozen J labels')
    r3=evaluate_r3(joined['E49'],predictions,human,request['falsifier_denominator'])
    both_fail=all(v['met'] is False for v in r2.values())
    falsifier=None if any(v['met'] is None for v in r2.values()) or r3['falsifier_low_accuracy'] is None else both_fail and r3['falsifier_low_accuracy']
    return {'experiment':'E52','status':'COMPLETE_ONCE_ONLY_COMPARISON','R1':read(HERE/'primary/E36/R1_SANITY.json'),
        'R2':{'met':None if any(v['met'] is None for v in r2.values()) else all(v['met'] for v in r2.values()),'banks':r2},
        'R3':r3,'falsifier':{'met':falsifier},'prospective_timing':timing,'forecast_sha256':sha(HERE/'E49_JFORECAST.json'),
        'input_receipt_sha256':sha(ROOT/request['verified_inputs']),'E49_analysis_seal_sha256':e49seal['sha256'],
        'measure_note':'native unprompted mention primary; forced choice (off-distribution) only for R2 rows without sealed readouts'}

def main():
    request=read(REQUEST)
    prerequisites=[ROOT/request['verified_inputs'],HERE/'E49_JFORECAST.json',HERE/'primary/E49/LABEL_SEAL.json']
    if request['falsifier_denominator'] is None or not all(p.exists() for p in prerequisites):
        print('E52 comparison WAITING: final E49 analysis/forecast or registered ruling absent; no claim or outcome access');return 2
    with CLAIM.open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','epoch':time.time()},f)
    result=comparison(request);out=HERE/'comparison_169';out.mkdir(exist_ok=False)
    dump(out/'METRICS.json',result)
    verdict=lambda x:'MET' if x is True else 'NOT MET' if x is False else 'NOT EVALUABLE'
    sensitivity=result['R3']['sensitivity_no_forecast_wrong'];r3=result['R3']
    (out/'RESULTS.md').write_text('# E52 once-only comparison\n\n'+'\n\n'.join(k+': '+verdict(result[k]['met']) for k in ('R1','R2'))+'\n\nR3 headline: '+verdict(r3['met'])+f"; {r3['correct']}/{r3['n_forecasted_gated']} forecasted gated rows correct; accuracy={r3['accuracy']}"+'\n\nR3 sensitivity (every gated NO FORECAST scored wrong): '+f"{sensitivity['correct']}/{sensitivity['denominator']} correct; accuracy={sensitivity['accuracy']}; NO FORECAST={sensitivity['no_forecast_counted_wrong']}"+'\n\nFalsifier: '+verdict(result['falsifier']['met'])+'\n')
    dump(out/'ANALYSIS_SEAL.json',{'files':{p.name:sha(p) for p in out.iterdir()}})
    print('E52 COMPLETE_ONCE_ONLY_COMPARISON');return 0

if __name__=='__main__':
    if len(sys.argv)!=1:raise SystemExit('No overrides; use the committed once-only command')
    raise SystemExit(main())
