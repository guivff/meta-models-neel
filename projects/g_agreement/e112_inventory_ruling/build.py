"""Reproducible copy-only inventory; refuses overwrite. Never reads outcome values."""
import json,subprocess,hashlib
from datetime import datetime
from pathlib import Path
from .copy_inventory import copy_fields
from projects.g_agreement.understand.wmech2 import core as c
ROOT=Path(__file__).resolve().parents[3]
COMMIT='0715326562305e57d3b696c717f88a7cdcab3385'
RELEASE='be1147070f1be9589ebd78ad96cc7d3dccf85388'
BRIEF='ed2bc87b1ee6fd73cab00d0173b806fc59fb76f7'
INPUT=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/cache/g_agreement/r_ops/e112/reh2/e112/inputs/INPUT_SEAL.json')
INPUT_SHA='cfa397a0749569cbefdc01029e4be98b092d9db0f765cb5ef50787dce137563b'
VECTOR=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e112-vectors-v1/vectors/VECTOR_SEAL.json')
VECTOR_SHA='a356cc5a0a96dac3a12c6fbcfa9a8feafc690420ccf6ef5c7f17e684b37e559d'
OUT=ROOT/'cache/g_agreement/understand/e112/inventory_ruling_ba760009e'

def blob(commit,path):return subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT)

def git_source(commit,path,parse=True):
    b=blob(commit,path);t=subprocess.check_output(['git','show','-s','--format=%cI',commit],cwd=ROOT,text=True).strip()
    assert datetime.fromisoformat(t)<datetime.fromisoformat('2026-10-29T07:48:15+00:00'), 'source commit is not pre-output'
    return dict(data=json.loads(b) if parse else b.decode(),pre_output_verified=True,custody=dict(commit=commit,member=path,sha256=hashlib.sha256(b).hexdigest(),commit_time=t,chronology='Before known-run first retained output 2026-10-29T07:48:15Z; R5 full provenance review required'))

def main():
    c.verify(INPUT,INPUT_SHA);c.verify(VECTOR,VECTOR_SHA)
    sources={'release':git_source(RELEASE,'results/g_agreement/understand/e112/CPU_RELEASE_RECEIPT.json'),
      'projection':git_source(COMMIT,'results/g_agreement/understand/e112/PROJECTION.json'),
      'plan':git_source(COMMIT,'results/g_agreement/understand/e112/PLAN.template.json'),
      'dependencies':git_source(COMMIT,'results/g_agreement/understand/e112/DEPENDENCIES.json'),
      'delivery':git_source(COMMIT,'results/g_agreement/understand/e112/DELIVERY.json'),
      'registration':git_source(BRIEF,'projects/g_agreement/BRIEF_UNDERSTAND.md',False),
      'worker':git_source(COMMIT,'results/g_agreement/understand/e112/worker112.py',False)}
    assert sources['release']['data']['input_seal_sha256']==INPUT_SHA
    plan=c.read(INPUT.parent/'PLAN.json')
    assert plan==sources['plan']['data']
    assert c.sha(VECTOR.parent/'PROJECTION.json')==sources['projection']['custody']['sha256']
    sources['bound_plan']=dict(data=plan,pre_output_verified=True,custody=dict(seal=str(INPUT),seal_sha256=INPUT_SHA,member='PLAN.json',sha256=c.sha(INPUT.parent/'PLAN.json'),pre_output_commit=COMMIT,release_commit=RELEASE))
    fields={k:('bound_plan',[k]) for k in ('experiment','item_ids','conditions','capture_seal_sha256','vector_seal_sha256','k','k_selection_sha256','basis_block','original_E80c_result_seal','none_regenerated')}
    fields.update({k:('projection',[k]) for k in ('n','centred','same_e80c_mu_and_basis','J_variance_share','cumulative_variance','source_capture_sha256','source_PCA384_sha256','source_J384_sha256','mean_recipe','basis_recipe')})
    fields.update({k:None for k in ('pre_output','route_verified','privacy_verified','labels_cpu_only','source_order_verified','pre_output_commits_verified')})
    fields['labels_on_pod']=('release',['labels_on_pod'])
    fields['E80_source_pins']=('dependencies',[])
    result=copy_fields(sources,fields)
    # Site values copied verbatim from the original source tuple, not inferred from arrays.
    line="for reader,layer in (('oracle',44),('nla',42)):"
    assert line in sources['worker']['data']
    result['values']['reader_blocks']={'oracle':44,'nla':42}
    result['provenance']['reader_blocks']=dict(status='COPIED',source='worker',literal=line,custody=sources['worker']['custody'])
    text=sources['registration']['data'];start=text.index('## §225 E112.');excerpt=text[start:].split('\n## ',1)[0]
    result['registration_text']=excerpt
    result['registration_provenance']=sources['registration']['custody']
    result['missing_fields']=[k for k,v in result['values'].items() if v=='MISSING']
    result['diagnostic_disposition']='Per-item diagnostics beyond PCA_k: not available; do not impute.'
    result['review']='R-5 must verify provenance before any guard claim. New inventory is post-output copy-only; no claim it was committed pre-output.'
    assert len(result['values']['item_ids'])==len(set(result['values']['item_ids']))==518
    OUT.mkdir(parents=True,exist_ok=False)
    c.write(OUT/'INVENTORY.json',result['values']);c.write(OUT/'PROVENANCE.json',{k:v for k,v in result.items() if k!='values'})
    c.seal(OUT,'INVENTORY_SEAL.json',experiment='E112',authority='ba760009e',status='COPY_ONLY_AWAITING_R5',pre_output_inventory=False,original_input_sha256=INPUT_SHA,projection_commit=COMMIT)
    print(json.dumps(dict(directory=str(OUT),seal_sha256=c.sha(OUT/'INVENTORY_SEAL.json'),files=c.read(OUT/'INVENTORY_SEAL.json')['files'],missing_fields=result['missing_fields'])))
if __name__=='__main__':main()
