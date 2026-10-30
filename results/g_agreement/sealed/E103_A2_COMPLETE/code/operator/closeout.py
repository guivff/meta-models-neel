"""Administrative closeout only. Never invokes a model, judge, or analysis adapter."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import json,tarfile,hashlib,math,subprocess,os,sys,shutil,re
w=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i5');r=Path('/Users/guivff/repl/activation-readers-i5/e103-core-20261028-a2');sys.path.insert(0,str(r));import i5_controller as C
state=C.read(r/'STATE.json');assert state['pod_id']=='244yq8nxxj3wzb'
closed=C.read(r/'CLOSED.json');assert closed['provider_query_null']and closed['archive_verified']and C.pod(state['pod_id'])is None
assert C.read(r/'CLEANUP.json')['inputs_absent']is True
receipt_path=w/'results/g_agreement/understand/e103/I5_A2_COMPLETE_CLOSEOUT.json';assert not receipt_path.exists(),'Already processed; never rebook'
ledger=w/'results/g_agreement/compute.jsonl';rows=[json.loads(x)for x in ledger.read_text().splitlines()if x.strip()];assert not any(x.get('pod_id')==state['pod_id']and x.get('event')=='pod_billed'for x in rows),'Already booked'
auth=C.read(r/'AUTHORIZATION.json');plan=C.read(r/'PLAN.json');archive=r/'final.pax.tar.gz';assert C.sha(archive)==C.read(r/'RESULT.json')['archive_sha256']
dest=w/'cache/g_agreement/understand/e103/a2_complete';dest.mkdir(mode=0o700,exist_ok=True)
with tarfile.open(archive)as t:
 members={m.name:m for m in t.getmembers()if m.isfile()};blob=t.extractfile('out/OUTPUT_SEAL.json').read();seal=json.loads(blob);assert seal['status']=='COMPLETE'and seal['completed_samples']==2512 and seal['expected_items']==314 and seal['gpu_type']=='H200'and seal['pod_id']==state['pod_id'];assert seal['source_seal_sha256']==auth['source_seal_sha256']and seal['public_source_sha256']==plan['public_sha256']
 for n,h in seal['files'].items():assert hashlib.sha256(t.extractfile('out/'+n).read()).hexdigest()==h,n
 assert {n[4:]for n in members if n.startswith('out/')and n!='out/OUTPUT_SEAL.json'}==set(seal['files'])
 jobs={n:m for n,m in members.items()if n.startswith('out/jobs/')and n.endswith('.json')};assert len(jobs)==2512;expected={(i,j)for i in plan['item_ids']for j in range(8)};seen=[]
 for n in jobs:
  x=json.load(t.extractfile(n));assert (x['temperature'],x['top_p'],x['top_k'],x['max_new_tokens'],x['seed'])==(1.,.95,0,64,20261028);assert isinstance(x['raw'],str)and isinstance(x['token_ids'],list)and len(x['token_ids'])<=64 and all(type(v)is int and v>=0 for v in x['token_ids']);seen.append((x['id'],x['repeat']))
 assert len(set(seen))==2512 and set(seen)==expected
 counts=json.load(t.extractfile('out/COUNTS.json'));assert counts==dict(source_items=314,samples=2512,serial_batch_size=1,reader_adapter_loads=0)
 first=seal['first_output_evidence'];member=members['out/'+first['path']];mtime=member.pax_headers['mtime'];assert int(Decimal(mtime)*10**9)==first['mtime_ns'];assert member.name==min(jobs,key=lambda n:Decimal(jobs[n].pax_headers['mtime']))
 hardware=json.load(t.extractfile('out/HARDWARE.json'));assert hardware['gpu_type']=='H200'and not hardware['reader_adapter_loaded']
 for m in t.getmembers():
  assert not Path(m.name).is_absolute()and '..'not in Path(m.name).parts
 t.extractall(dest,filter='data')
for p in dest.rglob('*'):
 if p.is_dir():p.chmod(0o700)
 elif p.is_file():p.chmod(0o600)
guards={}
for role in ['hardstop','backstop']:
 q=subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+C.label(r,role)],capture_output=True);assert q.returncode!=0;guards[role]=dict(retired=True,ready=C.read(r/(role+'.ready.json')))
stock=dict(x.split('=',1)for x in(r/'stock_guards/state').read_text().splitlines()if'='in x)
for key in ['hardstop_pid','hardstop_caffeinate_pid','watchdog_pid','watchdog_caffeinate_pid']:
 q=subprocess.run(['ps','-o','args=','-p',stock[key]],capture_output=True,text=True);assert str(r/'stock_guards')not in q.stdout
subprocess.run(['launchctl','bootout','gui/'+str(os.getuid())+'/'+C.label(r,'controller')],capture_output=True)
seconds=closed['charged_seconds_upper'];assert seconds+auth['prior_custody_seconds_upper']<=14400;gpu_usd=seconds*state['rate']/3600;allin=math.ceil((gpu_usd+2)*100)/100;now=datetime.now(timezone.utc)
x=dict(experiment='E103',status='COMPLETE_SAMPLING_NOT_SCIENTIFIC_VERDICT',timestamp_utc=now.isoformat(),authorization_commit=auth['authorization_commit'],pod_id=state['pod_id'],gpu_type='H200',created_utc=state['createdAt'],source_seal_sha256=seal['source_seal_sha256'],public_items_sha256=seal['public_source_sha256'],output_seal_sha256=hashlib.sha256(blob).hexdigest(),archive_sha256=C.sha(archive),archive_path=str(archive),workspace_retained_path=str(dest),all_output_hashes_verified=True,exact_314x8_id_repeat_inventory_verified=True,all_decoding_parameters_verified=True,first_output_utc=seal['first_output_utc'],first_output_evidence={**first,'archive_member':member.name,'archive_PAX_mtime':mtime,'archive_PAX_mtime_ns':int(Decimal(mtime)*10**9)},completed_samples=2512,required_samples=2512,A1_pilot_disposition='TIMING_ONLY_ARCHIVE_EXCLUDED_FROM_JUDGE',prior_charged_seconds_upper=auth['prior_custody_seconds_upper'],charged_seconds_upper=seconds,cumulative_GPU_hours_upper=(seconds+auth['prior_custody_seconds_upper'])/3600,cumulative_ceiling_GPU_hours=4,GPU_hours_upper=seconds/3600,gpu_usd_upper=gpu_usd,conservative_extras_usd=2,all_in_usd_upper=allin,provider_query_null_verified=True,inputs_deleted=True,independent_guards=guards,stock_guard_processes_retired=True,priced_reservation_released_usd=26.86,active_reservation_usd=0,judge_cost_usd=0,registered_analysis_run=False,rule_change=False,next='E56bankE103 registry + pinnedroute/privacy + fresh<=5USD admission before ALL782claim/1564calls; then frozenWmech2R-H2ONCE; no A1scientificuse')
receipt_path.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
public=w/'results/g_agreement/sealed/E103_A2_COMPLETE';public.mkdir(exist_ok=False)
shutil.copytree(dest/'out',public/'outputs');shutil.copy2(dest/'worker.log',public/'worker.log')
code=public/'code';code.mkdir()
with tarfile.open(r/'source.tar.gz')as t:t.extractall(code,filter='data')
for n in ['controller.py','i5_controller.py']:
 p=code/'operator'/n;p.parent.mkdir(exist_ok=True);shutil.copy2(r/n,p)
shutil.copy2(Path(__file__),code/'operator/closeout.py')
shutil.copy2(receipt_path,public/'CLOSEOUT.json')
for p in public.rglob('*'):
 if p.is_file():assert not re.search(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}',p.read_bytes()),str(p)
C.write(public/'SEAL.json',dict(experiment='E103',status='COMPLETE_SAMPLING_NOT_SCIENTIFIC_VERDICT',authorization_commit=auth['authorization_commit'],source_shared_commit='1a5968f6',output_seal_sha256=x['output_seal_sha256'],first_output_utc=x['first_output_utc'],first_output_evidence=x['first_output_evidence'],files={str(p.relative_to(public)):C.sha(p)for p in sorted(public.rglob('*'))if p.is_file()}))
with ledger.open('a')as f:f.write(json.dumps(dict(timestamp_utc=now.isoformat(),experiment='E103',track='F',event='pod_billed',pod_id=state['pod_id'],gpu_type='H200',GPU_hours=seconds/3600,gpu_usd_upper=gpu_usd,conservative_extras_usd=2,all_in_usd_upper=allin,status='COMPLETE',completed_samples=2512,first_output_utc=seal['first_output_utc'],reservation_released_usd=26.86,provider_query_null=True))+'\n')
status=w/'results/g_agreement/status/I-5.md';text=status.read_text();text=re.sub(r'Updated: .*','Updated: '+now.astimezone(ZoneInfo('Europe/Zurich')).isoformat(),text,count=1);text='\n'.join('| E103 | CORE sampling COMPLETE/CLOSED;2512/2512 exactH200samples | All314x8IDs/decoding/source/input/hashes/PAXmtime verified; inputdelete/providerNULL/guardsretired. A1timingonlyexcluded. Sampling/raw/code/seal published; E56bankE103/fresh5USDjudgeadmission pending beforeR-H2ONCE. |'if l.startswith('| E103 |')else l for l in text.splitlines())+'\n';text+='\n'+now.isoformat()+': E103 A2 sampling COMPLETE2512/2512; allfiles/314x8idrepeat/parameters/H200hardware/sealhashes/PAXmtime PASS. Permanentfinalarchive verifiedbeforeinputdelete/terminate, freshproviderqueryNULL andallguardsretired. Custody'+str(seconds)+'s /'+str(seconds/3600)+'GPUh /'+str(allin)+'USDallinupper bookedONCE replaces26.86reservation. I5closedtotal'+str(round(10.87+allin,2))+'USDupper; cumulativeGPUupper'+str(round(2.86814+gpu_usd,8))+' /hours'+str(round(.542177+seconds/3600,8))+'; allGPU/judgereserves0/judgeactual0. No scientificverdict/adapter/onceguard invoked. FullsealedE103_A2_COMPLETE/rawcodeandI5_A2_COMPLETE_CLOSEOUT.json shared; oldA1neverjudged. Parkedordering/gates unchanged.\n';text=re.sub(r'Closed I-5 cost .*?(?=\n\n)', 'Closed I-5 cost **USD'+str(round(10.87+allin,2))+' all-in upper**: historical10.87 plus E103A2 '+str(allin)+'. GPUupper '+str(round(2.86814+gpu_usd,8))+' /'+str(round(.542177+seconds/3600,8))+' GPU-h. All five I5pods closed/queryNULL/guardsretired; activeGPU/judgereserves0, judgeactual0. Costs bookedonce; conservative extras are bounds, not invoices.',text,count=1,flags=re.S);status.write_text(text)
with(w/'results/g_agreement/log.md').open('a')as f:f.write('\n'+now.isoformat()+' I5 E103A2 complete2512samples/314sources, exactallhashes/idrepeat/parameters/H200/PAXfirstmtime verified; finalarchive/inputdelete/queryNULL/guardsretiredPASS. '+str(seconds)+'s custody/'+str(allin)+'USDupper bookedonce;26.86reserve released. Source119files/rawalloutputs/closeoutcode published sealed/E103_A2_COMPLETE. E56judge/registeredR-H2ONCE pending, nojudgecalls/scientificanalysis.\n')
print(json.dumps({k:x[k]for k in ['status','completed_samples','first_output_utc','charged_seconds_upper','cumulative_GPU_hours_upper','all_in_usd_upper','output_seal_sha256']}))
