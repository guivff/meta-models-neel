"""Deterministic source/input archives and fresh-extract CPU import rehearsal."""
import argparse,ast,gzip,hashlib,io,json,os,subprocess,tarfile,tempfile
from pathlib import Path
from projects.g_agreement.e96.reconstructor_check import digest,write


def archive(path,paths):
    with path.open('wb') as raw:
        with gzip.GzipFile(fileobj=raw,mode='wb',mtime=0) as z:
            with tarfile.open(fileobj=z,mode='w') as tf:
                for p in sorted(paths):
                    data=p.read_bytes();info=tarfile.TarInfo(str(p));info.size=len(data);info.mode=0o644;info.mtime=0;tf.addfile(info,io.BytesIO(data))


def package(out,python,receipt):
    if out.exists():raise FileExistsError(out)
    out.mkdir(parents=True)
    paths=sorted(Path('projects/g_agreement/e106').glob('*.py'))
    paths += [Path('projects/g_agreement/e96')/n for n in ['reconstructor_check.py','prepare_smoke_inputs.py']]
    paths += sorted(Path('external/mats-nla-workspace/src/mats').rglob('*.py'))
    paths += [Path('results/g_agreement/understand/e76/common76.py')]
    source=out/'source.tar.gz';archive(source,paths)
    inputs=out/'arm_p_and_gate_inputs.tar.gz';archive(inputs,sorted(Path('cache/g_agreement/e106/inputs_v1').iterdir()))
    train=out/'t_dev_selection.tar.gz';archive(train,sorted(Path('cache/g_agreement/e106/t_dev_v1').iterdir()))
    with tempfile.TemporaryDirectory(prefix='e106-exact-') as t:
        root=Path(t).resolve()
        with tarfile.open(source) as tf:
            for member in tf.getmembers():
                p=root/member.name
                if not p.resolve().is_relative_to(root) or not member.isfile():raise ValueError('archive path')
                data=tf.extractfile(member).read()
                if hashlib.sha256(data).hexdigest()!=digest(member.name):raise ValueError('source archive bytes')
                ast.parse(data,filename=member.name);p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
        env=dict(os.environ,PYTHONPATH=str(root)+':'+str(root/'external/mats-nla-workspace/src'),PYTHONPYCACHEPREFIX=str(root/'bytecode'))
        code="import pathlib,torch,peft,transformers;import mats.readers.nla,mats.readers.olens;import projects.g_agreement.e106.worker as w;import projects.g_agreement.e106.prepare;import projects.g_agreement.e106.prepare_t;import projects.g_agreement.e106.bind_baseline;import projects.g_agreement.e106.prepare_eval;import projects.g_agreement.e106.production;import projects.g_agreement.e106.finalize_t;assert pathlib.Path(w.__file__).resolve().is_relative_to(pathlib.Path.cwd());print('Exact imports PASS; torch='+torch.__version__+'; peft='+peft.__version__+'; transformers='+transformers.__version__)"
        commands=[[str(python),'-c',code],[str(python),'-m','projects.g_agreement.e106.worker','--help'],[str(python),'-m','unittest','projects.g_agreement.e106.test_worker','projects.g_agreement.e106.test_production','projects.g_agreement.e106.test_eval']]
        results=[]
        for cmd in commands:
            r=subprocess.run(cmd,cwd=root,env=env,capture_output=True,text=True)
            results.append({'command':cmd[1:],'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr})
            if r.returncode:raise RuntimeError('fresh extract rehearsal failed: '+r.stderr)
    write(receipt,{'status':'EXACT_SOURCE_ARCHIVE_CPU_IMPORTS_AND_TESTS_PASS_NO_GPU','archives':{p.name:{'path':str(p.resolve()),'sha256':digest(p)} for p in [source,inputs,train]},'source_files':{str(p):digest(p) for p in paths},'rehearsal':results,'gpu_models_loaded':False,'first_output_utc':None})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('out','python','receipt'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();package(**vars(a))
