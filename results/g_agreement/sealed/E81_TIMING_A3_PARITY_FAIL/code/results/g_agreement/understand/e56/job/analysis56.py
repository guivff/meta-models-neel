"""E56 once-only registered analysis; §172 clarification2 (3ada24fb)."""
import argparse
from pathlib import Path
from contract56 import *
from stats_native import rate,signed_value,reported
from analysis_io import collect,judgments,j_inputs,probe_aucs,continuation_aucs,claim_once
IMPLICIT=['tense_implicit','linewrap_implicit','language_continuation','adjective_implicit','anomaly_state']
TWINS=[('tense_implicit','tense_asked'),('linewrap_implicit','linewrap_asked'),('language_continuation','language_report'),('adjective_implicit','adjective_asked')]
CONTROLS=['reasoning_bridge','rhyme_plan','instructed_focus']

def r1_gate(probes,j_rows):
    out={}
    for row in IMPLICIT:
        require(row in probes and row in j_rows,'missing separate J input or probe')
        p=probes[row];j=j_rows[row]['G3_AUROC'];require(0<=p<=1 and 0<=j<=1,'invalid gate metric')
        out[row]={'probe':p,'J_G3':j,'pass':p>=.90 and j<=.60}
    return out

def native_rates(data,jj):
    grouped={}
    for x in data['native']:
        kind=x['kind'];label=data['private'][x['unit_id']]['label'] if kind=='text' else int(x['direction_id'].endswith(':A'))
        key=(x['reader'],x['feature'],x.get('arm','text'));units=grouped.setdefault(key,{})
        units.setdefault(x['unit_id'],{})[x['repeat']]=signed_value(jj[x['id']],label)
    return {key:rate([[v[i] for i in range(1)] for _,v in sorted(units.items())]) for key,units in grouped.items()}

def rules(probes,jrows,rates):
    r1=r1_gate(probes,jrows);eligible=[r for r in IMPLICIT if r1[r]['pass']]
    controls={r:sum(rates[r,c,'text']['S']>=.30 for c in CONTROLS)>=2 for r in ('oracle','nla')}
    fact=any(reported(rates[r,'fact_recall','text']) for r in ('oracle','nla'))
    out={'gates':{'positive_controls':controls,'fact_recall_shared':fact},'R1':r1,'readers':{}}
    for r in ('oracle','nla'):
        n=sum(reported(rates[r,row,'text']) for row in eligible)
        r2='NOT EVALUABLE' if not controls[r] or not fact or not eligible else ('MET' if n>=2 else 'NOT MET')
        diffs={b:rates[r,b,'text']['S']-rates[r,a,'text']['S'] for a,b in TWINS}
        r3='NOT EVALUABLE' if not controls[r] else ('MET' if sum(round(v,12)>=.30 for v in diffs.values())>=3 else 'NOT MET')
        inj={row:{'J':rates[r,row,'J']['S'],'nonJ':rates[r,row,'nonJ']['S']} for rr,row,arm in rates if rr==r and arm=='J'}
        for row,v in inj.items():v.update(evaluable=v['J']>=.10,pass_rule=v['J']>=.10 and v['nonJ']<=.25*v['J'])
        r4='NOT EVALUABLE' if not controls[r] or sum(v['evaluable'] for v in inj.values())<4 else ('MET' if sum(v['pass_rule'] for v in inj.values())>=4 else 'NOT MET')
        out['readers'][r]={'R2':r2,'R2_reporting_rows':n,'R3':r3,'asked_minus_implicit':diffs,'R4':r4,'injection_rows':inj}
    out['R2_falsifier']='NOT EVALUABLE' if not fact or not all(controls.values()) or not eligible else all(rates[r,row,'text']['S']<=.10 for r in controls for row in eligible)
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();spec=read(a.spec)
    require(sha(a.spec)==read(HERE/'ANALYSIS_COMMAND.json')['spec_sha256'],'committed analysis spec identity')
    require(read(HERE/'RULE_STATUS.json')['status']=='RESOLVED','rule hold')
    verify(HERE,'SOURCE_SEAL.json',spec['source_seal_sha256'])
    data=collect(spec,'E56');jj=judgments(spec,data);j=j_inputs(spec,data)
    out=claim_once(spec['analysis_out'],'E56',sha(a.spec))
    try:
        probes=probe_aucs(data);rates=native_rates(data,jj);result=rules(probes,j,rates);result['NLA_truncation']=data['truncation'];result['acquisition_lineage']=data['lineage']
        dump(out/'RESULTS.json',result);dump(out/'NATIVE_RATES.json',{'|'.join(k):v for k,v in rates.items()});dump(out/'CONTINUATION.json',continuation_aucs(data));dump(out/'PROBE.json',probes)
        text='# E56 registered results\n\nPrediction: R1 transfers on tense, line-wrap and continuation-language; R2 not met for Oracle, marginal for NLA; R3 both; R4 Oracle.\n\n'
        for reader,v in result['readers'].items():text+=reader+': '+', '.join(k+' '+v[k] for k in ('R2','R3','R4'))+'.\n\n'
        text+='Gates were applied first. Signed rate and whole-item bootstrap follow §172 clarification2. Injection has two direction units per row, never40 independent items. See RESULTS.json for every row and gate.\n'
        (out/'RESULTS.md').write_text(text);seal(out,'ANALYSIS_SEAL.json',{'experiment':'E56','status':'COMPLETE','source_seal_sha256':spec['source_seal_sha256']})
    except BaseException as error:
        dump(out/'FAILURE.json',{'error':str(error)});raise
if __name__=='__main__':main()
