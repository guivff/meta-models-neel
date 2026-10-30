"""§190 clarification 1: NLA512 binary rows, supplement reused exactly once."""
import argparse
from pathlib import Path
from .core import *

ORDINAL={'table_column_ordinal','python_depth_ordinal'}

def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x]

def metadata(s):
    for p,h in s['inputs'].items(): require(sha(p)==h,'frozen input changed')
    coverage=read(s['coverage'])['items'];unique(coverage)
    e49=unique(read(s['e49_items']));e54=unique(read(s['e54_items']))
    w1=unique(lines(s['w1_items']));e36=unique(lines(s['e36_labels']))
    wdefs=read(s['w1_manifest'])['rows'];defs36=read(s['e36_definitions'])['rows']
    defs49=read(s['e49_candidates'])['rows'];defs54=read(s['e54_definitions'])['rows']
    out=[]; excluded=[]
    for c in coverage:
        bank,row,uid=c['bank'],c['row'],c['source_id']
        if row in ORDINAL:
            excluded.append(c);continue
        x={'E49':e49,'E54':e54,'W1':w1,'E36':e36}[bank][uid]
        if bank=='E49':
            values=defs49[row]['spec']['values'];target='A' if x['label']==1 else 'B'
        elif bank=='E54':
            target='A' if x['label']==1 else 'B'
            # Preserve the registered family-dependent bridge identity, fixed A/B order.
            twins=[v for v in e54.values() if v['feature']==row and v['template_index']==x['template_index']]
            values=[]
            for label in (1,0):
                v={t['value'] for t in twins if t['label']==label}
                require(len(v)==1,'ambiguous E54 frozen family value');values.append(v.pop())
        else:
            values=(wdefs if bank=='W1' else defs36)[row]['values']
            require(x['value'] in values and len(values)==2,'binary frozen mapping')
            target='A' if x['value']==values[0] else 'B'
        require(len(values)==2,'two registered values')
        out.append(dict(id=c['id'],item=uid,bank=bank,row=row,reader='nla',target=target,
                        property=row,values=dict(A=values[0],B=values[1]),owner=c['acquisition_owner']))
    require(len(out)==5376 and len(excluded)==288,'5664 coverage minus two ordinal rows')
    return out,excluded

def text_record(x):
    raw=x.get('raw',x['text']); text=x['text']
    # Frozen §172: text inside explanation tags, otherwise the entire unclosed output.
    if '<explanation>' in raw and '</explanation>' in raw:
        text=raw.split('<explanation>',1)[1].split('</explanation>',1)[0]
    return text, '</explanation>' not in raw

def collect(s):
    meta,excluded=metadata(s)
    root=Path(s['output']);z=verify(root/'OUTPUT_SEAL.json',s['output_sha256'])
    require(z['experiment']=='E78' and z['status']=='COMPLETE' and z['input_seal_sha256']==s['input_sha256'],'E78 seal identity')
    raw=unique(read(root/'RECORDS.json'))
    coverage=read(s['coverage']);expected={x['id'] for x in coverage['items'] if x['acquisition_owner']=='E78'}
    require(set(raw)==expected and len(raw)==4992,'complete new acquisition')
    sup=Path(s['supplement_output']);ss=verify(sup/'OUTPUT_SEAL.json',s['supplement_sha256'])
    require(ss['status']=='COMPLETE' and ss['input_seal_sha256']==coverage['supplement_input_seal_sha256'],'exact supplement input')
    supplement=unique(lines(sup/'nla_native.jsonl'))
    require({'E49:'+k for k in supplement}==set(coverage['supplement_ids']) and len(supplement)==672,'reserved supplement exact grid')
    require(not set(raw)&{'E49:'+k for k in supplement},'no duplicate acquisition')
    raw.update({'E49:'+k:v for k,v in supplement.items()})
    for x in meta:
        x['text'],x['truncated']=text_record(raw[x['id']])
    return meta,excluded

def analyze(rows):
    groups={}
    for x in rows: groups.setdefault(x['bank']+':'+x['row'],[]).append(x)
    result={}
    for key,xs in sorted(groups.items()):
        unique(xs,'item');r=stats({x['item']:x['score'] for x in xs})
        status='NOT EVALUABLE' if r['CI95'] is None else 'REPORTED' if round(r['estimate'],12)>=.20 and r['CI95'][0]>0 else 'MISSED'
        n=sum(x['truncated'] for x in xs)
        result[key]=dict(r,status=status,truncated=n,truncation_rate=n/len(xs),truncation_over_10_percent=10*n>len(xs))
    return dict(rows=result,ordinal={r:'NOT EVALUABLE (no registered mapping)' for r in sorted(ORDINAL)},
                measure='NLA512 §172 S; never merged with NLA128',
                comparison_128='Prior 128-token results remain separately sealed; no retroactive §172 classification is imputed.')

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['blind','analyze']);a=p.parse_args()
    commit=committed();s=read(HERE/'E78.json')
    if a.mode=='blind':
        rows,excluded=collect(s);export(rows,s['blind'],s['private'],s['output_sha256'],commit)
        # Omitted row inventory is private and contains no generated output.
        write(Path(s['private']).with_name('ORDINAL_NOT_EVALUABLE.json'),excluded)
    else:
        rows,jsha=load_codes(s);expected,_=metadata(s)
        require({x['id'] for x in rows}=={x['id'] for x in expected},'complete binary analysis grid')
        out=claim(s,commit);write(out/'RESULTS.json',analyze(rows))
        write(out/'REDACTION_SENSITIVITY.json',analyze([dict(x,score=None if x['redacted'] else x['score']) for x in rows]))
        write(out/'SCORED_ITEMS.json',rows)
        seal(out,'ANALYSIS_SEAL.json',experiment='E78',status='COMPLETE_ONCE',code_commit=commit,
             output_seal_sha256=s['output_sha256'],supplement_sha256=s['supplement_sha256'],judgment_seal_sha256=jsha)

if __name__=='__main__': main()
