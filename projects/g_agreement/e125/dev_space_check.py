import json,hashlib,importlib.util,sys,datetime
from pathlib import Path
import numpy as np,torch
from safetensors.torch import load_file

def run():
    R=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmechc');O=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e125-dev-space-check-v3');O.mkdir(exist_ok=False)
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
    src=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e120-inputs-v1/decoder');seal=json.loads((src/'INPUT_SEAL.json').read_text());items=json.loads((src/'items.json').read_text());assert sha(src/'items.json')==seal['files']['items.json'];dev=[x for x in items if x['split']=='dev'];assert len(dev)==200
    # Read only DEV row byte ranges. Never np.load/materialize the mixed test array.
    p=src/'h44.npy'
    with p.open('rb')as f:
     version=np.lib.format.read_magic(f);shape,fortran,dtype=(np.lib.format.read_array_header_1_0(f) if version==(1,0) else np.lib.format.read_array_header_2_0(f));assert shape==(600,5120)and dtype==np.float32 and not fortran
     offset=f.tell();rows=[]
     for x in dev:
      f.seek(offset+x['vector_index']*5120*4);v=np.frombuffer(f.read(5120*4),dtype=np.float32).copy();assert v.shape==(5120,)and np.isfinite(v).all();rows.append(v)
    raw=np.stack(rows);np.save(O/'dev_true_raw.npy',raw,allow_pickle=False);write(O/'DEV_ORDER.json',[x['id']for x in dev])
    mom=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i4/cache/g_agreement/e96/operator/whitener.pt');assert sha(mom)=='178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a'
    source=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/results/g_agreement/understand/e26/reward_audit/evidence/olens_draft/src/oracle_lens/core/whitening.py')
    blob=hashlib.sha1(b'blob '+str(source.stat().st_size).encode()+b'\0'+source.read_bytes()).hexdigest();assert blob=='a1129f7584eae21e70b8e7f85eeccac738d9ef06'
    spec=importlib.util.spec_from_file_location('_e125_pinned_whitening',source);module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    torch.set_num_threads(8);torch.set_num_interop_threads(1)
    w=module.load_whitener(mom,ridge_c=.1,device='cpu');white=w.whiten(torch.from_numpy(raw));assert tuple(white.shape)==(200,5120)and torch.isfinite(white).all();np.save(O/'dev_true_whitened.npy',white.numpy(),allow_pickle=False)
    mean=white.double().mean(0).numpy();sd=white.double().std(0,unbiased=True).numpy();np.save(O/'per_dimension_mean.npy',mean,allow_pickle=False);np.save(O/'per_dimension_sd.npy',sd,allow_pickle=False)
    q=lambda a:dict(zip(['min','p05','median','p95','max'],map(float,np.quantile(a,[0,.05,.5,.95,1]))))
    result=dict(experiment='E125',status='INCOMPLETE_MISSING_DEV_NATIVE_ORACLE_READOUTS',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),CPU_only=True,dev_items=200,test_arrays_opened=False,test_rows_read=0,mixed_source_handling='read NPY header then ONLY DEV byte ranges, never loaded mixed array or any TEST row',original_input_seal_sha256=sha(src/'INPUT_SEAL.json'),original_h44_sha256_from_seal=seal['files']['h44.npy'],moments_sha256=sha(mom),official_source_blob=blob,ridge_c=.1,true_whitened_per_dimension_mean=q(mean),true_whitened_per_dimension_abs_mean=q(np.abs(mean)),true_whitened_per_dimension_sd=q(sd),dev_reconstructor_items=0,median_rebuilt_true_cosine=None,mean_SD_space_match=None,affine_alignment_fit=False,space_proof_PASS=False,blocker='original E85 input receipt declares600captures but reader_test_items400; original late198worker releases only split=test to native Oracle. No sealed DEV native readout source located. Cannot substitute TEST readouts or first-generated-token capture.',original_reader_input_receipt='results/g_agreement/understand/e85/INPUT_BINDING.json',official_reader_source='results/g_agreement/understand/late198/worker.py:153',files={p.name:sha(p)for p in O.iterdir()if p.is_file()})
    write(O/'SPACE_PROOF.json',result);write(R/'results/g_agreement/understand/e125/SPACE_PROOF.json',dict(result,artifact_root=str(O)));print(json.dumps({k:result[k]for k in ['status','dev_items','test_rows_read','true_whitened_per_dimension_abs_mean','true_whitened_per_dimension_sd']},indent=2))

if __name__=="__main__":run()
