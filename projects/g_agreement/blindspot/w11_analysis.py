"""§87 registered CPU analysis; seals/grid precede labels, no orientation flips."""
from __future__ import annotations
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import numpy as np
from . import protocol as P
from . import analysis as A
from .w11_run import READERS


def row_decision(oracle_auc,probe_auc,random_auc,pretarget_aucs,complete=True):
    leak=all(v is not None and np.isfinite(v) and .48-1e-12<=v<=.52+1e-12 for v in pretarget_aucs)
    if len(pretarget_aucs)!=2:leak=False
    evaluable=bool(leak and complete and probe_auc is not None and np.isfinite(probe_auc) and probe_auc>=.85
                   and random_auc is not None and .40-1e-12<=random_auc<=.60+1e-12 and oracle_auc is not None and np.isfinite(oracle_auc))
    return {'leak_gate_pass':leak,'evaluable':evaluable,
        'status':'EVALUABLE' if evaluable else 'NOT EVALUABLE',
        'confirms':bool(evaluable and oracle_auc<=probe_auc-.15+1e-12)}


def summary(rows):
    evaluable=[r for r in rows if r['evaluable']]
    rate=A._rate(sum(r['confirms'] for r in evaluable),len(evaluable))
    return {'section':87,'status':'NOT EVALUABLE' if not evaluable else 'CONFIRMED' if rate['rate']>=.70 else 'NOT MET',
        'rate':rate,'evaluable_features':[r['feature'] for r in evaluable],
        'excluded_features':[r['feature'] for r in rows if not r['evaluable']],
        'denominator':'Oracle-evaluable features after native probe/random-donor and both pretarget gates'}


def analyse(bank,outputs,labels,out):
    """One invocation after retrieval; do not call from the GPU worker."""
    bank,outputs,labels,out=map(Path,(bank,outputs,labels,out))
    if out.exists():raise ValueError('analysis output already exists; no duplicate run')
    P.verify(bank,'INPUT_SEAL.json')
    manifest=json.loads((bank/'manifest.json').read_text())
    if manifest['experiment']!='W11':raise ValueError('wrong bank')
    for path,digest in manifest['source_files'].items():
        if P.sha(P.ROOT/path)!=digest:raise ValueError('analysis must use exact frozen source: '+path)
    capture=P.verify(outputs,'CAPTURE_SEAL.json')
    score=P.verify(outputs,'SCORE_SEAL.json')
    needed_capture={'acts42.npy','acts44.npy','pretarget.acts42.npy','pretarget.acts44.npy','items.order.json','provenance.json'}
    if not needed_capture<=set(capture['files']) or capture['status']!='W11_CAPTURE_SEALED':
        raise ValueError('incomplete capture seal')
    if not {'scores.jsonl','CAPTURE_SEAL.json','provenance.json','items.order.json','FORECAST.json'}<=set(score['files']) or score['status']!='SCORES_SEALED_W11_BEFORE_LABEL_JOIN':
        raise ValueError('incomplete score seal')
    provenance=json.loads((outputs/'provenance.json').read_text())
    if provenance['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or provenance['source_files']!=manifest['source_files']:
        raise ValueError('score source/input lineage mismatch')
    items=P.rows(bank/'items.input.jsonl');specs=json.loads((bank/'templates.json').read_text())
    ids=[x['id'] for x in items]
    if len(ids)!=1200 or len(set(ids))!=1200 or ids!=json.loads((outputs/'items.order.json').read_text()):
        raise ValueError('wrong item coverage or order')
    raw=P.rows(outputs/'scores.jsonl')
    expected={(x['id'],name,layer,arm) for x in items for name,layer in READERS for arm in ('true','random_donor')}
    keys=[(r['id'],r['reader'],r['layer'],r['arm']) for r in raw]
    if len(keys)!=len(set(keys)) or set(keys)!=expected:raise ValueError('incomplete/duplicate reader grid')
    for r in raw:
        if r['status']=='COMPLETE' and (not isinstance(r['scores'],list) or len(r['scores'])!=2 or not np.isfinite(r['scores']).all()):
            raise ValueError('invalid phrasing scores')
        if r['status']!='COMPLETE' and r['scores'] is not None:raise ValueError('invalid missing cell')
    scoremap=dict(zip(keys,raw))
    arrays={}
    for site in (42,44):
        for prefix in ('','pretarget.'):
            h=np.load(outputs/f'{prefix}acts{site}.npy',allow_pickle=False)
            if h.ndim!=2 or h.shape[0]!=len(items) or not np.isfinite(h).all():
                raise ValueError('invalid activation dimensions/finiteness')
            arrays[prefix,site]=h
    # No ground-truth content is read above this point.
    if P.sha(labels)!=manifest['labels_sha256']:raise ValueError('wrong frozen labels')
    records=P.rows(labels);lookup={r['id']:r for r in records}
    if len(records)!=len(lookup) or set(lookup)!=set(ids):raise ValueError('label coverage mismatch')
    for x in items:
        r=lookup[x['id']]
        if r['feature']!=x['feature'] or r['value'] not in ('present','absent') or r['split'] not in ('dev','test'):
            raise ValueError('label schema mismatch')
    # Create-only lock persists on failure: a retry requires an explicit instruction.
    lock=out.with_name(out.name+'.lock.json');lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:json.dump({'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'status':'STARTED'},f)
    from mats import metrics
    index={x['id']:i for i,x in enumerate(items)};rows=[];oof=[]
    with P.logged('w11_registered_analysis',extra={'section':87,'gpu_hours':0}):
        for feature in manifest['features']:
            idx=np.array([i for i,x in enumerate(items) if x['feature']==feature and lookup[x['id']]['split']=='test'])
            if len(idx)!=60:raise ValueError('test scope mismatch')
            names=[items[i]['id'] for i in idx]
            y=np.array([lookup[k]['value']=='present' for k in names],int)
            groups=np.array([lookup[k]['cluster'] for k in names])
            local={int(i):j for j,i in enumerate(idx)}
            donors=np.array([local[index[items[i]['donor_id']]] for i in idx])
            probe={};leak={}
            row={'feature':feature,'class':specs[feature]['class'],'domain':specs[feature]['domain'],
                 'n':len(idx),'n_clusters':len(set(groups)),'probes':{},'pretarget':{},'readers':{}}
            for site in (42,44):
                p,pm,folds=A.grouped_probe(arrays['',site][idx],y,groups,donors)
                before,bm,bfolds=A.grouped_probe(arrays['pretarget.',site][idx],y,groups,donors)
                probe[site]=metrics.auroc_labels(p,y);leak[site]=metrics.auroc_labels(before,y)
                row['probes'][str(site)]=asdict(metrics.auroc_ci(p,y,groups,n_boot=2000,seed=P.SEED))
                row['pretarget'][str(site)]={'auroc':leak[site],'gate_pass':.48-1e-12<=leak[site]<=.52+1e-12,'folds':bfolds}
                oof.extend({'id':key,'feature':feature,'site':site,'target':float(p[j]),'pretarget':float(before[j])} for j,key in enumerate(names))
            true_scores={}
            for name,site in READERS:
                cells=[[scoremap[k,name,site,arm] for k in names] for arm in ('true','random_donor')]
                complete=all(c['status']=='COMPLETE' for group in cells for c in group)
                if not complete:
                    row['readers'][name]={'status':'NOT EVALUABLE','true':None,'random_donor':None}
                    continue
                actual,random=[np.array([np.mean(c['scores']) for c in group]) for group in cells]
                a=asdict(metrics.auroc_ci(actual,y,groups,n_boot=2000,seed=P.SEED))
                d=asdict(metrics.auroc_ci(random,y,groups,n_boot=2000,seed=P.SEED))
                decision=row_decision(a['auroc'],probe[site],d['auroc'],list(leak.values()))
                row['readers'][name]={'true':a,'random_donor':d,'probe_auroc':probe[site],**decision}
                true_scores[name]=actual
            oracle=row['readers']['olens']
            row.update({k:oracle.get(k,False) for k in ('evaluable','confirms')})
            if 'nla' in true_scores and 'olens' in true_scores:
                n,o=true_scores['nla'],true_scores['olens']
                row['nla_minus_oracle']={'difference':metrics.auroc_labels(n,y)-metrics.auroc_labels(o,y),
                    'ci95':list(metrics.cluster_bootstrap(lambda j:metrics.auroc_labels(n[j],y[j])-metrics.auroc_labels(o[j],y[j]),
                        groups,n_boot=2000,seed=P.SEED)),'status':'DESCRIPTIVE'}
            rows.append(row)
        out.mkdir(parents=True,exist_ok=False)
        data={'experiment':'W11','rows':rows,'w11':summary(rows),'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
            'reader_seals':[P.sha(outputs/'SCORE_SEAL.json'),P.sha(outputs/'CAPTURE_SEAL.json')],
            'registered_analysis_source_sha256':P.sha(Path(__file__)),'labels_sha256':P.sha(labels),
            'section84_agreement':'PENDING; join separately with sealed section84 per-feature statuses, never substitute full-prefix shortcut flags'}
        P.dump(out/'metrics.json',data);P.jsonl(out/'probe.oof.jsonl',oof)
        P.dump(out/'ANALYSIS_SEAL.json',{'status':'REGISTERED_W11_ANALYSIS_COMPLETE',
            'files':{n:P.sha(out/n) for n in ('metrics.json','probe.oof.jsonl')}})
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('bank','outputs','labels','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=analyse(a.bank,a.outputs,a.labels,a.out)
    print(json.dumps(r['w11'],indent=2))
