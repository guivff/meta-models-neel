"""R2-B input preparation, audit and transfer CLI.

Live model execution deliberately requires a separate certified execution plan;
preparation/audit/release utilities never imply that that plan exists.
"""
from __future__ import annotations
import argparse,json,os,signal,subprocess,sys,time
from pathlib import Path
from projects.g_agreement.r_bench import remainder_r2b as D,remainder_r2b_runner as R,remainder_r2b_prepare as P


def load(path):return json.loads(Path(path).read_text())


def atomic_json(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.partial')
    temp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n');temp.replace(path)


def verify_files(root,files):
    root=Path(root).resolve()
    for name,want in files.items():
        p=(root/name).resolve()
        if not p.is_relative_to(root):raise ValueError(f'Unsafe member: {name}')
        if not p.is_file() or R.sha(p)!=want:raise ValueError(f'Missing/changed member: {name}')


def mac_receipt(package,manifest,pod,volume):
    package=Path(package);verify_files(package,manifest['compact_files'])
    actual={str(p.relative_to(package)) for p in package.rglob('*') if p.is_file()}
    if actual!=set(manifest['compact_files']):raise ValueError(f'Mac package inventory differs: {sorted(actual^set(manifest["compact_files"]))}')
    return dict(pod=pod,network_volume_id=volume,volume_manifest_sha256=D.digest(manifest),
                compact_files=manifest['compact_files'],verified_on='Mac')


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    a=sub.add_parser('certify');a.add_argument('--manifest',required=True);a.add_argument('--prereg-commit',required=True);a.add_argument('--registration',required=True)
    a=sub.add_parser('prepare-slice');a.add_argument('--main-selection',required=True);a.add_argument('--taught-selection',required=True);a.add_argument('--states',required=True);a.add_argument('--assets',required=True);a.add_argument('--depth',type=int,required=True);a.add_argument('--git-sha',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('measure');a.add_argument('--booking',required=True);a.add_argument('--run',required=True);a.add_argument('--host',required=True);a.add_argument('--port',type=int,required=True);a.add_argument('--identity',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('bootstrap');a.add_argument('--booking',required=True);a.add_argument('--run',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('prepare');a.add_argument('--bank',required=True);a.add_argument('--th3-csv',required=True);a.add_argument('--th3-manifest',required=True);a.add_argument('--states',required=True);a.add_argument('--inverter-union',required=True);a.add_argument('--n6-publication',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('collect');a.add_argument('--run',required=True);a.add_argument('--reader',choices=['source','olens','nla'],required=True);a.add_argument('--run-kind',choices=['real','smoke'],required=True);a.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    a=sub.add_parser('slice');a.add_argument('--run',required=True);a.add_argument('--run-kind',choices=['real','smoke'],required=True);a.add_argument('--worker',action='store_true',help=argparse.SUPPRESS)
    a=sub.add_parser('audit-process');a.add_argument('--process-dir',required=True)
    a=sub.add_parser('package');a.add_argument('--run',required=True);a.add_argument('--destination',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('mac-receipt');a.add_argument('--package',required=True);a.add_argument('--volume-manifest',required=True);a.add_argument('--pod',required=True);a.add_argument('--volume',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('release');a.add_argument('--run',required=True);a.add_argument('--volume-manifest',required=True);a.add_argument('--states-root',required=True);a.add_argument('--mac-receipt',required=True)
    a=ap.parse_args(argv)
    if a.command=='certify':
        from projects.g_agreement.r_bench import remainder_r2b_slice as S
        plan=load(a.manifest);S.validate_plan(plan)
        for filename,record in plan['input_files'].items():
            if R.sha(filename)!=record['sha256']:raise ValueError(f'Changed input: {filename}')
        # Operator has already pushed this commit; the prereg SHA is explicit.
        import re
        if not re.fullmatch('[0-9a-f]{40}',a.prereg_commit):raise ValueError(f'Invalid prereg commit: {a.prereg_commit}')
        plan['execution_reviewed']=True
        registration=dict(section=36,pushed_before_compute=True,prereg_commit=a.prereg_commit,manifest_sha256=D.digest(plan))
        atomic_json(a.manifest,plan);atomic_json(a.registration,registration)
        print('CERTIFIED CPU PLAN; assigned-pod guards and live smoke still required')
    elif a.command=='prepare-slice':
        from projects.g_agreement.r_bench import remainder_r2b_slice as S
        main=load(a.main_selection)['items'];taught=load(a.taught_selection)['items']
        taught=[dict(i,population='taught',recipe=i['arm']) for i in taught]
        items,files=P.bind_states(main+taught,a.states,layers=(44,))
        cells=S.capture_cells(items,a.depth);jobs,transfers=S.probe_jobs(cells,items)
        for filename in (a.main_selection,a.taught_selection,a.assets):
            files[str(Path(filename))]=dict(sha256=R.sha(filename),bytes=Path(filename).stat().st_size)
        result=dict(schema=2,scope='ablation_slice',cells=cells,probe_jobs=jobs,transfer_jobs=transfers,
            assets=load(a.assets),input_files=files,code_sha256=D.code_sha256(),git_sha=a.git_sha,
            execution_reviewed=False,decoder_depth=a.depth)
        atomic_json(a.out,result)
        print(json.dumps(dict(status='PREPARED',cells=len(cells),jobs=len(jobs),transfers=transfers,launch_ready=False)))
    elif a.command=='measure':
        from projects.g_agreement.r_bench.remainder_r2b_ops import measure_bandwidth
        print(json.dumps(measure_bandwidth(load(a.booking),a.run,a.host,a.port,a.identity,a.out)))
    elif a.command=='bootstrap':
        from projects.g_agreement.r_bench.remainder_r2b_ops import bootstrap
        Path(a.out).write_text(bootstrap(load(a.booking),a.run))
    elif a.command=='prepare':
        selection=P.main_selection(a.bank,a.th3_csv,a.th3_manifest)
        selection['items'],files=P.bind_states(selection['items'],a.states)
        rebuilt=P.join_rebuilt(selection['items'],a.inverter_union)
        n6=P.verify_n6(a.n6_publication)
        result=dict(schema=1,selection=selection,state_files=files,rebuilt=rebuilt,n6=n6,prepared_without_model_calls=True)
        atomic_json(a.out,result)
        print(json.dumps(dict(status='PREPARED',manifest_sha256=D.digest(result),launch_ready=False)))
    elif a.command in ('collect','slice'):
        if a.command=='slice':a.reader='olens'
        from projects.g_agreement.r_bench import remainder_r2b_engine as E
        guard=R.LiveGuard(a.run);guard()
        plan=guard.manifest
        if not plan.get('execution_reviewed') or not plan.get('code_sha256') or not plan.get('git_sha'):
            raise ValueError('Collection execution manifest has not passed review')
        if plan['code_sha256']!=D.code_sha256():raise ValueError('Execution code hash mismatch')
        if a.command=='slice':
            from projects.g_agreement.r_bench.remainder_r2b_slice import validate_plan
            validate_plan(plan)
        if not a.worker:
            command=[sys.executable,'-m','projects.g_agreement.r_bench.remainder_r2b_cli',a.command,
                     '--run',a.run,'--run-kind',a.run_kind,'--worker']
            if a.command=='collect':command+=['--reader',a.reader]
            env={k:v for k,v in os.environ.items() if not any(x in k.upper() for x in ('TOKEN','API_KEY','SECRET','PASSWORD'))}
            env.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1',XDG_CACHE_HOME=str(Path(a.run)/'runtime_cache'))
            p=subprocess.Popen(command,start_new_session=True,env=env)
            remaining=guard.booking['segment_deadline']-time.time()-guard.pull_reserve-30
            try:
                rc=p.wait(timeout=max(0,remaining))
            except BaseException as error:
                if p.poll() is None:
                    os.killpg(p.pid,signal.SIGTERM)
                    try:p.wait(timeout=10)
                    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
                if isinstance(error,subprocess.TimeoutExpired):raise ValueError('Collection hit reserved pull cutoff; retain partial outputs') from error
                raise
            if rc:raise ValueError(f'Collection worker failed: {rc}')
            return 0
        for filename,record in plan['input_files'].items():
            guard()
            if R.sha(filename)!=record['sha256']:raise ValueError(f'Changed input: {filename}')
        cells=[c for c in plan['cells'] if c['reader']==a.reader]
        process=D.stamp(guard.booking['pod'],plan['git_sha'],plan['code_sha256'],a.run_kind)
        engine=E.Engine(a.reader,plan['assets'],guard)
        if a.command=='slice':
            from projects.g_agreement.r_bench.remainder_r2b_pipeline import run_slice
            result=run_slice(plan,Path(a.run)/'outputs',process,engine,guard)
            print(json.dumps(result));return 0
        writer=R.RunWriter(Path(a.run)/'outputs',dict(cells=cells),process)
        files=E.execute_manifest(plan,a.reader,writer,engine,guard)
        print(json.dumps(dict(status='COLLECTED',process_dir=str(writer.root),files=len(files))))
    elif a.command=='audit-process':
        root=Path(a.process_dir);m=load(root/'volume_manifest.json');verify_files(root,m['files'])
        actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}-{'volume_manifest.json'}
        if actual!=set(m['files']):raise ValueError(f'Process inventory differs: {sorted(actual^set(m["files"]))}')
        process=load(root/'process.json')
        for row in P.lines(root/'rows.jsonl'):
            for k,v in process.items():
                if row.get(k)!=v:raise ValueError(f'Process stamp mismatch {k}: {row.get("cell")}')
        print(json.dumps(dict(status='VERIFIED',files=len(actual))))
    elif a.command=='package':
        from projects.g_agreement.r_bench.remainder_r2b_package import package
        result=package(a.run,a.destination);atomic_json(a.out,result);print(json.dumps(dict(files=len(result['files']),compact_files=len(result['compact_files']))))
    elif a.command=='mac-receipt':
        result=mac_receipt(a.package,load(a.volume_manifest),a.pod,a.volume)
        atomic_json(a.out,result);print('MAC VERIFIED')
    elif a.command=='release':
        guard=R.LiveGuard(a.run,science=False);guard()
        result=R.verified_release(guard.booking,load(a.mac_receipt),load(a.volume_manifest),a.states_root,guard,
                                  lambda r:atomic_json(Path(a.run)/'release.json',r))
        print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
