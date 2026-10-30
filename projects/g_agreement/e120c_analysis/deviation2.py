"""§238 deviation 2: judge codes; leading-word extractor failed on bullets."""
import argparse
import hashlib
import subprocess
from pathlib import Path
from . import adapter as original
from .analysis import summarize, readings
from projects.g_agreement.understand.wmech2 import core as c
ROOT=original.ROOT
HERE=original.HERE
GUARD=original.GUARD.with_name('DEVIATION2_ONCE.json')
LABEL='E120c deviation 2 (judge codes; leading-word extractor failed on bullets)'
ORIGINAL_SEAL='ff768004e28b89410847c76b047d84877eab97e049eb11ef4247fc47cf253000'

def score(scored):
    value=scored['a']
    c.require(value is None or type(value) is bool,'original judge boolean/null')
    return value

def committed():
    for name,digest in c.read(HERE/'DEVIATION2_SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(ROOT/name)==digest and hashlib.sha256(subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)).hexdigest()==digest,'committed deviation 2 source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def main():
    p=argparse.ArgumentParser();p.add_argument('--original-binding',required=True);a=p.parse_args()
    commit=committed()
    old=Path(a.original_binding).resolve()
    c.require(old.parent==original.GUARD.parent/'analysis_once','canonical original result')
    c.verify(old.parent/'ANALYSIS_SEAL.json',ORIGINAL_SEAL)
    s=c.read(old)
    c.require(Path(s['analysis'])==old.parent,'original analysis custody')
    rows,baseline=original.inputs(s,judge_score=score)
    summary=summarize(rows);result=readings(summary)
    s=dict(s,analysis=str(original.GUARD.parent/'deviation2_analysis_once'))
    out=c.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    c.write(out/'RESULTS.json',dict(experiment='E120',part='c',deviation=2,label=LABEL,status='DESCRIPTIVE',arms=summary,readings=result,baseline=baseline,original_analysis_seal_sha256=ORIGINAL_SEAL,score_source='bank E120 E85 rubric a_model_self_evaluated; UNPARSEABLE/null is missing',caveat='Question prompt is outside the lens training distribution; thresholds and complete-coverage reading requirement unchanged'))
    c.write(out/'BINDING.json',s)
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E120',part='c',deviation=2,label=LABEL,status='COMPLETE_ONCE',code_commit=commit,original_analysis_seal_sha256=ORIGINAL_SEAL)
if __name__=='__main__':main()
