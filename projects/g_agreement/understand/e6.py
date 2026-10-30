"""§93 script proxies and activation-only continuation prompt, exploratory."""
from contextlib import contextmanager
import copy,json,re
from pathlib import Path
from . import core as K
from projects.g_agreement.blindspot import protocol as P

FEATURES=['prose_paren','python_string','python_indent','list_depth','table_column']
PROMPT='Continue the source text represented by the activation. Output only the next text, not a description or explanation. Do not describe the activation. Continue for up to 32 tokens.'
SCRIPTS={
 'prose_paren':'first ASCII parenthesis is closing=>1, opening=>0, neither=>0.5',
 'python_string':'text fragment then ASCII quote followed by code delimiter/end=>1, leading quote=>0, otherwise0.5; proxy only, quote semantics ambiguous',
 'python_indent':'first nonempty line after newline: clip((12-leading_spaces)/8,0,1); no such line=>0.5',
 'list_depth':'first Markdown bullet line: clip((4-leading_spaces)/4,0,1); no bullet=>0.5',
 'table_column':'first generated line: >=5pipes=>1,1–3pipes=>0,none or4=>0.5; proxy for remaining columns, not asserted column truth',
}


def behaviour(feature,text):
    if feature=='prose_paren':
        m=re.search(r'[()]',text);return .5 if m is None else float(m.group()==')')
    if feature=='python_string':
        if re.search(r'''^[^'"\n]+['"]\s*(?:[,;)}\]]|$)''',text):return 1.
        return 0. if text.lstrip().startswith(('"',"'")) else .5
    if feature=='python_indent':
        lines=[line for line in text.split('\n')[1:] if line.strip()]
        if not lines:return .5
        line=lines[0].expandtabs(4);n=len(line)-len(line.lstrip(' '));return max(0.,min(1.,(12-n)/8))
    if feature=='list_depth':
        m=re.search(r'(?m)^([ \t]*)[-+*]\s+',text)
        return .5 if m is None else max(0.,min(1.,(4-len(m.group(1).expandtabs(4)))/4))
    if feature=='table_column':
        n=text.split('\n',1)[0].count('|');return 1. if n>=5 else 0. if 1<=n<=3 else .5
    raise ValueError(feature)


def format_status(text):
    if re.search(r'(?i)\b(?:cannot|can.t|unable to)\s+continue|can only describe',text):return 'EXPLICIT_CONTINUATION_REFUSAL'
    if '<explanation>' in text or re.match(r'(?i)^\s*(?:[-*]\s*)?(?:the|this) activation',text):return 'DESCRIPTIVE_FORMAT_MARKER'
    return 'NO_SCRIPTED_REFUSAL_MARKER'


@contextmanager
def continuation_reader(name,reader):
    if name=='olens':
        from mats.readers.olens import OracleLens
        value=OracleLens(model=reader.model,tok=reader.tok,alpha=reader.alpha,device=reader.device,
            prompt=reader.prompt+'\n'+PROMPT)
        yield value
    else:
        from mats.readers.nla import _render_prompt
        meta=copy.deepcopy(reader.meta);meta['prompt_templates']['actor']+='\n'+PROMPT
        ids,marker=_render_prompt(reader.tok,meta,False)
        previous=(reader.prompt_ids,reader.marker)
        try:reader.prompt_ids,reader.marker=ids,marker;yield reader
        finally:reader.prompt_ids,reader.marker=previous


def generate(name,reader,h):
    with continuation_reader(name,reader) as obj:
        if name=='olens':
            from mats.readers.olens import Sampling
            rows=obj.verbalize(h,44,k=1,sampling=Sampling(temperature=0,max_new_tokens=32),batch=8)
        else:
            from mats.readers.nla import Sampling
            rows=obj.verbalize_raw(h,k=1,sampling=Sampling(temperature=0,max_new_tokens=32),batch=8)
    return [r[0] for r in rows]


def prepare():
    _,_,templates=K.load_w1()
    def select(items):return [i for i,x in enumerate(items) if x['feature'] in FEATURES and x['split']=='test']
    return K.prepare('E6',FEATURES,select,{f:templates[f] for f in FEATURES},1800,
        {'prediction':'Readers may enact structure in continuations while not stating it',
         'continuation_prompt':PROMPT,'max_new_tokens':32,'do_sample':False,'generation_batch':8,
         'scripts':SCRIPTS,'format_policy':'Record explicit refusal and descriptive-format marker per output; no inferred refusal from low task score. Native construction errors reported as unsupported.',
         'limitations':'Script proxies do not prove functional correctness. Missing structural markers score neutral0.5; no score-conditioned filtering.'})


def free_check(out):
    """Part(a): only already sealed W1 free readouts, with unavailable rows explicit."""
    from collections import defaultdict,Counter
    from dataclasses import asdict
    import numpy as np
    from mats import metrics
    items,_,templates=K.load_w1();lookup={x['id']:x for x in items};records=[];lineage=[]
    for phase,filename in (('target','unasked.target.jsonl'),('nla','unasked.nla.jsonl')):
        root=P.ROOT/f'cache/g_agreement/blindspot/w1-units/priority/{phase}'
        seal=P.verify(root,'FREE_SEAL.json')
        if filename not in seal['files']:raise ValueError('free seal lacks readouts')
        lineage.append({'directory':str(root),'seal_sha256':P.sha(root/'FREE_SEAL.json')})
        records.extend(P.rows(root/filename))
    grouped=defaultdict(list)
    for r in records:
        x=lookup[r['id']]
        if x['feature'] not in FEATURES or x['split']!='test':continue
        if r['reader'] not in ('olens','nla'):continue
        if r['status']!='COMPLETE':continue
        text=r.get('text') or r.get('raw') or ''
        grouped[x['feature'],r['reader'],r['id']].append({'score':behaviour(x['feature'],text),'format':format_status(text)})
    rows=[]
    for f in FEATURES:
        for name in ('olens','nla'):
            ids=[key for feature,reader,key in grouped if feature==f and reader==name]
            if not ids:rows.append({'feature':f,'reader':name,'status':'NO_SEALED_FREE_READOUTS','n':0});continue
            score=np.array([np.mean([r['score'] for r in grouped[f,name,i]]) for i in ids])
            y=np.array([lookup[i]['value']==templates[f]['values'][0] for i in ids],int)
            groups=np.array([lookup[i]['cluster'] for i in ids])
            rows.append({'feature':f,'reader':name,'status':'EXPLORATORY','n':len(ids),
                'auroc':asdict(metrics.auroc_ci(score,y,groups,n_boot=2000,seed=P.SEED)),
                'format_markers':dict(Counter(r['format'] for i in ids for r in grouped[f,name,i])),
                'aggregation':'average existing samples within item, then AUROC/cluster CI; missing markers neutral0.5'})
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    P.dump(out/'metrics.json',{'status':'EXPLORATORY','scripts':SCRIPTS,'lineage':lineage,'rows':rows})
    (out/'RESULTS.md').write_text('# E6(a) exploratory enacted-structure script check\n\nPrediction: enactment may carry structure that descriptions do not state.\n\n'+
        '\n'.join(str(r) for r in rows)+'\n\nOnly sealed priority readouts are used; missing rows are reported. These are surface proxies, not proof of valid continuation.\n')
    return rows
