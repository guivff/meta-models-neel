"""Independent E97 block42 recapture validation and once-only administrative closeout."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
import importlib.util,json,tarfile,hashlib,math,subprocess,os,signal,time,shutil,re
import numpy as np
w=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i5');r=Path('/Users/guivff/repl/activation-readers-i5/e97r42-20261028-a1');spec=importlib.util.spec_from_file_location('C',r/'controller.py');C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
s=C.read(r/'STATE.json');closed=C.read(r/'CLOSED.json');result=C.read(r/'RESULT.json');assert s['pod_id']=='hfjn9tvvqexync'and result['status']=='COMPLETE'
assert closed['provider_query_null']and closed['archive_verified']and C.pod(s['pod_id'])is None;assert C.read(r/'CLEANUP.json')['inputs_absent']is True
receipt_path=w/'results/g_agreement/understand/e97/RECAP_211A_COMPLETE_CLOSEOUT.json';assert not receipt_path.exists(),'Already processed; never rebook'
ledger=w/'results/g_agreement/compute.jsonl';assert not any(x.get('pod_id')==s['pod_id']and x.get('event')=='pod_billed'for x in [json.loads(z)for z in ledger.read_text().splitlines()if z.strip()])
archive=r/'final.pax.tar.gz';assert C.sha(archive)==result['archive_sha256'];dest=w/'cache/g_agreement/understand/e97/recapture42_211a';dest.mkdir(mode=0o700,exist_ok=True)
with tarfile.open(archive)as t:
 blob=t.extractfile('out/CAPTURE_SEAL.json').read();cap=json.loads(blob);assert cap['status']=='COMPLETE'and cap['sites']==[42]and cap['capture_items']==6720 and cap['reader_outputs']==0 and cap['gpu_type']=='H200';assert cap['source_seal_sha256']=='ea3610f5a56a0b59e98ea634f391edd945393e99aa75c669d650bdc8b48fa355'
 files={m.name:m for m in t.getmembers()if m.isfile()};assert {n[4:]for n in files if n.startswith('out/')and n!='out/CAPTURE_SEAL.json'}==set(cap['files'])
 for n,h in cap['files'].items():assert hashlib.sha256(t.extractfile('out/'+n).read()).hexdigest()==h,n
 first=cap['first_output_evidence'];m=files['out/'+first['path']];pax=m.pax_headers['mtime'];assert int(Decimal(pax)*10**9)==first['mtime_ns']
 for m0 in t.getmembers():assert not Path(m0.name).is_absolute()and '..'not in Path(m0.name).parts
 t.extractall(dest,filter='data')
for p in dest.rglob('*'):
 if p.is_dir():p.chmod(0o700)
 elif p.is_file():p.chmod(0o600)
out=dest/'out';public=[json.loads(z)for z in(r/'inputs/PUBLIC_ITEMS.jsonl').read_text().splitlines()];assert len(public)==6720;order=json.loads((out/'items.order.json').read_text());assert order==[x['item_id']for x in public]
a=np.load(out/'acts42.npy',mmap_mode='r',allow_pickle=False);assert a.shape==(6720,5120)and a.dtype==np.float32 and np.isfinite(a).all()
batches=sorted((out/'batches').glob('*.npy'));assert [p.name for p in batches]==[f'{i:04d}.42.npy'for i in range(840)]
for i,p in enumerate(batches):
 b=np.load(p,allow_pickle=False);assert b.shape==(8,5120)and b.dtype==np.float32 and np.isfinite(b).all()and b.tobytes()==np.asarray(a[i*8:(i+1)*8]).tobytes()
assert not list(out.rglob('*.44.npy'))and not(out/'acts44.npy').exists()
retained=C.sha(r/'retained44.npy');assert retained=='113acaaeb7b292d283dfe91ee12a480b7e5b29f74dab35666211ea8c91756bee'
old=C.read(w/'results/g_agreement/understand/e97/capture_attempt2/CAPTURE_SEAL.json');assert old['files']['acts44.npy']=='e1447c98cc534328dd98fdc19743a841de9849c8db3013477f26a3b627becce2';forecast=C.sha(w/'results/g_agreement/understand/e52/r3b/E97_JFORECAST.json');assert forecast=='5f099f9d84246fc4039e4f793844b67de498aedf368645af95d7f4bbcff23485'
# Retire any stock shell still sleeping after TERM, matching this exact owned path.
stock=dict(x.split('=',1)for x in(r/'stock_guards/state').read_text().splitlines()if'='in x)
for key in ['hardstop_pid','hardstop_caffeinate_pid','watchdog_pid','watchdog_caffeinate_pid']:
 pid=int(stock[key]);q=subprocess.run(['ps','-o','args=','-p',str(pid)],capture_output=True,text=True)
 if str(r/'stock_guards')in q.stdout:
  os.kill(pid,signal.SIGTERM);time.sleep(.3);q=subprocess.run(['ps','-o','args=','-p',str(pid)],capture_output=True,text=True)
  if str(r/'stock_guards')in q.stdout:os.kill(pid,signal.SIGKILL)
 q=subprocess.run(['ps','-o','args=','-p',str(pid)],capture_output=True,text=True);assert str(r/'stock_guards')not in q.stdout
for role in ['hardstop','backstop']:
 q=subprocess.run(['launchctl','print','gui/'+str(os.getuid())+'/'+C.label(r,role)],capture_output=True);assert q.returncode!=0
subprocess.run(['launchctl','bootout','gui/'+str(os.getuid())+'/'+C.label(r,'controller')],capture_output=True)
now=datetime.now(timezone.utc);seconds=closed['charged_seconds_upper'];gpu=seconds*s['rate']/3600;allin=math.ceil((gpu+2)*100)/100
x=dict(experiment='E97',status='COMPLETE_BLOCK42_ONLY_RECAPTURE_VERIFIED',timestamp_utc=now.isoformat(),pod_id=s['pod_id'],gpu_type=s['gpu_type'],created_utc=s['createdAt'],source_seal_sha256=cap['source_seal_sha256'],capture_seal_sha256=hashlib.sha256(blob).hexdigest(),archive_sha256=C.sha(archive),archive_path=str(archive),retained_capture_path=str(out),public_items_sha256=cap['public_items_sha256'],items=6720,shape=[6720,5120],dtype='float32',finite=True,exact_public_order=True,batches=840,all_batch_aggregate_hashes_and_bitwise_concatenation_verified=True,sites=[42],original42_sha256=old['files']['acts42.npy'],new42_sha256=C.sha(out/'acts42.npy'),original42_comparison_diagnostic_only=True,new42_matches_original42=C.sha(out/'acts42.npy')==old['files']['acts42.npy'],physical_retained_test44_sha256=retained,original_full44_sealed_sha256=old['files']['acts44.npy'],original_full44_file_available=False,block44_hashes_unchanged=True,forecast_sha256=forecast,forecast_original_commit='8e8c0107d85b95bd7d9e93a9fe8752ff0a4627f4',forecast_rerun=False,reader_outputs=0,GO_issued=False,first_output_utc=cap['first_output_utc'],first_output_evidence={**first,'archive_member':m.name,'archive_PAX_mtime':pax,'archive_PAX_mtime_ns':int(Decimal(pax)*10**9)},final_pull_verified_before_input_deletion=True,inputs_deleted=True,provider_query_null_verified=True,independent_guards_retired=True,stock_guards_retired=True,charged_seconds_upper=seconds,GPU_hours_upper=seconds/3600,gpu_usd_upper=gpu,conservative_extras_usd=2,all_in_usd_upper=allin,reservation_released_usd=5.67,active_reservation_usd=0,pool='parked',next='Publish completecaptureseal then exactnew42/original44boundreaderinputs and standingforecastGO before native readers; freshmeasuredcaps/provider/900pooladmission required')
receipt_path.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
sealed=w/'results/g_agreement/sealed/E97_BLOCK42_RECAPTURE';sealed.mkdir(exist_ok=False);shutil.copy2(out/'CAPTURE_SEAL.json',sealed/'CAPTURE_SEAL.json');shutil.copy2(out/'items.order.json',sealed/'items.order.json');shutil.copy2(receipt_path,sealed/'CLOSEOUT.json')
shutil.copytree(r/'source',sealed/'code')
for name in ['controller.py','closeout_complete.py']:
 source_path=r/name
 if source_path.exists():p=sealed/'code/operator'/name;p.parent.mkdir(exist_ok=True);shutil.copy2(source_path,p)
shutil.copy2(Path(__file__),sealed/'code/operator/closeout.py')
for p in sealed.rglob('*'):
 if p.is_file():assert not re.search(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}',p.read_bytes()),str(p)
C.write(sealed/'SEAL.json',dict(experiment='E97',status='COMPLETE_BLOCK42_RECAPTURE_NO_READER_OUTCOMES',capture_seal_sha256=x['capture_seal_sha256'],first_output_utc=x['first_output_utc'],first_output_evidence=x['first_output_evidence'],large_arrays_custody=str(out),large_arrays_not_in_git=True,files={str(p.relative_to(sealed)):C.sha(p)for p in sorted(sealed.rglob('*'))if p.is_file()}))
with ledger.open('a')as f:f.write(json.dumps(dict(timestamp_utc=now.isoformat(),experiment='E97',track='F',event='pod_billed',pool='parked',pod_id=s['pod_id'],gpu_type=s['gpu_type'],GPU_hours=seconds/3600,gpu_usd_upper=gpu,conservative_extras_usd=2,all_in_usd_upper=allin,status='COMPLETE',capture_items=6720,first_output_utc=x['first_output_utc'],reservation_released_usd=5.67,provider_query_null=True))+'\n')
p=w/'results/g_agreement/status/I-5.md';text=p.read_text();text=re.sub(r'Updated: .*','Updated: '+now.astimezone(ZoneInfo('Europe/Zurich')).isoformat(),text,count=1);text='\n'.join('| E97 recapture / readers / E75 pooled rerun | Block42 recapture COMPLETE/CLOSED; readerGO pending | Exact6720float32finite/order/840batch+aggregatehashes/bitwiseconcatenation verified, sites42only; retained44/full44sealedhashes unchanged, standingforecastunchanged. Captureseal published before new42boundinputs/GO/native readers. |'if z.startswith('| E97 recapture / readers / E75 pooled rerun |')else z for z in text.splitlines())+'\n';text=re.sub(r'Closed I-5 cost .*?(?=\n\n)','Closed I-5 cost **USD'+str(round(23.02+allin,2))+' all-in upper**: prior23.02 plus E97recap '+str(allin)+'. All six I5podsclosed/queryNULL/guardsretired. ActiveGPU/judgereserves0/judgeactual0. Conservativeextras notinvoices; costsbookedonce.',text,count=1,flags=re.S);text+='\n'+now.isoformat()+': E97recaptureCOMPLETE exact6720/site42only/840batches/finitefloat32/order/allhashes/bitwiseconcatPASS. New42matchesold42diagnostically='+str(x['new42_matches_original42'])+'; hardware rulingno substitution. Originalretainedtest44physicalandfull44sealedhashunchanged/fullfileunavailable; forecastunchanged/norerun. OriginalPAXearliestpreproductionvalidationmtime verified. Finalpullbeforeinputdelete/terminate/freshNULL/allguardsretired; '+str(seconds)+'scustody/'+str(allin)+'USDallinupperbookedonce replaces5.67parkedreserve. NoE97GO/nativeoutcomes yet; exactnew42-boundinputs/standingforecastGO nextafterpublication; E75waitsjudgments.\n';p.write_text(text)
with(w/'results/g_agreement/log.md').open('a')as f:f.write('\n'+now.isoformat()+' E97block42recapture COMPLETE exact6720/order/finitefloat32/840batches/bitwiseaggregate/allhashes/site42only verified; retained44+sealedfull44hash+standingforecastunchanged, firstvalidationoriginalPAXnsverified. Finalpull/inputdelete/NULL/ownedguardsretired; booked'+str(allin)+'upperonce/releases5.67poolreserve. Rawarrayspermanentowncache, source/metadata/completeCAPTUREseal published; nativeGO/outcomespending.\n')
print(json.dumps({k:x[k]for k in ['status','capture_seal_sha256','new42_matches_original42','first_output_utc','charged_seconds_upper','all_in_usd_upper']}))
