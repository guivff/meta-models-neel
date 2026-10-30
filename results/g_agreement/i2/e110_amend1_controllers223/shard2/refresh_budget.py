from pathlib import Path
import json,subprocess,sys,time,hashlib
R=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2')
TOOLS=R/'cache/g_agreement/i2/budget_audit_tools_private'
def refresh(home):
 pub=json.loads((home.parent/'PROJECTION_PUBLICATION.json').read_text());assert pub['shared_commit']
 q=subprocess.run([sys.executable,str(TOOLS/'e110_amend1_owner_root223.py')],cwd=R,capture_output=True,text=True,timeout=90);assert q.returncode==0,'FRESH_ALLTRACK_BASE_HOLD'
 base=Path(json.loads(q.stdout)['private_audit'])
 q=subprocess.run([sys.executable,str(TOOLS/'e110_filter_storage223.py'),str(base)],cwd=R,capture_output=True,text=True,timeout=45);assert q.returncode==0,'FRESH_STORAGE_HOLD'
 path=Path(json.loads(q.stdout)['private_admission']);d=json.loads(path.read_text())
 assert time.time()-__import__('datetime').datetime.fromisoformat(d['as_of_utc']).timestamp()<120
 proof=dict(checked_epoch=__import__('datetime').datetime.fromisoformat(d['as_of_utc']).timestamp(),projection_posted=True,GPU_upper_with_candidate_usd=d['global_inclusive_upper_usd'],pool_upper_with_candidate_usd=d['pool_all_owner_root_upper_including_candidate_and_storage_usd'],candidate_GPU_upper_usd=5.85,private_admission_path=str(path),private_admission_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),projection_shared_commit=pub['shared_commit'])
 (home/'BUDGET.json').write_text(json.dumps(proof,indent=2)+'\n');return proof
