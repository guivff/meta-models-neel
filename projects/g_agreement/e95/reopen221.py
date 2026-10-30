"""Once-only §221 reevaluation: only labelled validator-corrected E87 seals."""
import argparse
import json
import os
from pathlib import Path
from projects.g_agreement.e95.reopen220 import discover,evaluate


def check(root):
    analysis,depth=discover(root,corrected=True)
    result=evaluate(analysis,depth)
    result['authority']='§221 item2 / f60fd54f; §220 /9c56f1a5'
    result['input_version']='validator-corrected (E87 deviation 1)'
    if result['status']=='WAITING_E87_ANALYSIS_SEAL':
        result['status']='WAITING_CORRECTED_E87_ANALYSIS_SEAL'
    if result['status']=='WAITING_E87_DEPTH_SEAL':
        result['status']='WAITING_CORRECTED_E87_DEPTH_SEAL'
    if analysis:result['analysis_seal_path']=str(analysis.relative_to(root))
    if depth:result['depth_seal_path']=str(depth.relative_to(root))
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    result=check(a.root);a.out.mkdir(parents=True,exist_ok=True)
    path=a.out/('WATCH_STATUS.json' if result['status'].startswith('WAITING') else 'GATE_DECISION.json')
    if result['status'].startswith('WAITING'):path.write_text(json.dumps(result,indent=2)+'\n')
    elif path.exists():assert json.loads(path.read_text())==result,'corrected gate already decided; no replay'
    else:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
        with os.fdopen(fd,'w') as f:f.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
