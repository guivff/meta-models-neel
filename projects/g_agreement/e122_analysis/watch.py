"""Source-pointer-only binding, then the sole guarded E122 phase sequence.

Invoke once when the exact PLAN/raw-index seals are ready. Re-entry verifies
completed phase seals without recomputing statistics; a failed guard stays fatal.
"""
import argparse
from pathlib import Path
from . import adapter as a


def bind_phase(plan, action):
    frozen,cells,_=a.frozen_inputs(plan)
    index_path=Path(plan['raw_index_seal'])
    index_seal=a.core.verify(index_path,plan['raw_index_sha256'])
    a.require(index_seal['experiment']=='E122' and index_seal['status']=='SOURCE_POINTERS_ONLY'
              and index_seal['contrast_source_sha256']==a.CONTRAST_SHA and index_seal['source_e85_bank_sha256']==a.E85_BANK_SHA
              and 'RAW_INDEX.json' in index_seal['files'], 'original source-only index')
    phase={'select-dev':'dev','native-test':'native_test','transplant':'transplant'}[action]
    metadata=dict(experiment='E122',status='COMPLETE',phase=phase,frozen_sha256=plan['frozen_sha256'],
                  block=44,score_mode='full_continuation_logprob_sum',source_seals=index_seal['source_seals'],
                  normalizer_plan_sha256=a.digest(plan))
    if phase!='dev':
        sp,choice=a.prior_selection(plan)
        metadata.update(selection_seal_sha256=a.sha(sp),selected_contrast_id=choice['selected_contrast_id'])
    if phase=='transplant':
        gp,gmeta=a.phase_seal('native_test')
        a.require(gmeta['frozen_sha256']==plan['frozen_sha256'] and a.read(gp.parent/'RESULTS.json')['R_BEV1']=='MET', 'gate before transplant index access')
        metadata.update(gate_seal_sha256=a.sha(gp),supplied_vector_mode=True,vectors_unscaled=True)
    # This file contains IDs/pointers only. Numerical arrays stay in the original
    # sealed job members and are opened later by adapter.measurements.
    index=a.read(index_path.parent/'RAW_INDEX.json')
    selected=[x for x in cells if x['split']==('dev' if phase=='dev' else 'test') and (phase!='transplant' or x['addressed']==0)]
    key='transplant' if phase=='transplant' else 'native'
    source=index[key]
    if phase!='transplant':
        a.require(set(source)=={x['id'] for x in cells}, 'all original native source pointers')
    else:
        a.require(set(source)=={x['id'] for x in selected}, 'all 200 transplant carrier pointers')
    records=[]
    for x in selected:
        v=source[x['id']]
        refs=v.values() if phase=='transplant' else [v]
        if phase=='transplant':a.require(set(v)=={'T','S'}, 'both source conditions')
        for ref in refs:
            a.require(set(ref)=={'seal_index','member','keys'}, 'source pointers only; no score substitution')
        records.append(dict(id=x['id'],**({'conditions':v} if phase=='transplant' else {'ref':v})))
    out=a.CANONICAL/'bindings'/phase
    if out.exists():
        seal=out/'OUTPUT_SEAL.json'
        prior=a.core.verify(seal,a.sha(seal))
        a.require(all(prior.get(k)==v for k,v in metadata.items()) and a.read(out/'MEASUREMENTS.json')==records, 'immutable previous source binding')
    else:
        out.mkdir(parents=True)
        a.write(out/'MEASUREMENTS.json',records)
        a.core.seal(out,'OUTPUT_SEAL.json',**metadata)
    return dict(frozen_seal=str(frozen),frozen_sha256=plan['frozen_sha256'],output_seal=str(out/'OUTPUT_SEAL.json'),output_sha256=a.sha(out/'OUTPUT_SEAL.json'))


def run(plan, commit):
    for action,phase in [('select-dev','dev_selection'),('native-test','native_test'),('transplant','transplant')]:
        if phase=='transplant':
            gp,gmeta=a.phase_seal('native_test')
            a.require(gmeta['frozen_sha256']==plan['frozen_sha256'], 'same native gate inventory')
            if a.read(gp.parent/'RESULTS.json')['R_BEV1']!='MET':
                return dict(status='COMPLETE_R_BEV1_NOT_MET_B_NOT_RUN',seal=str(gp),sha256=a.sha(gp))
        if (a.CANONICAL/(phase+'_ONCE.json')).exists() or (a.CANONICAL/phase).exists():
            sp,sm=a.phase_seal(phase)  # missing/incomplete seal fails; no recovery inference
            a.require(sm['frozen_sha256']==plan['frozen_sha256'], 'existing phase inventory')
            a.require(a.read(sp.parent/'BINDING.json')['output_sha256']==bind_phase(plan,action)['output_sha256'], 'existing exact source binding')
        else:
            a.execute(bind_phase(plan,action),action,commit)
    p,_=a.phase_seal('transplant')
    return dict(status='COMPLETE_ALL_PHASES',seal=str(p),sha256=a.sha(p))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);args=parser.parse_args()
    commit=a.committed()  # before any plan, source, raw score or prior analysis read
    print(run(a.read(args.plan),commit))


if __name__=='__main__':main()
