"""Prospective E135: unchanged E128 transport/scoring with doses6 only."""
import argparse
from pathlib import Path
import numpy as np
from projects.g_agreement.e127_analysis import transport as t, deviation1 as d
from projects.g_agreement.e127_analysis.common import require,rate,state
from projects.g_agreement.e128_addenda.adapter import category,PRIMARY_SHA
from projects.g_agreement.e128_analysis.coordinator import SPEC_SHA
from .transport import inputs

DOSES=(6,)
CONDITIONS=('steered','random')
LAYERS=(44,52)
CUSTODY=t.CUSTODY.parents[3]/'wt-wmech'/'cache/g_agreement/understand/e135'


def fixed_cohort(spec,expected_ids):
    # Read original native pair-logit records only; no original reader-code replay.
    path=Path(spec['e128_spec']);require(t.core.sha(path)==SPEC_SHA,'exact E128 source specification')
    s=t.core.read(path);op=Path(s['output_seal']);meta=t.core.verify(op,s['output_sha256'])
    ip=Path(s['inventory_seal']);t.core.verify(ip,s['inventory_sha256'])
    items=t.core.unique(t.core.read(ip.parent/'INVENTORY.json'),'item_id')
    require(set(items)==expected_ids,'same original84 identity set')
    sources=meta['source_seals'];seals=[t.core.verify(v['seal'],v['sha256']) for v in sources];cache={}
    def ref(p):
        n=p['seal_index'];require(type(n) is int and 0<=n<len(seals) and p['member'] in seals[n]['files'],'sealed native pointer')
        key=(n,p['member'])
        if key not in cache:cache[key]=t.core.read(Path(sources[n]['seal']).parent/p['member'])
        val=cache[key]
        for k in p['keys']:val=val[k]
        return val
    rows=t.core.unique(t.core.read(op.parent/'MEASUREMENTS.json'),'item_id');require(set(rows)==expected_ids,'full original84 native grid')
    selected=set()
    for i,row in rows.items():
        cell=row['doses']['4']['steered']['behaviour'];identity=ref(cell['identity']);record=ref(cell['record'])
        require(identity['item_id']==i and identity['condition']=='steered' and identity['dose']==4 and identity['raw_id']==record['id'],'original native identity')
        value=d.pair_answer(record,items[i]['new_value']);require(value is not None,'original native pair known')
        if value=='new':selected.add(i)
    require(len(selected)==42,'original fixed42')
    return selected


def calibration(data,ids):
    require(data['block']==40 and data['positions']=='eight_before_read' and data['unsteered'] is True,'original unsteered write positions')
    rows=data['cells'];by={(x['item_id'],x['dose'],x['condition']):x for x in rows}
    require(len(rows)==len(by)==168 and set(by)=={(i,a,c) for i in ids for a in DOSES for c in CONDITIONS},'exact168 calibration cells')
    natural=[];directions={c:[] for c in CONDITIONS}
    for i in sorted(ids):
        ref=by[i,6,'steered'];v=np.asarray(ref['natural_site_l2'],dtype=float)
        require(v.shape==(8,) and np.all(np.isfinite(v)) and np.all(v>0),'eight finite positive natural site norms')
        require(len(ref['write_positions'])==8 and len(set(ref['write_positions']))==8,'original eight write positions')
        natural.extend(v)
        for c in CONDITIONS:
            norms=[]
            for a in DOSES:
                z=by[i,a,c];w=np.asarray(z['natural_site_l2'],dtype=float)
                require(w.shape==(8,) and np.all(np.isfinite(w)) and np.all(w>0) and np.allclose(w,v,rtol=1e-5,atol=1e-6),'repeated pre-edit norms must agree; no counting repeated cells')
                require(z['write_positions']==ref['write_positions'],'same original write positions')
                n=z['composed_delta_l2'];require(type(n) in (float,int) and np.isfinite(n) and n>0,'actual finite composed delta norm')
                norms.append(n/a)
            require(np.allclose(norms,norms[0],rtol=1e-5,atol=1e-6),'same frozen direction scaled by dose only')
            directions[c].append(norms[0])
    require(np.allclose(directions['steered'],directions['steered'][0],rtol=1e-5,atol=1e-6),'one original class-mean direction magnitude')
    median=float(np.median(natural))
    ratios={}
    for a in (2,4,6,8):
        ratios[str(a)]={c:float(a*np.median(ns)/median) for c,ns in directions.items()}
        ratios[str(a)]['random_item_ratio_range']=[float(a*min(directions['random'])/median),float(a*max(directions['random'])/median)]
    return dict(median_unsteered_residual_l2=median,n_items=84,n_positions=672,raw_cells_checked=168,
                definition='median84x8 individual pre-edit site norms; repeated dose/control cells checked but counted once. Direction magnitude from actual composed delta divided by dose6.',
                repeated_norm_tolerance=dict(rtol=1e-5,atol=1e-6),ratios=ratios,
                historical_doses='2/4/8 scalar arithmetic from original frozen directions; no rerun')


def summarize(xs,a,c,l):
    codes=[x['doses'][a][c]['oracle'][l] for x in xs]
    def indicator(x,z,name):
        if z is None or z['category']=='UNPARSEABLE':return None
        if name in ('old','new'):return state(z,x[name+'_value'])
        return int(category(z,x['old_value'],x['new_value'])==('neither_or_unparseable' if name=='neither' else name))
    return dict(planned_n=len(xs),rates={name:rate([indicator(x,z,name) for x,z in zip(xs,codes)]) for name in ('old','new','dual','neither')},
                terminal_unparseable_n=sum(z is not None and z['category']=='UNPARSEABLE' for z in codes),unrun_n=sum(z is None for z in codes))


def analyze(records,fixed,cal):
    require(len(records)==84 and len({x['item_id'] for x in records})==84,'exact84 grid')
    require(len(fixed)==42 and fixed<={x['item_id'] for x in records},'fixed42 original cohort')
    for x in records:
        require(set(x['doses'])==set(DOSES),'exact6 only')
        for a in DOSES:
            require(set(x['doses'][a])==set(CONDITIONS),'both conditions')
            for z in x['doses'][a].values():
                require(z['pair_preference_flip_descriptive'] is None or type(z['pair_preference_flip_descriptive']) is bool,'pair-logit flag')
                require(set(z['oracle'])==set(LAYERS),'both blocks')
    reports={}
    for a in DOSES:
        flippers=[x for x in records if x['doses'][a]['steered']['pair_preference_flip_descriptive'] is True]
        cohorts={'all84':records,'own_flipped':flippers,'fixed_alpha4_42':[x for x in records if x['item_id'] in fixed],
                 'alpha6_flipped_in_alpha4_cohort':[x for x in flippers if x['item_id'] in fixed],
                 'newly_flipped_alpha6':[x for x in flippers if x['item_id'] not in fixed]}
        reports[str(a)]=dict(calibration_ratio=cal['ratios'][str(a)],
            flip_rates={c:rate([None if x['doses'][a][c]['pair_preference_flip_descriptive'] is None else int(x['doses'][a][c]['pair_preference_flip_descriptive']) for x in records]) for c in CONDITIONS},
            greedy_new_rates={c:rate([None if x['doses'][a][c]['answer'] is None else int(x['doses'][a][c]['answer']=='new') for x in records]) for c in CONDITIONS},
            cohorts={name:{c:{str(l):summarize(xs,a,c,l) for l in LAYERS} for c in CONDITIONS} for name,xs in cohorts.items()})
    return dict(experiment='E135',descriptive=True,confirmatory_rule=None,doses=reports,calibration=cal,
                cohort='Own steered pair-logit flippers; random shares those identities. Fixed42 from original E128 alpha4 native pair logits.',
                patterns='Newly flipped old44 near sealed alpha8 non-cohort rate suggests item property; near fixed-alpha4 cohort rate suggests dose dependence. Descriptive only; no invented threshold/equivalence test.',
                missing_policy='As E128, terminal UNPARSEABLE/unrun unknown excluded from observed rates with planned/known/missing coverage; neither is not missing. No refit/rejudging.',new_calls=0)


def calibration_sources(data,meta):
    sources=meta['source_seals'];seals=[t.core.verify(z['seal'],z['sha256']) for z in sources];cache={}
    for cell in data['cells']:
        ptr=cell['source_ref'];n=ptr['seal_index']
        require(type(n) is int and 0<=n<len(seals) and ptr['member'] in seals[n]['files'],'original calibration member')
        key=(n,ptr['member'])
        if key not in cache:cache[key]=t.core.read(Path(sources[n]['seal']).parent/ptr['member'])
        raw=cache[key]
        for k in ptr['keys']:raw=raw[k]
        mapping=ptr['field_mapping']
        require(set(mapping)=={'dose','condition','natural_site_l2','composed_delta_l2','write_positions'},'literal calibration field map')
        for target,source_key in mapping.items():require(cell[target]==raw[source_key],'calibration must equal original captured fields')
        if 'identity_mapping' in ptr:
            im=ptr['identity_mapping']
            def identity_ref(q):
                j=q['seal_index']
                require(type(j) is int and 0<=j<len(seals) and q['member'] in seals[j]['files'],'sealed identity member')
                key=(j,q['member'])
                if key not in cache:cache[key]=t.core.read(Path(sources[j]['seal']).parent/q['member'])
                value=cache[key]
                for k in q['keys']:value=value[k]
                return value,j
            original,j=identity_ref(im['pointer_ref']);acquired,k=identity_ref(im['acquisition_ref'])
            require(im['pointer_ref']['member']=='ORIGINAL_POINTERS.PRIVATE.json' and seals[j]['experiment']=='E135','original private pointer map')
            verify_input_pin(dict(source_input_sha256=seals[j]['input_sha256']))
            verify_input_pin(dict(source_input_sha256=sources[k]['sha256']))
            require(im['acquisition_ref']['member']=='items.json','original acquisition roster')
            require(raw['id']==original['id']==acquired['id'] and raw['base_id']==acquired['base_id'],'exact acquisition identity')
            require(raw['alpha']==acquired['alpha']==cell['dose'] and raw['condition']==acquired['condition']==cell['condition'],'acquisition dose and condition')
            require(original['original_base_id']==cell['item_id'],'original base cohort identity')
            require(original['scale']==cell['dose']/8,'original dose scale')
        else:
            identity=ptr['original_item_id_field'];require(raw[identity]==cell['item_id'],'original calibration base identity')
    return data


def verify_input_pin(meta):
    require(meta['source_input_sha256']=='381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047','E135 deviation1 alpha6 input seal')


def run(spec,commit):
    guard=CUSTODY/'ANALYSIS_ONCE.json';require(not guard.exists(),'E135 guard consumed; no replay')
    require(spec['status']=='COMPLETE' and spec['experiment']=='E135','complete executable binding')
    require(spec['source_receipt_verified'] is True and spec['calibration_original_direction_verified'] is True,'original runner source and calibration custody')
    out=t.core.claim(dict(analysis=str(CUSTODY/'analysis_once'),guard=str(guard),output_sha256=spec['output_sha256']),commit)
    items,original,meta=t.cohort(spec,'E135');ids={x['item_id'] for x in items}
    verify_input_pin(meta)
    fixed=fixed_cohort(spec,ids)
    cp=Path(spec['calibration_seal']);cm=t.core.verify(cp,spec['calibration_sha256'])
    require(cm['experiment']=='E135' and cm['status']=='COMPLETE' and cm['inventory_sha256']==spec['inventory_sha256'],'sealed calibration bound to same inventory')
    require(cm['direction_sha256']==meta['direction_sha256'] and cm['random_direction_sha256']==meta['random_direction_sha256'] and cm['unsteered_source_sha256']==meta['unsteered_source_sha256'],'original source/direction/norm hashes')
    data=calibration_sources(t.core.read(cp.parent/'CALIBRATION.json'),cm)
    cal=calibration(data,ids)
    records=inputs(spec,'E135',items,original,meta,pair_answer_fn=d.pair_answer)
    result=analyze(records,fixed,cal)
    t.core.write(out/'RESULTS.json',result);t.core.write(out/'BINDING.json',spec)
    t.core.seal(out,'ANALYSIS_SEAL.json',experiment='E135',status='COMPLETE_ONCE',code_commit=commit,inventory_sha256=spec['inventory_sha256'],output_sha256=spec['output_sha256'],calibration_sha256=spec['calibration_sha256'],new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=t.committed(Path(__file__).resolve().parent)
    print(run(t.core.read(args.spec),commit))
if __name__=='__main__':main()
