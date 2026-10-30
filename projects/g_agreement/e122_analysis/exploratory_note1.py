"""EXPLORATORY, POST HOC E122 note1; registered R-BEV1/R-BEV2 unchanged."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from . import adapter as a, rules

LABELS=dict(exploratory=True,post_hoc=True,analysis_type='EXPLORATORY_POST_HOC_E122_NOTE1',authority='Guiv direct instruction and BRIEF note1 01f45c0ba')
CONTRAST='formal_vs_informal'


def result(records,native):
    a.require(native['R_BEV1']=='NOT MET' and native['R_BEV2']=='NOT RUN' and native['selected_contrast_id']==CONTRAST,'registered record unchanged')
    denominator=native['native_addressed_shift']['estimate']
    a.require(denominator<0 and native['native_addressed_shift']['CI95'][1]<0,'original negative native addressed shift')
    a.require(all(x['split']=='test' and set(x['scores'])=={'T','S'}for x in records),'original test T/S only')
    delta,genres=rules.quartet_differences(records,None,100,transplant=True)
    pooled=rules.statistic(delta)
    carries=pooled['estimate']<0 and pooled['CI95'][1]<0
    if carries:reading='exploratory post hoc: read-site vector carries part of the cue effect in the native negative direction'
    elif pooled['CI95'][0]<=0<=pooled['CI95'][1]:reading='exploratory post hoc: no evidence that the read-site vector carries the cue effect; CI includes zero'
    else:reading='exploratory post hoc: no evidence of the specified negative-direction mediation'
    return dict(LABELS,experiment='E122',selected_contrast_id=CONTRAST,n_test_quartets=100,
                delta=pooled,per_genre={str(g):rules.statistic(v)for g,v in genres.items()},
                bootstrap=dict(draws=rules.DRAWS,seed=rules.SEED,unit='source item = original matched quartet; genres averaged within quartet',paired=True),
                exploratory_negative_direction_evidence=carries,reading=reading,
                fraction_recovered=dict(estimate=pooled['estimate']/denominator,numerator=pooled['estimate'],denominator=denominator,definition='exploratory post hoc pooled Delta / exact sealed native addressed shift',clipped=False),
                confirmatory_record=dict(R_BEV1='NOT MET',R_BEV2='NOT RUN'),
                note='Exploratory post hoc scoring does not meet, replace or change registered R-BEV2.')


def baseline(plan):
    frozen,cells,defs=a.frozen_inputs(plan)
    sp,choice=a.prior_selection(plan);gp,meta=a.phase_seal('native_test');native=a.read(gp.parent/'RESULTS.json')
    a.require(choice['selected_contrast_id']==CONTRAST==native['selected_contrast_id'],'only previously frozen formal_vs_informal')
    a.require(meta['frozen_sha256']==plan['frozen_sha256'] and native['R_BEV1']=='NOT MET' and native['R_BEV2']=='NOT RUN','preserve failed confirmatory gate')
    a.require(not (a.CANONICAL/'transplant_ONCE.json').exists() and not (a.CANONICAL/'transplant').exists(),'confirmatory part b stays NOT RUN')
    return frozen,cells,defs,sp,gp,native


def bind(plan,base):
    frozen,cells,defs,sp,gp,native=base
    ip=Path(plan['raw_index_seal']);index_meta=a.core.verify(ip,plan['raw_index_sha256'])
    a.require(index_meta['experiment']=='E122' and index_meta['status']=='SOURCE_POINTERS_ONLY'
              and index_meta['contrast_source_sha256']==a.CONTRAST_SHA and index_meta['source_e85_bank_sha256']==a.E85_BANK_SHA,'original source-only index')
    index=a.read(ip.parent/'RAW_INDEX.json')['transplant'];selected=[x for x in cells if x['split']=='test' and x['addressed']==0]
    a.require(set(index)=={x['id']for x in selected} and all(set(v)=={'T','S'}for v in index.values()),'full 200 T/S carriers')
    records=[dict(LABELS,id=x['id'],conditions=index[x['id']])for x in selected]
    out=a.CANONICAL/'exploratory_note1_binding';out.mkdir(exist_ok=False)
    a.write(out/'MEASUREMENTS.json',records)
    a.core.seal(out,'OUTPUT_SEAL.json',**LABELS,experiment='E122',status='COMPLETE',phase='transplant',
                frozen_sha256=plan['frozen_sha256'],block=44,score_mode='full_continuation_logprob_sum',
                selection_seal_sha256=a.sha(sp),native_test_seal_sha256=a.sha(gp),selected_contrast_id=CONTRAST,
                source_seals=index_meta['source_seals'],supplied_vector_mode=True,vectors_unscaled=True)
    return dict(LABELS,frozen_seal=str(frozen),frozen_sha256=plan['frozen_sha256'],output_seal=str(out/'OUTPUT_SEAL.json'),output_sha256=a.sha(out/'OUTPUT_SEAL.json'))


def run(plan,commit):
    guard=a.CANONICAL/'exploratory_note1_ONCE.json';out=a.CANONICAL/'exploratory_note1'
    a.require(not guard.exists() and not out.exists(),'exploratory note1 already claimed; no replay')
    base=baseline(plan);spec=bind(plan,base)
    # Separate exclusive exploratory guard, before the first T/S numerical read.
    with guard.open('x')as f:
        import json
        json.dump(dict(LABELS,code_commit=commit,utc=datetime.now(timezone.utc).isoformat(),output_sha256=spec['output_sha256'],native_test_seal_sha256=a.sha(base[4])),f)
    out.mkdir(exist_ok=False)
    a.write(out/'FIRST_OPENING.json',dict(LABELS,utc=datetime.now(timezone.utc).isoformat(),code_commit=commit,source_binding_sha256=spec['output_sha256']))
    rows=a.measurements(spec,'transplant',base[0],base[1],base[2],selection_path=base[3])
    a.write(out/'RESULTS.json',result(rows,base[5]))
    a.write(out/'BINDING.json',dict(LABELS,**{k:v for k,v in spec.items()if k not in LABELS},native_test_seal_sha256=a.sha(base[4])))
    a.core.seal(out,'ANALYSIS_SEAL.json',**LABELS,experiment='E122',status='COMPLETE_ONCE_EXPLORATORY_POST_HOC',code_commit=commit,
                native_test_seal_sha256=a.sha(base[4]),output_sha256=spec['output_sha256'],confirmatory_R_BEV1='NOT MET',confirmatory_R_BEV2='NOT RUN')
    baseline(plan)  # original phases unchanged; confirmatory b still untouched
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);args=p.parse_args()
    commit=a.committed();print(run(a.read(args.plan),commit))

if __name__=='__main__':main()
