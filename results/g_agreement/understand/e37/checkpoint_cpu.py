"""§134 clarification3: anonymous single-file retrieval and CPU tensor identity.

No model is instantiated and no forward pass occurs. Network failures alone
select the registered NOT_POSSIBLE branch; malformed tensors/configs stop.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import time
import urllib.error
import urllib.request

HERE=Path(__file__).resolve().parent
MANIFEST=HERE/'CHECKPOINT_MANIFEST_2026-10-26.json'


def read(path):return json.loads(Path(path).read_text())


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def write_new(path,value):
    with Path(path).open('x') as f:json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')


def normalized_name(name):
    # PEFT wrapper prefixes and optional named-adapter component only.
    name=name.removeprefix('base_model.model.')
    name=name.removeprefix('model.language_model.').removeprefix('language_model.').removeprefix('model.')
    name=re.sub(r'\.(lora_[AB])\.[^.]+\.weight$',r'.\1.weight',name)
    name=re.sub(r'\.(lora_embedding_[AB])\.[^.]+$',r'.\1',name)
    return name


def tensor_index(handle):
    result={}
    for key in handle.keys():
        normal=normalized_name(key)
        if normal in result:raise ValueError('PEFT normalisation collision; cannot compare uniquely')
        result[normal]=key
    if not result:raise ValueError('empty adapter checkpoint')
    return result


def compare_tensors(left,right):
    import torch
    from safetensors import safe_open
    comparisons=[]
    with safe_open(str(left),framework='pt',device='cpu') as a,safe_open(str(right),framework='pt',device='cpu') as b:
        ak,bk=tensor_index(a),tensor_index(b)
        for name in sorted(set(ak)|set(bk)):
            record={'name':name,'left_present':name in ak,'right_present':name in bk}
            if name in ak and name in bk:
                x,y=a.get_tensor(ak[name]),b.get_tensor(bk[name])
                record.update(left_shape=list(x.shape),right_shape=list(y.shape),left_dtype=str(x.dtype),right_dtype=str(y.dtype))
                record['equal']=x.shape==y.shape and x.dtype==y.dtype and bool(torch.equal(x,y))
            else:record['equal']=False
            comparisons.append(record)
    return {'all_equal':all(r['equal'] for r in comparisons),'left_tensor_count':len(ak),
        'right_tensor_count':len(bk),'different_tensors':sum(not r['equal'] for r in comparisons),
        'same_normalized_names':set(ak)==set(bk),'comparisons':comparisons,'comparison_device':'cpu',
        'criterion':'same normalized names, shapes, dtypes and exact torch.equal; no casting or tolerance'}


def download_one(destination,pin):
    if pin['repo_type']!='dataset' or pin['repo_id']!='agu18dec/local-workspace' or not re.fullmatch(r'[a-f0-9]{40}',pin['revision']):
        raise ValueError('exact registered dataset revision required')
    expected='ckpts/ao/distill/s3d.omp4bp.s2/step251/lora/adapter_model.safetensors'
    if pin['file']!=expected:raise ValueError('only the single registered lora tensor file may be downloaded')
    url='https://huggingface.co/datasets/'+pin['repo_id']+'/resolve/'+pin['revision']+'/'+expected
    request=urllib.request.Request(url,headers={'User-Agent':'E37-anonymous-single-file-CPU-check'})
    # No HF client/token discovery, no netrc, no authenticated proxy config.
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        response=opener.open(request,timeout=60)
    except (urllib.error.URLError,TimeoutError) as exc:
        return {'status':'NOT_POSSIBLE','error_type':type(exc).__name__,
                'http_status':getattr(exc,'code',None),'anonymous':True,'file_requests':1}
    try:
        with response,Path(destination).open('xb') as out:
            total=0
            while True:
                block=response.read(8*1024*1024)
                if not block:break
                total+=len(block)
                if total>2_000_000_000:raise ValueError('unexpected adapter size')
                out.write(block)
    except (urllib.error.URLError,TimeoutError,ConnectionError) as exc:
        Path(destination).unlink(missing_ok=True)
        return {'status':'NOT_POSSIBLE','error_type':type(exc).__name__,'http_status':None,'anonymous':True,'file_requests':1}
    if not total:raise ValueError('downloaded adapter is empty')
    digest=sha(destination)
    if pin.get('sha256') and digest!=pin['sha256']:raise ValueError('dataset adapter hash differs from provenance pin')
    return {'status':'DOWNLOADED','sha256':digest,'bytes':total,'anonymous':True,'file_requests':1}


def validate_selection(receipt,local_dir=None,check_files=True):
    manifest=read(MANIFEST);hf=manifest['readers']['olens_s3d_student_step251']
    if (receipt.get('manifest_sha256')!=sha(MANIFEST) or receipt.get('hf_adapter_sha256')!=hf['adapter_model_sha256']
            or receipt.get('schema')!='E37_CPU_CHECKPOINT_SELECTION_v1' or receipt.get('model_forwards')!=0
            or receipt.get('cpu_only') is not True or receipt.get('anonymous_single_file_only') is not True):
        raise ValueError('registered pre-forward CPU checkpoint selection required')
    check=receipt['download'];comparison=receipt.get('comparison');branch=receipt['selected_branch']
    if check.get('anonymous') is not True or check.get('file_requests')!=1:
        raise ValueError('anonymous single-file download receipt required')
    if comparison is not None:
        rows=comparison.get('comparisons',[])
        if (not rows or comparison.get('comparison_device')!='cpu'
                or len({r['name'] for r in rows})!=len(rows)
                or comparison.get('all_equal')!=all(r['equal'] for r in rows)
                or comparison.get('different_tensors')!=sum(not r['equal'] for r in rows)):
            raise ValueError('inconsistent complete tensor comparison')
    if receipt.get('readme_identity_claim_verified')!=(branch=='lora_hf_MATCH'):
        raise ValueError('identity claim flag differs from CPU comparison')
    if branch=='lora_hf_MATCH':
        if check['status']!='DOWNLOADED' or not comparison or comparison['all_equal'] is not True:raise ValueError('invalid match branch')
        expected=hf['adapter_model_sha256']
    elif branch=='lora_EXACT_RL_INIT':
        if check['status']!='DOWNLOADED' or not comparison or comparison['all_equal'] is not False:raise ValueError('invalid differing branch')
        expected=receipt['selected_files']['adapter_model.safetensors']
        if (receipt.get('selected_source_adapter_sha256')!=check['sha256']
                or receipt.get('loading_copy_tensor_check',{}).get('all_equal') is not True):
            raise ValueError('loading copy must preserve every original lora tensor')
    elif branch=='lora_hf_UNVERIFIED':
        if check['status']!='NOT_POSSIBLE' or comparison is not None or receipt.get('readme_identity_claim_verified') is not False:raise ValueError('invalid unavailable branch')
        expected=hf['adapter_model_sha256']
    else:raise ValueError('unregistered checkpoint branch')
    if receipt['selected_files'].get('adapter_config.json')!=hf['adapter_config_sha256']:
        raise ValueError('selected config differs from pinned HF config')
    if receipt['selected_files'].get('adapter_model.safetensors')!=expected:
        raise ValueError('selected bytes do not implement registered branch')
    if local_dir is not None and check_files:
        local_dir=Path(local_dir)
        if {p.name for p in local_dir.iterdir()}!=set(receipt['selected_files']):raise ValueError('exact selected adapter files required')
        for n,h in receipt['selected_files'].items():
            if sha(local_dir/n)!=h:raise ValueError('selected checkpoint changed after CPU check')
    return receipt


def prepare(hf_dir,out,received_epoch):
    hf_dir,out=Path(hf_dir),Path(out)
    if 'cache' not in out.resolve().parts:raise ValueError('all downloaded tensors belong under cache/')
    manifest=read(MANIFEST);hf=manifest['readers']['olens_s3d_student_step251']
    tensor=hf_dir/'adapter_model.safetensors';config=hf_dir/'adapter_config.json'
    if sha(tensor)!=hf['adapter_model_sha256'] or sha(config)!=hf['adapter_config_sha256']:
        raise ValueError('HF step251 model/config differ from registered provenance')
    if not 0<received_epoch<=min(time.time(),1793127600):raise ValueError('actual on-time checkpoint arrival required')
    out.mkdir(parents=True,exist_ok=False)
    downloaded=out/'lora.adapter_model.safetensors'
    download=download_one(downloaded,manifest['comparison_source'])
    comparison=None
    if download['status']=='DOWNLOADED':
        comparison=compare_tensors(downloaded,tensor)
        branch='lora_hf_MATCH' if comparison['all_equal'] else 'lora_EXACT_RL_INIT'
    else:branch='lora_hf_UNVERIFIED'
    chosen=out/'selected';chosen.mkdir()
    shutil.copyfile(config,chosen/'adapter_config.json')
    if branch=='lora_EXACT_RL_INIT':
        # Standard PEFT loader expects its saved key convention. Preserve the
        # downloaded bytes and record this purely name-normalized loading copy.
        # Actual selected tensors remain exact, with original shape/dtype.
        from safetensors import safe_open
        from safetensors.torch import save_file
        tensors={}
        with safe_open(str(downloaded),framework='pt',device='cpu') as f:
            for normal,key in tensor_index(f).items():tensors['base_model.model.model.'+normal]=f.get_tensor(key)
        save_file(tensors,str(chosen/'adapter_model.safetensors'))
        # Branch selection refers to the exact downloaded file. PEFT load copy
        # normalization is separately byte-pinned and tensor-equality verified.
        loading_comparison=compare_tensors(downloaded,chosen/'adapter_model.safetensors')
        if not loading_comparison['all_equal']:raise ValueError('loading copy altered original lora tensors')
    else:
        shutil.copyfile(tensor,chosen/'adapter_model.safetensors');loading_comparison=None
    result={'schema':'E37_CPU_CHECKPOINT_SELECTION_v1','manifest_sha256':sha(MANIFEST),
        'hf_adapter_sha256':sha(tensor),'download':download,'comparison':comparison,'selected_branch':branch,
        'selected_files':{p.name:sha(p) for p in chosen.iterdir()},'cpu_only':True,'model_forwards':0,
        'anonymous_single_file_only':True,'readme_identity_claim_verified':branch=='lora_hf_MATCH',
        'selected_source_adapter_sha256':download.get('sha256') if branch=='lora_EXACT_RL_INIT' else sha(tensor),
        'loading_copy_tensor_check':loading_comparison,'received_epoch':received_epoch,'completed_epoch':time.time()}
    validate_selection(result,chosen)
    write_new(out/'CPU_TENSOR_CHECK.json',result)
    receipt={'schema':'E37_SFT_RECEIPT_v1','status':'RECEIVED_FROZEN','issuer':'integrator','provided_by':'Agam',
        'checkpoint_identity':'s3d.omp4bp.s2/step251','identity_verified':True,'received_epoch':received_epoch,
        'local_path':str(chosen.resolve()),'files':result['selected_files'],
        'base_model_revision':manifest['base_model_revision'],'frozen_before_model_calls':True,'model_calls_before_freeze':0,
        'cpu_tensor_check_path':str((out/'CPU_TENSOR_CHECK.json').resolve()),'cpu_tensor_check_sha256':sha(out/'CPU_TENSOR_CHECK.json'),
        'selected_branch':branch,'readme_identity_claim_verified':result['readme_identity_claim_verified']}
    write_new(out/'CHECKPOINT_RECEIPT.json',receipt)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--hf-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--received-epoch',type=float,required=True)
    a=p.parse_args();result=prepare(a.hf_dir,a.out,a.received_epoch)
    print(json.dumps({'status':'CPU_CHECK_COMPLETE','branch':result['selected_branch'],'model_forwards':0}))
