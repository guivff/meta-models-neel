"""Draw Q1's outcome-independent test sample; keep labels and prefixes in cache."""
import argparse
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from projects.g_agreement.understand.e13 import io as I
from projects.g_agreement.blindspot.items import FEATURES
from projects.g_agreement.blindspot.w1b.registry_features import BY_ID

OUT=I.ROOT/'results/g_agreement/understand/q1'
CACHE=I.ROOT/'cache/g_agreement/understand/q1'
BANKS={'w1':I.ROOT/'cache/g_agreement/blindspot/w1-readonly-20261024/w1-bank-v2',
       's84':Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement/blindspot/w1b-bank-v1')}


def quotas(features,tier):
    ordered=sorted(features,key=lambda f:I.rank('q1-row-quota',tier,f))
    q={f:20//len(features)+int(i<20%len(features)) for i,f in enumerate(ordered)}
    odd=sorted([f for f,n in q.items() if n%2],key=lambda f:I.rank('q1-odd-value',tier,f))
    assert len(odd)%2==0
    extra_a=set(odd[:len(odd)//2])
    return {f:{'A':n//2+int(n%2 and f in extra_a),'B':n//2+int(n%2 and f not in extra_a)} for f,n in q.items()}


def freeze():
    tiers={'content':sorted(f for f,s in FEATURES.items() if s.kind=='semantic' and f!='python_effect'),
           'local_form':list(I.read(I.ROOT/'results/g_agreement/understand/e13/QUESTIONS_S84.json'))+['table_role','python_string'],
           'earlier_state':['prose_paren','python_depth','list_index','table_column']}
    if [len(tiers[t]) for t in tiers]!=[9,12,4]:raise ValueError('tier coverage')
    refs={}
    for name,bank in BANKS.items():
        seal=I.read(bank/'INPUT_SEAL.json')
        for n,h in seal['files'].items():
            if I.sha(bank/n)!=h:raise ValueError('bank seal changed')
        manifest=I.read(bank/'manifest.json')
        for n in ['labels.DO_NOT_STAGE.jsonl','items.DO_NOT_STAGE.jsonl']:
            if I.sha(bank/n)!=manifest['files'][n]:raise ValueError('full bank/labels changed')
        refs[name]={'bank':str(bank.resolve()),'files':{n:I.sha(bank/n) for n in ['INPUT_SEAL.json','manifest.json','items.input.jsonl','items.DO_NOT_STAGE.jsonl','labels.DO_NOT_STAGE.jsonl']}}
    metrics=I.read(I.ROOT/'results/g_agreement/blindspot/w1/analysis/metrics.json')
    semantic=sorted(r['feature'] for r in metrics['rows'] if r['reader']=='olens' and r['class']=='semantic' and r['status']=='EVALUABLE')
    if semantic!=tiers['content']:raise ValueError('content rows differ from E16 nine evaluable semantic rows')
    s84=set(I.read(I.ROOT/'results/g_agreement/understand/e13/QUESTIONS_S84.json'))
    specs={}
    for tier,features in tiers.items():
        for f in features:
            if f in s84:
                v=BY_ID[f];specs[f]={'bank':'s84','values':['present','absent'],'descriptions':[v.positive,v.negative]}
            else:
                v=FEATURES[f];specs[f]={'bank':'w1','values':list(v.values),'descriptions':list(v.descriptions)}
    plan={'at':datetime.now(timezone.utc).isoformat(),'registration_commit':'1095e4e9','section':107,'seed':I.SEED,
          'tiers':tiers,'quotas':{t:quotas(fs,t) for t,fs in tiers.items()},'specs':specs,'bank_refs':refs,
          'selection':'Within fixed row/A-B quotas choose lowest sha256 rank(seed,q1-item,tier,feature,arm,item_id); test only, distinct IDs. No reader/probe scores or prior free readouts used.',
          'human_subset':'All60items, one common generation index per item for both readers: minimum hash rank(seed,q1-human-generation,item_id,sample) over0..3.120readouts,40/tier,20/reader/tier,20/truevalue/tier. Freeze IDs now, before readouts.',
          'future_blind_format':'Exactly{id,question,readout}, opaque IDs and independent seeded order. Question includes exact text up to read token plus property A/B definitions, as Q1 requires text for hallucination/extra coding. No reader names, tier, truth, source ID/path, generation index, scores or key in coder files.',
          'required_free_grid':'60items x2readers(Oracle44/NLA42) x4generations(greedy0+three temperature0.7 samples1..3)=480; fresh E16 FREE_SEAL required, fullgrid and sourceinput binding verified before export. No replacement/resampling if incomplete.',
          'sample_code_sha256':I.sha(Path(__file__))}
    I.save(OUT/'SAMPLING_PLAN.json',plan)
    (OUT/'SCOPE.md').write_text('# §107 Q1 sampling implementation\n\nDated '+plan['at']+', before drawing any Q1 item. Implements1095e4e9 with seed20261024:60distinct test items,20per tier,10A/10B per tier. Content uses §106 nine evaluable W1 semantic rows (python_effect is NOT DECODABLE and excluded there). Local form uses all10§84rows plus W1 table_role/python_string. Earlier state uses the four listed W1 rows.\n\nRow quotas differ by at most1within each tier, every eligible row is covered. A/B quotas are as balanced within each row as its odd/even quota permits; seeded allocation balances odd extras across the tier. IDs are seeded-hash selected within row/value, with no selection on reader/probe scores, prior free outputs or coding. Original sealed bank/manifest hashes bind prefixes, IDs and truths. Keys and exact text stay in cache; public E16 request contains only bank/feature/item IDs and generation requirements, no labels.\n\nFreeze the later120human-readout subset now: one common generation index0..3peritem, bothreaders, all60items. This is an exact subset of the later480blind records, seed-shuffled independently; preserve opaque IDs for agreement. Both coding files use exactly{id,question,readout}. The question field includes the visible text prefix and both A/B alternatives, as Q1 requires, never the true alternative or reader identity. No coder file can be built until E16 seals the complete480readout grid. No old E13 outputs substituted. API$0/GPU0h for sampling; no model or pod operations.\n')
    print('Q1 sampling method frozen')


def draw():
    plan=I.read(OUT/'SAMPLING_PLAN.json')
    if I.sha(Path(__file__))!=plan['sample_code_sha256']:raise ValueError('sampling code changed')
    banks={}
    for name,ref in plan['bank_refs'].items():
        bank=Path(ref['bank'])
        if any(I.sha(bank/n)!=h for n,h in ref['files'].items()):raise ValueError('source changed')
        banks[name]={r['id']:r for r in I.rows(bank/'items.DO_NOT_STAGE.jsonl')}
    chosen=[]
    for tier,features in plan['tiers'].items():
        for f in features:
            spec=plan['specs'][f]
            for arm,value in zip(['A','B'],spec['values']):
                candidates=[r for r in banks[spec['bank']].values() if r['feature']==f and r['split']=='test' and r['value']==value]
                n=plan['quotas'][tier][f][arm]
                candidates.sort(key=lambda r:I.rank('q1-item',tier,f,arm,r['id']))
                if len(candidates)<n:raise ValueError('insufficient frozen stratum')
                for r in candidates[:n]:
                    chosen.append({'id':r['id'],'bank':spec['bank'],'feature':f,'tier':tier,'value':value,'truth_AB':arm,
                                   'human_generation':min(range(4),key=lambda s:I.rank('q1-human-generation',r['id'],s)),
                                   'text':r['text'],'ids':r['ids'],'question':'Read the text up to the read position:\n\n'+r['text']+'\n\nDoes the readout explicitly state the property at that position? A = '+spec['descriptions'][0]+'; B = '+spec['descriptions'][1]+'.',
                                   'cluster':r['cluster']})
    if len(chosen)!=60 or len({r['id'] for r in chosen})!=60:raise ValueError('sample size/unique IDs')
    if Counter((r['tier'],r['truth_AB']) for r in chosen)!={(t,a):10 for t in plan['tiers'] for a in ['A','B']}:raise ValueError('tier/value balance')
    CACHE.mkdir(parents=True,exist_ok=True)
    key=CACHE/'ITEM_KEY.DO_NOT_SHARE.jsonl';I.jsonl(key,chosen)
    request={'section':107,'source_registration':'1095e4e9','seed':I.SEED,'items':[{'bank':r['bank'],'feature':r['feature'],'id':r['id']} for r in chosen],
             'free_generations':{'0':'greedy','1':'temperature0.7','2':'temperature0.7','3':'temperature0.7'},'readers':{'olens':44,'nla':42},
             'expected_records':480,'no_labels_in_this_request':True,'input_bank_seal_hashes':{b:r['files']['INPUT_SEAL.json'] for b,r in plan['bank_refs'].items()},
             'return_schema':'id,reader(olens/nla),layer,sample(0..3),raw; FREE_SEAL must bind raw+provenance and sampled item request. Do not send keys/truth to any coder.'}
    I.save(OUT/'E16_ITEM_REQUEST.json',request)
    I.save(OUT/'SAMPLE_RECEIPT.json',dict(status='SIXTY_ITEMS_FROZEN_AWAITING_E16_FREE_SEAL',at=datetime.now(timezone.utc).isoformat(),seed=I.SEED,
             n_items=60,per_tier={t:20 for t in plan['tiers']},per_tier_AB={t:{'A':10,'B':10} for t in plan['tiers']},
             row_counts=dict(Counter(r['feature'] for r in chosen)),item_request_sha256=I.sha(OUT/'E16_ITEM_REQUEST.json'),
             key_cache_only=str(key),key_sha256=I.sha(key),sampling_plan_sha256=I.sha(OUT/'SAMPLING_PLAN.json'),api_calls=0,gpu_hours=0))
    print('60items frozen:20/tier,10A/10B; cache-only key; E16 item IDs ready')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','draw']);a=p.parse_args();{'freeze':freeze,'draw':draw}[a.action]()
