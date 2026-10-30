"""Verify blind coding inputs before any private-key access; aggregate fixed codes."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from collections import Counter
import argparse
from projects.g_agreement.understand.e13 import io as I
from projects.g_agreement.understand.e13.analyse import rate

OUT=I.ROOT/'results/g_agreement/understand/q_analysis'
CACHE=I.ROOT/'cache/g_agreement/understand'
CODES=CACHE/'claude_codes_q'
SAMPLES={'q1_passA':CACHE/'q1/pass_a.jsonl','q1_passB':CACHE/'q1/pass_b.jsonl',**{n:CACHE/'q2'/n/'blind_sample.jsonl' for n in ['q2a','q2b','q2c']}}
NOW=lambda:datetime.now(ZoneInfo('Europe/Zurich')).isoformat()


def verify():
    seal=I.read(CODES/'CLAUDE_CODES_SEAL.json')
    if seal['status']!='CODES_SEALED_BEFORE_KEY_JOIN':raise ValueError('codes not sealed')
    result={}
    for name,path in SAMPLES.items():
        cp=CODES/f'{name}.CLAUDE_CODES.jsonl';meta=seal['samples'][name]
        if I.sha(cp)!=meta['sha256'] or I.sha(path)!=meta['input_sha256']:raise ValueError('input/code hash mismatch')
        codes=I.rows(cp);inputs={r['id']:r for r in I.rows(path)}
        if len(codes)!=meta['n'] or len({r['id'] for r in codes})!=len(codes) or {r['id'] for r in codes}!=set(inputs):raise ValueError('code coverage')
        quotes=Counter()
        for r in codes:
            raw=inputs[r['id']]['readout']
            if name=='q1_passB':
                if type(r['hallucination']) is not bool or any(not isinstance(r[k],str) for k in ['hallucination_quote','extra','extra_quote']):raise ValueError('pass B types')
                for flag,q in [('hallucination','hallucination_quote'),('extra','extra_quote')]:
                    if r[flag]:quotes['required_quotes']+=1;quotes['evidence_failures']+=int(not r[q] or r[q] not in raw)
            else:
                if r['mode'] not in ['continues','describes','mixed'] or type(r['mentions']) is not bool or type(r['enacts']) is not bool:raise ValueError('code schema')
                if r['mention_kind'] not in (['quotes_token','states_property'] if r['mentions'] else [None]) or r['value'] not in (['A','B','unclear'] if r['mentions'] else [None]) or r['enact_value'] not in (['A','B','unclear'] if r['enacts'] else [None]):raise ValueError('inconsistent code')
                if r['mentions'] or r['enacts']:quotes['required_quotes']+=1;quotes['evidence_failures']+=int(not r['evidence'] or r['evidence'] not in raw)
                if name=='q2b' and type(r['structure_named']) is not bool:raise ValueError('Q2b extra field')
                if name=='q2c':
                    if not isinstance(r['structure_tokens'],list) or any(not isinstance(v,str) for v in r['structure_tokens']):raise ValueError('structure schema')
                    quotes['nonverbatim_structure_tokens']+=sum(v not in raw for v in r['structure_tokens'])
        result[name]={'n':len(codes),'codes_sha256':I.sha(cp),'input_sha256':I.sha(path),'quote_checks':dict(quotes)}
    original={r['id']:r for r in I.rows(CACHE/'q1/blind_sample.jsonl')}
    for name in ['q1_passA','q1_passB']:
        for r in I.rows(SAMPLES[name]):
            old=original[r['id']]
            if r['readout']!=old['readout']:raise ValueError('Q1 raw changed')
            if name=='q1_passA' and r['question']!=old['question'].split('\n\n')[-1]:raise ValueError('Q1 pass A contains a different question/context')
            if name=='q1_passB' and old['question'] not in r['text_and_question']:raise ValueError('Q1 pass B context changed')
    I.save(OUT/'PREJOIN_VERIFICATION.json',dict(at=NOW(),status='HASHES_AND_SCHEMA_VERIFIED_BEFORE_PRIVATE_KEY_JOIN',seal_sha256=I.sha(CODES/'CLAUDE_CODES_SEAL.json'),seal=seal,samples=result,
        rater2_files_present=[str(p) for p in (CACHE/'codex_codes').glob('*') if p.is_file()]))
    (OUT/'JOIN_NOTE.md').write_text('''# §107 Q studies: descriptive rater-1 join

Dated '''+NOW()+''', after code sealing/verification and before this local key join. All four producer coding notes are preserved in PREJOIN_VERIFICATION.json. Q1 pass A has only the property question and supplies mode/mention/enact codes; pass B sees the source prefix and supplies hallucination/extra. No pass-B data are used to revise pass-A codes. Some structural cues were scripted; Q2c wrapper tokens were removed by the producer's truth-blind merge rule; pass-B extra strictness varies by chunk. These are coding limitations, not exclusions. Keep every sealed code unchanged.

Report per sample, tier/native reader and row as applicable. Mention-kind rates use all readouts as denominator; also provide composition among mentions. Accuracy primary = correct A/B / all coded mentions (unclear unresolved in denominator); resolved A/B accuracy also reported. Same convention for enactments. Every binary/category proportion has Wilson95 CIs; zero denominators unavailable. Q1 four generations/item and W6 repeated doses are correlated, so record-level Wilson intervals are descriptive, not cluster-adjusted tests. Q2c any nonempty normalized structure_tokens list is a structure-token event; no new token filtering.

Q2b dose0 has source truth B. Nonzero editing has no independent state truth: accuracy is unavailable there. Source-B agreement and target-A alignment are separate named references, never relabelled as accuracy. Q1-defined tiers apply by explicit row membership; semantic Q2a rows are content. Q2c python_indent/list_depth have no Q1 tier assignment and are reported unassigned_by_Q1 plus their row results, not silently assigned a new tier.

No rater-2 codes were present at verification; κ is pending, not zero. Do not create new coder calls. Finish coding tables before the gallery. Gallery source/formula amendment b51c7915 was supplied before ranking: sealed original W1/§84 native asked scores, mean frozen paired log-odds; sign by truth, percentile within reader/row test items, d=pctNLA-pctOracle; two greatest|d| per tier plus one seeded-hash random from the rest. No probe term. Preserve requested sample items and all previous seals; no new API/GPU use.
''')
    print('All5blind-code/input seals and derivative Q1 views verified; no private keys accessed')


def accuracy(rows,flag,value):
    yes=[r for r in rows if r[flag]];resolved=[r for r in yes if r[value] in ['A','B']]
    known=[r for r in yes if r['truth'] is not None];known_resolved=[r for r in resolved if r['truth'] is not None]
    corr=sum(r[value]==r['truth'] for r in known_resolved)
    complete=len(known)==len(yes)
    return {'rate':rate(len(yes),len(rows)), 'accuracy':rate(corr,len(yes)) if complete else None,
            'resolved_accuracy':rate(corr,len(resolved)) if complete else None,
            'unresolved':len(yes)-len(resolved),'unknown_truth':len(yes)-len(known),
            'known_truth_only_accuracy':rate(corr,len(known)),'known_truth_only_resolved_accuracy':rate(corr,len(known_resolved))}


def summarize(rows):
    result={'n':len(rows),'mode':{v:rate(sum(r['mode']==v for r in rows),len(rows)) for v in ['continues','describes','mixed']},
            'mentions':accuracy(rows,'mentions','value'),'enacts':accuracy(rows,'enacts','enact_value')}
    result['mention_kind']={kind:{'rate':rate(sum(r['mention_kind']==kind for r in rows),len(rows)),
                                'share_among_mentions':rate(sum(r['mention_kind']==kind for r in rows),sum(r['mentions'] for r in rows)),
                                'accuracy':accuracy([r for r in rows if r['mention_kind']==kind],'mentions','value')}
                            for kind in ['quotes_token','states_property']}
    if rows and rows[0]['sample']=='q1':
        result['hallucination']=rate(sum(r['hallucination'] for r in rows),len(rows));result['extra']=rate(sum(bool(r['extra'].strip()) for r in rows),len(rows))
    if rows and rows[0]['sample']=='q2b':
        result['structure_named']=rate(sum(r['structure_named'] for r in rows),len(rows))
        for field in ['mentions','enacts']:
            val='value' if field=='mentions' else 'enact_value';ys=[r for r in rows if r[field]];rs=[r for r in ys if r[val] in ['A','B']]
            result[field]['source_B_agreement']=rate(sum(r[val]=='B' for r in ys),len(ys))
            result[field]['target_A_alignment']=rate(sum(r[val]=='A' for r in ys),len(ys))
            result[field]['resolved_target_A_alignment']=rate(sum(r[val]=='A' for r in rs),len(rs))
    if rows and rows[0]['sample']=='q2c':result['structure_tokens']=rate(sum(bool(r['structure_tokens']) for r in rows),len(rows))
    return result


def analyse():
    pre=I.read(OUT/'PREJOIN_VERIFICATION.json')
    for name,path in SAMPLES.items():
        if I.sha(path)!=pre['samples'][name]['input_sha256'] or I.sha(CODES/f'{name}.CLAUDE_CODES.jsonl')!=pre['samples'][name]['codes_sha256']:raise ValueError('codes/input changed')
    q1receipt=I.read(I.ROOT/'results/g_agreement/understand/q1/BLIND_SAMPLE_RECEIPT.json');q2receipt=I.read(I.ROOT/'results/g_agreement/understand/q2/SAMPLES_RECEIPT.json')
    keyrefs={}
    for sample in ['q1','q2a','q2b','q2c']:
        rec=q1receipt if sample=='q1' else q2receipt[sample];keyrefs[sample]=rec
        if I.sha(Path(rec['key_cache_only']))!=rec['key_sha256']:raise ValueError('key changed')
    plan=I.read(I.ROOT/'results/g_agreement/understand/q1/SAMPLING_PLAN.json')
    feature_tier={f:t for t,features in plan['tiers'].items() for f in features}
    joined=[]
    for sample in ['q1','q2a','q2b','q2c']:
        keys={r['id']:r for r in I.rows(Path(keyrefs[sample]['key_cache_only']))}
        code_name='q1_passA' if sample=='q1' else sample
        codes=I.rows(CODES/f'{code_name}.CLAUDE_CODES.jsonl')
        if sample=='q1':passb={r['id']:r for r in I.rows(CODES/'q1_passB.CLAUDE_CODES.jsonl')}
        if set(keys)!={r['id'] for r in codes}:raise ValueError('code/key mismatch')
        for c in codes:
            k=keys[c['id']];truth=k.get('truth_AB') if sample!='q2b' else ('B' if k['dose']==0 else None)
            tier=k['tier'] if sample=='q1' else 'content' if sample=='q2a' else feature_tier.get(k['feature'],'unassigned_by_Q1')
            joined.append({**k,**c,**(passb[c['id']] if sample=='q1' else {}),'sample':sample,'generation':k.get('sample'),'source_value':k.get('value'),'truth':truth,'tier':tier})
    # Original 'sample' generation is retained in generation; dataset name replaces it above.
    tables={}
    def group(name,fields,filtered):
        groups={}
        for r in filtered:groups.setdefault(tuple(r[f] for f in fields),[]).append(r)
        tables[name]=[{**dict(zip(fields,key)),**summarize(rs)} for key,rs in sorted(groups.items())]
    group('by_sample',['sample'],joined)
    group('by_tier_reader',['sample','tier','reader','layer'],joined)
    group('by_row_reader',['sample','feature','reader','layer'],[r for r in joined if r['sample']!='q1'])
    group('q2b_by_dose',['sample','dose','reader','layer'],[r for r in joined if r['sample']=='q2b'])
    group('q2b_by_row_dose',['sample','feature','dose','reader','layer'],[r for r in joined if r['sample']=='q2b'])
    group('q2c_by_reader_value',['sample','reader','truth'],[r for r in joined if r['sample']=='q2c'])
    group('q2c_by_row_reader_value',['sample','feature','reader','truth','source_value'],[r for r in joined if r['sample']=='q2c'])
    data={'at':NOW(),'status':'RATER1_DESCRIPTIVE_TABLES_COMPLETE_GALLERY_NEXT','tables':tables,'rater2_status':'NO_CODES_PRESENT_IN_CACHE_CODEX_CODES_AT_PREFLIGHT','kappa':None,
          'producer_notes':pre['seal']['notes'],'prejoin_verification_sha256':I.sha(OUT/'PREJOIN_VERIFICATION.json'),'api_calls':0,'gpu_hours':0}
    I.save(OUT/'RATER1_METRICS.json',data)
    fmt=lambda x:'UNAVAILABLE' if x is None or x['rate'] is None else f"{x['k']}/{x['n']} = {100*x['rate']:.1f}% [{max(0,100*x['ci95'][0]):.1f}, {min(100,100*x['ci95'][1]):.1f}]"
    lines=['# Q1/Q2 rater-1 coding results','','DESCRIPTIVE. All code/input hashes and ID coverage verified before private-key joins. All required evidence quotes and normalized structure tokens are verbatim. No exclusions, recoding or new coder calls. Wilson95 intervals are per readout; repeated generations/doses are correlated. Q1 mode/mention/enact uses property-only pass A; hallucination/extra uses contextual pass B.','','Producer notes:']+['- '+n for n in pre['seal']['notes']]
    for title,key in [('Whole samples','by_sample'),('Tier and native reader','by_tier_reader'),('Q2 rows and native reader','by_row_reader'),('Q2b by dose','q2b_by_dose')]:
        lines+=['','## '+title,'','| Group | Continues | Describes | Mixed | Mention | Quotes token | States property | Correct/all mentions | Correct/resolved mentions | Enacts | Correct/all enacts | Correct/resolved enacts |','|---|---|---|---|---|---|---|---|---|---|---|']
        for r in tables[key]:
            label=' / '.join(str(r[f]) for f in ['sample','tier','feature','dose','reader','layer'] if f in r)
            m,e=r['mentions'],r['enacts'];ks=r['mention_kind']
            values=[r['mode'][v] for v in ['continues','describes','mixed']]+[m['rate'],ks['quotes_token']['rate'],ks['states_property']['rate'],m['accuracy'],m['resolved_accuracy'],e['rate'],e['accuracy'],e['resolved_accuracy']]
            lines.append('| '+label+' | '+' | '.join(fmt(x) for x in values)+' |')
    lines+=['','## Q1 contextual pass B','','| Tier / reader | Hallucination | Extra |','|---|---|---|']
    for r in tables['by_tier_reader']:
        if r['sample']=='q1':lines.append(f"| {r['tier']} / {r['reader']} L{r['layer']} | {fmt(r['hallucination'])} | {fmt(r['extra'])} |")
    lines+=['','## Q2b named structure and enactment references','','Nonzero-dose edited-state truth is not independently observed, so accuracy there is unavailable. Dose0 accuracy uses source truth B. Source-B agreement and target-A alignment below are reference matches, not edited-state accuracy.','','| Dose | Structure named | Enactments | Source-B agreement among enacts | Target-A alignment among enacts | Target-A alignment among resolved enacts |','|---|---|---|---|---|---|']
    for r in tables['q2b_by_dose']:
        e=r['enacts'];lines.append(f"| {r['dose']} | {fmt(r['structure_named'])} | {fmt(e['rate'])} | {fmt(e['source_B_agreement'])} | {fmt(e['target_A_alignment'])} | {fmt(e['resolved_target_A_alignment'])} |")
    lines+=['','## Q2c normalized structure-token rate','','A/B mean each row’s frozen first/second value, not a global presence/absence. Structure event = nonempty producer-normalized structure_tokens; no extra filtering.','','| Reader / row / true value | Any structure token |','|---|---|']
    for key in ['q2c_by_reader_value','q2c_by_row_reader_value']:
        for r in tables[key]:lines.append('| '+' / '.join(str(r[f]) for f in ['reader','feature','truth','source_value'] if f in r)+' | '+fmt(r['structure_tokens'])+' |')
    lines+=['','## Denominators and availability','','Unclear values stay in correct/all-mention or enactment denominators; resolved accuracy excludes unclear. Zero denominator is unavailable, not zero accuracy. Mention-kind rates use all readouts; composition and subtype-specific accuracies are also in JSON. Q2c python_indent/list_depth are unassigned by Q1 tiers and retain separate row results. Q2b row-by-dose metrics are in JSON. No registered verdict is changed.','','Rater2 codes were not present at preflight; Cohen’s κ is pending, not zero. Gallery is selected after these tables under the clarified b51c7915 rule, separately sealed.']
    (OUT/'RATER1_RESULTS.md').write_text('\n'.join(lines)+'\n')
    I.save(OUT/'RATER1_TABLE_SEAL.json',{'files':{n:I.sha(OUT/n) for n in ['RATER1_METRICS.json','RATER1_RESULTS.md','PREJOIN_VERIFICATION.json','JOIN_NOTE.md']}})
    print('Rater1 tables complete; no gallery ranking performed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['verify','analyse']);a=p.parse_args();{'verify':verify,'analyse':analyse}[a.action]()
