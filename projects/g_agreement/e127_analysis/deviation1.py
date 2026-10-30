"""§238 deviation1: pair-logit flip source only; original greedy run untouched."""
import argparse
from copy import deepcopy
from pathlib import Path
import numpy as np
from . import transport as t, rules as r127
from projects.g_agreement.e128_analysis import rules as r128
from .common import require, state, rate, criterion, rule
LABEL='deviation 1 (pair-logit flips; greedy window failed)'


def pair_answer(record,new_value):
    """E104 mean(A-B) on frozen first-token pairs; strict preferences, tie neither."""
    if record is None:return None
    require(new_value in ('A','B'),'original A/B orientation')
    require('pair_logits' in record,'sealed first-token candidate pairs required')
    pairs=np.asarray(record['pair_logits'],dtype=float)
    require(pairs.ndim==2 and pairs.shape[0]>0 and pairs.shape[1]==2 and np.isfinite(pairs).all(),'finite original candidate pairs')
    delta=float(np.mean(pairs[:,0]-pairs[:,1]))*(1 if new_value=='A' else -1)
    return 'new' if delta>0 else 'old' if delta<0 else 'other'


def analyze127(records):
    xs=deepcopy(records)
    for x in xs:
        for z in x['conditions'].values():z['answer']=z['pair_answer_deviation1']
    result=r127.analyze(xs)
    result['flipped_set_definition']='context_update first-token candidate pairs strictly favour new AND no_prefix strictly favours old; E104 mean(A-B); ties neither'
    result['behaviour_measure']='E104 frozen first-token candidate-pair logit preference'
    return result


def analyze128(records):
    # Reuse the registered lower-dose rules, then add original alpha8 on this SAME measure.
    xs=deepcopy(records)
    for x in xs:
        for d,zs in x['doses'].items():
            for z in zs.values():z['flipped']=None if d==8 else z['pair_preference_flip_descriptive']
    result=r128.analyze(xs)
    cohort=[x for x in xs if x['doses'][8]['steered']['pair_preference_flip_descriptive'] is True]
    rates={c:{str(l):{v:rate([state(x['doses'][8][c]['oracle'][l],x[v+'_value']) for x in cohort]) for v in ('old','new')} for l in (44,52)} for c in ('steered','random')}
    pattern=rule([criterion(rates['steered']['44']['old'],.50,.35),criterion(rates['steered']['52']['new'],.70)])
    result['doses']['8']=dict(flipped_n=len(cohort),behaviour_missing_n=sum(x['doses'][8]['steered']['pair_preference_flip_descriptive'] is None for x in xs),flipped_set_rates=rates,descriptive_pattern=pattern,random_behaviour_flipped_n=sum(x['doses'][8]['random']['pair_preference_flip_descriptive'] is True for x in xs),random_control_population='same steered-flipped cohort, not separately selected')
    result['flip_counts']['8']=len(cohort)
    if result['alpha_min'] is None and not result['selection_ambiguous'] and len(cohort)>=42:
        result['alpha_min']=8
        result['R_DOSE1']='NOT EVALUABLE'
        result['reading']='the flip needs α = 8 on the same E104 pair-logit measure; retain strong-steer caveat/question open'
    result['selection']='smallest2/4/8 with>=42 E104 first-token pair-logit flips; original alpha8 sealed result reused, no greedy imputation'
    result['alpha8_pair_logit_reference'].update(measure='SAME E104 candidate-pair first-token logit preference',used_for_alpha_min=True)
    result['alpha8_source']='original sealed E104 pair-preference flags and optional E104/E109 judgments unchanged; no alpha8 rerun/rejudge'
    return result


def run(spec,experiment,commit):
    guard=t.CUSTODY/experiment.lower()/'DEVIATION1_ONCE.json'
    require(not guard.exists(),'deviation1 once guard consumed; no replay')
    items,original,meta=t.cohort(spec,experiment)
    records=t.inputs(spec,experiment,items,original,meta,pair_answer_fn=pair_answer)
    analysis=t.CUSTODY/experiment.lower()/'deviation1_once'
    out=t.core.claim(dict(analysis=str(analysis),guard=str(guard),output_sha256=spec['output_sha256']),commit)
    result=(analyze127 if experiment=='E127' else analyze128)(records)
    result.update(analysis_label=LABEL,deviation=1,registered_greedy_result='NOT EVALUABLE (measurement)',new_calls=0)
    t.core.write(out/'RESULTS.json',result);t.core.write(out/'BINDING.json',spec)
    t.core.seal(out,'ANALYSIS_SEAL.json',experiment=experiment,status='COMPLETE_ONCE',analysis_label=LABEL,code_commit=commit,inventory_sha256=spec['inventory_sha256'],output_sha256=spec['output_sha256'],new_calls=0)
    return out/'ANALYSIS_SEAL.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--experiment',choices=['E127','E128'],required=True);a=p.parse_args()
    commit=t.committed(Path(__file__).resolve().parent)
    t.committed(Path(__file__).resolve().parents[1]/'e128_analysis')
    print(run(t.core.read(a.spec),a.experiment,commit))

if __name__=='__main__':main()
