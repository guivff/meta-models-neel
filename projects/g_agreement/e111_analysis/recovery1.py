"""One explicitly user-authorized recovery after unsaved plotting failure; no scientific changes."""
import argparse
from pathlib import Path
import tempfile
from . import adapter as a
c=a.core
FAILURE_SHA='7dd286dfa5da8b326ddd4ee8d57a2145a96851a802c157135b2a4ea29b46d768'
SPEC_SHA='8d495b00b415c2f42a6f3859fe59920a365be406f5ce1cbd4460123e1564d466'
GUARD=a.GUARD.with_name('RECOVERY1_ONCE.json')
OUT=a.GUARD.parent/'recovery1_analysis_once'


def validate_failure(failure_seal,original_guard):
    c.verify(failure_seal,FAILURE_SHA)
    failure=c.read(Path(failure_seal).parent/'FAILURE.json')
    c.require(c.sha(original_guard)==failure['guard_sha256'],'original consumed guard preserved')
    c.require(failure['status']=='FAILED_AFTER_GUARD_NO_SCIENTIFIC_RESULT_SAVED' and failure['original_output_files']==[],'only registered unsaved failure')


def plot_smoke(folder):
    # Synthetic fixtures only, before inputs and before recovery claim.
    a.contrast.figure({'rows':{r:{'estimate':.1,'CI95':[-.1,.3]} for r in a.contrast.ROWS}},folder/'contrast.png')
    from .analysis import EXPERIMENTS
    a.figure({'pooled_bins':[],'R_SL2':{e:{'bins':[]} for e in EXPERIMENTS}},folder/'bins.png')
    for f in ('contrast.png','bins.png'):c.require((folder/f).read_bytes().startswith(b'\x89PNG'),'plot smoke PNG')


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    commit=a.committed()
    for f,h in c.read(a.ROOT/'results/g_agreement/understand/e111/analysis/RECOVERY1_SOURCE_RECEIPT.json')['files'].items():
        c.require(c.sha(a.ROOT/f)==h,'recovery source receipt')
    failure=a.ROOT/'results/g_agreement/understand/e111/execution_failure_once/FAILURE_SEAL.json'
    validate_failure(failure,a.GUARD)
    c.require(not list((a.GUARD.parent/'analysis_once').iterdir()),'original failed output stays empty')
    c.require(c.sha(args.spec)==SPEC_SHA,'TrackQ11:19 verified final SPEC')
    with tempfile.TemporaryDirectory(prefix='e111-recovery-smoke-') as folder:plot_smoke(Path(folder))
    spec=c.read(args.spec);records,census,direct=a.inputs(spec)
    out=c.claim(dict(analysis=str(OUT),guard=str(GUARD),output_sha256=spec['binding_sha256']),commit)
    direct_result=a.contrast.analyze(direct)
    result=a.analyze(records);result['census']=census;result['R_SL0']=direct_result
    result['R_SL2']['E100_a'].update(status='EXCLUDED',reason=census['excluded_experiments']['E100_a'])
    result['execution_provenance']=dict(status='USER_AUTHORIZED_RECOVERY1',original_failure_seal_sha256=FAILURE_SHA,original_guard_preserved=True,scientific_rules_and_seeds_unchanged=True)
    # Persist completed statistics before plotting, so a rendering failure cannot lose them again.
    c.write(out/'RESULTS.json',result);c.write(out/'BINDING.json',spec)
    a.contrast.figure(direct_result,out/'SITE_VS_CARRIED.png');a.figure(result,out/'BINS.png')
    c.seal(out,'ANALYSIS_SEAL.json',experiment='E111',status='COMPLETE_ONCE_RECOVERY1',code_commit=commit,binding_sha256=spec['binding_sha256'],original_failure_seal_sha256=FAILURE_SHA)

if __name__=='__main__':main()
