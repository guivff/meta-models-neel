from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,tarfile,subprocess,time,os,re
import numpy as np
import sys
sys.path.insert(0,str(Path.cwd()))
from projects.g_agreement.e97 import readers as W
w=Path.cwd();base=w/'cache/g_agreement/understand/e97';recap=w/'results/g_agreement/sealed/E97_BLOCK42_RECAPTURE/CAPTURE_SEAL.json';digest=W.sha(recap);commit=subprocess.check_output(['git','rev-parse','e9f102e7'],text=True).strip();committed=subprocess.check_output(['git','show',commit+':'+str(recap.relative_to(w))]);assert hashlib.sha256(committed).hexdigest()==digest=='4d57e0c1e7ebd36f4172364059d8a09326f62666ef9bd44b2c9f294a387a399f';recap_epoch=int(subprocess.check_output(['git','show','-s','--format=%ct',commit],text=True))
fpath='results/g_agreement/understand/e52/r3b/E97_JFORECAST.json';frozen=subprocess.check_output(['git','show',W.FORECAST_COMMIT+':'+fpath]);assert hashlib.sha256(frozen).hexdigest()==W.FORECAST==W.sha(w/fpath);forecast_epoch=int(subprocess.check_output(['git','show','-s','--format=%ct',W.FORECAST_COMMIT],text=True))
old=base/'oracle_reader_inputs_v1';old_seal=json.loads((old/'INPUT_SEAL.json').read_text())
for n,h in old_seal['files'].items():assert W.sha(old/n)==h
public=[json.loads(z)for z in Path('/Users/guivff/repl/activation-readers-i5/e97r42-20261028-a1/inputs/PUBLIC_ITEMS.jsonl').read_text().splitlines()];test_ix=[i for i,x in enumerate(public)if x['split']=='test'];ids=[public[i]['item_id']for i in test_ix];items=json.loads((old/'items.json').read_text());assert [x['id']for x in items]==ids
aggregate=base/'recapture42_211a/out/acts42.npy';h=np.load(aggregate,mmap_mode='r',allow_pickle=False);cap=json.loads(recap.read_text());assert W.sha(aggregate)==cap['files']['acts42.npy'];paths={};seals={};archives={}
for reader in ['oracle','nla']:
 out=base/(reader+'_reader_inputs_v2');assert not out.exists(),'Inspect existing final inputs; do not rebuild blindly';out.mkdir(mode=0o700)
 shutil.copy2(old/'items.json',out/'items.json');shutil.copytree(old/'parity',out/'parity');shutil.copy2(recap,out/'BLOCK42_RECAPTURE_SEAL.json')
 if reader=='oracle':shutil.copy2(old/'vectors.npy',out/'vectors.npy')
 else:np.save(out/'vectors.npy',np.asarray(h[test_ix]),allow_pickle=False)
 vectors=np.load(out/'vectors.npy',mmap_mode='r',allow_pickle=False);W.validate(items,vectors)
 if reader=='oracle':assert W.sha(out/'vectors.npy')=='113acaaeb7b292d283dfe91ee12a480b7e5b29f74dab35666211ea8c91756bee'
 else:assert vectors.tobytes()==np.asarray(h[test_ix]).tobytes()
 for kind in (['oracle']if reader=='oracle'else['oracle','nla']):
  for suffix in ['json','npy']:shutil.copy2(base/'reader_smoke_reference'/f'SMOKE_{kind}.{suffix}',out/f'SMOKE_{kind}.{suffix}')
 data=dict(experiment='E97',reader=reader,n=3360,test_only=True,reader_native_layer=44 if reader=='oracle' else 42,capture_sha256=W.CAPTURE,bank_sha256=W.BANK,forecast_sha256=W.FORECAST,public_items_sha256=W.sha('/Users/guivff/repl/activation-readers-i5/e97r42-20261028-a1/inputs/PUBLIC_ITEMS.jsonl'),source_vector_sha256=W.sha(out/'vectors.npy'),block42_vector_source_sha256=cap['files']['acts42.npy'],block42_recapture_sha256=digest,original_block44_sha256=cap['original_block44_sha256'],retained_oracle_test44_sha256=cap['retained_oracle_test44_sha256'],files={str(p.relative_to(out)):W.sha(p)for p in sorted(out.rglob('*'))if p.is_file()},first_output_utc='unknown',first_output_evidence='ReaderinputCPUassemblyonly; recapturevalidationfirstoutput retainedinseparatecaptureseal',GO_issued=False)
 (out/'INPUT_SEAL.json').write_text(json.dumps(data,indent=2,sort_keys=True)+'\n');seals[reader]=W.sha(out/'INPUT_SEAL.json');paths[reader]=out
 arc=base/(reader+'_reader_inputs_v2.tar.gz')
 with tarfile.open(arc,'w:gz')as t:
  for p in sorted(out.rglob('*')):
   if p.is_file():t.add(p,arcname=str(Path('inputs')/p.relative_to(out)),recursive=False)
 with tarfile.open(arc)as t:
  for n,hv in data['files'].items():assert hashlib.sha256(t.extractfile('inputs/'+n).read()).hexdigest()==hv,n
 for p in out.rglob('*'):
  p.chmod(0o700 if p.is_dir()else 0o600)
 arc.chmod(0o600);archives[reader]=dict(path=str(arc),sha256=W.sha(arc),input_seal_sha256=seals[reader],vectors_sha256=data['source_vector_sha256'],large_arrays_in_git=False)
now=datetime.now(timezone.utc);assert recap_epoch<now.timestamp();go=dict(experiment='E97',capture_sha256=W.CAPTURE,bank_sha256=W.BANK,forecast_sha256=W.FORECAST,forecast_original_commit=W.FORECAST_COMMIT,forecast_commit_epoch=forecast_epoch,forecast_git_verified=True,forecast_published_before_GO=True,block42_recapture_sha256=digest,recapture_git_verified=True,recapture_published_before_GO=True,recapture_shared_commit=commit,recapture_sealed_epoch=recap_epoch,issued_epoch=now.timestamp(),issued_utc=now.isoformat(),input_sha256_by_reader=seals,oracle_only_deadline_fallback=False,reader_allocation_pending=True,scope='FrozenE97testreadersonly afterfreshregisteredcaps/provider/pooladmission; onegreedy/testitem/reader; no dev; originalstandingforecast unchanged',GO_requires_new_forecast=False)
for reader,out in paths.items():
 inputs=W.verify(out,'INPUT_SEAL.json',seals[reader]);W.validate_go(go,seals[reader],reader,time.time());W.verify_recapture_binding(out,inputs,go,reader)
p=w/'results/g_agreement/understand/e97/GO_211A.json';assert not p.exists();p.write_text(json.dumps(go,indent=2,sort_keys=True)+'\n')
receipt=dict(experiment='E97',stage='FINAL_BOUND_TEST_INPUTS_AND_GO_CPU_PASS_NO_NATIVE_ALLOCATION',timestamp_utc=now.isoformat(),first_output_utc=cap['first_output_utc'],first_output_evidence=cap['first_output_evidence'],recapture_seal_sha256=digest,recapture_shared_commit=commit,recapture_published_epoch=recap_epoch,GO_sha256=W.sha(p),GO_issued_epoch=go['issued_epoch'],archives=archives,exact_test_ids=3360,exact_public_order_verified=True,float32_finite=True,Oracle44_original_vector_file_unchanged=True,NLA42_test_vectors_bitwise_equal_new_aggregate_slices=True,standing_forecast_unchanged=True,only_old_W1_parity_labels_inherited_exception=True,E97_labels_on_pod=False,smoke_references='ExistingsealedhistoricalH200Oracle128andNLA512 fixtures; hashesincludedineachinputseal',runtime_source_seal_sha256='b8ea3f8f58e0d2d76862b6999dec563b70f41d647fce2d338af162d64c49641f',runtime_archive_sha256='603653fd6edd18b11c8c45e32938e5af9ec7b8467dcc1360aec5875a3969289b',runtime_unchanged_no_rebuild_or_retest=True,CPU_checks='allnewinputtar/memberhashes; originalvectorsreuse; readers.validate/validate_go/verify_recapture_bindingPASSforbothreaders; gitpublishedrecapseal+originalforecastexactbytes/orderPASS',reader_allocation=False,model_calls=0,pending=['Exactruntime/controllerbinding and remoteNLA12filewrapper/_assetsallhashes','Fresh measuredregisteredreader6500/11500caps+creationstaging and currentpool/providerheadroomadmission; guardedlifecycle','Nativeoutputs then registered E56 judging/pooledE75analysis'])
q=p.with_name('READER_BOUND_INPUTS_GO_CPU_RECEIPT.json');q.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
seal=p.with_name('GO_211A_SEAL.json');seal.write_text(json.dumps(dict(experiment='E97',stage='BOUND_READER_GO_NO_NATIVE_OUTCOMES',first_output_utc=cap['first_output_utc'],first_output_evidence=cap['first_output_evidence'],files={p.name:W.sha(p),q.name:W.sha(q)}),indent=2,sort_keys=True)+'\n')
for q0 in [p,q,seal]:assert not re.search(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{20,}',q0.read_bytes())
print(json.dumps(dict(GO_sha256=W.sha(p),input_seals=seals,recapture_published_before_GO=True,reader_allocations=0)))
