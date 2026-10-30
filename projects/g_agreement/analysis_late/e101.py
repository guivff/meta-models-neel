"""§209 once-only analysis; test readouts opened only after the source commit gate."""
import argparse,math
from pathlib import Path
import numpy as np
from .common import *
from projects.g_agreement.e101.contract import committed_dose
CONTENT=('language_plan','format_plan','fact_recall','language_continuation')
BOOK=('nesting_depth','indent_level','page_range_digit')
ROWS=CONTENT+BOOK
READERS={'oracle':44,'nla':42}

def acquire(s):
    doses=committed_dose(ROOT,s['dose_path'],s['dose_commit'],s['dose_sha256'])
    require(doses['scoring_mode']=='continuation' and doses['dev_count']==84 and doses['dose_policy']=='independent_blocks','registered dose selection')
    selected=doses['selected_doses']
    require(set(selected)=={f'{r}:{b}' for r in ROWS for b in READERS.values()},'all row/block doses')
    targets,ts=load(s['targets'],'TARGETS.json');targets=core.unique(targets)
    require(ts.get('labels_cpu_only') is True and ts.get('experiment')=='E101','CPU target seal')
    for row in ROWS:require(sum(t['row']==row for t in targets.values())==84,'84 CPU test targets/row')
    require(len(targets)==588,'full test inventory')
    for t in targets.values():
        require(t['split']=='test' and t['target'] in ('A','B') and set(t['values'])=={'A','B'} and t['contrast_target_sign'] in (-1,1),'target schema')
        require(set(t['J_fraction'])=={'42','44'} and all(math.isfinite(v) and 0<=v<=1 for v in t['J_fraction'].values()),'J fraction both dev directions')
    rows=[];seen=set()
    for shard in s['shards']:
        items,ins=load(shard['input'],'items.json');ip=Path(shard['input']['seal']).parent
        require('MANIFEST.json' in ins['files'] and ins.get('labels_on_pod') is False,'sealed public input manifest')
        manifest=read(ip/'MANIFEST.json')
        require(manifest['stage']=='test' and manifest['dose_sha256']==s['dose_sha256'] and manifest['dose_commit']==s['dose_commit'] and manifest['scoring_mode']=='continuation','test input dose provenance')
        grid,outs=load(shard['output'],'JOB_GRID.json');op=Path(shard['output']['seal']).parent
        require(outs['experiment']=='E101' and outs['stage']=='test' and outs['status']=='COMPLETE' and outs['input_sha256']==shard['input']['sha256'] and outs['dose_sha256']==s['dose_sha256'],'complete bound test output')
        require(outs['source_sha256']==s['runner_source_sha256'],'runner source pin')
        require(sorted(read(op/'COMPLETED.json'))==list(range(len(grid))),'complete jobs')
        data={}
        for n,j in enumerate(grid):
            name=f'jobs/{n:06d}.json';require(name in outs['files'],'sealed job')
            rr=read(op/name);require([x['id'] for x in rr]==[items[i]['id'] for i in j['indices']],'exact scheduled job order')
            for x in rr:
                key=(x['id'],j['kind']);require(key not in data,'duplicate acquisition');data[key]=x
        for x in items:
            require(x['base_id'] in targets,'unknown test item');t=targets[x['base_id']]
            reader={44:'oracle',42:'nla'}[x['block']]
            require(x['row']==t['row'] and x['condition'] in ('steered','random') and x['alpha']==selected[f'{x["row"]}:{x["block"]}']['alpha'] and x['alpha'] is not None,'registered row/dose/condition')
            key=(x['base_id'],reader,x['condition']);require(key not in seen,'duplicate test cell');seen.add(key)
            pairs=data[(x['id'],'logits')]['pair_logprobs']
            require(len(pairs)==len(x['candidate_ids']) and pairs and all(len(p)==2 and all(math.isfinite(v) for v in p) for p in pairs),'full frozen continuation logprobs')
            contrast=float(np.mean([a-b for a,b in pairs]));ratio=x['norm_ratio']
            require(math.isfinite(ratio) and ratio>0,'finite norm ratio')
            rows.append(dict(id=x['id'],item_id=x['base_id'],row=x['row'],reader=reader,condition=x['condition'],alpha=x['alpha'],text=data[(x['id'],reader)]['text'],
                property=t['property'],values=t['values'],target=t['target'],flipped=contrast*t['contrast_target_sign']>0,contrast=contrast,norm_ratio=ratio,norm_over_1_5=ratio>1.5))
        require(len(data)==2*len(items),'no unregistered acquisition outputs')
    omitted=set(s.get('operational_not_run',[]))
    require(omitted <= {'language_plan:44'},'§212 only language_plan may be operationally omitted')
    if omitted:
        disposition,receipt=load(s['operational_disposition'],'DISPOSITION.json')
        require(disposition.get('cell')=='language_plan:44' and disposition.get('status')=='NOT RUN (operational)' and disposition.get('retime_failed') is True,'sealed one-retime failure required')
    expected={(i,reader,c) for i,t in targets.items() for reader,b in READERS.items() if selected[f'{t["row"]}:{b}']['alpha'] is not None and f'{t["row"]}:{b}' not in omitted for c in ('steered','random')}
    require(seen==expected,'exact eligible test grid')
    if s.get('scope')=='descriptive_two_cell':
        require({k:v['alpha'] for k,v in selected.items() if v['alpha'] is not None}=={'fact_recall:44':4,'language_plan:44':4},'§212 frozen two eligible cells only')
        if not s.get('baselines'):return rows,selected,targets
    baseline,bs=load(s['baselines'],'BASELINES.json')
    require(bs.get('experiment')=='E101' and bs.get('existing_outputs_only') is True and bs.get('source_seals'),'sealed historical baseline joins')
    source_seals=[verify(source['seal'],source['sha256']) for source in bs['source_seals']]
    want={(i,r,'unsteered') for i in targets for r in READERS}|{(i,'text','text') for i,t in targets.items() if t['row'] in CONTENT}
    require(len(baseline)==len(want) and {(x['item_id'],x['reader'],x['condition']) for x in baseline}==want,'complete historical baseline grid')
    for x in baseline:
        ref=x['source_ref'];entry=bs['source_seals'][ref['seal_index']];ss=source_seals[ref['seal_index']]
        require(ref['member'] in ss['files'],'baseline member not sealed')
        value=read(Path(entry['seal']).parent/ref['member'])
        for key in ref['keys']:value=value[key]
        require(value==x['text'],'baseline exact source text')
        t=targets[x['item_id']]
        rows.append(dict(x,id='baseline:'+x['item_id']+':'+x['reader'],row=t['row'],property=t['property'],values=t['values'],target=t['target']))
    return rows,selected,targets

def analyze(rows,selected,targets,cohort,descriptive=False,operational_not_run=()):
    require(cohort=='steered_flipped','§209 clarification 3 (22729040): paired steered-flipped cohort')
    result=dict(experiment='E101',bootstrap=dict(draws=DRAWS,seed=SEED,unit='item',paired=True),cohort=cohort,rows={},rules={})
    by={(x['item_id'],x['reader'],x['condition']):x for x in rows}
    for row in ROWS:
        ids=sorted(i for i,t in targets.items() if t['row']==row); rr={}
        for reader,b in READERS.items():
            alpha=selected[f'{row}:{b}']['alpha']
            j={targets[i]['J_fraction'][str(b)] for i in ids};require(len(j)==1,'one dev direction per row/block')
            un=stat({i:by.get((i,reader,'unsteered'),{}).get('score') for i in ids})
            if f'{row}:{b}' in operational_not_run:
                rr[reader]=dict(status='NOT RUN (operational)',reason='§212 amendment2 one retime failed',alpha=alpha,J_fraction=j.pop(),unsteered=un);continue
            if alpha is None:
                rr[reader]=dict(status='NOT EVALUABLE',reason='no dev dose reaches 70%',alpha=None,J_fraction=j.pop(),unsteered=un);continue
            st={i:by[(i,reader,'steered')] for i in ids};ra={i:by[(i,reader,'random')] for i in ids}
            sv={i:st[i]['score'] if st[i]['flipped'] else None for i in ids}
            rv={i:ra[i]['score'] if (st[i]['flipped'] if cohort=='steered_flipped' else ra[i]['flipped']) else None for i in ids}
            rr[reader]=dict(status='EVALUABLE',alpha=alpha,B=stat({i:int(st[i]['flipped']) for i in ids}),B_random=stat({i:int(ra[i]['flipped']) for i in ids}),
                S_target=stat(sv),S_random=stat(rv),difference=stat(sv,rv),S_all_steered=stat({i:st[i]['score'] for i in ids}),S_all_random=stat({i:ra[i]['score'] for i in ids}),flipped_n=sum(x['flipped'] for x in st.values()),
                flipped_unparseable=sum(st[i]['flipped'] and st[i]['score'] is None for i in ids),J_fraction=j.pop(),J_chance=.27,unsteered=un,
                norms={c:{i:dict(ratio=x['norm_ratio'],flag=x['norm_over_1_5']) for i,x in z.items()} for c,z in [('steered',st),('random',ra)]})
        result['rows'][row]=rr
        if row in CONTENT:
            # Report explicit stated-value presence and stated-only separately.
            result['rows'][row]['text_stated_rate']=stat({i:by.get((i,'text','text'),{}).get('stated_value') for i in ids})
            result['rows'][row]['text_stated_only_rate']=stat({i:None if by.get((i,'text','text'),{}).get('score') is None else int(by[(i,'text','text')]['score']==-1) for i in ids})
    for reader in READERS:
        f1=[];ff1=[];f2=[];ff2=[]
        for row in CONTENT:
            z=result['rows'][row][reader]
            if z['status']!='EVALUABLE':f1.append(None);ff1.append(None);continue
            f1.append(both(ge(z['S_target'],.40),low(z['S_target'],.20),ge(z['difference'],.30),low(z['difference'],0)))
            ff1.append(le(z['S_target'],.10))
        for row in BOOK:
            z=result['rows'][row][reader]
            if z['status']!='EVALUABLE' or not ge(z['B'],.70):f2.append(None);ff2.append(None);continue
            f2.append(both(le(z['S_target'],.10),high(z['S_target'],.20)));ff2.append(ge(z['S_target'],.30))
        a,c=count(f1,3),count(f2,2)
        result['rules'][reader]={'R-F1':a,'R-F1_falsifier':count(ff1,3),'R-F2':c,'R-F2_falsifier':count(ff2,2),
            'R-F3':dict(status='MET' if a['status']==c['status']=='MET' else 'NOT MET' if 'NOT MET' in (a['status'],c['status']) else 'NOT EVALUABLE')}
    if descriptive:
        result['scope']='descriptive_two_cell'
        result['authority']='§212 E101 clarification4 and amendment2'
        result['null_wording']='the steering vectors at α ≤ 4 never crossed the decision boundary of the frozen behavioural contrast on 12 of 14 cells'
        result['metric_limitations']=['nesting_depth short candidate [2205] is a strict prefix of the long candidate; summed sequence log-probability structurally favours the short one','page_range_digit is 0/84 at baseline']
        result['rules']={reader:{rule:dict(status='NOT EVALUABLE',reason='§212: only two of fourteen cells reach alpha; descriptive tests only') for rule in ('R-F1','R-F2','R-F3','R-F1_falsifier','R-F2_falsifier')} for reader in READERS}
        result['baselines_status']='provided' if any(x['condition']=='unsteered' for x in rows) else 'NOT PROVIDED; descriptive two-cell result does not wait for text baselines'
    return result

def figure(result,path):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(9,7))
    for row,rs in result['rows'].items():
        for reader in READERS:
            z=rs[reader]
            if z['status']!='EVALUABLE' or z['S_target']['estimate'] is None:continue
            x,y=z['B']['estimate'],z['S_target']['estimate'];ax.scatter(x,y,marker='o' if reader=='oracle' else '^');ax.annotate(row+' / '+reader,(x,y),fontsize=7)
            if z['S_target']['CI95']:ax.vlines(x,*z['S_target']['CI95'],alpha=.4)
    ax.set(xlabel='Behaviour flip B',ylabel='S_target among flipped items',xlim=(-.02,1.02),ylim=(-1.05,1.05),title='E101: behaviour versus reader report')
    fig.tight_layout();fig.savefig(path);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['export','analyze']);p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=read(a.spec);require(s['experiment']=='E101','experiment');require(s.get('scope')=='descriptive_two_cell','latest §212 descriptive scope required');rows,doses,targets=acquire(s)
    digest=hashlib.sha256(json.dumps(s,sort_keys=True).encode()).hexdigest()
    if a.action=='export':core.export(rows,s['blind'],s['private'],digest,commit);return
    scored,jhash=core.load_codes(dict(s,output_sha256=digest));original=core.unique(rows)
    require(set(original)=={x['id'] for x in scored},'exact scored inventory')
    for x in scored:require(all(x[k]==v for k,v in original[x['id']].items()),'private join mutation')
    codes=core.unique(read(Path(s['judgments'])/'JUDGMENTS.json'))
    for x in scored:
        if x['reader']=='text':
            code=codes[x['opaque_id']];stated='B' if x['target']=='A' else 'A'
            x['stated_value']=None if code['category']=='UNPARSEABLE' else int(stated in code['values'])
    require(s['cohort']=='steered_flipped','clarification 3 cohort')
    import matplotlib
    out=reserve('E101',s,commit)
    result=analyze(scored,doses,targets,s['cohort'],descriptive=True,operational_not_run=s.get('operational_not_run',[]));result['judgment_sha256']=jhash
    finish('E101',s,commit,result,out,lambda out:figure(result,out/'B_VS_REPORT.png'))
if __name__=='__main__':main()
