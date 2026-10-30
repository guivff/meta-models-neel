from pathlib import Path
import sys,json,subprocess,hashlib,datetime,shutil,time
sys.path.insert(0,'projects/g_agreement/ops');import i5_controller as C
base=Path('results/g_agreement/understand/e98');delivery=base/'wlens_forecast';receipt=C.read(delivery/'E98_WLENS_FORECAST_RECEIPT_20261029.json');assert not(base/'GO_R3B.json').exists()
bundle=Path(receipt['git_delivery']['bundle_path']);assert C.sha(bundle)==receipt['git_delivery']['bundle_sha256'];subprocess.run(['git','bundle','verify',str(bundle)],check=True,capture_output=True)
for src,dest in [('forecast-original','forecast-original'),('input-plan-original','input-plan-original')]:subprocess.run(['git','fetch',str(bundle),'refs/wlens/e98/'+src+':refs/i5/e98/wlens-'+dest],check=True,capture_output=True)
fc=receipt['original_forecast_commit'];pc=receipt['input_plan_original_commit'];assert subprocess.check_output(['git','rev-parse','refs/i5/e98/wlens-forecast-original'],text=True).strip()==fc;assert subprocess.check_output(['git','rev-parse','refs/i5/e98/wlens-input-plan-original'],text=True).strip()==pc
ft=int(subprocess.check_output(['git','show','-s','--format=%ct',fc],text=True));pt=int(subprocess.check_output(['git','show','-s','--format=%ct',pc],text=True));assert pt<receipt['claim_created_epoch']<ft<time.time()
for name,info in receipt['files'].items():
 data=subprocess.check_output(['git','show',fc+':results/g_agreement/understand/e98/'+name]);assert hashlib.sha256(data).hexdigest()==info['sha256']==C.sha(delivery/name)
plan=C.read(delivery/'JLENS_INPUT_PLAN.json');fore=C.read(delivery/'E98_JFORECAST.json');completion=C.read(delivery/'JLENS_COMPLETION_SEAL.json');code=C.read(delivery/'JLENS_CODE_SEAL.json')
assert fore['status']=='SEALED_PROSPECTIVE_TO_ORACLE_OUTPUTS'and completion['status']=='COMPLETE'and fore['reader_outcomes_accessed']is False and fore['experiment']=='E98'and fore['layer']==18 and fore['k']==16 and fore['null_directions']==200
assert fore['capture_seal_sha256']==C.sha(Path('cache/g_agreement/understand/e98/capture_v1/out/CAPTURE_SEAL.json'))==receipt['capture_seal_sha256'];assert fore['asset_card_sha256']==C.sha(base/'ASSET_CARD.json')==receipt['asset_card_sha256'];assert fore['jlens_sha256']==receipt['jlens_sha256'];assert fore['total_test_items']==2184 and fore['binary_test_items']==1932 and fore['excluded_test_items']==252
assert C.sha(delivery/'JLENS_INPUT_PLAN.json')==fore['plan_sha256']==completion['plan_sha256'];assert fore['dropped_rows']==[]
owner=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wlens')
for name,h in code['files'].items():
 source=owner/name;assert C.sha(source)==h
 if not name.startswith('external/'):
  data=subprocess.check_output(['git','show',pc+':'+name]);assert hashlib.sha256(data).hexdigest()==h
 dest=delivery/'code'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
for name,h in plan['source_pins'].items():assert C.sha(Path(name))==h
raw=Path(completion['raw_root']);assert C.sha(raw/'RAW_SEAL.json')==completion['raw_seal_sha256'];rs=C.read(raw/'RAW_SEAL.json')
for name,h in rs['files'].items():assert C.sha(raw/name)==h
rawpub=delivery/'raw';rawpub.mkdir(exist_ok=True)
for path in raw.iterdir():
 if path.is_file()and path.suffix=='.json':shutil.copy2(path,rawpub/path.name)
shutil.copy2('/private/tmp/i5_e98_go.py',delivery/'code/i5_verify_go.py')
now=datetime.datetime.now(datetime.timezone.utc);go=dict(experiment='E98',issuer='I-5',input_sha256='75597e5b3d4e02a4b3e527670ddfd57ef3cc72840e322cfb53df08d8b6039182',capture_sha256=receipt['capture_seal_sha256'],forecast_commit=fc,forecast_sha256=receipt['forecast_sha256'],forecast_commit_verified=True,forecast_committed_epoch=ft,input_plan_commit=pc,input_plan_committed_epoch=pt,issued_epoch=now.timestamp(),issued_utc=now.isoformat(),reader_outputs_opened=False,capture_closed_queryNULL=True,card_sha256=receipt['asset_card_sha256'],model=receipt['model'],layer=18,chronology='capture completed then originalforecastcommit then thisGO then futureOracleoutputs; never pre-captureclaim',source_originals_imported_and_git_blobs_verified=True,cap_total_gpu_seconds=36000,prior_capture_gpu_seconds=580.1988520622253,proposed_reader_max_seconds=32400,judge_cap_usd=10,dropped_rows=[],forecast_nonbinary_exclusions=fore['exclusions'])
C.write(base/'GO_R3B.json',go);C.write(base/'I5_FORECAST_INTAKE_VERIFIED.json',dict(timestamp_utc=now.isoformat(),receipt_sha256=C.sha(delivery/'E98_WLENS_FORECAST_RECEIPT_20261029.json'),forecast_commit=fc,input_plan_commit=pc,all_original_git_blobs_verified=True,all_code_and_raw_member_hashes_verified=True,completed_forecast_never_recomputed=True,source_code_files=len(code['files']),raw_files=len(rs['files']),large_raw_custody=str(raw),GO_sha256=C.sha(base/'GO_R3B.json'),native_reader_allocated=False))
C.write(base/'GO_R3B_SEAL.json',dict(experiment='E98',files={str(p.relative_to(base)):C.sha(p)for p in [base/'GO_R3B.json',base/'I5_FORECAST_INTAKE_VERIFIED.json',*(delivery.rglob('*'))]if p.is_file()},first_output_utc=datetime.datetime.fromtimestamp(receipt['first_Wlens_J_readout']['mtime_ns']/1e9,datetime.timezone.utc).isoformat(),first_output_evidence=receipt['first_Wlens_J_readout']))
print('Original forecast/plan/code/raw verified, GO issued',C.sha(base/'GO_R3B.json'))
