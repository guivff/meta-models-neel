"""One application of section107 b51c7915 after coding tables are sealed."""
import argparse
import bisect
import hashlib
import math
from pathlib import Path
from projects.g_agreement.understand.e13 import io as I
from .run import OUT,CACHE,NOW

SOURCES={'w1':CACHE.parent/'blindspot/w1-readonly-20261024/w1-assembled',
         's84':Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement/blindspot/w1b-units/ybqkwg5zoc3vwg/w1b-out')}
GAL=CACHE/'q_analysis/gallery'


def tie(item):return hashlib.sha256((str(I.SEED)+item).encode()).hexdigest()

def percentile(sorted_values,value):
    return (bisect.bisect_left(sorted_values,value)+bisect.bisect_right(sorted_values,value))/(2*len(sorted_values))

def choose(rows):
    rank=sorted(rows,key=lambda r:(-abs(r['d']),tie(r['item'])))
    if len(rank)!=20:raise ValueError('tier is not original20items')
    return [dict(rank[0],selection='largest_abs_d'),dict(rank[1],selection='second_largest_abs_d'),
            dict(min(rank[2:],key=lambda r:tie(r['item'])),selection='seeded_random_from_remaining18')]


def freeze():
    # No scores ranked or selection made by this preflight.
    qplan=I.read(I.ROOT/'results/g_agreement/understand/q1/SAMPLING_PLAN.json');refs=[]
    for bank,root in SOURCES.items():
        for role in ['target','nla']:
            base=root/role;seal=I.read(base/'SCORE_SEAL.json')
            for n,h in seal['files'].items():
                if Path(n).is_absolute() or '..' in Path(n).parts or I.sha(base/n)!=h:raise ValueError('asked score seal mismatch')
            provenance=I.read(base/('provenance.target.json' if role=='target' else 'provenance.nla.json'))
            if provenance['input_seal_sha256']!=qplan['bank_refs'][bank]['files']['INPUT_SEAL.json']:raise ValueError('wrong asked bank')
            refs.append({'bank':bank,'role':role,'directory':str(base),'seal_sha256':I.sha(base/'SCORE_SEAL.json'),'scores_sha256':seal['files']['scores.target.jsonl' if role=='target' else 'scores.nla.jsonl']})
    plan={'at':NOW(),'registration_amendment':'b51c7915','coding_table_seal_sha256':I.sha(OUT/'RATER1_TABLE_SEAL.json'),
          'source_refs':refs,'percentile_convention':'Empirical midrank (number less +0.5 number equal)/n, within full original row/test/native reader; signed mean paired log-odds. All ties treated identically. Percentiles in[0,1].',
          'signed_score':'mean original frozen phrasing-pair logodds if trueA, negative mean if trueB. No probe term.',
          'difference':'pctNLA-pctOracle','candidate_pool':'original frozen60Q1items only,20/tier',
          'selection':'two greatestabs(d) pertier; tie sha256(UTF8(str(20261024)+item_id)); then smallest samehash among remaining18. No coding/readout content in ranking.',
          'gallery_render':'All4original generations for both readers, no generation curation; original sourceprefix/truevalue and fixed coder annotations. Full unblinded artifacts in cache, publicselection+hashes.',
          'code_sha256':I.sha(Path(__file__))}
    I.save(OUT/'GALLERY_PLAN.json',plan)
    print('Gallery plan/source seals fixed; no score ranked')


def rank_once():
    plan=I.read(OUT/'GALLERY_PLAN.json')
    if I.sha(Path(__file__))!=plan['code_sha256'] or I.sha(OUT/'RATER1_TABLE_SEAL.json')!=plan['coding_table_seal_sha256']:raise ValueError('gallery code or tables changed')
    qp=I.read(I.ROOT/'results/g_agreement/understand/q1/SAMPLING_PLAN.json');receipt=I.read(I.ROOT/'results/g_agreement/understand/q1/SAMPLE_RECEIPT.json')
    kp=Path(receipt['key_cache_only'])
    if I.sha(kp)!=receipt['key_sha256']:raise ValueError('item key changed')
    selected_items=I.rows(kp);asked={};population={}
    for ref in plan['source_refs']:
        bank=ref['bank'];role=ref['role'];reader='oracle' if role=='target' else 'nla';native=44 if role=='target' else 42
        base=Path(ref['directory']);filename='scores.target.jsonl' if role=='target' else 'scores.nla.jsonl'
        if I.sha(base/'SCORE_SEAL.json')!=ref['seal_sha256'] or I.sha(base/filename)!=ref['scores_sha256']:raise ValueError('asked scores changed')
        bankpath=Path(qp['bank_refs'][bank]['bank']);labels={r['id']:r for r in I.rows(bankpath/'labels.DO_NOT_STAGE.jsonl')};mf=I.read(bankpath/'manifest.json')
        if I.sha(bankpath/'labels.DO_NOT_STAGE.jsonl')!=qp['bank_refs'][bank]['files']['labels.DO_NOT_STAGE.jsonl']:raise ValueError('labels changed')
        scores={}
        for r in I.rows(base/filename):
            if r['reader']!=('olens' if reader=='oracle' else 'nla') or r['arm']!='true' or r['layer']!=native:continue
            lab=labels[r['id']]
            if lab['split']!='test':continue
            f=lab['feature'];values=mf['rows'][f]['values']
            if r['status']!='COMPLETE' or r['score_kind']!='summed_sequence_logodds' or len(r['scores'])!=2 or any(not math.isfinite(x) for x in r['scores']):raise ValueError('incomplete/nonpaired native asked scores')
            if r['id'] in scores:raise ValueError('duplicate asked ID')
            mean=math.fsum(r['scores'])/len(r['scores']);signed=mean if lab['value']==values[0] else -mean
            scores[r['id']]={'mean':mean,'signed':signed,'feature':f,'true_AB':'A' if lab['value']==values[0] else 'B'}
        expected={r['id'] for r in labels.values() if r['split']=='test'}
        if set(scores)!=expected:raise ValueError('full row/test population missing')
        for f in {r['feature'] for r in scores.values()}:
            population[bank,reader,f]=sorted(r['signed'] for r in scores.values() if r['feature']==f)
        asked[bank,reader]=scores
    candidates=[]
    for item in selected_items:
        bank=item['bank'];f=item['feature'];entry={'item':item['id'],'feature':f,'tier':item['tier'],'bank':bank,'readers':{}}
        for reader in ['oracle','nla']:
            s=asked[bank,reader][item['id']]
            if s['true_AB']!=item['truth_AB']:raise ValueError('question truth ordering differs')
            pop=population[bank,reader,f];entry['readers'][reader]={**s,'percentile':percentile(pop,s['signed']),'population_n':len(pop)}
        entry['d']=entry['readers']['nla']['percentile']-entry['readers']['oracle']['percentile'];candidates.append(entry)
    picked=[]
    for tier in qp['tiers']:picked+=choose([r for r in candidates if r['tier']==tier])
    GAL.mkdir(parents=True,exist_ok=False)
    I.save(GAL/'ALL60_RANKING.json',{'candidates':candidates,'plan_sha256':I.sha(OUT/'GALLERY_PLAN.json')})
    I.save(OUT/'GALLERY_SELECTION.json',{'at':NOW(),'amendment':'b51c7915','selected':picked,'all60_cache_path':str(GAL/'ALL60_RANKING.json'),'all60_sha256':I.sha(GAL/'ALL60_RANKING.json')})
    # Selection is persisted before any gallery readout is opened.
    qr=I.read(I.ROOT/'results/g_agreement/understand/q1/BLIND_SAMPLE_RECEIPT.json')
    blind={r['id']:r for r in I.rows(Path(qr['sample']))};keys=I.rows(Path(qr['key_cache_only']));itemkeys={r['id']:r for r in selected_items}
    ac={r['id']:r for r in I.rows(CACHE/'claude_codes_q/q1_passA.CLAUDE_CODES.jsonl')};bc={r['id']:r for r in I.rows(CACHE/'claude_codes_q/q1_passB.CLAUDE_CODES.jsonl')}
    examples=[]
    for pick in picked:
        item=itemkeys[pick['item']];readouts=[]
        for key in sorted([r for r in keys if r['item']==pick['item']],key=lambda r:(r['reader'],r['sample'])):
            readouts.append({'reader':key['reader'],'layer':key['layer'],'sample':key['sample'],'raw':blind[key['id']]['readout'],'passA':ac[key['id']],'passB':bc[key['id']]})
        if len(readouts)!=8:raise ValueError('gallery needs all8readouts')
        examples.append({**pick,'true_value':item['value'],'truth_AB':item['truth_AB'],'source_prefix':item['text'],'readouts':readouts})
    I.save(GAL/'GALLERY.json',{'status':'UNBLINDED_DESCRIPTIVE_GALLERY_NOT_FOR_CODERS','selection_plan':plan,'examples':examples})
    lines=['# Q1 frozen gallery: three items per tier','','UNBLINDED DESCRIPTIVE GALLERY. Exact b51c7915 asked-score percentile rule, no probe term. Two greatest absolute reader-percentile differences plus one seeded random item from the rest. All four original generations from each reader retained. No human notes or unblinded pass was added. Coder annotations remain unchanged in GALLERY.json.']
    for i,r in enumerate(examples,1):
        lines+=['',f"## {i}. {r['tier']} / {r['feature']} — {r['selection']}",'',f"Item `{r['item']}`; true **{r['truth_AB']} = {r['true_value']}**. Oracle percentile {r['readers']['oracle']['percentile']:.6f}; NLA percentile {r['readers']['nla']['percentile']:.6f}; d={r['d']:.6f}.",'','Source prefix (verbatim):','']
        lines+=['    '+s if s else '' for s in r['source_prefix'].split('\n')]
        for rd in r['readouts']:
            a,b=rd['passA'],rd['passB'];lines+=['',f"### {rd['reader']} L{rd['layer']}, generation {rd['sample']}",'',f"Rater1: mode={a['mode']}; mentions={a['mentions']} ({a['mention_kind']}), value={a['value']}; enacts={a['enacts']}, enact_value={a['enact_value']}; hallucination={b['hallucination']}; extra={bool(b['extra'].strip())}.",'','Readout (verbatim):','']
            lines+=['    '+s if s else '' for s in rd['raw'].split('\n')]
    (GAL/'GALLERY.md').write_text('\n'.join(lines)+'\n')
    I.save(OUT/'GALLERY_RECEIPT.json',{'status':'NINE_ITEMS_SELECTED_ONCE_AFTER_CODING_TABLES','n_items':9,'n_readouts':72,'files':{str(GAL/n):I.sha(GAL/n) for n in ['GALLERY.json','GALLERY.md','ALL60_RANKING.json']},'selection_sha256':I.sha(OUT/'GALLERY_SELECTION.json'),'plan_sha256':I.sha(OUT/'GALLERY_PLAN.json'),'api_calls':0,'gpu_hours':0})
    print('Gallery selected once:9items,72verbatimreadouts')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','rank']);a=p.parse_args();{'freeze':freeze,'rank':rank_once}[a.action]()
