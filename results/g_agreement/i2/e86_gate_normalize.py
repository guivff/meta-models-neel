"""Copy sealed pre-existing E86 gate scalars; never fit probes or score readouts."""
from pathlib import Path
from collections import Counter
import json,hashlib,datetime
r=Path.cwd();read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
selection=r/'cache/g_agreement/i2/e86_selected_once';cpu=r/'cache/g_agreement/i2/e86_selected_capture_a1/cpu_probe_once';judge=r/'cache/g_agreement/i2/e86_judge_cpu_v1';release=r/'cache/g_agreement/i2/section212_restarts_v1/e86-a2/READER_RELEASE.json'
for base,name in [(selection,'SELECTION_SEAL.json'),(cpu,'CPU_RECEIPT_SEAL.json')]:
 for member,digest in read(base/name)['files'].items():assert sha(base/member)==digest,member
assert sha(release)==sha(cpu/'READER_RELEASE.json')=='a13b247655ff2d65d69933c6bb20b3b3b67a933232a6adcdf0f864ea0097f38a'
report=read(selection/'SELECTION_REPORT.json');probes=read(cpu/'PUBLIC_PROBE_RECEIPT.json');joins=read(judge/'JOIN_MAP.PRIVATE.json');ids=set(read(release)['released_ids']);assert len(ids)==400
by={x['capture_public_id']:(x['subset'],x['arm'])for x in joins};assert set(by)==ids
released=Counter(by.values());assert released=={('yn','honest'):200,('yn','role'):200}
counts={};lineage={}
for subset in ['open','yn']:
 for arm in ['honest','lie','role']:
  key=subset+'/'+arm;counts[key]={split:report['counts'][key+'/'+split]['n']for split in ['dev','test']};counts[key]['released_test']=released[(subset,arm)]
  for split in ['dev','test']:lineage['achieved_counts/'+key+'/'+split]=dict(source='selection_report',keys=['counts',key+'/'+split,'n'])
  lineage['achieved_counts/'+key+'/released_test']=dict(source='original_release_and_join',count='unique capture_public_id only; no outcome/filter recomputation')
truth={}
for i,x in enumerate(probes['groups']):
 key=x['arm']+'/'+str(x['layer']);assert key not in truth;truth[key]={k:x[k]for k in ['status','dev_auroc','test_auroc']}
 for field in truth[key]:lineage['truth_probes/'+key+'/'+field]=dict(source='public_probe_receipt',keys=['groups',i,field])
assert len(truth)==6
out=r/'results/g_agreement/i2/e86_gate_diagnostics_v1';out.mkdir(exist_ok=True)
files={'GATE_DIAGNOSTICS.json':dict(experiment='E86',achieved_counts=counts,truth_probes=truth,BOW_QA=report['BOW_QA'],open_truth_probe='NOT_APPLICABLE_BY_CLARIFICATION1',primary_R_K1='NOT_EVALUABLE_BLOCKED_LIE_UNDERPOWERED_OPEN'),
 'SCALAR_LINEAGE.json':dict(original_source_hashes=dict(selection_report=sha(selection/'SELECTION_REPORT.json'),selection_seal=sha(selection/'SELECTION_SEAL.json'),public_probe_receipt=sha(cpu/'PUBLIC_PROBE_RECEIPT.json'),cpu_receipt_seal=sha(cpu/'CPU_RECEIPT_SEAL.json'),original_release=sha(release),private_join=sha(judge/'JOIN_MAP.PRIVATE.json')),fields=lineage,no_gate_or_probe_rerun=True,no_readout_or_judgment_scoring=True,private_joins_and_labels_local=True)}
for name,data in files.items():
 p=out/name;text=json.dumps(data,indent=2,sort_keys=True)+'\n'
 if p.exists():assert p.read_text()==text
 else:p.write_text(text)
s=out/'SOURCE_SEAL.json';data=dict(experiment='E86',status='ORIGINAL_GATE_SCALARS_BOUND_NO_OUTCOME_ANALYSIS',files={n:sha(out/n)for n in files},original_release_sha256=sha(release),original_scientific_output_sha256='cfa46523e1fe50337113679fbdada86568a0e6e92348088e28f5a978175fa075',normalizer_sha256=sha(Path(__file__)))
text=json.dumps(data,indent=2,sort_keys=True)+'\n'
if s.exists():assert s.read_text()==text
else:s.write_text(text)
print(json.dumps(dict(diagnostics_seal_sha256=sha(s),counts=counts,probe_entries=len(truth),no_new_gate_fit_or_analysis=True)))
