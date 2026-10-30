"""One separate opening for §243 A/B; no refit, classification or judging."""
import argparse
from pathlib import Path
import numpy as np
from projects.g_agreement.e127_analysis import transport as t, deviation1 as d
from projects.g_agreement.e127_analysis.common import require, rate
from results.g_agreement.understand.e94.score94 import value_class
from projects.g_agreement.e128_analysis.coordinator import SPEC_SHA

CATEGORIES=('old','new','dual','neither_or_unparseable')
DOSES=(2,4,8)
CONDITIONS=('steered','random')
LAYERS=(44,52)
PRIMARY_SHA='9b4c54a4422bb60db12d32899cd68cb4715ec2ec6a6c0e4498eb933c6f8c23c7'


def category(code, old, new):
    require(old != new and {old,new}=={'A','B'}, 'original orientation')
    value_class(code,new)
    if code['category']=='UNPARSEABLE': return 'neither_or_unparseable'
    values=set(code['values'])
    return 'dual' if len(values)==2 else 'old' if old in values else 'new' if new in values else 'neither_or_unparseable'


def table(xs,dose,condition,layer):
    codes=[x['doses'][dose][condition]['oracle'][layer] for x in xs]
    cats=[category(z,x['old_value'],x['new_value']) for x,z in zip(xs,codes)]
    return dict(planned_n=len(xs),unparseable_n=sum(z['category']=='UNPARSEABLE' for z in codes),
                categories={c:rate([int(v==c) for v in cats]) for c in CATEGORIES})


def tables(xs,dose):
    return {c:{str(l):table(xs,dose,c,l) for l in LAYERS} for c in CONDITIONS}


def paired(xs,condition,layer,category_name,draws=5000,seed=0):
    # Every fixed-cohort item contributes both cells. UNPARSEABLE belongs to the
    # explicit combined bin, not an invented old/new/dual value.
    delta=np.array([int(category(x['doses'][8][condition]['oracle'][layer],x['old_value'],x['new_value'])==category_name)
                    -int(category(x['doses'][4][condition]['oracle'][layer],x['old_value'],x['new_value'])==category_name) for x in xs],dtype=float)
    if not len(delta): return dict(n=0,estimate=None,CI95=None,valid_bootstraps=0)
    rng=np.random.default_rng(seed)
    boot=delta[rng.integers(0,len(delta),(draws,len(delta)))].mean(axis=1)
    return dict(n=len(delta),estimate=float(delta.mean()),CI95=np.quantile(boot,[.025,.975]).tolist(),valid_bootstraps=draws)


def analyze(records):
    require(len(records)==84 and len({x['item_id'] for x in records})==84,'exact84 distinct items')
    records=sorted(records,key=lambda x:x['item_id'])
    for x in records:
        require(set(x['doses'])==set(DOSES),'exact2/4/8 grid')
        for a in DOSES:
            require(set(x['doses'][a])==set(CONDITIONS),'both conditions')
            for z in x['doses'][a].values():
                require(type(z['pair_preference_flip_descriptive']) is bool,'complete sealed pair-logit flips')
                require(set(z['oracle'])==set(LAYERS),'both layers')
    fixed=[x for x in records if x['doses'][4]['steered']['pair_preference_flip_descriptive']]
    require(len(fixed)==42,'original42 alpha4 flippers')
    a={str(dose):dict(all84=tables(records,dose),flipped=tables([x for x in records if x['doses'][dose]['steered']['pair_preference_flip_descriptive']],dose)) for dose in DOSES}
    b=dict(n=42,tables={str(dose):tables(fixed,dose) for dose in (4,8)},
           differences={c:{str(l):{v:paired(fixed,c,l,v) for v in CATEGORIES} for l in LAYERS} for c in CONDITIONS})
    return dict(experiment='E128 addenda A/B',label='exploratory, post hoc',A=a,B=b,
                cohort='Each dose uses its steered pair-logit flippers; random control uses identical items. B fixes the alpha4 steered42.',
                missing_policy='UNPARSEABLE is counted in neither_or_unparseable as required by §243, with separate unparseable count; no rejudging or assertion of semantic neither.',
                bootstrap=dict(draws=5000,seed=0,unit='paired original item',contrast='alpha8 minus alpha4',interval='percentile95'),
                reading='Positive fixed-cohort old44 difference indicates dose dependence. Approximately unchanged with a higher whole-set alpha8 rate suggests item selection; no invented equivalence threshold or confirmatory rule.',
                original_R_DOSE1='NOT MET (copied unchanged)',new_calls=0)


def run(spec,commit):
    guard=t.CUSTODY/'e128'/'ADDENDA243_ONCE.json'
    require(not guard.exists(),'addenda guard consumed; never replay')
    primary=t.CUSTODY/'e128'/'deviation1_once'/'ANALYSIS_SEAL.json'
    t.core.verify(primary,PRIMARY_SHA)
    # Exclusive claim before opening any value-code inputs for this addendum.
    out=t.core.claim(dict(analysis=str(t.CUSTODY/'e128'/'addenda243_once'),guard=str(guard),output_sha256=spec['output_sha256']),commit)
    items,original,meta=t.cohort(spec,'E128')
    records=t.inputs(spec,'E128',items,original,meta,pair_answer_fn=d.pair_answer)
    t.core.write(out/'RESULTS.json',analyze(records));t.core.write(out/'BINDING.json',spec)
    t.core.seal(out,'ANALYSIS_SEAL.json',experiment='E128 addenda243',status='COMPLETE_ONCE',code_commit=commit,primary_seal_sha256=PRIMARY_SHA,spec_sha256=SPEC_SHA,new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=t.committed(Path(__file__).resolve().parent)
    require(t.core.sha(args.spec)==SPEC_SHA,'unchanged original E128 SPEC')
    print(run(t.core.read(args.spec),commit))
if __name__=='__main__':main()
