"""Isolated E106 TileLang pre-model smoke; never loads weights or patches FLA."""
import argparse,hashlib,importlib.metadata as md,importlib.util,json,os,sys,time
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def module_sources(name):
    spec=importlib.util.find_spec(name)
    if spec is None:raise RuntimeError('missing base runtime '+name)
    p=Path(spec.origin).resolve();root=p.parent
    return {'root':str(root),'python_files':{str(f.relative_to(root)):sha(f) for f in sorted(root.rglob('*.py'))}}


def verify_overlay(manifest,overlay):
    d=json.loads(Path(manifest).read_text());overlay=Path(overlay).resolve()
    if any((overlay/n).exists() for n in ['torch','triton','fla','peft','transformers','numpy']):raise ValueError('overlay cannot replace scientific/base packages')
    for name,p in d['pins'].items():
        dist=md.distribution(name)
        if dist.version!=p['version'] or not Path(dist._path).resolve().is_relative_to(overlay):raise ValueError('pinned dependency is not from isolated overlay: '+name)
    for flag in ['FLA_TILELANG','FLA_DISABLE_BACKEND_DISPATCH']:
        if flag in os.environ:raise ValueError('leave official backend selection flags unset: '+flag)
    return d


def smoke(manifest,overlay,out,cpu_only=False,hardware="H200"):
    if out.exists():raise FileExistsError(out)
    if hardware=="H200":verify_overlay(manifest,overlay)
    elif hardware!="B200" or cpu_only:raise ValueError("explicit H200 or native B200 GPU path")
    import torch
    if hardware=="H200":import tilelang,tvm_ffi
    if torch.__version__.split('+')[0]!='2.8.0':raise RuntimeError('preserve Torch2.8 API')
    result={'torch':torch.__version__,'hardware':hardware,'tilelang':tilelang.__version__ if hardware=='H200' else None,'tvm_ffi':md.version('apache-tvm-ffi') if hardware=='H200' else None,'overlay':str(overlay.resolve()) if hardware=='H200' else None,'model_loaded':False,'guard_bypassed':False}
    if hardware=="H200":
        from tilelang import language as T
        for key in ['TL_DISABLE_TMA_LOWER','TL_ENABLE_FAST_MATH']:getattr(tilelang.PassConfigKey,key)
        assert hasattr(tilelang,'jit') and hasattr(T,'Tensor')
    if cpu_only:
        result.update(status='CPU_IMPORT_PASS_GPU_KERNEL_UNTESTED',cuda_tested=False)
    else:
        import triton
        from fla.ops.gated_delta_rule import chunk_gated_delta_rule
        import fla
        from projects.g_agreement.e106.dispatch_proof import tilelang_target,identity,CallProof
        root=Path(fla.__file__).resolve().parent
        if torch.cuda.device_count()!=1 or hardware not in torch.cuda.get_device_name(0):raise RuntimeError('exact admitted H200/B200 GPU required')
        if any(k in os.environ for k in ['FLA_TILELANG','FLA_DISABLE_BACKEND_DISPATCH']):raise ValueError('official defaults only')
        if hardware=='H200':
            from fla.ops.common.backends.tilelang import TileLangBackend
            from fla.utils import has_usable_nvcc,IS_NVIDIA_HOPPER
            if not IS_NVIDIA_HOPPER or not has_usable_nvcc() or not TileLangBackend.is_available() or not TileLangBackend.is_enabled():raise RuntimeError('official default Hopper TileLang backend unavailable')
            function,description=tilelang_target(TileLangBackend,root)
        else:
            if torch.cuda.get_device_capability(0)!=(10,0):raise RuntimeError('native B200 sm100 required')
            from fla.ops.common.chunk_o import chunk_bwd_dqkwg
            function,description=identity(chunk_bwd_dqkwg,root,'chunk_bwd_dqkwg')
        sources={n:module_sources(n) for n in ['fla','triton']};torch.manual_seed(20261029);torch.cuda.manual_seed_all(20261029)
        q=torch.randn((1,128,2,128),device='cuda',dtype=torch.bfloat16,requires_grad=True)
        k=torch.randn_like(q,requires_grad=True);v=torch.randn((1,128,4,128),device='cuda',dtype=torch.bfloat16,requires_grad=True)
        g=(-.1*torch.rand((1,128,4),device='cuda')).requires_grad_();beta=torch.rand((1,128,4),device='cuda',requires_grad=True)
        out.parent.mkdir(parents=True,exist_ok=True)
        target=out.with_suffix('.TARGET.json')
        if target.exists():raise FileExistsError(target)
        target.write_text(json.dumps(dict(description,hardware=hardware,model_loaded=False,proof_status='PENDING'),indent=2)+'\n')
        t=time.monotonic()
        with CallProof(function,description) as proof:
            output,_state=chunk_gated_delta_rule(q,k,v,g,beta,output_final_state=False,use_qk_l2norm_in_kernel=True)
            output.float().square().mean().backward();torch.cuda.synchronize()
        if not torch.isfinite(output).all() or any(x.grad is None or not torch.isfinite(x.grad).all() for x in [q,k,v,g,beta]):raise RuntimeError('nonfinite gated-delta forward/backward')
        provenance=proof.receipt()
        if sources!={n:module_sources(n) for n in ['fla','triton']}:raise RuntimeError('base FLA/Triton source changed')
        result.update(status=hardware+'_GATED_DELTA_BACKWARD_SMOKE_PASS',cuda_tested=True,gpu=torch.cuda.get_device_name(0),triton=triton.__version__,seconds=time.monotonic()-t,dispatch_provenance=provenance,base_sources=sources,all_gradients_finite=True)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('manifest','overlay','out'):p.add_argument('--'+k,type=Path,required=True)
 p.add_argument('--cpu-only',action='store_true');p.add_argument('--hardware',choices=['H200','B200'],default='H200');a=p.parse_args();smoke(a.manifest,a.overlay,a.out,a.cpu_only,a.hardware)
