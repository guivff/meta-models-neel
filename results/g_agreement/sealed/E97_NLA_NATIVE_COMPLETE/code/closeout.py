from pathlib import Path
import sys,argparse,json,tarfile,hashlib,os,shutil,decimal,datetime,math
sys.path.insert(0,'projects/g_agreement/ops');import i5_controller as C;import i5_reader_controller as R
p=argparse.ArgumentParser();p.add_argument('--reader',choices=['oracle','nla'],required=True);a=p.parse_args();reader=a.reader
r=Path('/Users/guivff/repl/activation-readers-i5/e97-'+reader+'-20261029-a1');base=Path('results/g_agreement');receipt=base/('understand/e97/I5_'+reader.upper()+'_NATIVE_COMPLETE_CLOSEOUT.json');assert not receipt.exists(),'Already closed/booked'
s=C.read(r/'STATE.json');plan=C.read(r/'PLAN.json');closed=C.read(r/'CLOSED.json');result=C.read(r/'RESULT.json');assert result['status']=='COMPLETE'and result['completed_items']==3360 and closed['provider_query_null']and closed['archive_verified'];assert C.read(r/'CLEANUP.json')['inputs_absent'];assert C.pod(s['pod_id'])is None
archive=r/'final.pax.tar.gz';assert C.sha(archive)==result['archive_sha256'];R.retire_stock(r)
root=Path('cache/g_agreement/understand/e97')/(reader+'_native_complete');root.mkdir(parents=True,exist_ok=True);os.chmod(root,0o700);hashes={};mtimes={}
with tarfile.open(archive,'r|gz')as t:
 for m in t:
  if not m.isfile():continue
  assert not Path(m.name).is_absolute()and'..'not in Path(m.name).parts
  data=t.extractfile(m).read();dst=root/m.name;dst.parent.mkdir(parents=True,exist_ok=True);os.chmod(dst.parent,0o700);dst.write_bytes(data);os.chmod(dst,0o600);hashes[m.name]=hashlib.sha256(data).hexdigest();mtimes[m.name]=dict(path=m.name,mtime_ns=int(decimal.Decimal(m.pax_headers.get('mtime',str(m.mtime)))*1000000000),pax_mtime=m.pax_headers.get('mtime',str(m.mtime)))
seal=C.read(root/'out/OUTPUT_SEAL.json');rows=[C.read(f)for f in(root/'out/records').glob('*.json')];R.complete_grid(seal,rows,plan,s)
assert all(hashes['out/'+n]==h for n,h in seal['files'].items());assert {n[4:]for n in hashes if n.startswith('out/')and n!='out/OUTPUT_SEAL.json'}==set(seal['files'])
candidates=[v for n,v in mtimes.items()if n.startswith('out/records/')or n.startswith('out/B200_SMOKE')or n=='out/parity/PARITY_RESULT.json'];first=min(candidates,key=lambda x:x['mtime_ns']);ev=seal['first_output_evidence'];assert ev['mtime_ns']==first['mtime_ns']
# Reverify immutable executed source archive and every original manifest member.
assert C.sha(r/'source.tar.gz')==plan['payload_hashes']['source.tar.gz'];sources={}
with tarfile.open(r/'source.tar.gz')as t:
 for m in t:
  if m.isfile():sources[m.name]=t.extractfile(m).read()
manifest=json.loads(sources['E97_READER_SOURCE.json']);assert hashlib.sha256(sources['E97_READER_SOURCE.json']).hexdigest()==plan['source_seal_sha256'];assert len(manifest['files'])==100
for n,h in manifest['files'].items():assert hashlib.sha256(sources[n]).hexdigest()==h
public=base/'sealed'/('E97_'+reader.upper()+'_NATIVE_COMPLETE');assert not(public/'SEAL.json').exists();public.mkdir(parents=True,exist_ok=True);shutil.copytree(root/'out',public/'outputs',dirs_exist_ok=True)
code=public/'code';code.mkdir(exist_ok=True)
for n,data in sources.items():
 d=code/'exact_source'/n;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(data)
for n in ['controller.py','i5_controller.py']:shutil.copy2(r/n,code/n)
shutil.copy2('/private/tmp/i5_e97_reader_closeout.py',code/'closeout.py');shutil.copy2('/private/tmp/i5_e97_reader_closeout.py',r/'closeout_complete.py')
for n in ['STATE.json','CLOSED.json','RESULT.json','CLEANUP.json','ASSIGNMENT.json','WORKER_STARTED.json','hardstop.ready.json','backstop.ready.json','final.pax.tar.gz.receipt.json']:
 if(r/n).exists():shutil.copy2(r/n,public/n)
for n in ['worker.log','GO.json']:shutil.copy2(root/n,public/n)
hours=closed['charged_seconds_upper']/3600;gpu=hours*closed['rate'];cost=math.ceil((gpu+2)*100)/100;release={'oracle':16.43,'nla':27.53}[reader];now=datetime.datetime.now(datetime.timezone.utc).isoformat();ledger=base/'compute.jsonl';old=[json.loads(l)for l in ledger.read_text().splitlines()];assert not any(d.get('pod_id')==s['pod_id']and d.get('event')=='pod_billed'for d in old)
row=dict(timestamp_utc=now,experiment='E97',track='F',event='pod_billed',phase='native_'+reader,pool='parked',pod_id=s['pod_id'],gpu_type=s['gpu_type'],GPU_hours=hours,gpu_usd_upper=gpu,conservative_extras_usd=2,all_in_usd_upper=cost,status='COMPLETE',native_test_items=3360,first_output_utc=seal['first_output_utc'],first_output_evidence=first,reservation_released_usd=release,provider_query_null=True)
with ledger.open('a')as f:f.write(json.dumps(row)+'\n')
# Prior29.18 already includes every closed run through E98capture; include all later owned booking rows once.
cut=datetime.datetime.fromisoformat('2026-10-29T01:59:36.744590+00:00');later=[d for d in old+[row]if d.get('track')=='F'and d.get('event')=='pod_billed'and datetime.datetime.fromisoformat(d['timestamp_utc'].replace('Z','+00:00'))>cut];total=round(29.18+sum(d['all_in_usd_upper']for d in later),2)
close=dict(row,all_member_hashes_verified=True,complete_native_grid=True,executed_source_files_verified=100,source_sha256=plan['source_seal_sha256'],GO_sha256=plan['payload_hashes']['GO.json'],input_sha256=plan['input_sha256'],output_seal_sha256=C.sha(root/'out/OUTPUT_SEAL.json'),pax_sha256=C.sha(archive),permanent_archive=str(archive),raw_cache=str(root.resolve()),input_deleted=True,independent_and_stock_guards_retired=True,I5_closed_allin_upper=total,scientific_verdict='PENDING registered judgments/analysis',judge_calls_by_I5=0)
C.write(receipt,close);C.write(public/'CLOSEOUT.json',close);C.write(public/'SEAL.json',dict(experiment='E97',reader=reader,status='COMPLETE',timestamp_utc=now,files={str(f.relative_to(public)):C.sha(f)for f in public.rglob('*')if f.is_file()and f!=public/'SEAL.json'},first_output_utc=seal['first_output_utc'],first_output_evidence=first))
with(base/'log.md').open('a')as f:f.write('\n'+now+' E97 '+reader+' native COMPLETE3360 exactoriginaltestIDs/onegreedy/native'+str(44 if reader=='oracle'else 42)+'/GO/input/source100/allfilehashes/H200/PAXfirstnsPASS. PermanentPAX verified beforeinputdelete/providerterminatefreshNULL/allguardsretired. '+str(closed['charged_seconds_upper'])+'s/'+str(cost)+'allinupperbookedONCE releases'+str(release)+'. No scientificverdict/judge/analysis.\n')
for rel in ['i5/HANDOFF.md','status/I-5.md']:
 with(base/rel).open('a')as f:f.write('\n'+now+' E97 '+reader+' native COMPLETE/CLOSED3360/'+s['pod_id']+'/NULL/guardsretired. Exactgrid/input/GO/source100/PAX/allfilehashes verified; sealpublicE97_'+reader.upper()+'_NATIVE_COMPLETE. Originalfirstvalidation/readout'+seal['first_output_utc']+' path/ns'+str(first)+'. Custody'+str(closed['charged_seconds_upper'])+'s/'+str(cost)+'allinupperONCE/releases'+str(release)+', I5closed'+str(total)+'. No native replay/judge/analysis/inferredR-P1; otherreaderstatusindependent.\n')
print(json.dumps({k:close[k]for k in ['phase','all_in_usd_upper','GPU_hours','I5_closed_allin_upper','output_seal_sha256','first_output_utc','first_output_evidence']}))
