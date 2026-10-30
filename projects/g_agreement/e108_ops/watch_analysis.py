"""Wait for the complete E108 normalized seal, invoke the committed adapter once."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def inspect(spec_path, adapter):
    if not spec_path.exists():
        return 'WAITING_SPEC', None
    spec=json.loads(spec_path.read_text())
    output=Path(spec['output_seal'])
    if not output.exists():
        return 'WAITING_COMPLETE_BANK', spec
    value=json.loads(output.read_text())
    if value.get('status')!='COMPLETE':
        return 'WAITING_COMPLETE_BANK', spec
    assert sha(output)==spec['output_sha256'], 'normalized output seal hash'
    analysis=Path(spec['analysis'])
    if (analysis/'ANALYSIS_SEAL.json').exists():
        adapter.core.verify(analysis/'ANALYSIS_SEAL.json',sha(analysis/'ANALYSIS_SEAL.json'))
        return 'ALREADY_COMPLETE', spec
    assert not adapter.GUARD.exists(), 'once guard consumed without complete analysis; never replay'
    adapter.committed()
    adapter.inputs(spec)  # All source/privacy/full-inventory checks, no statistics or claim.
    return 'READY', spec


def publish(root, analysis, receipt_dir):
    # Publish only known CPU aggregate/receipt outputs; no source labels or joins.
    paths=[analysis,receipt_dir]
    now=datetime.datetime.now(datetime.timezone.utc).isoformat()
    for name in ['results/g_agreement/e108/HANDOFF.md','results/g_agreement/reviews/R-3/HANDOFF.md']:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('a') as f:
            f.write('\n## '+now+' — E108 analysis arrival\n\nI-3 watcher: committed once-only adapter completed; ANALYSIS_SEAL at '+str((analysis/'ANALYSIS_SEAL.json').relative_to(root))+'. Review on arrival; do not replay.\n')
        paths.append(p)
    assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=root,text=True).strip(), 'unrelated staged work'
    subprocess.run(['git','add',*[str(p.relative_to(root)) for p in paths]],cwd=root,check=True)
    diff=subprocess.check_output(['git','diff','--cached','--unified=0'],cwd=root,text=True)
    added='\n'.join(x[1:] for x in diff.splitlines() if x.startswith('+') and not x.startswith('+++'))
    assert not re.search(r'hf_|sk-|HF_TOKEN|api_key|Bearer|(?:\d{1,3}\.){3}\d{1,3}|root@',added,re.I), 'secret/host scan'
    subprocess.run(['git','commit','-m','Publish once-only E108 analysis and reviewer handoff'],cwd=root,check=True)
    for attempt in range(3):
        subprocess.run(['git','pull','--rebase','origin','r/blindspot'],cwd=root,check=True)
        pushed=subprocess.run(['git','push','origin','HEAD:r/blindspot'],cwd=root,capture_output=True,text=True)
        if pushed.returncode==0:return
        assert any(x in pushed.stderr for x in ['fetch first','non-fast-forward','cannot lock ref']),pushed.stderr
    raise RuntimeError('publication pending concurrent updates; analysis must not rerun')


def run(spec_path, adapter, execute=False, runner=None):
    state,spec=inspect(spec_path,adapter)
    if state!='READY' or not execute:
        return state,spec
    if runner is None:
        runner=lambda:subprocess.run([sys.executable,'-m','projects.g_agreement.e108_analysis.adapter','--spec',str(spec_path)],cwd=adapter.ROOT,check=True)
    runner()
    assert (Path(spec['analysis'])/'ANALYSIS_SEAL.json').is_file(), 'adapter did not seal; never retry claim'
    return 'COMPLETE_ONCE',spec


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--watch',action='store_true')
    p.add_argument('--publish',action='store_true');p.add_argument('--poll-seconds',type=float,default=10)
    a=p.parse_args();assert a.poll_seconds>=1 and (not a.publish or a.execute)
    from projects.g_agreement.e108_analysis import adapter
    while True:
        state,spec=run(a.spec,adapter,a.execute)
        if state in ('COMPLETE_ONCE','ALREADY_COMPLETE'):
            out=Path(spec['analysis']).resolve();root=adapter.ROOT
            assert out.is_relative_to(root/'results/g_agreement'), 'publish aggregate within shared results only'
            receipt_dir=root/'results/g_agreement/e108/analysis_execution';receipt_dir.mkdir(parents=True,exist_ok=True)
            receipt=receipt_dir/'RECEIPT.json'
            if not receipt.exists():
                first=out/'RESULTS.json';ns=first.stat().st_mtime_ns
                receipt.write_text(json.dumps(dict(experiment='E108',track='M',status=state,analysis_seal_sha256=sha(out/'ANALYSIS_SEAL.json'),first_output_utc=datetime.datetime.fromtimestamp(ns/1e9,datetime.timezone.utc).isoformat(),first_output_evidence=dict(member='RESULTS.json',sha256=sha(first),mtime_ns=ns),GPU_calls=0,judge_calls=0),indent=2)+'\n')
            if a.publish:publish(root,out,receipt_dir)
            print(json.dumps(dict(status=state)));return
        if not a.watch or state=='READY':
            print(json.dumps(dict(status=state)));return
        time.sleep(a.poll_seconds)


if __name__=='__main__':main()
