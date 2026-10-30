"""Administrative complete-only E98 closeout; never launches or analyzes a worker."""
from pathlib import Path
import argparse,datetime,decimal,hashlib,json,math,os,shutil,subprocess,sys,tarfile
sys.path.insert(0,str(Path.cwd()/'projects/g_agreement/ops'))
import i5_controller as C
import i5_e98_reader_controller as E
RUN=Path('/Users/guivff/repl/activation-readers-i5/e98-reader-20261029-a1')
BASE=Path('results/g_agreement')

def validate_records(seal,records,plan,state):
    E.complete_grid(seal,records,plan,state)
    if seal['status']!='COMPLETE' or len(records)!=2184:raise ValueError('Complete full bank only')
    if {x['id'] for x in records}!=set(plan['item_ids']):raise ValueError('Exact native IDs')
    for x in records:
        if not isinstance(x['text'],str) or not isinstance(x['tokens'],list) or len(x['tokens'])>128:raise ValueError('Frozen greedy128 schema')

def main():
    receipt=BASE/'understand/e98/I5_READER_COMPLETE_CLOSEOUT.json'
    if receipt.exists():raise ValueError('Closeout already exists; never replay')
    state=C.read(RUN/'STATE.json');plan=C.read(RUN/'PLAN.json')
    old=[json.loads(l)for l in(BASE/'compute.jsonl').read_text().splitlines()]
    if any(x.get('event')=='pod_billed'and x.get('pod_id')==state['pod_id']for x in old):raise ValueError('Pod already booked; finish partial publication manually')
    # These reads fail before any mutation if the existing controller is still working.
    closed=C.read(RUN/'CLOSED.json');result=C.read(RUN/'RESULT.json');clean=C.read(RUN/'CLEANUP.json');adm=C.read(RUN/'MEASURED_PRODUCTION.json')
    assert result['status']=='COMPLETE'and result['completed_items']==2184
    assert closed['provider_query_null']and closed['archive_verified']and clean['inputs_absent']
    assert C.pod(state['pod_id'])is None
    assert adm['pod_id']==state['pod_id']and adm['createdAt']==state['createdAt']
    assert adm['cap_seconds']==math.ceil(adm['max_measured_setup_seconds']+1.25*adm['measured_work_seconds'])
    assert state['deadline_epoch']==adm['deadline_epoch']==state['created_epoch']+adm['cap_seconds']
    assert adm['first_native_sample_retained']and adm['native_items']==2184
    assert adm['admitted_epoch']<=state['created_epoch']+900
    assert closed['charged_seconds_upper']+plan['prior_gpu_seconds']<=36000
    assert all(C.sha(RUN/n)==h for n,h in plan['operator_hashes'].items())
    assert all(C.sha(RUN/n)==h for n,h in plan['payload_hashes'].items())
    archive=RUN/'final.pax.tar.gz';assert C.sha(archive)==result['archive_sha256']
    root=Path('cache/g_agreement/understand/e98/reader_native_complete');root.mkdir(parents=True,exist_ok=True);os.chmod(root,0o700)
    hashes={};times={}
    with tarfile.open(archive,'r|gz')as t:
        for m in t:
            if not m.isfile():continue
            assert not Path(m.name).is_absolute()and '..'not in Path(m.name).parts
            data=t.extractfile(m).read();d=root/m.name;d.parent.mkdir(parents=True,exist_ok=True);os.chmod(d.parent,0o700);d.write_bytes(data);os.chmod(d,0o600)
            hashes[m.name]=hashlib.sha256(data).hexdigest();mt=m.pax_headers.get('mtime',str(m.mtime));times[m.name]=dict(path=m.name,pax_mtime=mt,mtime_ns=int(decimal.Decimal(mt)*1000000000))
    seal=C.read(root/'out/OUTPUT_SEAL.json')
    assert {n[4:]for n in hashes if n.startswith('out/')and n!='out/OUTPUT_SEAL.json'}==set(seal['files'])
    assert all(hashes['out/'+n]==h for n,h in seal['files'].items())
    records=[C.read(f)for f in(root/'out/records').glob('*.json')];validate_records(seal,records,plan,state)
    assert hashes['out/GO.json']==plan['payload_hashes']['GO.json']
    assert C.read(root/'out/MEASURED_PRODUCTION.json')==adm
    ass=C.read(root/'out/ASSIGNMENT.json');assert ass['cap_seconds']==adm['cap_seconds']and ass['deadline_epoch']==adm['deadline_epoch']
    hardware=C.read(root/'HARDWARE.json');assert hardware['count']==1 and ('H100'in hardware['cuda_name']or'H200'in hardware['cuda_name'])
    first=min((v for n,v in times.items()if n.startswith('out/records/')),key=lambda v:v['mtime_ns'])
    assert first['mtime_ns']==seal['first_output_evidence']['mtime_ns']
    launch=C.read(BASE/'understand/e98/I5_READER_MEASURED_LAUNCH_RECEIPT.json');assert first['mtime_ns']==launch['first_output_evidence']['mtime_ns']
    E.retire_stock(RUN)
    for role in ['hardstop','backstop']:
        x=subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+C.label(RUN,role)],capture_output=True)
        assert x.returncode!=0,'Owned provider guard service not retired'
    public=BASE/'sealed/E98_READER_NATIVE_COMPLETE';assert not(public/'SEAL.json').exists()
    public.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'out',public/'outputs',dirs_exist_ok=True)
    code=public/'code';code.mkdir(exist_ok=True)
    with tarfile.open(RUN/'source.tar.gz')as t:
        for m in t:
            if not m.isfile():continue
            assert not Path(m.name).is_absolute()and'..'not in Path(m.name).parts
            d=code/'exact_source'/m.name;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(t.extractfile(m).read())
    assert C.sha(code/'exact_source/projects/g_agreement/e98/worker.py')==plan['worker_sha256']
    for n in plan['operator_hashes']:
        d=code/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(RUN/n,d)
    shutil.copy2(RUN/'timing_worker.py',code/'timing_worker.py');shutil.copy2(__file__,code/'closeout.py')
    for n in ['STATE.json','PLAN.json','CLOSED.json','RESULT.json','CLEANUP.json','ASSIGNMENT.json','WORKER_STARTED.json','MEASURED_PRODUCTION.json','hardstop.ready.json','backstop.ready.json','final.pax.tar.gz.receipt.json']:
        shutil.copy2(RUN/n,public/n)
    for n in ['worker.log','HARDWARE.json']:shutil.copy2(root/n,public/n)
    now=datetime.datetime.now(datetime.timezone.utc).isoformat();hours=closed['charged_seconds_upper']/3600;gpu=hours*closed['rate'];cost=math.ceil((gpu+2)*100)/100
    firstutc=datetime.datetime.fromtimestamp(first['mtime_ns']/1e9,datetime.timezone.utc).isoformat()
    row=dict(timestamp_utc=now,experiment='E98',track='F',pool='parked',event='pod_billed',phase='native_reader',pod_id=state['pod_id'],gpu_type=state['gpu_type'],GPU_hours=hours,gpu_usd_upper=gpu,conservative_extras_usd=2,all_in_usd_upper=cost,status='COMPLETE',native_test_items=2184,first_output_utc=firstutc,first_output_evidence=first,reservation_released_usd=49.61,provider_query_null=True)
    cut=datetime.datetime.fromisoformat('2026-10-29T01:59:36.744590+00:00');later=[d for d in old+[row]if d.get('track')=='F'and d.get('event')=='pod_billed'and datetime.datetime.fromisoformat(d['timestamp_utc'].replace('Z','+00:00'))>cut];total=round(29.18+sum(d['all_in_usd_upper']for d in later),2)
    close=dict(row,all_member_hashes_verified=True,complete_native_grid=True,output_seal_sha256=C.sha(root/'out/OUTPUT_SEAL.json'),pax_sha256=C.sha(archive),source_archive_sha256=plan['payload_hashes']['source.tar.gz'],worker_sha256=plan['worker_sha256'],GO_sha256=plan['payload_hashes']['GO.json'],capture_sha256=plan['capture_sha256'],measured_production=adm,cumulative_E98_GPU_hours=(closed['charged_seconds_upper']+plan['prior_gpu_seconds'])/3600,input_deleted=True,independent_and_stock_guards_retired=True,I5_closed_allin_upper=total,scientific_verdict='PENDING registered judgments/analysis',judge_calls_by_closeout=0)
    # Once-only row precedes receipt: a crash here must be finished manually, never replayed.
    with(BASE/'compute.jsonl').open('a')as f:f.write(json.dumps(row)+'\n')
    C.write(receipt,close);C.write(public/'CLOSEOUT.json',close)
    C.write(public/'SEAL.json',dict(experiment='E98',phase='reader',status='COMPLETE',timestamp_utc=now,first_output_utc=firstutc,first_output_evidence=first,files={str(p.relative_to(public)):C.sha(p)for p in public.rglob('*')if p.is_file()and p!=public/'SEAL.json'}))
    note='\n'+now+' E98native COMPLETE/CLOSED2184/exact frozen128greedy4B18/source/card/input/capture/GO/timing/PAX allhashes/NULL/guardsverified; '+str(cost)+'allinupperbookedONCE releases49.61, I5closed'+str(total)+'. No judgment/analysis/scientificagreement claim.\n'
    for n in ['log.md','i5/HANDOFF.md','status/I-5.md','understand/e98/HANDOFF.md']:
        with(BASE/n).open('a')as f:f.write(note)
    print(json.dumps(close))
if __name__=='__main__':main()
