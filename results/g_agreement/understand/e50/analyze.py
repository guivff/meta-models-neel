"""§166 once-only analysis: complete verified grid first, private labels last."""
import argparse
import math
from pathlib import Path
import sys
import numpy as np
import contract as C
from operational_gates import validate_operational_gates
from secondary import ROWS as SECONDARY_ROWS
sys.path.insert(0,str(C.ROOT))
from projects.g_agreement.understand.e24_statements import statement

PARITY_ROWS=('prose_sentiment','prose_paren','python_string')

def auc(scores,labels):
    x=np.asarray(scores);y=np.asarray(labels)
    if len(x)!=len(y) or not np.isfinite(x).all() or set(y)!={0,1}:raise ValueError('finite two-class AUROC required')
    delta=x[y==1,None]-x[y==0]
    return float(np.mean((delta>0)+.5*(delta==0)))

def median(values):return float(np.median(values))

def naming(records,labels,row):
    counts=dict.fromkeys(('correct_only','wrong_only','both','neither'),0)
    for r in records:
        status=statement(row,r['raw']);target='A' if labels[r['id']]['y'] else 'B'
        if status in ('both','neither'):counts[status]+=1
        elif status in ('A','B'):counts['correct_only' if status==target else 'wrong_only']+=1
        else:raise ValueError('missing frozen correctness detector')
    return counts

def evaluate_rules(cells,parity):
    by={(x['split'],x['arm'],x['row']):x for x in cells}
    if len(cells)!=100 or len(by)!=100 or set(by)!={(s,a,r) for s in ('A','B') for a in ('L','S') for r in C.ROWS}:
        raise ValueError('all four arms and25 rows required')
    if any(not math.isfinite(c['auroc']) or not 0<=c['auroc']<=1 for c in cells):raise ValueError('finite AUROCs required')
    split_metrics={};eligible=[]
    for s,spec in C.plan()['splits'].items():
        train=median([by[s,'L',r]['auroc'] for r in spec['train']])
        held={a:median([by[s,a,r]['auroc'] for r in spec['heldout']]) for a in ('L','S')}
        split_metrics[s]={'training_L_median':train,'heldout_median':held,'status':'UNDERTRAINED' if train<.80 else 'TRAINED'}
        if train>=.80:eligible.append(s)
    label='single-split (n = 8 rows)' if len(eligible)==1 else 'two-split (n = 16 rows)' if len(eligible)==2 else 'both splits UNDERTRAINED; descriptive only'
    held={a:[by[s,a,r]['auroc'] for s in eligible for r in C.plan()['splits'][s]['heldout']] for a in ('L','S')}
    med={a:median(v) if v else None for a,v in held.items()}
    count=sum(x>=.70 for x in held['L']);needed=5*len(eligible)
    r1=None if not eligible else med['L']>=.75 and count>=needed and med['S']<=.60
    # Clarification2 makes R2/R3 use the remaining split. With neither trained,
    # R1/R3/falsifier are NE; retain the registered no-tax measurement on both.
    tax_splits=eligible or ['A','B']
    content=median([by[s,'L',r]['auroc'] for s in tax_splits for r in C.CONTENT])
    if set(parity)!={'A','B'} or any(set(v)!=set(PARITY_ROWS) for v in parity.values()):raise ValueError('both post-training W1 grids required')
    deltas=[abs(c['post']-c['pre']) for s in tax_splits for c in parity[s].values()]
    if any(not math.isfinite(x) for x in deltas):raise ValueError('finite parity deltas required')
    nets={};counts={}
    for arm in ('L','S'):
        counts[arm]=dict.fromkeys(('correct_only','wrong_only','both','neither'),0)
        for s in eligible:
            for row in C.plan()['splits'][s]['heldout']:
                c=by[s,arm,row]['naming']
                if set(c)!=set(counts[arm]) or any(type(v) is not int or v<0 for v in c.values()) or sum(c.values())!=84:
                    raise ValueError('complete correctness partition required')
                for k,v in c.items():counts[arm][k]+=v
        nets[arm]=(counts[arm]['correct_only']-counts[arm]['wrong_only'])/(len(eligible)*8*84) if eligible else None
    return {'report_label':label,'eligible_splits':eligible,'split_metrics':split_metrics,
        'R1':{'met':r1,'heldout_medians':med,'L_rows_ge_070':count,'required':needed,'denominator':len(held['L'])},
        'R2':{'met':content>=.95 and max(deltas)<=.05,'content_L_median':content,'max_W1_absolute_change':max(deltas),'splits':tax_splits},
        'R3':{'met':None if not eligible else nets['L']>=.20 and nets['S']<=.05,'net_naming':nets,'counts':counts,'n_per_arm':len(eligible)*672},
        'falsifier':{'met':None if not eligible else all(split_metrics[s]['heldout_median']['L']<=.60 for s in eligible)}}

def asked(path,ids):
    data=C.rows(path)
    if (len(data)!=84 or len(ids)!=84 or {r['id'] for r in data}!=ids
            or any(len(r['scores'])!=2 or any(type(x) not in (int,float) or not math.isfinite(x) for x in r['scores']) for r in data)):
        raise ValueError('complete84-item two-phrasing finite score grid required')
    return {r['id']:float(np.mean(r['scores'])) for r in data}

def validate_collection(inputs,collections,parity_input,secondary_input=None):
    C.verify(inputs);binding=C.read(C.HERE/'BOUND_INPUT.json')
    if C.sha(inputs/'INPUT_SEAL.json')!=binding['input_seal_sha256']:raise ValueError('bound v2 input changed')
    C.verify(C.ROOT,str((C.HERE/'SOURCE_MANIFEST.json').relative_to(C.ROOT)))
    C.verify(parity_input)
    if C.sha(parity_input/'INPUT_SEAL.json')!=C.read(C.HERE/'PARITY_PREPARATION_2026-10-25.json')['parity_input_seal_sha256']:raise ValueError('frozen W1 input changed')
    test=C.rows(inputs/'test.jsonl');dev=C.rows(inputs/'dev.jsonl');pitems=C.rows(parity_input/'items.jsonl')
    ids={row:{x['id'] for x in test if x['feature']==row} for row in C.ROWS}
    pids={row:{x['id'] for x in pitems if x['feature']==row} for row in PARITY_ROWS}
    scores={};free={};post={};pre={};secondary_scores={};seen=set();pods=set();total=0;allocated=0;secondary_binding=None
    for directory in map(Path,collections):
        seal=C.verify(directory,'OUTPUT_SEAL.json')
        if {p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()}!=set(seal['files'])|{'OUTPUT_SEAL.json'}:raise ValueError('exact complete output seal required')
        a=C.read(directory/'assignment.json');run=C.read(directory/'RUN_RECEIPT.json')
        C.assignment(a,now=a['provider_created_epoch'])
        if (run.get('experiment')!='E50' or run.get('status')!='COMPLETE_FULL_ASSIGNED_GRID'
                or a['source_manifest_sha256']!=C.sha(C.HERE/'SOURCE_MANIFEST.json')
                or a['input_seal_sha256']!=binding['input_seal_sha256']
                or run.get('plan_sha256')!=C.sha(C.HERE/'PLAN.json') or run.get('test_labels_opened') is not False
                or type(run.get('gpu_seconds_provider')) not in (int,float)
                or not 0<run['gpu_seconds_provider']<=a['allocated_gpu_seconds']
                or a['pod_id'] in pods):raise ValueError('complete original E50 custody required')
        pods.add(a['pod_id']);total+=run['gpu_seconds_provider'];allocated+=a['allocated_gpu_seconds']
        validate_operational_gates(directory,run,a)
        if C.read(directory/'ADMISSION.json')['status']!='ADMIT_FULL_GRID':raise ValueError('warmed admission required')
        split=a['runs'][0][0]
        if split in seen:raise ValueError('duplicate split')
        seen.add(split)
        raw=C.rows(directory/'PARITY_SCORES.jsonl')
        pre[split]={r:{x['id']:float(np.mean(x['scores'])) for x in raw if x['feature']==r} for r in PARITY_ROWS}
        if any(set(pre[split][r])!=pids[r] for r in PARITY_ROWS) or len(raw)!=252:raise ValueError('complete pre-training W1 grid required')
        parity_labels=C.read(parity_input/'labels.json');reported=C.read(directory/'PARITY_RESULT.json')
        for row in PARITY_ROWS:
            keys=sorted(pids[row]);actual=auc([pre[split][row][k] for k in keys],[parity_labels[k] for k in keys])
            if abs(actual-reported['rows'][row]['observed'])>1e-12:raise ValueError('raw W1 parity must reproduce its receipt')
        if C.read(directory/'SECONDARY_BINDING.json')!=a['secondary']:raise ValueError('secondary binding changed')
        if secondary_binding is None:secondary_binding=a['secondary']
        elif secondary_binding!=a['secondary']:raise ValueError('same secondary decision on both pods required')
        if a['secondary']['status']=='FROZEN_VERIFIED':
            from secondary import load_secondary
            stest,_,_=load_secondary(secondary_input,a)
            sids={row:{x['id'] for x in stest if x['feature']==row} for row in SECONDARY_ROWS}
        elif a['secondary']['status']!='NOT_FROZEN_AT_LAUNCH':raise ValueError('unknown secondary status')
        for s,arm in a['runs']:
            folder=directory/(s+'__'+arm);sealed=C.verify(folder,'SCORE_SEAL.json')
            expected={r+'.asked.jsonl' for r in C.ROWS}|{r+'.free.jsonl' for r in C.plan()['splits'][s]['heldout']}|{'SCHEDULE.json','train.jsonl','adapter.pt'}
            if arm=='L':
                expected|={r+'.w1post.jsonl' for r in PARITY_ROWS}
                if a['secondary']['status']=='FROZEN_VERIFIED':expected|={r+'.e49.jsonl' for r in SECONDARY_ROWS}
            if set(sealed['files'])!=expected:raise ValueError('complete registered run files required')
            if C.read(folder/'SCHEDULE.json')!=C.training_schedule(dev,s,arm):raise ValueError('training schedule drift')
            train=C.rows(folder/'train.jsonl')
            if [r['step'] for r in train]!=list(range(1,401)) or any(not math.isfinite(r['loss']) for r in train):raise ValueError('400 finite training steps required')
            for row in C.ROWS:scores[s,arm,row]=asked(folder/(row+'.asked.jsonl'),ids[row])
            for row in C.plan()['splits'][s]['heldout']:
                data=C.rows(folder/(row+'.free.jsonl'))
                if len(data)!=84 or {r['id'] for r in data}!=ids[row] or any(not isinstance(r['raw'],str) for r in data):raise ValueError('84 native readouts per held-out row required')
                free[s,arm,row]=data
            if arm=='L':
                for row in PARITY_ROWS:post[s,row]=asked(folder/(row+'.w1post.jsonl'),pids[row])
                if a['secondary']['status']=='FROZEN_VERIFIED':
                    for row in SECONDARY_ROWS:secondary_scores[s,row]=asked(folder/(row+'.e49.jsonl'),sids[row])
    if seen!={'A','B'} or len(pods)!=2 or total>C.CAP or allocated>C.CAP or len(scores)!=100 or len(free)!=32:raise ValueError('complete four-run two-pod grid within7200s required')
    return test,scores,free,pre,post,secondary_scores,secondary_binding

def bootstrap_ci(scores,y,groups):
    rng=np.random.default_rng(C.SEED);clusters=sorted(set(groups));draw=[]
    for _ in range(2000):
        ix=np.concatenate([np.flatnonzero(groups==g) for g in rng.choice(clusters,len(clusters),replace=True)])
        if len(set(y[ix]))==2:draw.append(auc(scores[ix],y[ix]))
    if not draw:raise ValueError('no valid cluster-bootstrap draws')
    return np.quantile(draw,[.025,.975]).tolist()

def content_only_reference():
    binding=C.read(C.HERE/'E44_REFERENCE_2026-10-26.json');root=C.ROOT/binding['analysis_directory']
    if C.sha(root/'ANALYSIS_SEAL.json')!=binding['analysis_seal_sha256'] or C.sha(root/'METRICS.json')!=binding['metrics_sha256']:
        raise ValueError('existing sealed E44 reference changed')
    C.verify(root,'ANALYSIS_SEAL.json');result=C.read(root/'METRICS.json')
    if result.get('experiment')!='E44' or result.get('status')!='COMPLETE_ANALYSIS':raise ValueError('complete E44 reference required')
    values={x['row']:next(a for a in x['asked'] if a['step']==400) for x in result['cells']}
    if set(values)!=set(C.ROWS):raise ValueError('all25 E44 reference summaries required')
    return {'binding':binding,'step400':values,'rerun':False}

def analysis(inputs,collections,parity_input,out,secondary_input=None,secondary_private=None):
    inputs,parity_input,out=map(Path,(inputs,parity_input,out))
    if out.exists():raise FileExistsError('immutable analysis')
    test,scores,rawfree,pre,post,sscores,sbinding=validate_collection(inputs,collections,parity_input,secondary_input)
    reference=content_only_reference()
    # All seals, custody, parity, training and scored grids verified BEFORE labels.
    private=inputs/'test.labels.DO_NOT_STAGE.jsonl'
    if C.sha(private)!=C.read(C.HERE/'BOUND_INPUT.json')['private_test_labels_sha256']:raise ValueError('private test key differs')
    raw=C.rows(private);labels={r['id']:r for r in raw}
    if len(raw)!=2100 or set(labels)!={r['id'] for r in test}:raise ValueError('exact private label coverage required')
    plabels=C.read(parity_input/'labels.json');parity={s:{} for s in ('A','B')}
    for s in parity:
        for row in PARITY_ROWS:
            ids=sorted(post[s,row]);y=[plabels[k] for k in ids]
            parity[s][row]={'pre':auc([pre[s][row][k] for k in ids],y),'post':auc([post[s,row][k] for k in ids],y)}
    from common.stats import wilson
    cells=[]
    for (s,arm,row),sc in sorted(scores.items()):
        ids=sorted(sc);y=np.array([labels[k]['y'] for k in ids]);groups=np.array([labels[k]['cluster'] for k in ids])
        if sum(y)!=42 or any(labels[k]['feature']!=row or labels[k]['y'] not in (0,1) for k in ids):raise ValueError('balanced row labels required')
        values=np.array([sc[k] for k in ids]);counts=naming(rawfree[s,arm,row],labels,row) if (s,arm,row) in rawfree else None
        cells.append({'split':s,'arm':arm,'row':row,'auroc':auc(values,y),'ci95':bootstrap_ci(values,y,groups),
            'naming':counts,'naming_rate_ci95':{k:wilson(v,84) for k,v in counts.items()} if counts else None})
    rules=evaluate_rules(cells,parity)
    secondary={'status':sbinding['status'],'descriptive_only':True,'cells':[]}
    if sscores:
        if secondary_private is None or C.sha(secondary_private)!=sbinding['private_test_labels_sha256']:raise ValueError('bound E49 private key required')
        sl=C.rows(secondary_private);lookup={x['id']:x for x in sl}
        wanted=set().union(*(set(x) for x in sscores.values()))
        if len(sl)!=924 or set(lookup)!=wanted:raise ValueError('exact E49 private test key required')
        for (s,row),sc in sorted(sscores.items()):
            ids=sorted(sc)
            if any(lookup[k]['feature']!=row for k in ids):raise ValueError('E49 row mismatch')
            secondary['cells'].append({'split':s,'row':row,'arm':'L','auroc':auc([sc[k] for k in ids],[lookup[k]['y'] for k in ids])})
    result={'experiment':'E50','status':'COMPLETE_ANALYSIS',**rules,'cells':cells,'W1_parity':parity,'E49':secondary,
        'plan_sha256':C.sha(C.HERE/'PLAN.json'),'input_seal_sha256':C.sha(inputs/'INPUT_SEAL.json'),
        'output_seals':[C.sha(Path(d)/'OUTPUT_SEAL.json') for d in collections],'E44_reference':reference}
    out.mkdir(parents=True,exist_ok=False);C.dump(out/'METRICS.json',result)
    verdict=lambda x:'MET' if x is True else 'NOT MET' if x is False else 'NOT EVALUABLE'
    lines=['# E50 registered results','',rules['report_label'],'']
    for name in ('R1','R2','R3','falsifier'):lines.extend([name+': '+verdict(rules[name]['met'])+' — '+rules['report_label'],''])
    for s,m in rules['split_metrics'].items():lines.extend([s+': '+m['status']+'; training L median '+str(m['training_L_median'])+'; held-out L median '+str(m['heldout_median']['L']),''])
    lines+=['E49: '+secondary['status']+' (descriptive).','', 'Both-undertrained reports retain R2 no-tax measurements on both splits; transfer/naming/falsifier verdicts are NOT EVALUABLE.','']
    (out/'RESULTS.md').write_text('\n'.join(lines));C.seal(out,'ANALYSIS_SEAL.json');return result

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','parity-input','out'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--collections',nargs=2,type=Path,required=True)
    for name in ('secondary-input','secondary-private'):p.add_argument('--'+name,type=Path)
    a=p.parse_args();analysis(a.inputs,a.collections,a.parity_input,a.out,a.secondary_input,a.secondary_private)
    print('E50 COMPLETE_ANALYSIS; see sealed report_label in every verdict')
