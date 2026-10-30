"""E24 CPU-only C3, clarified R0–R5; C5 descriptive, C6 cross-check and blinded C4 audit packet."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from projects.g_agreement.blindspot import protocol as P
from .e24_relaunch import PRIORITY, C6_LAYERS, read, seal, parity
from .e24_statements import statement

def dump_output(path,value):
    # Output conversion only; no estimator or decision-rule changes.
    def scalar(x):
        if isinstance(x,np.generic):return x.item()
        raise TypeError(f'Unsupported JSON type: {type(x).__name__}')
    P.dump(path,json.loads(json.dumps(value,default=scalar)))


SEED=20261025


def validate_scope_authority(plan):
    """§130 restores §118; never silently analyse a superseded reduced plan."""
    if plan.get('scope_amendment')=='d3d91630':
        raise ValueError('five-layer amendment superseded by §130 (4769ca0e)')
    if 'channels' in plan and plan['channels']!=['C1','C2','C3','C4','C5','C6','C7']:
        raise ValueError('§130 requires full registered C1–C7 scope')


def auc(y, scores):
    y=np.asarray(y,dtype=bool);s=np.asarray(scores,dtype=float)
    if s.ndim!=1 or s.shape!=y.shape or not np.isfinite(s).all() or not y.any() or y.all():raise ValueError('invalid binary AUROC')
    a=s[y,None];b=s[None,~y]
    return float(np.mean((a>b)+.5*(a==b)))


def draws(clusters):
    groups=[np.flatnonzero(np.array(clusters)==c) for c in sorted(set(clusters))]
    rng=np.random.default_rng(SEED)
    return [np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))]) for _ in range(2000)]


def metric(y,s,boot):
    values=np.array([auc(np.asarray(y)[b],np.asarray(s)[b]) for b in boot])
    return {'auroc':auc(y,s),'ci95':np.quantile(values,[.025,.975]).tolist(),
            'p_above_chance':float((1+sum(values<=.5))/(len(values)+1))},values


def holm(values):
    result={};last=0.
    for j,k in enumerate(sorted(values,key=values.get)):
        last=max(last,min(1.,(len(values)-j)*values[k]));result[k]=last
    return result


def majority(successes, unresolved, total):
    if not total:return None
    if successes>total/2:return True
    if successes+unresolved<=total/2:return False
    return None


def all_resolved(values):
    if False in values:return False
    if not values or None in values:return None
    return True


def carried_reversal(cell):
    return (cell['C2']['auroc']>=.70 and cell['C2_swap']['auroc']<=.40
            and cell['C2_swap']['ci95'][1]<.50)


def c5_anchor(actual, reference):
    return {'C5':actual,'E1b':reference,'C5_pass':abs(actual-reference)<=.03+1e-12}


def statement_shift(true,y,a,b):
    """Unchanged S14 ar_lib.statement_shift formula, with §118's fresh raw reference."""
    import torch
    y=torch.as_tensor(y,dtype=torch.bool)
    d=true[y].float().mean(0)-true[~y].float().mean(0)
    norm=d.norm().clamp_min(1e-9);delta=a.float()-b.float()
    return {'ratio':float(delta@(d/norm)/norm),
            'cosine':float(torch.nn.functional.cosine_similarity(delta,d,dim=0))}


def best_dev(y, scores):
    scores=np.asarray(scores)
    if scores.shape!=(len(y),8):raise ValueError('eight phrasings required')
    values=[auc(y,scores[:,j]) for j in range(8)]
    return int(np.argmax(values)),values


def blind_packet(canonical, items, specs, structure):
    rng=np.random.default_rng(SEED);chosen=[]
    for f in structure:
        ids=sorted(x['id'] for x in items if x['feature']==f and x['split']=='test')
        chosen.append(ids[int(rng.integers(len(ids)))])
    extra=sorted(x['id'] for x in items if x['feature'] in structure and x['split']=='test' and x['id'] not in chosen)
    chosen.append(extra[int(rng.integers(len(extra)))])
    packet=[];key=[]
    for l,rows in canonical.items():
        for uid in chosen:
            x=rows[uid];f=x['feature'];opaque=hashlib.sha256(f'E24-audit:{SEED}:{l}:{uid}'.encode()).hexdigest()[:24]
            packet.append({'id':opaque,'row':f,'A':specs[f]['values'][0],'B':specs[f]['values'][1],'readout':x['C4']})
            key.append({'id':opaque,'layer':l,'source_id':uid,'regex':statement(f,x['C4'])})
    rng.shuffle(packet)
    return packet,key


def analyse(a):
    if not a.out.resolve().is_relative_to((P.ROOT/"cache").resolve()):raise ValueError("judge outputs must remain under cache")
    import torch
    from mats.probes import fit_logreg
    from common.stats import wilson
    plan=read(a.plan);scope=read(a.bank/'SCOPE.json')
    validate_scope_authority(plan)
    for n,digest in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=getattr(a,'source_overrides',{}).get(n,digest):raise ValueError('analysis source changed: '+n)
    P.verify(a.bank,'INPUT_SEAL.json')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256'] or P.sha(a.labels)!=plan['labels_sha256']:
        raise ValueError('input/label binding')
    items=P.rows(a.bank/'items.input.jsonl');ids=[x['id'] for x in items]
    pods={};admission=None;canonical={};anchor_rows={}
    for out in a.outputs:
        P.verify(out,'SCORE_SEAL.json');adm=read(out/'ADMISSION.json')
        capture=out/'capture';P.verify(capture,'CAPTURE_SEAL.json')
        if read(capture/'ORDER.json')!=ids or read(capture/'BINDING.json')['plan_sha256']!=P.sha(a.plan):raise ValueError('local capture binding')
        parity(np.load(capture/'acts44.npy',allow_pickle=False),np.load(a.bank/'reference44.npy',allow_pickle=False))
        if admission is not None and admission!=adm:raise ValueError('different global admissions')
        admission=adm;slot=read(out/'FORECAST.json')['slot']
        if slot in pods:raise ValueError('duplicate pod slot')
        pods[slot]=out
        for l in adm['pods'][slot]['layers']:
            dest=out/f'L{l}';P.verify(dest,'SCORE_SEAL.json');P.verify(capture,f'L{l}_SEAL.json')
            bind=read(dest/'BINDING.json')
            if (bind['layer']!=l or bind['plan_sha256']!=P.sha(a.plan) or bind['input_seal_sha256']!=plan['input_seal_sha256']
                or bind['capture_layer_seal_sha256']!=P.sha(capture/f'L{l}_SEAL.json') or bind['admission_sha256']!=P.sha(out/'ADMISSION.json')):
                raise ValueError('score provenance mismatch')
            rr=P.rows(dest/'readouts.jsonl');rows={r['id']:r for r in rr}
            if len(rows)!=len(rr) or set(rows)!={x['id'] for x in items if x['split']=='test'}:raise ValueError('incomplete C1/C4 population')
            if l==44:anchor_rows[slot]=rows
            elif l in canonical:raise ValueError('duplicate nonanchor layer')
            else:canonical[l]=(rows,dest)
    if admission is None or set(pods)!=set(range(len(admission['pods']))):raise ValueError('all admitted pods required; partial run not adjudicated')
    canonical[44]=(anchor_rows[min(pods)],pods[min(pods)]/'L44')
    if set(canonical)!=set(admission['layers_priority']):raise ValueError('admitted layer missing')
    if admission['C6']:
        for out in pods.values():
            c6=out/'c6_capture';P.verify(c6,'CAPTURE_SEAL.json')
            if read(c6/'BINDING.json')['input_seal_sha256']!=plan['input_seal_sha256']:raise ValueError('C6 input binding')
    lock=getattr(a,'analysis_lock',a.bank.with_suffix('.e24-analysis.lock'))
    with lock.open('x') as f:f.write(json.dumps({'plan_sha256':P.sha(a.plan),'outputs':[str(p) for p in a.outputs]}))
    a.out.mkdir(parents=True,exist_ok=False)
    private=read(a.labels);labels={x['id']:x for x in private['w1']};specs=read(a.bank/'templates.json')
    if set(labels)!=set(ids):raise ValueError('label population')
    w1={x['feature']:x['true']['auroc'] for x in private['w1_metrics']['rows'] if x['reader']=='olens' and x['layer']==44}
    e15={x['feature']:x['readers']['olens']['arms']['true']['auroc'] for x in private['e15_metrics'] if x['valid_pairs']}
    c2=read(a.bank/'c2.json');order={uid:i for i,uid in enumerate(ids)}
    rowspec={};r0={};report={};saved={};directions={}
    for f in scope['rows_c1_c3_c4']:
        tr=[x['id'] for x in items if x['feature']==f and x['split']=='dev'];te=[x['id'] for x in items if x['feature']==f and x['split']=='test']
        if set(labels[i]['cluster'] for i in tr)&set(labels[i]['cluster'] for i in te):raise ValueError('dev/test template leakage')
        y=np.array([labels[i]['value']==specs[f]['values'][0] for i in te]);yt=np.array([labels[i]['value']==specs[f]['values'][0] for i in tr])
        boot=draws([labels[i]['cluster'] for i in te]);rowspec[f]=(tr,te,yt,y,boot)
        checks=[]
        for slot,rr in sorted(anchor_rows.items()):
            c1=auc(y,[np.mean(rr[i]['C1']) for i in te]);c2v=auc(y,[np.mean(rr[i]['C2']) for i in te]) if f in c2 else None
            checks.append({'slot':slot,'C1':c1,'W1':w1[f],'C1_pass':abs(c1-w1[f])<=.03+1e-12,
                'C2':c2v,'E15':e15.get(f),'C2_pass':None if c2v is None else abs(c2v-e15[f])<=.03+1e-12})
        r0[f]={'interpretable':all(c['C1_pass'] and c['C2_pass'] is not False for c in checks),'anchors':checks}
    torch.set_num_threads(4)
    for l in admission['layers_priority']:
        rr,dest=canonical[l];h=np.load(dest.parent/'capture'/f'acts{l}.npy',allow_pickle=False)
        if l==44:parity(h,np.load(a.bank/'reference44.npy',allow_pickle=False))
        c5order=read(dest/'C5_ORDER.json');c5=np.load(dest/'C5.npy',allow_pickle=False);c5map={uid:i for i,uid in enumerate(c5order)}
        if set(c5map)!={x['id'] for x in items if x['split']=='test' and x['feature'] in scope['rows_c5']} or len(c5map)!=len(c5order) or c5.shape!=(2100,h.shape[1]):raise ValueError('C5 coverage/shape')
        layer={}
        for f,(tr,te,yt,y,boot) in rowspec.items():
            model=fit_logreg(torch.from_numpy(h[[order[i] for i in tr]]),torch.tensor(yt),lam=1e-3,iters=200)
            pred=model.decision(torch.from_numpy(h[[order[i] for i in te]])).numpy();direction=model.direction().numpy()
            directions[f'L{l}__{f}']=direction;saved[f'L{l}__{f}']={'ids':te,'scores':pred.tolist()}
            m1,b1=metric(y,[np.mean(rr[i]['C1']) for i in te],boot);m3,_=metric(y,pred,boot)
            cell={'interpretable':r0[f]['interpretable'],'C1':m1,'C3':m3,
                  'C1_per_pair':[auc(y,[rr[i]['C1'][j] for i in te]) for j in range(len(specs[f]['olens']))]}
            if f in c2:
                m2,b2=metric(y,[np.mean(rr[i]['C2']) for i in te],boot);ms,_=metric(y,[np.mean(rr[i]['C2_swap']) for i in te],boot)
                cell.update(C2=m2,C2_swap=ms,C2_minus_C1={'difference':m2['auroc']-m1['auroc'],'ci95':np.quantile(b2-b1,[.025,.975]).tolist()})
            if f in scope['rows_c5']:
                mc,_=metric(y,c5[[c5map[i] for i in te]]@direction,boot);cell['C5']=mc
            if f in scope['structure_rows']:
                codes=[statement(f,rr[i]['C4']) for i in te]
                k=sum(code==('A' if yy else 'B') for code,yy in zip(codes,y));cell['C4']={'k':int(k),'n':len(te),'codes':codes}
            layer[f]=cell
        report[str(l)]=layer
    # Clarification 2: C5 remains descriptive but its anchor joins R0 on every pod.
    reference=read(P.ROOT/plan['e1b_reference'])['rows']
    if set(reference)!=set(scope['rows_c5']):raise ValueError('E1b anchor reference coverage')
    for slot,out in sorted(pods.items()):
        dest=out/'L44';co=read(dest/'C5_ORDER.json');cv=np.load(dest/'C5.npy',allow_pickle=False)
        cm={uid:i for i,uid in enumerate(co)}
        if set(cm)!=set(canonical[44][0]).intersection({x['id'] for x in items if x['feature'] in scope['rows_c5']}) or len(cm)!=len(co) or cv.shape!=(2100,len(next(iter(directions.values())))):
            raise ValueError('per-pod C5 anchor coverage/shape')
        for f in scope['rows_c5']:
            _,te,_,y,_=rowspec[f]
            value=auc(y,cv[[cm[i] for i in te]]@directions[f'L44__{f}'])
            check=c5_anchor(value,reference[f])
            next(c for c in r0[f]['anchors'] if c['slot']==slot).update(check)
            r0[f]['interpretable'] = r0[f]['interpretable'] and check['C5_pass']
    for layer in report.values():
        for f,cell in layer.items():cell['interpretable']=r0[f]['interpretable']
    family={f'{f}:{l}':(report[str(l)][f]['C1']['p_above_chance'] if l in canonical and r0[f]['interpretable'] else 1.)
            for f in scope['structure_rows'] for l in PRIORITY if l!=44}
    if len(family)!=scope['holm_family_size']:raise ValueError('Holm family changed')
    adjusted=holm(family);rules={};r2=[]
    for l in admission['layers_priority']:
        layer=report[str(l)];eligible=[f for f in scope['structure_rows'] if r0[f]['interpretable'] and layer[f]['C3']['auroc']>=.8]
        blind=[f for f in eligible if layer[f]['C1']['auroc']<=layer[f]['C3']['auroc']-.15+1e-12]
        valid=list(c2)
        unresolved=[f for f in valid if not r0[f]['interpretable']]
        carried=[f for f in valid if r0[f]['interpretable'] and carried_reversal(layer[f])]
        dissociated=[f for f in valid if r0[f]['interpretable'] and layer[f]['C2_minus_C1']['ci95'][0]>0]
        pooled=[layer[f]['C4'] for f in scope['structure_rows'] if r0[f]['interpretable']]
        k=sum(c['k'] for c in pooled);n=sum(c['n'] for c in pooled);interval=list(wilson(k,n)) if n else None
        rules[str(l)]={'R1':{'held':None if any(not r0[f]['interpretable'] and layer[f]['C3']['auroc']>=.8 for f in scope['structure_rows']) else bool(eligible) and len(blind)/len(eligible)>=.75,'denominator':eligible,'blind':blind},
            'R3_prime':{'held':majority(len(carried),len(unresolved),len(valid)),'denominator':valid,'unresolved':unresolved,'carried':carried},
            'R4':{'held':None if any(not r0[f]['interpretable'] for f in scope['structure_rows']) else interval is not None and interval[2]<.05,'k':k,'n':n,'rate_lo_hi':interval},
            'R5':{'held':majority(len(dissociated),len(unresolved),len(valid)),'denominator':valid,'unresolved':unresolved,'dissociated':dissociated}}
        if l!=44:
            for f in scope['structure_rows']:
                if r0[f]['interpretable'] and layer[f]['C1']['auroc']>=.7 and adjusted[f'{f}:{l}']<.05 and report['44'][f]['C1']['auroc']<=.6:
                    r2.append({'feature':f,'layer':l,'auroc':layer[f]['C1']['auroc'],'holm_p':adjusted[f'{f}:{l}']})
    c6report={};c7report={}
    if admission['C6']:
        ci=P.rows(a.bank/'c6.input.jsonl');cl={x['id']:x['label'] for x in private['c6']}
        for out in pods.values():
            if read(out/'c6_capture/ORDER.json')!=[x['id'] for x in ci]:raise ValueError('C6 order')
        for l in C6_LAYERS:
            _,dest=canonical[l];true=torch.from_numpy(np.load(dest.parent/'c6_capture'/f'acts{l}.npy',allow_pickle=False));recon=torch.from_numpy(np.load(dest/'C6.npy',allow_pickle=False))
            order6=read(dest/'C6_ORDER.json');out={}
            expected=[[f,p[0],s] for f,ps in read(a.bank/'c6.pairs.json').items() for p in ps for s in ('A','B')]
            if order6!=expected or len(recon)!=len(expected):raise ValueError('C6 statement alignment')
            if l==44:parity(true.numpy(),np.load(a.bank/'c6.reference44.npy',allow_pickle=False))
            for j in range(0,len(order6),2):
                f,pid,_=order6[j];ix=[i for i,x in enumerate(ci) if x['feature']==f]
                value=statement_shift(true[ix],[cl[ci[i]['id']] for i in ix],recon[j],recon[j+1])
                if l==44:
                    published=private['c6_published'][f]['layers']['44']['stmt']['ol:'+pid]['ratio']
                    value.update(published_ratio=published,reproduced=abs(value['ratio']-published)<=.05)
                out[f+':'+pid]=value
            c6report[str(l)]=out
    if admission['C7']:
        for l in (20,44,60):
            _,dest=canonical[l];records=P.rows(dest/'C7.jsonl');byid={x['id']:x for x in records}
            if len(byid)!=len(records) or set(byid)!={x['id'] for x in items if x['feature'] in scope['rows_c5']}:raise ValueError('C7 coverage')
            rows={}
            for f in scope['rows_c5']:
                tr,te,yt,y,boot=rowspec[f];j,dev=best_dev(yt,[byid[i]['scores'] for i in tr]);scores=np.array([byid[i]['scores'] for i in te])
                rows[f]={'best_dev_index':j,'dev_aurocs':dev,'test_all8':[auc(y,scores[:,k]) for k in range(8)],'test_selected':metric(y,scores[:,j],boot)[0]}
            c7report[str(l)]=rows
    packet,key=blind_packet({l:rr for l,(rr,_) in canonical.items()},items,specs,scope['structure_rows'])
    P.jsonl(a.out/'JUDGE_PACKET.jsonl',packet);P.jsonl(a.out/'JUDGE_KEY.DO_NOT_SEND.jsonl',key)
    dump_output(a.out/'metrics.json',{'R0':r0,'layers':report,'rules':rules,'R2_cells':r2,'holm':adjusted,
        'R1_across_layers':(True if sum(r['R1']['held'] is True for r in rules.values())>=9 else None if sum(r['R1']['held'] is not False for r in rules.values())>=9 else False),
        'R5_at_all_R3_prime_layers':all_resolved([r['R5']['held'] for r in rules.values() if r['R3_prime']['held'] is True]),
        'C5_status':'DESCRIPTIVE_PER_ROW_LAYER_NO_ACROSS_LAYER_RULE','C6':c6report,'C7':c7report,
        'C6_44_status':('REPRODUCED' if all(x['reproduced'] for x in c6report['44'].values()) else 'NOT REPRODUCED') if c6report else 'NOT RUN',
        'C4_judge_status':'PENDING_BLINDED_AUDIT','bootstrap':'2000 W1 template-cluster draws; paired across channels; seed20261025',
        'invalid_R0_rows_uninterpretable_everywhere':[f for f,v in r0.items() if not v['interpretable']]})
    np.savez(a.out/'directions.npz',**directions);P.dump(a.out/'probe_predictions.json',saved)
    seal(a.out,['metrics.json','directions.npz','probe_predictions.json','JUDGE_PACKET.jsonl','JUDGE_KEY.DO_NOT_SEND.jsonl'],
         'ANALYSIS_SEAL.json','E24_CPU_ANALYSIS_COMPLETE_JUDGE_AUDIT_PENDING')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('bank','plan','labels','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--outputs',type=Path,nargs='+',required=True);p.add_argument('--c6-capture',type=Path)
    analyse(p.parse_args())
