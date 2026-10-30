"""§187/§189 sealed E70/E72 readers, native scoring, no acquisition."""
import argparse
from pathlib import Path
from .core import *
from .e78 import text_record

ROWS=('unit_system','var_type_at_use','user_expertise')

def collect(s):
    for p,h in s['inputs'].items(): require(sha(p)==h,'frozen late-run input changed')
    e=s['experiment'];items=unique(read(s['items']));labels=unique(read(s['labels']))
    values=read(s['candidates'])['rows']
    root=Path(s['output']);z=verify(root/'OUTPUT_SEAL.json',s['output_sha256'])
    require(z['status']=='COMPLETE' and z['experiment']==e and z['input_seal_sha256']==s['input_sha256'],'exact late output')
    raw=read(root/'RECORDS.json');out=[]
    for x in raw:
        k=items[x['id']];row=k['feature'];v=s['control_values'] if row=='prose_sentiment' else values[row]['spec']['values']
        require(x['feature']==row and x['repeat']==0 and x['reader_native_layer']==(44 if x['reader']=='oracle' else 42),'native identity')
        if e=='E70':
            require(all(x[n]==k[n] for n in ('sign','dose','carrier_id')),'injection identity')
            target='A' if k['sign']==1 else 'B';unit=k['carrier_id'];cell=str(k['dose'])
        else:
            require(x['reader']=='oracle' and x['source_layer'] in (36,40) and x['off_distribution'] is True,'earlier-layer identity')
            target='A' if labels[x['id']]['label']==1 else 'B';unit=x['id'];cell=str(x['source_layer'])
        text,truncated=text_record(x) if x['reader']=='nla' else (x['text'],False)
        out.append(dict(id=f"{x['reader']}:{x['source_layer']}:{x['id']}",item=x['id'],unit=unit,row=row,cell=cell,
                        sign=k.get('sign'),reader=x['reader'],target=target,property=row,values=dict(A=v[0],B=v[1]),
                        text=text,truncated=truncated,source_layer=x['source_layer']))
    validate(out,e);return out

def validate(rows,e):
    unique(rows);require(len(rows)==(320 if e=='E70' else 504),'complete late-run cardinality')
    for reader in (('oracle','nla') if e=='E70' else ('oracle',)):
        for row in (*ROWS,'prose_sentiment') if e=='E70' else ROWS:
            for cell in (('1',) if row=='prose_sentiment' else ('1','2','4')) if e=='E70' else ('36','40'):
                xs=[x for x in rows if (x['reader'],x['row'],x['cell'])==(reader,row,cell)]
                if e=='E70':
                    require(len(xs)==16 and len({x['unit'] for x in xs})==8,'eight carriers both signs')
                    require(all({x['sign'] for x in xs if x['unit']==u}=={-1,1} for u in {x['unit'] for x in xs}),'paired +/- signs')
                else:require(len(xs)==84 and len({x['item'] for x in xs})==84,'84 earlier-layer items')
    if e=='E72':
        require({x['item'] for x in rows if x['cell']=='36'}=={x['item'] for x in rows if x['cell']=='40'},'matched earlier-layer items')

def carrier_rate(rows):
    """Resample carriers, retaining both signs and per-sign missingness."""
    units=sorted({x['unit'] for x in rows});a=[];n=[]
    for u in units:
        kept=[x['score'] for x in rows if x['unit']==u and x['score'] is not None]
        a.append(sum(kept));n.append(len(kept))
    a=np.array(a,float);n=np.array(n,float);ix=np.random.default_rng(20261027).integers(0,len(units),(2000,len(units)))
    den=n[ix].sum(1);num=a[ix].sum(1)
    return dict(estimate=float(a.sum()/n.sum()) if n.sum() else None,
                CI95=None if (den==0).any() else np.quantile(num/den,[.025,.975]).tolist(),
                carriers=len(units),kept=int(n.sum()),UNPARSEABLE=len(rows)-int(n.sum()))

def analyze(rows,e):
    result={}
    for reader in (('oracle','nla') if e=='E70' else ('oracle',)):
        groups={}
        for x in rows:
            if x['reader']==reader:groups.setdefault(x['row']+':'+x['cell'],[]).append(x)
        rates={}
        for k,xs in sorted(groups.items()):
            r=stats({x['id']:x['score'] for x in xs});r['truncation_rate']=sum(x['truncated'] for x in xs)/len(xs)
            r['truncation_over_10_percent']=r['truncation_rate']>.10
            if e=='E70':r['carrier_bootstrap']=carrier_rate(xs)
            else:r['S_at_least_point20']=None if r['estimate'] is None else round(r['estimate'],12)>=.20
            rates[k]=r
        if e=='E70':
            control=rates['prose_sentiment:1']['estimate'];state=[v['estimate'] for k,v in rates.items() if not k.startswith('prose_sentiment:')]
            verdict='NOT MET' if (control is not None and round(control,12)<.30) or any(v is not None and round(v,12)>.10 for v in state) else 'NOT EVALUABLE' if control is None or None in state else 'MET'
            result[reader]=dict(rates=rates,R_D1=verdict,control_pass=None if control is None else round(control,12)>=.30,
                 falsifier=True if any(v is not None and round(v,12)>=.20 for v in state) else None if None in state else False)
        else:result[reader]=dict(rates=rates,status='DESCRIPTIVE; off-distribution source blocks36/40, unchanged Oracle44 prompt')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('experiment',choices=['E70','E72']);p.add_argument('mode',choices=['blind','analyze']);a=p.parse_args()
    commit=committed();s=read(HERE/(a.experiment+'.json'))
    if a.mode=='blind':export(collect(s),s['blind'],s['private'],s['output_sha256'],commit)
    else:
        rows,jsha=load_codes(s);validate(rows,a.experiment)
        if a.experiment=='E70':require(sha(s['diagnostics'])==s['diagnostics_sha256'],'sealed dose diagnostics')
        out=claim(s,commit);write(out/'RESULTS.json',analyze(rows,a.experiment))
        write(out/'REDACTION_SENSITIVITY.json',analyze([dict(x,score=None if x['redacted'] else x['score']) for x in rows],a.experiment))
        if a.experiment=='E70':write(out/'DIAGNOSTICS.json',read(s['diagnostics']))
        write(out/'SCORED_ITEMS.json',rows)
        seal(out,'ANALYSIS_SEAL.json',experiment=a.experiment,status='COMPLETE_ONCE',code_commit=commit,
             output_seal_sha256=s['output_sha256'],judgment_seal_sha256=jsha)

if __name__=='__main__':main()
