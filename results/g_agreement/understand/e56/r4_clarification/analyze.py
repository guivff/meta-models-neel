"""Supersedes the not-yet-run E56 command; same once-only output, added R4 eligibility."""
import argparse
from diagnostics import *
from analysis56 import rules,native_rates
from analysis_io import collect,judgments,j_inputs,probe_aucs,continuation_aucs,claim_once
from contract56 import dump,seal

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec);cmd=read(HERE/'ANALYSIS_COMMAND.json');require(sha(a.spec)==cmd['spec_sha256'],'amended spec pin')
 for name,digest in cmd['source_files'].items():require(sha(ROOT/name)==digest,'amended source pin')
 original=Path(s['original_spec']);require(sha(original)==s['original_spec_sha256'],'unchanged original spec');spec=read(original);verify(HERE.parent/'job','SOURCE_SEAL.json',spec['source_seal_sha256']);data=collect(spec,'E56');jj=judgments(spec,data);j=j_inputs(spec,data)
 out=claim_once(spec['analysis_out'],'E56',sha(a.spec))
 try:
  diag=compute(s['diagnostics']);probes=probe_aucs(data);rates=native_rates(data,jj);result=rules(probes,j,rates)
  for reader,v in result['readers'].items():
   for row,x in v['injection_rows'].items():
    x['diagnostics']=diag[row];x['evaluable']=x['evaluable'] and diag[row]['eligible'];x['pass_rule']=x['pass_rule'] and x['evaluable']
   eligible=sum(x['evaluable'] for x in v['injection_rows'].values());passes=sum(x['pass_rule'] for x in v['injection_rows'].values());v['R4']='NOT EVALUABLE' if not result['gates']['positive_controls'][reader] or eligible<4 else 'MET' if passes>=4 else 'NOT MET'
  result.update(R4_diagnostics=diag,NLA_truncation=data['truncation'],acquisition_lineage=data['lineage'],R4_authority='f21ed03e section172 clarification1')
  dump(out/'RESULTS.json',result);dump(out/'R4_DIAGNOSTICS.json',diag);dump(out/'NATIVE_RATES.json',{'|'.join(k):v for k,v in rates.items()});dump(out/'CONTINUATION.json',continuation_aucs(data));dump(out/'PROBE.json',probes)
  (out/'RESULTS.md').write_text('# E56 registered results\n\n'+ '\n'.join(r+': '+', '.join(k+' '+v[k] for k in ('R2','R3','R4')) for r,v in result['readers'].items())+'\n\nR4 information/distribution exclusions applied before verdict; diagnostics include all injected vectors.\n');seal(out,'ANALYSIS_SEAL.json',{'experiment':'E56','status':'COMPLETE','source_seal_sha256':spec['source_seal_sha256'],'amended_command_sha256':sha(HERE/'ANALYSIS_COMMAND.json')})
 except BaseException as e:dump(out/'FAILURE.json',{'error':str(e)});raise
if __name__=='__main__':main()
