from pathlib import Path
import hashlib,json,shutil,datetime,time
import sys
sys.path.insert(0,str(Path.cwd()))
import numpy as np
from projects.g_agreement.understand.e79_extension.build import fit_row,load_original
root=Path.cwd();e=root/'results/g_agreement/understand/e79_extension';spec=json.loads((e/'INPUTS.json').read_text());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();started=time.monotonic()
for p,h in spec['files'].items():assert sha(p)==h,p
for p,h in spec['seals'].items():assert sha(p)==h,p
owner=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-internals-b/cache/g_agreement/understand/e79_extension');receipt=json.loads((e/'BUILD_RECEIPT.json').read_text());assert sha(owner/'KEY.DO_NOT_SHARE.json')==receipt['private_map_sha256'];assert sha(owner/'CPU_DIRECTIONS.npz')==receipt['cpu_directions_sha256']
meta=json.loads(Path(spec['metadata']).read_text());order=json.loads(Path(spec['order']).read_text());acts=np.load(spec['acts44'],mmap_mode='r',allow_pickle=False);q=np.asarray(np.load(spec['basis'],allow_pickle=False),float);q=q.T if q.shape==(384,5120)else q;original=load_original(spec)
items=json.loads((e/'pod_inputs/ITEMS.json').read_text());vectors=np.load(e/'pod_inputs/INPUT_VECTORS.npy',mmap_mode='r',allow_pickle=False);key=json.loads((owner/'KEY.DO_NOT_SHARE.json').read_text());by={x['id']:x for x in key};assert set(by)=={x['id']for x in items};cpu=np.load(owner/'CPU_DIRECTIONS.npz',allow_pickle=False);checked=0
for offset,row in enumerate(['user_expertise','unit_system']):
 ids,h,means,d,u,f,targets=fit_row(meta,order,acts,row,spec['values'][row],original,q,5+offset);ix={ident:i for i,ident in enumerate(ids)}
 for suffix,value in [('means',means),('d',d),('unit_directions',u)]:assert np.array_equal(cpu[row+'__'+suffix],value),(row,suffix)
 for condition,alpha in [('baseline',0)]+[(c,a)for a in (1,2,4,.25,.5)for c in ('J','nonJ','random')]:
  expected=h.astype(np.float32)if condition=='baseline'else original.injection(h,d,u[('J','nonJ','random').index(condition)],targets,alpha).astype(np.float32)
  selected=[x for x in items if x['row']==row and x['condition']==condition and x['alpha']==alpha];assert len(selected)==84
  seen=[]
  for x in selected:
   k=by[x['id']];j=ix[k['source_item_id']];assert np.array_equal(vectors[x['index']],expected[j]);assert k['sign']==int(targets[j])and k['target_label']==int(targets[j]>0);seen.append(j);checked+=1
  assert sorted(seen)==list(range(84))and sum(by[x['id']]['target_label']for x in selected)==42
assert checked==2688
private=root/'cache/g_agreement/understand/e79_extension/private';private.mkdir(parents=True,mode=0o700,exist_ok=False)
for n in ['KEY.DO_NOT_SHARE.json','CPU_DIRECTIONS.npz']:shutil.copy2(owner/n,private/n);(private/n).chmod(0o600)
r=dict(experiment='E79_extension',status='OWNER_VECTORS_VERIFIED_RUNNER_CPU_BOUND_LAUNCH_HELD',verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),pod_seal_sha256=sha(e/'pod_inputs/RESULT_SEAL.json'),rows=['user_expertise','unit_system'],n=2688,all_vectors_reconstructed_bit_identical=True,dev_means_directions_exact=True,targets_balanced_and_paired=True,source_inputs_verified=len(spec['files']),source_seals_verified=len(spec['seals']),CPU_wall_seconds=time.monotonic()-started,private_permanent_cache=str(private),private_map_sha256=sha(private/'KEY.DO_NOT_SHARE.json'),cpu_directions_sha256=sha(private/'CPU_DIRECTIONS.npz'),gpu_allocations=0,reader_outputs=0,first_output_utc='unknown',first_output_evidence='CPU construction validation only; no readout/judgment/outcome analysis',launch_hold='Exact executable archive, provider operator binding and fresh priced shared-budget admission pending; no reservation')
(e/'I5_INTAKE_VERIFICATION.json').write_text(json.dumps(r,indent=2)+'\n')
code=dict(experiment='E79_extension',stage='NATIVE_ONLY_RUNNER_CPU_CODE_SEALED_NOT_LAUNCH_READY',first_output_utc='unknown',first_output_evidence='Prospective code only',original_runner_sha256='721ce7680400df9a96b0ce1e54ea944a5c080acd94335bed08006d790a9a8f0c',operational_delta='AST removes token/warm_cont/continuationwarmup and limits retained pilot kinds to native. Original native loop, jobs, input copies, Clock andmeanx1.25 untouched.',files={n:sha(root/n)for n in ['projects/g_agreement/e79_extension/runner.py','projects/g_agreement/e79_extension/test_runner.py']},CPU_tests='2passed0.56s: exact2688 native/336jobs, one discarded warmup, no continuation/repetition; scriptimportsPASS; ownerdevindependencetest1PASS0.10s',planned_creation_ceiling_seconds=7200,exact_archive_preflight_complete=False,gpu_allocations=0)
(e/'I5_RUNNER_CODE_SEAL.json').write_text(json.dumps(code,indent=2)+'\n');print('Verified',checked,'exact owner vectors; permanent private copy secured; CPU wall',r['CPU_wall_seconds'])
