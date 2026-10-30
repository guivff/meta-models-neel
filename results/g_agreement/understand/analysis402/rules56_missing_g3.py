"""09494e79: adapter copy of sealed E56 rules; only null G3 gate handling changes."""
from analysis56 import IMPLICIT,TWINS,CONTROLS,require
from missingness import reported

def r1_gate(probes,j_rows):
    out={}
    for row in IMPLICIT:
        require(row in probes and row in j_rows,'missing separate J input or probe')
        p=probes[row];j=j_rows[row]['G3_AUROC'];require(0<=p<=1,'invalid probe metric')
        if j is None:
            out[row]={'probe':p,'J_G3':None,'pass':False,'status':'NOT EVALUABLE','reason':'missing frozen G3 (09494e79)'}
            continue
        require(0<=j<=1,'invalid gate metric')
        out[row]={'probe':p,'J_G3':j,'pass':p>=.90 and j<=.60}
    return out

def rules(probes,jrows,rates):
    r1=r1_gate(probes,jrows);eligible=[r for r in IMPLICIT if r1[r]['pass']]
    controls={r:sum(rates[r,c,'text']['S'] is not None and rates[r,c,'text']['S']>=.30 for c in CONTROLS)>=2 for r in ('oracle','nla')}
    fact=any(reported(rates[r,'fact_recall','text']) for r in ('oracle','nla'))
    out={'gates':{'positive_controls':controls,'fact_recall_shared':fact},'R1':r1,'readers':{}}
    for r in ('oracle','nla'):
        n=sum(reported(rates[r,row,'text']) for row in eligible)
        r2='NOT EVALUABLE' if not controls[r] or not fact or not eligible or any(rates[r,row,'text']['S'] is None for row in eligible) else ('MET' if n>=2 else 'NOT MET')
        diffs={b:None if rates[r,b,'text']['S'] is None or rates[r,a,'text']['S'] is None else rates[r,b,'text']['S']-rates[r,a,'text']['S'] for a,b in TWINS}
        r3='NOT EVALUABLE' if not controls[r] or any(v is None for v in diffs.values()) else ('MET' if sum(round(v,12)>=.30 for v in diffs.values())>=3 else 'NOT MET')
        inj={row:{'J':rates[r,row,'J']['S'],'nonJ':rates[r,row,'nonJ']['S']} for rr,row,arm in rates if rr==r and arm=='J'}
        for row,v in inj.items():v.update(evaluable=v['J'] is not None and v['nonJ'] is not None and v['J']>=.10,pass_rule=v['J'] is not None and v['nonJ'] is not None and v['J']>=.10 and v['nonJ']<=.25*v['J'])
        r4='NOT EVALUABLE' if not controls[r] or sum(v['evaluable'] for v in inj.values())<4 else ('MET' if sum(v['pass_rule'] for v in inj.values())>=4 else 'NOT MET')
        out['readers'][r]={'R2':r2,'R2_reporting_rows':n,'R3':r3,'asked_minus_implicit':diffs,'R4':r4,'injection_rows':inj}
    out['R2_falsifier']='NOT EVALUABLE' if not fact or not all(controls.values()) or not eligible or any(rates[r,row,'text']['S'] is None for r in controls for row in eligible) else all(rates[r,row,'text']['S']<=.10 for r in controls for row in eligible)
    return out
