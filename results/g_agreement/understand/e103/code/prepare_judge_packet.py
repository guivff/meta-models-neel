from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,importlib.util,os,subprocess,re
w=Path.cwd();owner=w/'cache/g_agreement/understand/e103/owner_selection_v1/private';sampling=w/'results/g_agreement/sealed/E103_A2_COMPLETE';out=w/'cache/g_agreement/understand/e103/judge_packet_v1'
assert not out.exists(),'Never rebuild an existing packet without inspecting its receipt'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
queue_seal=json.loads((w/'results/g_agreement/understand/e103/ALL_CLAIMS_SEAL.json').read_text());selection_seal=json.loads((w/'results/g_agreement/understand/e103/SELECTION_SEAL.json').read_text())
assert sha(owner/'ALL_CLAIM_CALLS.PRIVATE.json')==queue_seal['sha256']=='d6915af78af0f02b66c41b75d33d47e478cd5d6e610ab915f10440970c9b54e1'
assert sha(owner/'SELECTION.PRIVATE.json')==selection_seal['files']['SELECTION.PRIVATE.json']
source=w/'results/g_agreement/understand/e103/judge103.py';frozen=subprocess.check_output(['git','show','f42e0a75:results/g_agreement/understand/e103/judge103.py']);assert source.read_bytes()==frozen
spec=importlib.util.spec_from_file_location('frozen_judge103',source);J=importlib.util.module_from_spec(spec);spec.loader.exec_module(J)
sample_seal=json.loads((sampling/'outputs/OUTPUT_SEAL.json').read_text());public_seal=json.loads((sampling/'SEAL.json').read_text());assert sample_seal['status']=='COMPLETE'and sample_seal['completed_samples']==2512
for n,h in public_seal['files'].items():assert sha(sampling/n)==h,n
for n,h in sample_seal['files'].items():assert sha(sampling/'outputs'/n)==h,n
samples={};sample_hashes={}
for p in sorted((sampling/'outputs/jobs').glob('*.json')):
 x=json.loads(p.read_text());key=(x['id'],x['repeat']);assert key not in samples;samples[key]=x['raw'];sample_hashes[key]=sha(p)
assert len(samples)==2512 and len({i for i,r in samples})==314
assert all((i,r)in samples for i in {i for i,r in samples}for r in range(8))
selection={x['uid']:x for x in json.loads((owner/'SELECTION.PRIVATE.json').read_text())};queue=json.loads((owner/'ALL_CLAIM_CALLS.PRIVATE.json').read_text());assert len(queue)==1564 and len({q['id']for q in queue})==1564
requests=[];mapping=[];pairs={}
for q in queue:
 u=selection[q['readout_uid']];claim=u['claims'][q['claim_index']]
 assert q['claim']==claim['claim']and q['verdict']==claim['verdict']
 assert all(q[k]==u[k]for k in ['wave','bank','reader','cohort','item_id'])
 expected=u['own_source_id']if q['arm']=='own'else u['control_source_id'];assert q['arm']in ('own','mismatched')and q['source_id']==expected
 values=[samples[(q['source_id'],r)]for r in range(8)];prompt=J.render(q['claim'],values);opaque=hashlib.sha256(('E103|'+q['id']).encode()).hexdigest()[:32]
 requests.append(dict(id=opaque,prompt=prompt));mapping.append(dict(id=opaque,owner_call_id=q['id'],source_id=q['source_id'],readout_uid=q['readout_uid'],claim_index=q['claim_index'],arm=q['arm'],prompt_sha256=hashlib.sha256(prompt.encode()).hexdigest(),raw_sample_sha256=[sample_hashes[(q['source_id'],r)]for r in range(8)]))
 pairs.setdefault((q['readout_uid'],q['claim_index']),set()).add(q['arm'])
assert len(pairs)==782 and all(v=={'own','mismatched'}for v in pairs.values())and len({r['id']for r in requests})==1564
out.mkdir(mode=0o700)
for name,data in [('REQUESTS.PRIVATE.json',requests),('MAPPING.PRIVATE.json',mapping)]:
 p=out/name;p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
receipt=dict(experiment='E103',stage='EXACT_CPU_JUDGE_PACKET_READY_WAIT_OWNER_BANK_CHANNEL_AND_ADMISSION',timestamp_utc=datetime.now(timezone.utc).isoformat(),first_output_utc=public_seal['first_output_utc'],first_output_evidence=public_seal['first_output_evidence'],sampling_seal_sha256=sha(sampling/'SEAL.json'),output_seal_sha256=sha(sampling/'outputs/OUTPUT_SEAL.json'),owner_full_queue_sha256=queue_seal['sha256'],selection_seal_sha256=sha(w/'results/g_agreement/understand/e103/SELECTION_SEAL.json'),frozen_prompt_commit='f42e0a75',frozen_prompt_source_sha256=sha(source),calls=1564,claims=782,source_items=314,samples=2512,exact8_raw_per_call=True,all_claims_from_frozen_owner_queue=True,own_mismatched_joins_verified=True,request_fields=['id','prompt'],label_verdict_bank_reader_cohort_not_in_packet_fields=True,private_directory=str(out),private_permissions='0700directory0600files',files={p.name:sha(p)for p in out.iterdir()},route='E56 pinned registered route only; owner bankE103 registry notyetlanded',registered_judge_cap_usd=5,judge_reservation_usd=0,judge_calls_sent=0,response_values_created=False,scientific_analysis_run=False,pending=['W-internals-B committed E103 bank/channel','Current route/privacy/exactdestination + actualsharedjudge ledger and <=5USD priced admission','Full sealed judge grid then frozen Wmech2 R-H2 once'])
p=w/'results/g_agreement/understand/e103/I5_JUDGE_PACKET_CPU_RECEIPT.json';p.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
assert not re.search(rb'hf_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}',p.read_bytes())
print(json.dumps(dict(calls=len(requests),claims=len(pairs),all8_raw_exact=True,judge_calls_sent=0,private=str(out))))
