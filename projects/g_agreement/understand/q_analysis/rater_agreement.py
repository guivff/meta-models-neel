"""Agreement with delivered, hash-sealed rater2; no new annotations."""
from pathlib import Path
from collections import defaultdict
import shutil
from .followup import joined
from .run import I,OUT,CACHE,NOW
from projects.g_agreement.understand.e13.claude_analysis import kappa
from projects.g_agreement.understand.e13.analyse import rate


def canon(v):return 'NONE' if v is None else str(v)


def measure(rows,field):
    if field=='value_both_mention':rows=[r for r in rows if r['one']['mentions'] and r['two']['mentions']];actual='value'
    elif field=='enact_value_both_enact':rows=[r for r in rows if r['one']['enacts'] and r['two']['enacts']];actual='enact_value'
    else:actual=field
    def extract(code):
        if actual=='extra_presence':return canon(bool(code['extra'].strip()))
        if actual=='structure_tokens_present':return canon(bool(code['structure_tokens']))
        if actual=='structure_token_set':return I.canonical(sorted(set(code['structure_tokens'])))
        return canon(code[actual])
    a=[extract(r['one']) for r in rows];b=[extract(r['two']) for r in rows]
    result=kappa(a,b);result['raw_agreement_wilson95']=rate(sum(x==y for x,y in zip(a,b)),len(a))
    return result


def run():
    proof=I.read(OUT/'RATER2_PREJOIN_VERIFICATION.json');base=CACHE/'codex_codes'
    if I.sha(base/'CODES_SEAL.json')!=proof['producer_seal_sha256']:raise ValueError('rater2 seal changed')
    for sample,ref in proof['samples'].items():
        if I.sha(base/(sample+'.jsonl'))!=ref['codes_sha256']:raise ValueError('rater2 codes changed')
    # Reader/tier grouping uses only the already verified original private keys.
    r1=joined();r2={name:{r['id']:r for r in I.rows(base/(name+'.jsonl'))} for name in ['q1_passA','q1_passB','q2a','q2b','q2c']}
    rows=[]
    for r in r1:
        code={**r2['q1_passA'][r['id']],**r2['q1_passB'][r['id']]} if r['sample']=='q1' else r2[r['sample']][r['id']]
        rows.append({'sample':r['sample'],'tier':r['tier'],'reader':r['reader'],'one':r,'two':code})
    fields=['mode','mentions','mention_kind','value','value_both_mention','enacts','enact_value','enact_value_both_enact']
    output=[]
    for scope,names in [('sample',['sample']),('tier_reader',['sample','tier','reader'])]:
        groups=defaultdict(list)
        for r in rows:groups[tuple(r[n] for n in names)].append(r)
        for key,rs in sorted(groups.items()):
            sample=key[0];fs=fields+(['hallucination','extra_presence'] if sample=='q1' else ['structure_named'] if sample=='q2b' else ['structure_tokens_present','structure_token_set'] if sample=='q2c' else [])
            for f in fs:output.append({'stratum':scope,**dict(zip(names,key)),'field':f,**measure(rs,f)})
    data={'at':NOW(),'status':'RATER2_CATEGORICAL_AGREEMENT_COMPLETE','prejoin_verification_sha256':I.sha(OUT/'RATER2_PREJOIN_VERIFICATION.json'),
          'input_provenance':'Producer seal binds code hashes but omits input hashes; local verification supplements with canonical sealed input hashes, complete unique ID coverage and exact per-ID evidence checks. No new annotation or repair.',
          'fields':'Categorical fields use unchanged delivered categories; NONE is a distinct category, unclear is retained. Conditional value comparisons use only both-positive codes. Extra is presence of nonempty text. Structure tokens compared as presence and exact unordered token set; no wrapper filtering added. About/evidence/extra prose has no meaningful categorical semantic kappa and is not recoded.',
          'kappa_ci':'Kappa is not a binomial proportion; Wilson95 attached to raw agreement, not to kappa. Degenerate identical categories give undefined kappa, not zero.',
          'rows':output,'api_calls':0,'gpu_hours':0}
    I.save(OUT/'RATER2_KAPPA.json',data)
    archive=CACHE/'q_analysis/followup_before_rater2';archive.mkdir(parents=True,exist_ok=False)
    for n in ['FOLLOWUP.md','FOLLOWUP.json','FOLLOWUP_SEAL.json']:shutil.copyfile(OUT/n,archive/n)
    follow=I.read(OUT/'FOLLOWUP.json');follow['rater2']={'status':'SEALED_CODES_LOCALLY_INPUT_BOUND_KAPPA_COMPLETE','producer_code_seal_sha256':proof['producer_seal_sha256'],
        'prejoin_verification_sha256':I.sha(OUT/'RATER2_PREJOIN_VERIFICATION.json'),'provenance_limitation':data['input_provenance'],'categorical_agreement':output}
    I.save(OUT/'FOLLOWUP.json',follow)
    fmt=lambda x:'UNAVAILABLE' if x['rate'] is None else f"{x['k']}/{x['n']} [{max(0,x['ci95'][0]):.3f}, {min(1,x['ci95'][1]):.3f}]"
    lines=['','## Rater2 agreement (arrived during this run)','','Rater2 code-hash seal verified; it omits input hashes. Local verification additionally binds canonical sealed input hashes, full unique-ID sets and per-ID exact evidence. The prior pending statement above records the earlier preflight and is superseded by this section. No codes were repaired or excluded. Kappa uses categorical codes as delivered; NONE and unclear are separate. About/evidence/free extra prose has no meaningful semantic kappa without new coding; extra presence is compared instead. Structure-token agreement uses presence and the exact unordered set, with no new wrapper normalization.','','Kappa is not a proportion; Wilson95 below is for raw agreement. Undefined kappa means a degenerate category distribution or no eligible records, not zero agreement.','','| Sample | Field | n | Kappa | Raw agreement k/n [Wilson95] |','|---|---|---:|---:|---|']
    for r in output:
        if r['stratum']!='sample':continue
        kval='UNDEFINED' if r['kappa'] is None else f"{r['kappa']:.3f}"
        lines.append(f"| {r['sample']} | {r['field']} | {r['n']} | {kval} | {fmt(r['raw_agreement_wilson95'])} |")
    lines+=['','Per-tier/reader kappa for every categorical field is included in FOLLOWUP.json and RATER2_KAPPA.json. Kappa measures coder agreement, not validity; rater1/rater2 structural/quote conventions remain as delivered.']
    with (OUT/'FOLLOWUP.md').open('a') as f:f.write('\n'.join(lines)+'\n')
    I.save(OUT/'FOLLOWUP_SEAL.json',{'files':{n:I.sha(OUT/n) for n in ['FOLLOWUP.json','FOLLOWUP.md','FOLLOWUP_PLAN.json','RATER2_KAPPA.json','RATER2_PREJOIN_VERIFICATION.json']},
                                   'rater1_followup_archive':str(archive),'rater1_followup_archive_seal_sha256':I.sha(archive/'FOLLOWUP_SEAL.json')})
    print('Rater2 kappa added to FOLLOWUP; original follow-up output archived unchanged')

if __name__=='__main__':run()
