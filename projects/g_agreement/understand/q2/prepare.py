"""Build sealed-source Q2 samples; labels and source identities remain in cache."""
import argparse
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import subprocess
from projects.g_agreement.understand.e13 import io as I
from projects.g_agreement.understand.e10.pool import W1,W6
from projects.g_agreement.blindspot.items import FEATURES

OUT=I.ROOT/'results/g_agreement/understand/q2'
CACHE=I.ROOT/'cache/g_agreement/understand/q2'
BANK=I.ROOT/'cache/g_agreement/blindspot/w1-readonly-20261024/w1-bank-v2'
CORE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement')
E6=CORE/'blindspot/understand-units/5xg04qljqfe472/pack-out/E6'
E6_BANK=CORE/'understand/e6-stage-v1'
A_FEATURES=['prose_sentiment','python_effect','latex_subject']
C_FEATURES=['prose_paren','python_string','python_indent','list_depth','table_column']


def verify(base,name,refs):
    doc=I.read(base/name)
    for n,h in doc['files'].items():
        if Path(n).is_absolute() or '..' in Path(n).parts or I.sha(base/n)!=h:raise ValueError('source seal mismatch '+n)
    refs.append({'path':str(base/name),'sha256':I.sha(base/name),'verified_files':len(doc['files'])})
    return doc


def freeze():
    refs=[]
    verify(BANK,'INPUT_SEAL.json',refs)
    mf=I.read(BANK/'manifest.json')
    if I.sha(BANK/'labels.DO_NOT_STAGE.jsonl')!=mf['files']['labels.DO_NOT_STAGE.jsonl']:raise ValueError('labels changed')
    verify(W1/'target','FREE_SEAL.json',refs);verify(W1/'nla','FREE_SEAL.json',refs)
    verify(W6,'SCORE_SEAL.json',refs);verify(E6,'SCORE_SEAL.json',refs);verify(E6_BANK,'INPUT_SEAL.json',refs)
    if I.read(E6/'provenance.json')['input_seal_sha256']!=I.sha(E6_BANK/'INPUT_SEAL.json'):raise ValueError('E6 input lineage')
    e6plan=I.read(E6_BANK/'plan.json');lp=Path(e6plan['labels_local'])
    if I.sha(lp)!=e6plan['labels_sha256']:raise ValueError('E6 labels changed')
    files=[BANK/'labels.DO_NOT_STAGE.jsonl',W1/'target/unasked.target.jsonl',W1/'nla/unasked.nla.jsonl',W6/'experiment/native/raw_scores.json',E6/'scores.jsonl',lp]
    plan={'at':datetime.now(timezone.utc).isoformat(),'section':107,'registration':'efe4a827','seed':I.SEED,'source_seals':refs,
          'files':{str(p):I.sha(p) for p in files},'e6_labels':str(lp),
          'q2a':'150 distinct W1 test items paired across readers,50/row,25/value/row; choose IDs by hash rank(seed,q2a-item,feature,value,id); choose one common generation0/1 per item by seeded hash. Raw original free strings preserved including parser failures; no content/score filtering.300readouts.',
          'q2b':'Guiv ruling:240fromNONZEROdoses only,48/dose,24/row/dose; plusALL80dose0readouts,40/row.320uniqueOracle outputs. Choose nonzero cases by hash rank(seed,q2b-item,feature,dose,item). No coherence/score filtering. Original source valueB and steering targetA stay in key; edited-state truth is not independently observed.',
          'q2c':'All840sealedE6continuations,84/row/reader,5rows,420matchedtestitems. No content/score filtering, no missing substitution.',
          'blind_format':'Exactly{id,question,readout}; opaque ID rank(seed,q2-opaque,dataset,feature,reader,item,sample_or_dose); independent hash order. Questions name original/steered property and frozen A/B definitions, not reader, dose, source prompt, true value or score.',
          'codebook':'Same Q1 codebook; Q2b additionally structure_named; Q2c additionally bracket_or_structure_tokens. This step only builds files; no coder, API or key join. No source prefixes requested here; hallucination/extra source-truth checks cannot be inferred from readout-only samples.',
          'questions':{f:'Property at the original read position: '+f.replace('_',' ')+'. A = '+FEATURES[f].descriptions[0]+'; B = '+FEATURES[f].descriptions[1]+'.' for f in set(A_FEATURES+C_FEATURES)},
          'code_sha256':I.sha(Path(__file__))}
    I.save(OUT/'PLAN.json',plan)
    (OUT/'SCOPE.md').write_text('# §107 Q2 blind sampling\n\nDated '+plan['at']+', before Q2 selection/export. Implements efe4a827 and Guiv’s clarified Q2b ruling:240nonzero-dose outputs plusall80dose0=320, no duplicates. Q2a uses50matchedteststates per each of3rows,25/value, onecommonoriginalgeneration perstate,150readouts/reader. Q2c retains all840sealed continuations. Exactsource hashes and sampling/opaque-ID/shuffle rules in PLAN.json. Original parser failures, incomplete endings and any empty raw strings are preserved; no outcome/content filter.\n\nQuestions name only the feature and frozenA/B definitions; no reader/dose/truth/prompt/score metadata. All source identities, native sites, source truth and doses stay in cache-only keys. W6 editing targets A from source B; the edited-state value is not an independently measured truth. This must remain distinct in later scoring. Questions/source context policy follows the requested E13-style readout-only files; source-factual hallucination/extra checks cannot be established without the source text. No code execution by blind agents/API in this preparation. No Q2d work requested.\n')
    print('Q2 source seals verified; sample rules frozen')


def export(name,records):
    folder=CACHE/name;folder.mkdir(parents=True,exist_ok=True)
    cases=[]
    for r in records:
        opaque=I.rank('q2-opaque',name,r['feature'],r['reader'],r['item'],r.get('sample',r.get('dose')))
        cases.append(({'id':opaque,'question':r['question'],'readout':r['readout']},{'id':opaque,**{k:v for k,v in r.items() if k not in ['question','readout']},'readout_sha256':I.digest(r['readout'])}))
    cases.sort(key=lambda x:I.rank('q2-order',name,x[0]['id']))
    if len(cases)!=len({r[0]['id'] for r in cases}):raise ValueError('duplicate blind identities')
    I.jsonl(folder/'blind_sample.jsonl',[r[0] for r in cases]);I.jsonl(folder/'KEY.DO_NOT_SHARE.jsonl',[r[1] for r in cases])
    return {'path':str(folder/'blind_sample.jsonl'),'sha256':I.sha(folder/'blind_sample.jsonl'),'n':len(cases),
            'reader_counts':dict(Counter(r['reader'] for r in records)),'row_counts':dict(Counter(r['feature'] for r in records)),
            'dose_counts':dict(Counter(str(r['dose']) for r in records if 'dose' in r)),
            'empty_raw':sum(not r['readout'].strip() for r in records),'key_cache_only':str(folder/'KEY.DO_NOT_SHARE.jsonl'),'key_sha256':I.sha(folder/'KEY.DO_NOT_SHARE.jsonl')}


def build():
    plan=I.read(OUT/'PLAN.json')
    if I.sha(Path(__file__))!=plan['code_sha256']:raise ValueError('code changed')
    rel='results/g_agreement/understand/q2/PLAN.json'
    if subprocess.check_output(['git','show','HEAD:'+rel],cwd=I.ROOT)!=(OUT/'PLAN.json').read_bytes():raise ValueError('plan not committed')
    for p,h in plan['files'].items():
        if I.sha(Path(p))!=h:raise ValueError('frozen source changed')
    labels={r['id']:r for r in I.rows(BANK/'labels.DO_NOT_STAGE.jsonl')}
    a={(r['id'],r['sample']):r for r in I.rows(W1/'target/unasked.target.jsonl') if r['reader']=='olens'}
    b={(r['id'],r['sample']):r for r in I.rows(W1/'nla/unasked.nla.jsonl')}
    records=[]
    for f in A_FEATURES:
        for value in FEATURES[f].values:
            pool=[r for r in labels.values() if r['feature']==f and r['split']=='test' and r['value']==value]
            pool.sort(key=lambda r:I.rank('q2a-item',f,value,r['id']))
            if len(pool)<25:raise ValueError('insufficient Q2a stratum')
            for r in pool[:25]:
                sample=min(range(2),key=lambda s:I.rank('q2a-generation',r['id'],s))
                for reader,raws,layer in [('oracle',a,44),('nla',b,42)]:
                    src=raws[r['id'],sample]
                    if src['layer']!=layer:raise ValueError('W1 site')
                    records.append(dict(feature=f,reader=reader,layer=layer,item=r['id'],sample=sample,value=value,
                                        truth_AB='A' if value==FEATURES[f].values[0] else 'B',split='test',source_status=src['status'],readout=src['raw'],question=plan['questions'][f]))
    qa=export('q2a',records)
    raw=[r for r in I.read(W6/'experiment/native/raw_scores.json') if r['key'][1]=='oracle']
    if len(raw)!=480 or len({tuple(r['key']) for r in raw})!=480:raise ValueError('W6 Oracle grid')
    selected=[]
    for f in ['prose_paren','table_column']:
        for dose in [0.,1.,2.,4.,8.,16.]:
            pool=[r for r in raw if r['key'][0]==f and r['key'][2]==dose]
            if len(pool)!=40:raise ValueError('W6 cell grid')
            pool.sort(key=lambda r:I.rank('q2b-item',f,dose,r['key'][3]))
            selected+=pool[:40 if dose==0 else 24]
    records=[]
    for r in selected:
        f,_,dose,item=r['key'];truth=labels[item]
        if truth['feature']!=f or truth['split']!='test' or truth['value']!=FEATURES[f].values[1]:raise ValueError('W6 source-valueB lineage')
        records.append(dict(feature=f,reader='oracle',layer=44,item=item,dose=dose,source_value=truth['value'],source_truth_AB='B',steering_target_AB='A',edited_truth='NOT_INDEPENDENTLY_OBSERVED',readout=r['readout'],question=plan['questions'][f]))
    qb=export('q2b',records)
    e6labels={r['id']:r for r in I.rows(Path(plan['e6_labels']))};rows=I.rows(E6/'scores.jsonl');records=[]
    if len(rows)!=840 or Counter((r['feature'],r['reader']) for r in rows)!={(f,reader):84 for f in C_FEATURES for reader in ['olens','nla']}:raise ValueError('E6 full grid')
    if len({(r['id'],r['reader']) for r in rows})!=840:raise ValueError('duplicate E6 case')
    for r in rows:
        lab=e6labels[r['id']];f=r['feature'];reader='oracle' if r['reader']=='olens' else 'nla'
        if lab['split']!='test' or lab['feature']!=f or r['layer']!=(44 if reader=='oracle' else 42):raise ValueError('E6 source/site')
        records.append(dict(feature=f,reader=reader,layer=r['layer'],item=r['id'],sample=0,value=lab['value'],truth_AB='A' if lab['value']==FEATURES[f].values[0] else 'B',split=lab['split'],source_status=r['status'],readout=r['text'],question=plan['questions'][f]))
    qc=export('q2c',records)
    if [qa['n'],qb['n'],qc['n']]!=[300,320,840]:raise ValueError('final Q2 sizes')
    I.save(OUT/'SAMPLES_RECEIPT.json',dict(status='ALL_THREE_Q2_SAMPLES_READY_NOT_CODED',at=datetime.now(timezone.utc).isoformat(),seed=I.SEED,
             q2a=qa,q2b=qb,q2c=qc,plan_sha256=I.sha(OUT/'PLAN.json'),api_calls=0,gpu_hours=0))
    print('Q2a300, Q2b320, Q2c840 blind records ready; keys cache-only')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['freeze','build']);a=p.parse_args();{'freeze':freeze,'build':build}[a.action]()
