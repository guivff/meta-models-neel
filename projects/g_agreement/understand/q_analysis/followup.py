"""cf19c2e8 descriptive follow-ups; original coding and gallery remain unchanged."""
from pathlib import Path
from collections import defaultdict
import argparse
import json
import numpy as np
from .run import I,OUT,CACHE,CODES,NOW,summarize

REG='cf19c2e8'
SEED=20261024
B=2000


def verify_originals():
    for name,h in I.read(OUT/'ANALYSIS_SEAL.json')['files'].items():
        if I.sha(OUT/name)!=h:raise ValueError('original aggregate seal changed')
    pre=I.read(OUT/'PREJOIN_VERIFICATION.json')
    if I.sha(CODES/'CLAUDE_CODES_SEAL.json')!=pre['seal_sha256']:raise ValueError('rater1 seal changed')
    for name,ref in pre['samples'].items():
        if I.sha(CODES/f'{name}.CLAUDE_CODES.jsonl')!=ref['codes_sha256']:raise ValueError('sealed codes changed')
    for path,h in I.read(OUT/'GALLERY_RECEIPT.json')['files'].items():
        if I.sha(Path(path))!=h:raise ValueError('sealed gallery/ranking changed')
    return pre


def joined():
    verify_originals()
    rec1=I.read(I.ROOT/'results/g_agreement/understand/q1/BLIND_SAMPLE_RECEIPT.json')
    rec2=I.read(I.ROOT/'results/g_agreement/understand/q2/SAMPLES_RECEIPT.json')
    tiermap={f:t for t,fs in I.read(I.ROOT/'results/g_agreement/understand/q1/SAMPLING_PLAN.json')['tiers'].items() for f in fs}
    output=[]
    for sample in ['q1','q2a','q2b','q2c']:
        rec=rec1 if sample=='q1' else rec2[sample];path=Path(rec['key_cache_only'])
        if I.sha(path)!=rec['key_sha256']:raise ValueError('key changed')
        keys={r['id']:r for r in I.rows(path)}
        codes=I.rows(CODES/f"{'q1_passA' if sample=='q1' else sample}.CLAUDE_CODES.jsonl")
        extra={r['id']:r for r in I.rows(CODES/'q1_passB.CLAUDE_CODES.jsonl')} if sample=='q1' else {}
        if set(keys)!={r['id'] for r in codes}:raise ValueError('key/code coverage')
        for c in codes:
            k=keys[c['id']]
            truth=k['truth_AB'] if sample!='q2b' else ('B' if k['dose']==0 else None)
            tier=k['tier'] if sample=='q1' else 'content' if sample=='q2a' else tiermap.get(k['feature'],'unassigned_by_Q1')
            output.append({**k,**c,**extra.get(c['id'],{}),'sample':sample,'generation':k.get('sample'),'source_value':k.get('value'),'truth':truth,'tier':tier})
    return output


def leaves(obj,prefix=''):
    out={}
    if isinstance(obj,dict):
        if set(obj)=={'k','n','rate','ci95'}:out[prefix]=obj
        else:
            for k,v in obj.items():out.update(leaves(v,f'{prefix}.{k}' if prefix else k))
    return out


def at_path(obj,path):
    for k in path.split('.'):
        if obj is None:return {'k':0,'n':0}
        obj=obj[k]
    return obj if obj is not None else {'k':0,'n':0}


def bootstrap_group(rows):
    ids=sorted({r['item'] for r in rows});n=len(ids)
    item_rows={i:[r for r in rows if r['item']==i] for i in ids}
    stats=summarize(rows);points=leaves(stats)
    item_stats={i:summarize(item_rows[i]) for i in ids}
    draws=np.random.default_rng(SEED).integers(0,n,size=(B,n))
    out={}
    for path,point in points.items():
        kn=np.asarray([[at_path(item_stats[i],path)[v] for v in ['k','n']] for i in ids],dtype=float)
        # Ratio of pooled counts, not the mean of item-specific conditional accuracies.
        sampled=kn[draws].sum(axis=1);valid=sampled[:,1]>0
        vals=sampled[valid,0]/sampled[valid,1]
        out[path]={**point,'cluster_ci95':np.quantile(vals,[.025,.975]).tolist() if len(vals) else None,
                   'bootstrap_valid':int(valid.sum()),'bootstrap_undefined':int((~valid).sum())}
    return {'n_items':n,'n_records':len(rows),'generations_or_outputs_per_item':dict(sorted((str(k),v) for k,v in __import__('collections').Counter(len(v) for v in item_rows.values()).items())),
            'rates':out}


def freeze():
    verify_originals()
    plan={'at':NOW(),'registration':REG,'status':'DESCRIPTIVE_REGISTERED_AFTER_RATER1_TABLES_WERE_SEEN','bootstrap_replicates':B,'seed':SEED,
          'bootstrap':'Resample sorted item IDs with replacement within each sample/tier/reader, retain every observed output of each drawn item (all4generations inQ1, selected doses together inQ2b). Same default_rng(seed) item-index draws for every rate within a group; restart seed per group. Ratio of pooled numerator/denominator counts. Equal-tailed percentile95%. Undefined denominator draws omitted from quantiles and counted; zero defined draws→unavailable.',
          'rate_scope':'All rate leaves of the original tier-reader summaries, including mode, mention kinds, conditional accuracies, enactment, Q1hallucination/extra and applicableQ2extras. Original Wilson intervals/points retained.',
          'mention_kind_accuracy':'quotes_token/states_property separately; correct/allkind mentions includes unclear as unresolved; correct/resolved usesA/B only. Both Wilson and cluster95%.',
          'asked_free_rule':'Q1only, original sealed gallery ALL60_RANKING percentiles. Asked high=pct>=0.5. Oracle free success=3or4of4enacts with correct codedA/B; NLA=3or4of4mentions with correct codedA/B. Nonmention/nonenact/unclear count as not correct; 2of4 is not a majority (tie reported separately). All20items/tier/reader; list IDs for both discordance directions. High percentile is not itself an asked-answer correctness claim.',
          'codes_unchanged':True,'no_new_coding_calls':True,'rater2_policy':'Require code/input hash seal before per-fieldkappa; do not use unsealed JSONLs. Do not wait.',
          'q2d_policy':'No finished sample/codes currently in sharedcache; NOTDONECURRENTLY. DeadlineSunday2026-10-25T23:59:00+01:00(CET), no automatic wakeup/codingcall/API/GPU. Report any delivered completed artifact separately.',
          'code_sha256':I.sha(Path(__file__)),'original_analysis_seal_sha256':I.sha(OUT/'ANALYSIS_SEAL.json'),'ranking_sha256':I.sha(CACHE/'q_analysis/gallery/ALL60_RANKING.json')}
    I.save(OUT/'FOLLOWUP_PLAN.json',plan)
    print('Post-table descriptive follow-up conventions recorded; no follow-up rates computed')


def run():
    plan=I.read(OUT/'FOLLOWUP_PLAN.json')
    if I.sha(Path(__file__))!=plan['code_sha256']:raise ValueError('follow-up code changed')
    rows=joined();old=I.read(OUT/'RATER1_METRICS.json')
    groups=defaultdict(list)
    for r in rows:groups[r['sample'],r['tier'],r['reader'],r['layer']].append(r)
    cluster=[];kind=[]
    for key,rs in sorted(groups.items()):
        sample,tier,reader,layer=key;cell=bootstrap_group(rs)
        oldcell=next(r for r in old['tables']['by_tier_reader'] if (r['sample'],r['tier'],r['reader'],r['layer'])==key)
        for path,point in leaves(oldcell).items():
            actual=cell['rates'][path]
            if (point['k'],point['n'])!=(actual['k'],actual['n']):raise ValueError('original point/denominator changed')
        label=dict(zip(['sample','tier','reader','layer'],key));cluster.append({**label,**cell})
        for mention_kind in ['quotes_token','states_property']:
            prefix=f'mention_kind.{mention_kind}.accuracy'
            kind.append({**label,'mention_kind':mention_kind,
                         'mentions':cell['rates'][f'{prefix}.rate'],
                         'correct_all':cell['rates'][f'{prefix}.accuracy'],
                         'correct_resolved':cell['rates'][f'{prefix}.resolved_accuracy'],
                         'unresolved':summarize([r for r in rs if r['mention_kind']==mention_kind])['mentions']['unresolved']})
    rank=I.read(CACHE/'q_analysis/gallery/ALL60_RANKING.json')['candidates'];asked={r['item']:r for r in rank}
    q1=defaultdict(list)
    for r in rows:
        if r['sample']=='q1':q1[r['tier'],r['reader'],r['item']].append(r)
    items=[]
    for (tier,reader,item),rs in sorted(q1.items()):
        if len(rs)!=4 or {r['generation'] for r in rs}!={0,1,2,3}:raise ValueError('Q1 generations not intact')
        flag,value=('enacts','enact_value') if reader=='oracle' else ('mentions','value')
        correct=sum(r[flag] and r[value]==r['truth'] for r in rs)
        pct=asked[item]['readers'][reader]['percentile'];high=pct>=.5;success=correct>=3
        items.append({'tier':tier,'reader':reader,'item':item,'feature':rs[0]['feature'],'asked_percentile':pct,'asked_high':high,'free_correct_generations':correct,
                      'free_majority_correct':success,'two_of_four_tie':correct==2,'discordant':high!=success})
    cross=[]
    for tier,reader in sorted({(r['tier'],r['reader']) for r in items}):
        subset=[r for r in items if (r['tier'],r['reader'])==(tier,reader)]
        counts={}
        for high in [False,True]:
            for success in [False,True]:counts[f'asked_{"high" if high else "low"}__free_{"majority" if success else "no_majority"}']=sum(r['asked_high']==high and r['free_majority_correct']==success for r in subset)
        if len(subset)!=20 or sum(counts.values())!=20:raise ValueError('item cross-tab coverage')
        cross.append({'tier':tier,'reader':reader,'n_items':20,'counts':counts,'two_of_four_ties':sum(r['two_of_four_tie'] for r in subset),
                      'asked_high_no_free_majority_ids':[r['item'] for r in subset if r['asked_high'] and not r['free_majority_correct']],
                      'asked_low_free_majority_ids':[r['item'] for r in subset if not r['asked_high'] and r['free_majority_correct']]})
    r2=[p.name for p in (CACHE/'codex_codes').iterdir() if p.is_file() and not p.name.startswith('._')]
    data={'at':NOW(),'status':'DESCRIPTIVE_POST_TABLE_FOLLOWUPS_COMPLETE','registration':REG,'methods':plan,'cluster_rates':cluster,'mention_kind_accuracy':kind,
          'asked_free_cross_tabs':cross,'asked_free_per_item':items,'rater2':{'files_present':r2,'status':'UNSEALED_FILES_PRESENT_KAPPA_PENDING','kappa':None},
          'q2d':{'status':'NOT_DONE_CURRENTLY_NO_FINISHED_SAMPLE_OR_CODES','deadline':'2026-10-25T23:59:00+01:00','deadline_timezone':'CET','new_coding_calls':0},'api_calls':0,'gpu_hours':0}
    I.save(OUT/'FOLLOWUP.json',data)
    fmt=lambda p:'UNAVAILABLE' if p is None else '['+', '.join(f'{max(0,min(1,x)):.3f}' for x in p)+']'
    primary=['mode.continues','mode.describes','mode.mixed','mentions.rate','mention_kind.quotes_token.rate','mention_kind.states_property.rate','mentions.accuracy','mentions.resolved_accuracy','enacts.rate','enacts.accuracy','enacts.resolved_accuracy','hallucination','extra','structure_named','enacts.source_B_agreement','enacts.target_A_alignment','enacts.resolved_target_A_alignment','structure_tokens']
    lines=['# §107 Q1/Q2 descriptive follow-ups','','**Registered after the rater-1 tables were seen**, cf19c2e8. No verdict changes, new coding calls, API or GPU. Existing codes/asked-score percentiles and original seals unchanged.','','## 1. Item-cluster bootstrap intervals','','2000resamples, seed20261024. Items resampled within sample/tier/reader; all4Q1 generations or all observed Q2b doses stay together. Ratios pool counts across drawn items. Wilson intervals retained for comparison; these bootstrap percentile intervals are not necessarily wider. A zero-observed event can have bootstrap[0,0], which is not proof its population probability is zero. Conditional-accuracy draws with no eligible mentions/enacts are undefined; the table counts them.','','| Sample / tier / reader | Rate | k/n | Wilson95 | Item-cluster95 | Defined draws/2000 | Items |','|---|---|---:|---|---|---:|---:|']
    for g in cluster:
        for path in primary:
            if path not in g['rates']:continue
            r=g['rates'][path]
            lines.append(f"| {g['sample']} / {g['tier']} / {g['reader']} L{g['layer']} | {path} | {r['k']}/{r['n']} | {fmt(r['ci95'])} | {fmt(r['cluster_ci95'])} | {r['bootstrap_valid']} | {g['n_items']} |")
    lines+=['','All additional rate leaves (composition, known-truth and subtype denominators) are in FOLLOWUP.json. Q2b nonzero edited-state accuracy remains unavailable; source agreement/target alignment are separate references.','','## 2. Mention accuracy by kind','','Correct/all keeps unclear in the denominator as unresolved. Correct/resolved includes only codedA/B. No code reassignment between quoting a token and stating a property.','','| Sample / tier / reader | Kind | Correct/all; Wilson95; cluster95 | Correct/resolved; Wilson95; cluster95 | Unclear |','|---|---|---|---|---:|']
    for r in kind:
        def cell(x):return f"{x['k']}/{x['n']}; {fmt(x['ci95'])}; {fmt(x['cluster_ci95'])}"
        lines.append(f"| {r['sample']} / {r['tier']} / {r['reader']} | {r['mention_kind']} | {cell(r['correct_all'])} | {cell(r['correct_resolved'])} | {r['unresolved']} |")
    lines+=['','## 3. Asked percentile versus majority-correct free output','','Q1 only. Asked high means signed-score percentile≥0.5 within the original row/test/native-reader population. Oracle free success = at least3of4correct enactments; NLA = at least3of4correct mentions. Unclear/absent codes are not correct;2of4is a tie and not a majority. High percentile is a relative signed score, not itself an asked-answer correctness classification. Counts cover all20items per tier/reader.','','| Tier / reader | Asked low: no majority | Asked low: majority | Asked high: no majority | Asked high: majority | 2/4ties |','|---|---:|---:|---:|---:|---:|']
    for r in cross:
        c=r['counts'];lines.append(f"| {r['tier']} / {r['reader']} | {c['asked_low__free_no_majority']} | {c['asked_low__free_majority']} | {c['asked_high__free_no_majority']} | {c['asked_high__free_majority']} | {r['two_of_four_ties']} |")
    for r in cross:
        lines+=['',f"### {r['tier']} / {r['reader']}: discordant item IDs",'', 'Asked high, no free majority: '+(', '.join('`'+v+'`' for v in r['asked_high_no_free_majority_ids']) or 'none')+'.','', 'Asked low, free majority: '+(', '.join('`'+v+'`' for v in r['asked_low_free_majority_ids']) or 'none')+'.']
    lines+=['','## Pending inputs','','Rater2 JSONLs exist, but no code/input-hash seal is present: κ is pending; unsealed codes are not used. Q2d is NOT DONE CURRENTLY: no finished sample/codes are present in sharedcache. DeadlineSunday25October2026,23:59CET; this is not a claim the deadline has elapsed. No API/GPU/coding calls or recurring checks were started.']
    (OUT/'FOLLOWUP.md').write_text('\n'.join(lines)+'\n')
    I.save(OUT/'FOLLOWUP_SEAL.json',{'files':{n:I.sha(OUT/n) for n in ['FOLLOWUP.json','FOLLOWUP.md','FOLLOWUP_PLAN.json']}})
    print('Cluster intervals, mention-kind accuracy and120item cross-tab records written')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','run']);a=p.parse_args();{'freeze':freeze,'run':run}[a.action]()
