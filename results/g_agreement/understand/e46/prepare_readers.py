"""Bind the already sealed E46 persistence; no persistence or reader computation."""
from io46 import *
from reader_worker import eligible_rows
import tarfile,shutil

def prepare():
 verify(HERE,'BANK_SEAL.json');verify(HERE/'persistence_2026-10-26','PERSISTENCE_SEAL.json','96f8c9c28c40fc87586e3a7b81e9e7eebdd26f6f5129de11838548c9bb828e38')
 med=read(HERE/'persistence_2026-10-26/ROW_MEDIANS.json');eligible=eligible_rows(med)
 if med['bank_seal_sha256']!=sha(HERE/'BANK_SEAL.json') or med['state_seal_sha256']!=sha(HERE/'STATE_FUNCTION_SEAL.json'):raise ValueError('persistence binding')
 if sha(HERE/'cache/persistence_items.json')!=med['item_ledger_sha256']:raise ValueError('persistence ledger hash')
 stage=HERE/'cache/readers_2026-10-26';stage.mkdir(exist_ok=False)
 items=read(HERE/'cache/prepared/items.PRIVATE.json')
 with (stage/'items.jsonl').open('x') as f:
  for x in items:
   if x['feature'] in eligible:f.write(json.dumps({k:x[k] for k in ['id','feature','text','ids','split','cluster']})+'\n')
 base=HERE.parent/'e36';runtime=__import__('reader_worker').load_runtime(ROOT)
 parity=read(base/'LAUNCH_REQUEST.json')['parity_inputs'];runtime.G.load_inputs(parity)
 receipt=read(HERE/'cache/VERIFIED_PULL.json');out=Path(receipt['output_directory']);verify(out,'FOLLOWING_TEXT_SEAL.json',receipt['following_text_seal_sha256'])
 prior=read(out/'PROVENANCE.json')['total_custody_seconds']
 def binding(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
 sources=list(runtime.C.REQUIRED_SOURCE_PATHS)+['results/g_agreement/understand/e46/'+n for n in ['reader_worker.py','prepare_readers.py','analyze_readers_once.py','io46.py','test_readers.py']]+['projects/g_agreement/blindspot/protocol.py','external/mats-nla-workspace/src/mats/metrics.py']
 source_files={n:sha(ROOT/n) for n in sorted(set(sources))}
 plan={'experiment':'E46_READERS','registration':'§157; clarification 1','eligible_rows':eligible,'persistence_seal':binding(HERE/'persistence_2026-10-26/PERSISTENCE_SEAL.json'),'persistence_medians':binding(HERE/'persistence_2026-10-26/ROW_MEDIANS.json'),'bank_seal':binding(HERE/'BANK_SEAL.json'),'state_seal':binding(HERE/'STATE_FUNCTION_SEAL.json'),'reader_items':binding(stage/'items.jsonl'),'candidates':binding(HERE/'CANDIDATES.json'),'parity_inputs':parity,'reference_seal':binding(base/'analysis_overnight149/ANALYSIS_SEAL.json'),'aggregate_cap_seconds':10800,'minimum_prior_gpu_seconds':prior,'prior_gpu_seconds_policy':'Integrator supplies full actual earlier E46 custody, including retrieval and termination; minimum is recorded acquisition custody only. Deduct it from 10800.','registered_revisions':runtime.C.REGISTERED_REVISIONS,'source_files':source_files,'channels':['probe','oracle_descriptive','nla'],'probe_recipe':runtime.C.PROBE_RECIPE,'test_items':84*len(eligible),'capture_items':168*len(eligible),'value_word_channel':False,'continuation_channel':False}
 dump(HERE/'READER_PLAN.json',plan)
 dump(HERE/'READER_CODE_SEAL.json',{'complete':True,'files':{n:sha(HERE/n) for n in ['reader_worker.py','prepare_readers.py','analyze_readers_once.py','test_readers.py','io46.py','READER_PLAN.json']}})
 request={'experiment':'E46','stage':'READERS','status':'READY_FOR_INTEGRATOR_READER_ASSIGNMENT','priority_after':['E42'],'operator':'integrator','plan_path':str((HERE/'READER_PLAN.json').relative_to(ROOT)),'plan_sha256':sha(HERE/'READER_PLAN.json'),'persistence_seal_sha256':plan['persistence_seal']['sha256'],'eligible_rows':eligible,'channels':['probe','Oracle asked','NLA asked'],'aggregate_cap_seconds':10800,'minimum_prior_gpu_seconds':prior,'parity':{'items':252,'rows':runtime.G.ROWS,'tolerance':.02,'required_before_production':True,'input_seal_sha256':runtime.G.INPUT_SHA256},'assignment_required':['issuer=integrator','experiment=E46','pod_id=RUNPOD_POD_ID','plan_sha256','assets_manifest_sha256','gpu_type=H200','gpu_count=1','prior_gpu_seconds=actual total prior E46 custody','allocation_started_at=provider creation epoch','hard_deadline <= allocation_started_at + 10800 - prior_gpu_seconds','external_stop.confirmed=true','external_stop.deadline=hard_deadline','external_stop.receipt','phase_estimates_seconds with all eight E36 phase keys; oracle_value_word=0 and continuation=0'],'worker_argv':['python','results/g_agreement/understand/e46/reader_worker.py','--root','CHECKOUT_ROOT','--plan','results/g_agreement/understand/e46/READER_PLAN.json','--assignment','READER_ASSIGNMENT.json','--assets','VERIFIED_NATIVE_ASSETS.json','--out','NEW_OUTPUT_DIRECTORY'],'cpu_analysis_argv':['/Users/guivff/Documents/Neel_Exploration/activation-readers/.venv/bin/python','results/g_agreement/understand/e46/analyze_readers_once.py','--receipt','results/g_agreement/understand/e46/cache/VERIFIED_READER_PULL.json']}
 shutil.copyfile(HERE/'LAUNCH_REQUEST.json',HERE/'LAUNCH_REQUEST_ACQUISITION.json')
 (HERE/'LAUNCH_REQUEST.json').write_text(json.dumps(request,indent=2,sort_keys=True)+'\n')
 members=set(source_files)|{v['path'] for v in plan.values() if isinstance(v,dict) and 'path' in v and 'sha256' in v}
 # Reference outcomes remain CPU-only, never staged with the reader job.
 members.discard(plan['reference_seal']['path'])
 for name in ['READER_PLAN.json','READER_CODE_SEAL.json','LAUNCH_REQUEST.json']:members.add(str((HERE/name).relative_to(ROOT)))
 for name in read(ROOT/parity['path'])['files']:members.add(str((Path(parity['path']).parent/name)))
 archive=stage/'E46_READERS.tar.gz'
 with tarfile.open(archive,'w:gz') as t:
  for n in sorted(members):t.add(ROOT/n,arcname=n)
 dump(HERE/'READER_STAGING_ARCHIVE.json',{'path':str(archive.relative_to(ROOT)),'sha256':sha(archive),'E46_labels_in_archive':False,'W1_parity_labels':252,'members':sorted(members)})
 print('Reader-ready rows:',eligible,'plan:',sha(HERE/'READER_PLAN.json'))
if __name__=='__main__':prepare()
