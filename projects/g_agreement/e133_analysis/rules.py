"""§241 E126 ratios and E127 reader rules repointed to natural matched pairs."""
import math
import numpy as np
from common.stats import bootstrap_ci
from projects.g_agreement.e127_analysis.common import require,rate,criterion,rule
from projects.g_agreement.e126_analysis.rules import BLOCKS,PATCHES,SEED,DRAWS,all3,any3
READS=(44,52,60)


def readout(code,text,value_map,current,previous):
    """Original E104 categories/evidence; frozen CPU opaque-value mapping, no rejudge."""
    if code is None:return None
    require(code['category']in ('states_value','names_property_without_value','exhibits','silent','UNPARSEABLE'),'original E104 code category')
    values=code['values'];require(isinstance(values,list)and len(set(values))==len(values),'explicit value set')
    if code['category']=='UNPARSEABLE':return None
    evidence=code['evidence'];require(isinstance(evidence,str)and isinstance(text,str),'original text/evidence')
    require((not evidence and not values)if code['category']=='silent'else bool(evidence)and evidence in text,'original mandatory verbatim evidence; silent empty')
    if code['category']!='states_value':require(not values,'non-stating code has no values')
    else:require(bool(values)and all(v in value_map for v in values),'frozen opaque value alphabet')
    stated={value_map[v]for v in values}
    return dict(current=int(stated=={current}),previous=int(stated=={previous}),other=int(bool(stated)and stated!={current}and stated!={previous}),none=int(not stated),dual_current_previous=int(current in stated and previous in stated))


def ratio(own,other,patched):
    if any(v is None for v in (own,other,patched)):return None
    require(all(type(v)in(int,float)and math.isfinite(v)for v in (own,other,patched)),'finite original fixed-contrast log odds')
    return None if other==own else (patched-own)/(other-own)


def paired_median(values,draws=DRAWS):
    """Median over both member ratios; matched pairs resampled together."""
    require(all(len(v)==2 for v in values),'two original members per source pair')
    flat=[v for pair in values for v in pair]
    if not flat or any(v is None for v in flat):return dict(estimate=None,CI95=None,n_pairs=len(values),n_items=len(flat),n_defined=sum(v is not None for v in flat),reason='missing/zero denominator retained; no cohort shrinking')
    require(all(math.isfinite(v)for v in flat),'finite ratios')
    point,lo,hi=bootstrap_ci(np.asarray(values),fn=np.median,n_boot=draws,seed=SEED)
    return dict(estimate=point,CI95=[lo,hi],n_pairs=len(values),n_items=len(flat),n_defined=len(flat))


def episode_median(values,episodes,draws=DRAWS):
    """QA2: same per-prompt point median; bootstrap WHOLE original source episodes."""
    require(len(values)==len(episodes)and all(e is not None for e in episodes)and all(len(v)==2 for v in values),'frozen source episode for every QA2 pair')
    flat=[v for pair in values for v in pair];groups=list(dict.fromkeys(episodes));base=dict(n_pairs=len(values),n_items=len(flat),n_defined=sum(v is not None for v in flat),n_episodes=len(groups),bootstrap_unit='source episode; all its pairs/members stay together')
    if not flat or any(v is None for v in flat):return dict(base,estimate=None,CI95=None,reason='missing/zero denominator retained; no cohort shrinking')
    require(all(math.isfinite(v)for v in flat),'finite QA2 ratios')
    point=float(np.median(flat))
    if len(groups)<2:return dict(base,estimate=point,CI95=None,reason='fewer than2 independent source episodes; CI not evaluable')
    ix=[[j for j,e in enumerate(episodes)if e==g]for g in groups];rng=np.random.default_rng(SEED);stats=[]
    for _ in range(draws):
        selected=rng.integers(0,len(groups),len(groups));sample=[v for k in selected for j in ix[k]for v in values[j]];stats.append(float(np.median(sample)))
    lo,hi=np.quantile(stats,[.025,.975]);return dict(base,estimate=point,CI95=[float(lo),float(hi)])


def episode_rate(values,episodes,draws=DRAWS):
    """§245/R-Q 7d1085d97: known-denominator reader mean, whole-episode draws."""
    require(len(values)==len(episodes)and all(e is not None for e in episodes),'original source episode for every QA2 readout')
    result=rate(values);result.pop('Wilson95')
    groups={}
    for e,v in zip(episodes,values):groups.setdefault(e,[]).append(v)
    arrays=[groups[e]for e in sorted(groups,key=str)];stats=[]
    if arrays:
        ix=np.random.default_rng(SEED).integers(0,len(arrays),(draws,len(arrays)))
        for draw in ix:
            known=[v for k in draw for v in arrays[k]if v is not None]
            if known:stats.append(float(np.mean(known)))
    ci=np.quantile(stats,[.025,.975]).tolist()if len(stats)==draws else None
    return dict(result,CI95=ci,n_episodes=len(arrays),defined_draws=len(stats),undefined_draws=draws-len(stats),draws=draws,seed=SEED,bootstrap_unit='original source episode; all its pairs/members stay together')


def classify(reads,patches,informative,reader_interval='Wilson95'):
    def reader_test(stat,minimum,lower=None):
        if reader_interval=='Wilson95':return criterion(stat,minimum,lower)
        if stat['estimate']is None or lower is not None and stat[reader_interval]is None:return None
        return bool(stat['estimate']>=minimum and(lower is None or stat[reader_interval][0]>lower))
    def low(stat):return None if stat['estimate']is None else stat['estimate']<=.15
    controls=all3([low(patches[b][p])for b in BLOCKS for p in PATCHES[1:]])
    later=any3([None if patches[b]['read_token']['estimate']is None or patches[b]['read_token']['CI95']is None else patches[b]['read_token']['estimate']>=.50 and patches[b]['read_token']['CI95'][0]>.25 for b in (52,56)])
    prev44=reader_test(reads['44']['previous'],.30,.20)
    cur44=None if reads['44']['current']['estimate']is None else reads['44']['current']['estimate']<=.40
    cur60=reader_test(reads['60']['current'],.70)
    natural=all3([prev44,cur44,cur60,later,low(patches[44]['read_token']),controls])
    early=patches[44]['read_token']['estimate'];falsifier=any3([reader_test(reads['44']['current'],.70,.55),None if early is None else early>=.50])
    status=lambda x:'NOT EVALUABLE'if x is None else 'MET'if x else 'NOT MET'
    return dict(R_NL1=status(natural)if informative else 'DESCRIPTIVE ONLY',falsifier=status(falsifier)if informative else 'DESCRIPTIVE ONLY',control_medians_all5_at_most015=controls,informative=informative,gate='at least50screened multi-hop pairs',reading='natural staleness replicates with E126 mechanism'if informative and natural is True else 'state formed and readable by44; externally written-state caveat'if informative and falsifier is True else 'fewer than50multi-hop pairs; descriptive only'if not informative else 'between registered readings; report as is')


def analyze(pairs,draws=DRAWS):
    require(len({x['pair_id']for x in pairs})==len(pairs),'unique frozen selected pairs')
    out={};private=[]
    for kind,limit in [('multi_hop',84),('one_hop',42)]+([('babi_qa2',42)]if any(x['kind']=='babi_qa2'for x in pairs)else[]):
        xs=[x for x in pairs if x['kind']==kind];require(len(xs)<=limit,'no expanded screened cohort')
        blocks=(44,52)if kind=='one_hop'else BLOCKS
        require(all(len(x['members'])==2 for x in xs),'both members retained')
        reads={str(l):{name:rate([None if m['readouts'][l]is None else m['readouts'][l][name]for x in xs for m in x['members']])for name in ('current','previous','other','none','dual_current_previous')}for l in READS}
        if kind=='babi_qa2':
            episodes=[x['source_episode_id']for x in xs for m in x['members']]
            reads={str(l):{name:episode_rate([None if m['readouts'][l]is None else m['readouts'][l][name]for x in xs for m in x['members']],episodes,draws)for name in ('current','previous','other','none','dual_current_previous')}for l in READS}
        rs={b:{p:[]for p in PATCHES}for b in blocks}
        for x in xs:
            members=x['members'];require([m['member']for m in members]==[0,1],'matched original member order')
            for b in blocks:
                for patch in PATCHES:
                    vals=[ratio(m['own_logodds'],members[1-j]['own_logodds'],m['patches'][b][patch])for j,m in enumerate(members)]
                    rs[b][patch].append(vals)
                    private.append(dict(pair_id=x['pair_id'],kind=kind,source_episode_id=x.get('source_episode_id'),block=b,control=patch,member_ratios=vals,own_logodds=[m['own_logodds']for m in members],other_logodds=[members[1-j]['own_logodds']for j in (0,1)],patched_logodds=[m['patches'][b][patch]for m in members]))
        patches={b:{p:episode_median(rs[b][p],[x['source_episode_id']for x in xs],draws)if kind=='babi_qa2'else paired_median(rs[b][p],draws)for p in PATCHES}for b in blocks}
        out[kind]=dict(n_pairs=len(xs),n_items=2*len(xs),reader_rates=reads,patches=patches,descriptive=(kind!='multi_hop'))
    if 'babi_qa2'in out:
        z=out['babi_qa2'];z['threshold_pattern_descriptive']=classify(z['reader_rates'],z['patches'],True,reader_interval='CI95');z['threshold_mode']='QA2 descriptive only; whole-episode reader CIs; never pooled or promoted into confirmatory R-NL1'
    primary=out['multi_hop'];verdict=classify(primary['reader_rates'],primary['patches'],primary['n_pairs']>=50)
    return dict(experiment='E133',**verdict,groups=out,bootstrap=dict(draws=draws,seed=SEED,unit='matched source pair; both member ratios travel together',statistic='median of per-prompt ratios, no ratio of medians'),normalization='R=(patched-own)/(other-own) under SAME frozen ordered recipient contrast; zero gap/missing retained undefined',reader_interval='Synthetic E133: unchanged E127 Wilson95 per item; QA2: whole-source-episode bootstrap CI95, known denominator, undefined draws reported; no added threshold',missing_policy='UNPARSEABLE and incomplete numeric cells stay missing/undefined; planned counts retained, no imputation or complete-case filter'),private
