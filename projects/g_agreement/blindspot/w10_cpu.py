"""§86 budget-limited frozen mode judge and once-only registered CPU analysis.

No target/reader inference. Do not run analyse until the 200 blinded judge results
are complete. The frozen 80 scripted assessments and all score seals are required.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
import math
import os
from pathlib import Path
import time
import numpy as np
from . import protocol as P
from . import analysis as A
from . import w10_checks as C

READERS=(('olens',44),('nla',42),('jlens',44))


def seal_named(out,names,filename,status):
    P.dump(Path(out)/filename,{'status':status,'files':{n:P.sha(Path(out)/n) for n in names}})


def preflight(bank,outputs):
    bank,outputs=Path(bank),Path(outputs);P.verify(bank,'INPUT_SEAL.json')
    m=json.loads((bank/'manifest.json').read_text())
    required={
        'CAPTURE_SEAL.json':{'acts42.npy','acts44.npy','items.order.json','surprisal.jsonl','provenance.json'},
        'SCORE_SEAL.json':{'scores.jsonl','items.order.json','surprisal.jsonl','provenance.json','FORECAST.json'},
        'MODE_GENERATION_SEAL.json':{'mode_generations.jsonl','provenance.json'}}
    for s,names in required.items():
        receipt=P.verify(outputs,s)
        if not names<=set(receipt['files']):raise ValueError('seal lacks required files: '+s)
    if P.sha(Path(C.__file__))!=m['source_files']['projects/g_agreement/blindspot/w10_checks.py']:
        raise ValueError('must use the frozen mode-check rules')
    if P.sha(Path(A.__file__))!='45a06d29445cc678fb4e71edce4944b7e481357662a1d59f8c8203a3c4e4d75c':
        raise ValueError('W1 grouped-probe/bootstrap analysis source changed')
    p=json.loads((outputs/'provenance.json').read_text())
    if p['source_files']!=m['source_files'] or p['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json'):
        raise ValueError('scored bank/source lineage mismatch')
    items=P.rows(bank/'items.input.jsonl');ids=[x['id'] for x in items]
    if len(ids)!=4368 or len(set(ids))!=4368 or json.loads((outputs/'items.order.json').read_text())!=ids:
        raise ValueError('capture item/order coverage mismatch')
    raw=P.rows(outputs/'scores.jsonl');keys=[(r['id'],r['reader'],r['layer'],r['arm']) for r in raw]
    expected={(i,r,l,a) for i in ids for r,l in READERS for a in ('true','random_donor')}
    if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('incomplete/duplicate score grid')
    for r in raw:
        if r['status']!='COMPLETE' or not isinstance(r['scores'],list) or len(r['scores'])!=2 or not np.isfinite(r['scores']).all():
            raise ValueError('incomplete or nonfinite phrasing scores')
    checks=P.rows(bank/'mode_checks.input.jsonl');gens=P.rows(outputs/'mode_generations.jsonl')
    if len(checks)!=280 or len(gens)!=280 or {x['id'] for x in gens}!={x['id'] for x in checks}:
        raise ValueError('mode-generation coverage mismatch')
    return m,items,dict(zip(keys,raw))


def judge(packet,out,model='openai/gpt-5-mini',cap=3.0):
    """One budget-reserved API pass; no retries, no raw HTTP error/key logging."""
    import requests
    packet,out=Path(packet),Path(out);P.verify(packet,'MODE_PACKET_SEAL.json')
    if out.exists():raise ValueError('judge directory already exists; preserve it, no automatic duplicate')
    if not 0<cap<=3:raise ValueError('judge cap must be <=$3')
    rows=P.rows(packet/'judge_packet.jsonl')
    if len(rows)!=200 or len({r['id'] for r in rows})!=200:raise ValueError('need exact 200 blinded packets')
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key:raise ValueError('OPENROUTER_API_KEY is absent; no key printed')
    try:
        response=requests.get('https://openrouter.ai/api/v1/models',timeout=15)
        response.raise_for_status();meta=next(x for x in response.json()['data'] if x['id']==model)
    except Exception as exc:
        raise RuntimeError('judge pricing/network preflight failed: '+type(exc).__name__) from None
    price=meta['pricing'];inp=float(price['prompt']);completion=float(price['completion']);fixed=float(price.get('request',0))
    if not all(math.isfinite(x) and x>=0 for x in (inp,completion,fixed)):raise ValueError('invalid model prices')
    max_tokens=2048
    reserves=[(len(r['prompt'].encode('utf-8'))+4096)*inp+max_tokens*completion+fixed for r in rows]
    if sum(reserves)>cap:raise ValueError('conservative full-judge price bound exceeds cap; no calls made')
    out.mkdir(parents=True,exist_ok=False)
    spent=0.;judged=[]
    ledger={'model':model,'pricing':price,'cap_usd':cap,'reserved_full_pass_usd':sum(reserves),
        'api_calls':0,'charged_or_reserved_usd':0.,'packet_seal_sha256':P.sha(packet/'MODE_PACKET_SEAL.json')}
    P.dump(out/'budget.json',ledger)
    for row,reserve in zip(rows,reserves):
        if spent+reserve>cap:raise RuntimeError('budget exhausted; no further request sent')
        # Reserve the full worst-case amount before sending; ambiguous failures stay charged.
        spent+=reserve;ledger.update(api_calls=ledger['api_calls']+1,charged_or_reserved_usd=spent)
        P.dump(out/'budget.json',ledger)
        try:
            response=requests.post('https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization':'Bearer '+key},json={'model':model,'temperature':0,'max_tokens':max_tokens,
                    'messages':[{'role':'user','content':row['prompt']}]},timeout=60)
            response.raise_for_status();body=response.json()
            result=json.loads(body['choices'][0]['message']['content'])
            if any(type(result.get(k)) is not bool for k in ('A_follows','B_follows')):
                raise ValueError('judge must return boolean A_follows/B_follows')
            charge=body.get('usage',{}).get('cost')
            if isinstance(charge,(int,float)) and math.isfinite(charge) and charge>=0:
                spent+=charge-reserve
            ledger.update(charged_or_reserved_usd=spent);P.dump(out/'budget.json',ledger)
        except Exception as exc:
            P.dump(out/'FAILURE.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,'api_calls':ledger['api_calls'],
                'charged_or_reserved_usd':spent,'automatic_retry':False})
            raise RuntimeError('judge stopped; see sanitized FAILURE.json; no automatic retry') from None
        assessed={'id':row['id'],'A_follows':result['A_follows'],'B_follows':result['B_follows'],
            'reason':str(result.get('reason','')),'model':model,'request_id':body.get('id')}
        judged.append(assessed)
        with (out/'judged.partial.jsonl').open('a') as f:f.write(json.dumps(assessed,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    P.jsonl(out/'judged.jsonl',judged)
    P.dump(out/'provenance.json',{'packet_seal_sha256':P.sha(packet/'MODE_PACKET_SEAL.json'),'model':model,
        'frozen_prompt':'verbatim per packet; no labels or reader scores supplied','judgements':200})
    seal_named(out,['judged.jsonl','budget.json','provenance.json'],'MODE_JUDGE_SEAL.json','BLINDED_JUDGE_COMPLETE')
    return ledger


def adjudicate(rows):
    mode=[r for r in rows if r['class']=='mode']
    one=[r for r in mode if r['readers']['olens']['evaluable']]
    two=[r for r in one if r['readers']['nla']['evaluable']]
    h1=A._rate(sum(r['readers']['olens']['true']['auroc']<=r['probes']['44']['auroc']-.25+1e-12 for r in one),len(one))
    h2=A._rate(sum(r['nla_minus_oracle']['difference']>=.10-1e-12 and r['nla_minus_oracle']['ci95'][0]>0 for r in two),len(two))
    return {'H1':{**h1,'status':'NOT EVALUABLE' if not one else 'CONFIRMED' if h1['rate']>=.75 else 'NOT MET',
                  'denominator':'Oracle-evaluable mode rows'},
        'H2':{**h2,'status':'NOT EVALUABLE' if not two else 'CONFIRMED' if h2['rate']>=.50 else 'NOT MET',
              'denominator':'mode rows evaluable for both Oracle and NLA'}}


def analyse(bank,outputs,packet,judgements,out):
    bank,outputs,packet,judgements,out=map(Path,(bank,outputs,packet,judgements,out))
    if out.exists():raise ValueError('analysis already exists; no rerun')
    manifest,items,scoremap=preflight(bank,outputs)
    P.verify(packet,'MODE_PACKET_SEAL.json');P.verify(judgements,'MODE_JUDGE_SEAL.json')
    if json.loads((judgements/'provenance.json').read_text())['packet_seal_sha256']!=P.sha(packet/'MODE_PACKET_SEAL.json'):
        raise ValueError('judge packet lineage mismatch')
    pp=json.loads((packet/'provenance.json').read_text())
    if pp['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or pp['generation_seal_sha256']!=P.sha(outputs/'MODE_GENERATION_SEAL.json'):
        raise ValueError('mode packet generation/input lineage mismatch')
    scripted=P.rows(packet/'script_results.jsonl');judged=P.rows(judgements/'judged.jsonl')
    if len(scripted)!=80 or len(judged)!=200 or {x['id'] for x in judged}!={x['id'] for x in P.rows(packet/'judge_packet.jsonl')}:
        raise ValueError('mode assessments incomplete')
    acts={site:np.load(outputs/f'acts{site}.npy',allow_pickle=False) for site in (42,44)}
    if any(h.ndim!=2 or len(h)!=4368 or not np.isfinite(h).all() for h in acts.values()):raise ValueError('invalid activations')
    if P.sha(bank/'labels.DO_NOT_STAGE.jsonl')!=manifest['labels_sha256']:raise ValueError('labels differ from scored freeze')
    # All score, generation, assessment and input checks precede this ground-truth join.
    labels=P.rows(bank/'labels.DO_NOT_STAGE.jsonl');lookup={r['id']:r for r in labels}
    if len(lookup)!=len(labels) or set(lookup)!={x['id'] for x in items}:raise ValueError('label coverage mismatch')
    activity=C.mode_activity(labels,scripted,judged)
    pool=[r for r in labels if r['feature'].startswith('surprisal_')]
    surprise=C.label_surprisal(pool,P.rows(outputs/'surprisal.jsonl'))
    selected_surprise={r['id']:r for r in surprise};index={x['id']:i for i,x in enumerate(items)}
    templates=json.loads((bank/'templates.json').read_text())
    lock=out.with_name(out.name+'.lock.json');lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'status':'STARTED','score_seal_sha256':P.sha(outputs/'SCORE_SEAL.json')},f)
    from mats import metrics
    from scipy.stats import ks_2samp
    rows=[];all_oof=[];saved={}
    with P.logged('w10_registered_analysis_once',extra={'unit':'vzovpasgdwsz71','model_forwards':0}):
        for feature,spec in templates.items():
            is_surprise=feature.startswith('surprisal_')
            local_labels=selected_surprise if is_surprise else lookup
            ids=[x['id'] for x in items if x['feature']==feature and x['id'] in local_labels and local_labels[x['id']]['split']=='test']
            idx=np.array([index[k] for k in ids]);y=np.array([local_labels[k]['value']==spec['values'][0] for k in ids],int)
            groups=np.array([local_labels[k]['cluster'] for k in ids])
            if not len(ids) or len(set(groups))<5 or set(y)!={0,1}:raise ValueError('invalid grouped test population: '+feature)
            row={'feature':feature,'class':spec['class'],'n':len(ids),'n_clusters':len(set(groups)),
                'mode_active':activity.get(feature),'probes':{},'readers':{},'class_values':spec['values']}
            probe={}
            for site in (42,44):
                p,_,folds=A.grouped_probe(acts[site][idx],y,groups,np.arange(len(idx)))
                probe[site]=p;row['probes'][str(site)]=asdict(metrics.auroc_ci(p,y,groups,n_boot=2000,seed=P.SEED))
                all_oof.extend({'id':k,'feature':feature,'layer':site,'score':float(p[j])} for j,k in enumerate(ids))
            true_arrays={}
            for name,site in READERS:
                true=np.array([np.mean(scoremap[k,name,site,'true']['scores']) for k in ids])
                donor=np.array([np.mean(scoremap[k,name,site,'random_donor']['scores']) for k in ids])
                a=asdict(metrics.auroc_ci(true,y,groups,n_boot=2000,seed=P.SEED));d=asdict(metrics.auroc_ci(donor,y,groups,n_boot=2000,seed=P.SEED))
                reasons=[]
                if row['probes'][str(site)]['auroc']<.85:reasons.append('probe below0.85')
                if not .40-1e-12<=d['auroc']<=.60+1e-12:reasons.append('random donor outside[0.40,0.60]')
                if not is_surprise and not activity[feature]['pass']:reasons.append('mode active below70%')
                phrasing=[asdict(metrics.auroc_ci(np.array([scoremap[k,name,site,'true']['scores'][j] for k in ids]),y,groups,n_boot=2000,seed=P.SEED)) for j in range(2)]
                row['readers'][name]={'true':a,'random_donor':d,'evaluable':not reasons,
                    'status':'NOT EVALUABLE' if reasons else 'EVALUABLE','gate_failures':reasons,'phrasing_pairs':phrasing,
                    'probe_minus_reader':row['probes'][str(site)]['auroc']-a['auroc']}
                true_arrays[name]=true
            n,o=true_arrays['nla'],true_arrays['olens']
            row['nla_minus_oracle']={'difference':metrics.auroc_labels(n,y)-metrics.auroc_labels(o,y),
                'ci95':list(metrics.cluster_bootstrap(lambda j:metrics.auroc_labels(n[j],y[j])-metrics.auroc_labels(o[j],y[j]),groups,n_boot=2000,seed=P.SEED))}
            if is_surprise:
                lengths=[np.array([len(items[index[k]]['ids']) for k in ids])[y==side] for side in (1,0)]
                p=float(ks_2samp(*lengths).pvalue);diff=float(abs(lengths[0].mean()-lengths[1].mean()))
                row['length_check']={'ks_p':p,'mean_difference':diff,'status':'LENGTH_CONFOUNDED' if p<=.2 or diff>1 else 'MATCHED','scope':'DESCRIPTIVE; no rematching'}
            saved[feature]={'y':y,'groups':groups,'probe':probe[44],'oracle':true_arrays['olens']}
            rows.append(row)
        far_near=[]
        for mode in ('language','register','audience','format','length','persona','topic'):
            near,far=(saved[mode+'_'+d] for d in ('near','far'))
            groups=np.concatenate([near['groups'],far['groups']]);y=np.concatenate([near['y'],far['y']])
            p=np.concatenate([near['probe'],far['probe']]);o=np.concatenate([near['oracle'],far['oracle']])
            distance=np.concatenate([np.zeros(len(near['y']),int),np.ones(len(far['y']),int)])
            def contrast(j):
                n=j[distance[j]==0];f=j[distance[j]==1]
                gap=lambda k:metrics.auroc_labels(p[k],y[k])-metrics.auroc_labels(o[k],y[k])
                return gap(f)-gap(n)
            far_near.append({'mode':mode,'far_minus_near_probe_oracle_gap':float(contrast(np.arange(len(y)))),
                'ci95':list(metrics.cluster_bootstrap(contrast,groups,n_boot=2000,seed=P.SEED)),'status':'DESCRIPTIVE; paired passage-cluster resampling, fixed OOF probes'})
        verdict=adjudicate(rows)
        data={'experiment':'W10','section':86,'rows':rows,'mode_activity':activity,'primary':verdict,'far_minus_near':far_near,
            'source_sha256':P.sha(Path(__file__)),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
            'score_seal_sha256':P.sha(outputs/'SCORE_SEAL.json'),'mode_judge_seal_sha256':P.sha(judgements/'MODE_JUDGE_SEAL.json'),
            'probe_method':'unchanged W1 lambda0.001, 5 template-grouped folds on test, train-only standardization; fixed OOF bootstrap',
            'reconstructor_window':'OPEN_DEPENDENCY; no blind-by-construction claim',
            'surprisal_policy':C.SURPRISAL_POLICY,'science_receipt':json.loads((outputs/'SCIENCE_RECEIPT.json').read_text())}
        out.mkdir(parents=True,exist_ok=False);P.dump(out/'metrics.json',data);P.jsonl(out/'probe.oof.jsonl',all_oof)
        line='HANDOFF W10 §86: '+'; '.join(f"{h} {r['status']} {r['k']}/{r['n']} ({r['rate']:.3f})" if r['rate'] is not None else f"{h} NOT EVALUABLE 0/0" for h,r in verdict.items())
        (out/'HANDOFF.txt').write_text(line+'\n')
        lines=['# W10 §86 results','','Prediction: Oracle misses operating mode while NLA reads more.','',line,'',
            '| Row | Active | Probe42 | Probe44 | Oracle | NLA | J-lens | Oracle gate | NLA gate |',
            '|---|---:|---:|---:|---:|---:|---:|---|---|']
        for r in rows:
            active='n/a' if r['mode_active'] is None else str(r['mode_active']['follows'])+'/20'
            lines.append(f"| {r['feature']} | {active} | {r['probes']['42']['auroc']:.3f} | {r['probes']['44']['auroc']:.3f} | {r['readers']['olens']['true']['auroc']:.3f} | {r['readers']['nla']['true']['auroc']:.3f} | {r['readers']['jlens']['true']['auroc']:.3f} | {r['readers']['olens']['status']} | {r['readers']['nla']['status']} |")
        lines+=['','All signed reader AUROCs, CIs, phrasings, random controls and failure reasons are in metrics.json.','',
            '| Mode | Far − near (probe − Oracle) | 95% CI |','|---|---:|---|']
        lines += [f"| {r['mode']} | {r['far_minus_near_probe_oracle_gap']:.3f} | {r['ci95']} |" for r in far_near]
        lines+=['','Surprisal rows are DESCRIPTIVE and excluded from H1/H2. The reconstructor window remains unresolved.']
        (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
        seal_named(out,['metrics.json','probe.oof.jsonl','HANDOFF.txt','RESULTS.md'],'ANALYSIS_SEAL.json','REGISTERED_W10_ANALYSIS_COMPLETE')
    return data


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command',required=True)
    j=sub.add_parser('judge');j.add_argument('--packet',type=Path,required=True);j.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('analyse')
    for n in ('bank','outputs','packet','judgements','out'):a.add_argument('--'+n,type=Path,required=True)
    args=parser.parse_args()
    if args.command=='judge':print(json.dumps(judge(args.packet,args.out)))
    else:
        result=analyse(args.bank,args.outputs,args.packet,args.judgements,args.out);print(json.dumps(result['primary']))
