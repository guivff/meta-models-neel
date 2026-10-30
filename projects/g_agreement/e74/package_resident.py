"""Freeze and test exact E74 resident runtime bytes on CPU; never launch it."""
import argparse
import gzip
import hashlib
import io
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import time
from . import ops, resident, smoke50, stage
from .package_smoke import secret_or_private_json


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--python',type=Path,required=True)
    p.add_argument('--version',choices=['v1','v2','v3','v4','v5','v6','v6-c7'],default='v6-c7')
    a=p.parse_args();root=a.root.resolve();r=root/'results/g_agreement/e74'
    names=['ops.py','hardware.py','stage.py','archive_stage.py','resident.py','smoke.py','smoke50.py','prepare_smoke50.py',
           'test_operator.py','test_hardware.py','test_smoke.py','test_smoke50.py']
    members={'projects/g_agreement/e74/'+n:(root/'projects/g_agreement/e74'/n).read_bytes() for n in names}
    extra={'inputs/fixtures.json':'staging/smoke50/fixtures.json','inputs/INPUT_SEAL.json':'staging/smoke50/INPUT_SEAL.json',
           'inputs/items.input.jsonl':'staging/items.input.jsonl','inputs/READER_PLAN.json':'operator/cpu_input/READER_PLAN.json',
           'runtime/olens_glm53_usage.py':'evidence/olens_glm53_usage.py',
           'runtime/vllm_metamodels_glm53_b26f02d.tar.gz':'evidence/vllm_metamodels_glm53_b26f02d.tar.gz',
           'assets/WEIGHT_MANIFEST.json':'WEIGHT_MANIFEST.json','assets/TRANSFER_MANIFEST.json':'operator/TRANSFER_MANIFEST.json'}
    members.update({name:(r/path).read_bytes() for name,path in extra.items()})
    smoke50.load_inputs(r/extra['inputs/fixtures.json'],r/extra['inputs/INPUT_SEAL.json'])
    items=resident.load_items(r/'staging/items.input.jsonl')
    reader_sha=ops.sha(r/'operator/cpu_input/READER_PLAN.json')
    resident.read_plan(r/'operator/cpu_input/READER_PLAN.json',reader_sha,items)
    selected=stage.selected(ops.bound(r/'ASSET_FILE_MANIFEST.json',stage.ASSET_SHA))
    projected=[{k:e[k] for k in ('area','path','size_bytes','identity','resolve_url')} for e in selected]
    transfer=ops.bound(r/'operator/TRANSFER_MANIFEST.json',stage.TRANSFER_SHA)
    ops.require(transfer['files']==projected,'transfer projection differs')
    for name,raw in members.items():
        if name.endswith('.json'):ops.require(not secret_or_private_json(json.loads(raw)), 'forbidden JSON key in package')
        if name.endswith('.jsonl'):
            for line in raw.splitlines():ops.require(set(json.loads(line))=={'id','ids','read_position'}, 'non-label-free item')
    source={'status':'E74_RESIDENT_SOURCE_FROZEN','fixture_sha256':smoke50.FIXTURE_SHA,
            'files':{name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(members.items())}}
    source_bytes=ops.encoded(source);source_sha=hashlib.sha256(source_bytes).hexdigest()
    members['SOURCE_SEAL.json']=source_bytes
    checks=[];start=time.monotonic();started=ops.utc()
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(prefix='e74-resident-exact-') as td:
        td=Path(td);archive=td/('e74-resident-'+a.version+'.tar.gz')
        with archive.open('xb') as f,gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as gz,tarfile.open(fileobj=gz,mode='w') as tar:
            for name,raw in sorted(members.items()):
                m=tarfile.TarInfo(name);m.size=len(raw);m.mode=0o600;tar.addfile(m,io.BytesIO(raw))
        ops.require(archive.stat().st_size<=20_000_000 and sum(map(len,members.values()))<=20_000_000,'archive cap exceeded')
        # Exercise the actual timed extraction/receipt producer, then run the
        # tests from the extracted package, with no repository imports.
        from .archive_stage import stage as unpack
        exact=td/'exact';unpack(archive,ops.sha(archive),exact,time.time(),source_sha)
        commands=[['-m','projects.g_agreement.e74.smoke50','--preflight','--fixtures','inputs/fixtures.json','--input-seal','inputs/INPUT_SEAL.json'],
                  ['-c',"from projects.g_agreement.e74 import resident as r,ops; from pathlib import Path; x=r.load_items(Path('inputs/items.input.jsonl')); p=Path('inputs/READER_PLAN.json'); assert len(r.read_plan(p,ops.sha(p),x))==6804; print('PASS frozen14184inputs/6804readerIDs; no labels; CPU only')"],
                  ['-m','unittest','projects.g_agreement.e74.test_operator','projects.g_agreement.e74.test_hardware','projects.g_agreement.e74.test_smoke50','projects.g_agreement.e74.test_smoke','-v']]
        for command in commands:
            run=subprocess.run([str(a.python),*command],cwd=exact,env=env,capture_output=True,text=True,timeout=60)
            checks.append({'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
            if run.returncode:raise RuntimeError(json.dumps(checks[-1]))
        # CPU-only probe tests use repository-local existing mats sources; not
        # shipped to the pod. They do not need captures or labels from E74.
        run=subprocess.run([str(a.python),'-m','unittest','projects.g_agreement.e74.test_cpu_intake','projects.g_agreement.e74.test_pull_capture','-v'],cwd=root,env=env,capture_output=True,text=True,timeout=60)
        checks.append({'command':['-m','unittest','projects.g_agreement.e74.test_cpu_intake','projects.g_agreement.e74.test_pull_capture','-v'],'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
        if run.returncode:raise RuntimeError(json.dumps(checks[-1]))
        final=r/('staging/e74-resident-'+a.version+'.tar.gz')
        with final.open('xb') as f:f.write(archive.read_bytes())
    out=r/('operator/resident-'+a.version);out.mkdir(parents=True,exist_ok=False)
    (out/'SOURCE_SEAL.json').write_bytes(source_bytes)
    cpu_files=['projects/g_agreement/e74/'+x for x in ['cpu_intake.py','test_cpu_intake.py','pull_capture.py','test_pull_capture.py','package_resident.py']]
    cpu_files+=['external/mats-nla-workspace/src/mats/probes.py','external/mats-nla-workspace/src/mats/metrics.py']
    ops.write(out/'CPU_SOURCE_SEAL.json',{'files':{x:ops.sha(root/x) for x in cpu_files},'label':'CPU_ONLY_NOT_POD_PAYLOAD'})
    receipt={'status':'PASS_CPU_ONLY','started_utc':started,'finished_utc':ops.utc(),'seconds':time.monotonic()-start,
             'checks':checks,'gpu_calls':0,'model_weight_download_bytes':0,'actual_author_engine_tested':False,
             'tests_passed':sum(int(m[1]) for c in checks for m in re.finditer(r'Ran (\d+) tests',c['stderr'])),
             'source_seal_sha256':source_sha}
    ops.write(out/'CPU_TESTS.json',receipt)
    ops.write(out/'PACKAGE.json',{'status':'CPU_TESTED_NOT_ADMITTED','archive':{'path':str(final),'bytes':final.stat().st_size,'sha256':ops.sha(final)},
              'source_seal_sha256':source_sha,'cpu_test_receipt_sha256':ops.sha(out/'CPU_TESTS.json'),
              'reader_plan_sha256':reader_sha,'fixture_sha256':smoke50.FIXTURE_SHA,'port_seal_sha256':resident.PORT_SHA,
              'members':{name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(members.items())},
              'replaces_operationally':'standalone smoke50 archive1c8aea3c preserved unchanged; it cannot continue resident',
              'authorises_launch':False,'contains_labels':False,'wild_content_publicly_redistributed':False})
    print(json.dumps({'status':'PASS_CPU_ONLY','archive_sha256':ops.sha(final),'source_seal_sha256':source_sha,'bytes':final.stat().st_size}))


if __name__=='__main__':main()
