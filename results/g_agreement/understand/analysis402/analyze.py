"""Once-only scientific entry points after new-layout custody validation."""
import argparse
from blind import *
from analysis_io import j_inputs,probe_aucs,continuation_aucs,claim_once
from missingness import metrics,audit
from measures62 import behaviour_aucs
from oracle_rules import rules62,eval_measure

def load_config(path):
 command=read(HERE/'COMMANDS.json');require(sha(path)==command['specs'][path.name],'analysis config pin');verify(HERE,'SOURCE_SEAL.json',command['source_seal_sha256'])
 for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'analysis dependency '+n)
 return read(path)

def ladder_j(spec,data):
 root=Path(spec['j_input']);s=verify(root,'J_SEAL.json');require(s['capture_seal_sha256']==data['capture_seals'][spec['experiment']] and s['input_seal_sha256']==spec['input_seal_sha256'],'J capture/input');rows=read(root/'J_ROWS.json');require(set(rows)==set(probe_aucs(data)),'J/probe grid');return rows

def compute56(spec,data,jj,jrows):
 from missingness import native_rates
 from rules56_missing_g3 import rules
 sys.path.insert(0,str(U/'e56/r4_clarification'));from diagnostics import compute
 amendment=read(U/'e56/r4_clarification/ANALYSIS_SPEC.json');diag=compute(amendment['diagnostics']);probe=probe_aucs(data);rates=native_rates(data,jj);result=rules(probe,jrows,rates)
 for reader,v in result['readers'].items():
  for row,x in v['injection_rows'].items():x['diagnostics']=diag[row];x['evaluable']=x['evaluable'] and diag[row]['eligible'];x['pass_rule']=x['pass_rule'] and x['evaluable']
  eligible=sum(x['evaluable'] for x in v['injection_rows'].values());passes=sum(x['pass_rule'] for x in v['injection_rows'].values());v['R4']='NOT EVALUABLE' if not result['gates']['positive_controls'][reader] or eligible<4 else 'MET' if passes>=4 else 'NOT MET'
 result.update(R4_diagnostics=diag,R4_authority='f21ed03e section172 clarification1');return result,{'R4_DIAGNOSTICS.json':diag,'NATIVE_RATES.json':{'|'.join(k):v for k,v in rates.items()}}

def compute62(spec,data,jj,jrows,pdata=None,pjj=None):
 probe=probe_aucs(data);rates=metrics(data['private'],data['native'],jj);result=rules62(probe,rates,jrows);result['readers']['nla']={'status':'NOT RUN','authority':'402be5f0'}
 result.update(behaviour=behaviour_aucs(list(data['private'].values()),data['behaviour']),eval_ladder=eval_measure(list(data['private'].values()),data['native'],jj));result['eval_ladder']['nla']={'status':'NOT RUN'}
 available=[st for st,ok in result['R_L0'].items() if ok];result['behaviour']['R_L3']='NOT EVALUABLE' if len(available)<4 else 'MET' if sum(result['behaviour']['AUROC'][st]>=.80 for st in available)>=4 else 'NOT MET'
 if pdata is None:
  require(pjj is None,'no placebo judgments when E62P NOT RUN')
  result['E62P']={'status':'NOT RUN','reason':'NO_FIT','authority':'94a770cc(c)'}
  result['R_L5']={'oracle':{'verdict':'NOT EVALUABLE','reason':'E62P NOT RUN (NO_FIT)'},'nla':{'status':'NOT RUN'}}
  result.update(probe=probe,rates={'|'.join(k):v for k,v in rates.items()},J_rows=jrows)
  return result,{}
 prates=metrics(pdata['private'],pdata['native'],pjj);require(sha(spec['placebo_confound_check'])==spec['placebo_confound_check_sha256'],'ratified placebo construction check');result['placebo_confound_check']=read(spec['placebo_confound_check']);result['placebo_probe']=probe_aucs(pdata);result['placebo_rates']={'|'.join(k):v for k,v in prates.items()}
 differences={st:{r:None if rates['oracle',st+'_'+r]['S'] is None or prates['oracle',st+'_'+r+'p']['S'] is None else rates['oracle',st+'_'+r]['S']-prates['oracle',st+'_'+r+'p']['S'] for r in ('L2','L4')} for st in result['R_L0'] if result['R_L0'][st] and st!='S5'};passes=sum(all(v is not None and round(v,12)>=.2 for v in ds.values()) for ds in differences.values());result['R_L5']={'oracle':{'real_minus_placebo':differences,'passing_states':passes,'excluded_states':{'S5':'650138c5: |phi|=0.288675>0.2; retain data, exclude L4p from R-L5'},'verdict':'NOT EVALUABLE' if len(differences)<4 or any(v is None for ds in differences.values() for v in ds.values()) else 'MET' if passes>=4 else 'NOT MET','placebo_at_least_real_L4':{st:None if ds['L4'] is None else ds['L4']<=0 for st,ds in differences.items()}},'nla':{'status':'NOT RUN'}}
 result.update(probe=probe,rates={'|'.join(k):v for k,v in rates.items()},J_rows=jrows);return result,{}

def load_placebo(not_run):
 if not_run:return None,None
 ps=load_config(HERE/'E62P_SPEC.json');pdata=collect(ps,'E62P');return pdata,judgments(ps,pdata)

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);p.add_argument('--mode',choices=['verify','blind','analyze'],required=True);p.add_argument('--e62p-not-run',action='store_true');a=p.parse_args();spec=load_config(a.spec);e=spec['experiment'];require(not a.e62p_not_run or (e=='E62' and a.mode=='analyze'),'E62P flag only for E62 analysis');data=collect(spec,e)
 if a.mode=='verify':print(e+' VERIFIED_EXACT_UNION');return
 if a.mode=='blind':prepare(spec,e,data);print(e+' BLIND_PACKET_SEALED');return
 require(read(U/'e56/job/RULE_STATUS.json')['status']=='RESOLVED','shared rate definition resolved')
 require(read(U/'e56/job/RULE_STATUS.json')['status']=='RESOLVED','shared rate definition resolved')
 jj=judgments(spec,data);jrows=j_inputs(spec,data) if e in ('E56','E57') else ladder_j(spec,data) if e=='E62' else {} if e=='E62' else {}
 if e=='E62':pdata,pjj=load_placebo(a.e62p_not_run)
 # Reuse the original exclusive output directories: a legacy invocation blocks this one and vice versa.
 out=claim_once(spec['analysis_out'],e,sha(a.spec))
 try:
  extra={}
  if e=='E56':result,extra=compute56(spec,data,jj,jrows)
  elif e=='E57':
   from rules57_missing_g3 import compute
   require(set(data['plan']['rows'])==set(jrows),'complete E57 J rows');result,counts=compute(data,jj,jrows);extra['COUNTS.json']=counts
  elif e=='E62':result,extra=compute62(spec,data,jj,jrows,pdata,pjj)
  else:result={'probe':probe_aucs(data),'rates':{'|'.join(k):v for k,v in metrics(data['private'],data['native'],jj).items()},'NLA':'NOT RUN','purpose':'placebo cells; R-L5 evaluated in E62'}
  result['judgment_missingness']=audit(data['native'],jj);extra['UNPARSEABLE_COUNTS.json']=result['judgment_missingness']
  result.update(NLA_truncation=data['truncation'],acquisition_lineage=data['lineage']);dump(out/'RESULTS.json',result);dump(out/'PROBE.json',probe_aucs(data))
  if e in ('E56','E57'):dump(out/'CONTINUATION.json',continuation_aucs(data))
  for name,value in extra.items():dump(out/name,value)
  (out/'RESULTS.md').write_text('# '+e+' registered results\n\n'+json.dumps(result.get('readers',result.get('R_B',{})),indent=2)+'\n')
  seal(out,'ANALYSIS_SEAL.json',{'experiment':e,'status':'COMPLETE','cohort_id':COHORT,'source_seal_sha256':spec['source_seal_sha256'],'adapter_source_seal_sha256':sha(HERE/'SOURCE_SEAL.json'),'manifest_sha256':sha(spec['receipt'])})
 except BaseException as error:dump(out/'FAILURE.json',{'error':str(error)});raise
if __name__=='__main__':main()
