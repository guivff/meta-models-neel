"""CPU-testable fast-kernel admission for a possible later §79 allocation.

Diagnostic only: no model weights, forward, scoring, installation or pod lifecycle call.
The prior run remains immutable. This module is not a new launch receipt.
"""
from __future__ import annotations
import argparse,inspect,json,os,platform,sys
from pathlib import Path
from . import corpus as C

EXPECTED={'torch':'2.8.0+cu128','transformers':'5.18.0','flash-linear-attention':'0.5.2','fla-core':'0.5.2','einops':'0.8.2','triton':'3.4.0','ninja':'1.13.2'}
SYMBOLS={'causal_conv1d_fn':'causal_conv1d','torch_chunk_gated_delta_rule':'fla'}

def validate_metadata(meta):
 for name,version in EXPECTED.items():
  if meta.get('packages',{}).get(name)!=version:raise ValueError('kernel runtime package '+name+' must be '+version)
 # The only selected prebuilt convolution wheel is Linux/cp312/Torch2.8/CUDA12/ABI TRUE.
 for name,expected in [('system','Linux'),('machine','x86_64'),('python_minor','3.12'),('cxx11_abi',True),('cuda_version','12.8')]:
  if meta.get(name)!=expected:raise ValueError('kernel wheel incompatible '+name+'='+repr(meta.get(name)))
 if not meta.get('cuda_available') or 'H200' not in meta.get('device',''):raise ValueError('requires assigned H200 CUDA device')
 if meta['packages'].get('causal-conv1d','').split('+',1)[0]!='1.7.0':raise ValueError('kernel runtime package causal-conv1d must be1.7.0')
 return meta

def dispatch_proof(functions):
 result={}
 for name,prefix in SYMBOLS.items():
  fn=functions.get(name);seen=set();proof=None
  for _ in range(8):
   if not inspect.isfunction(fn) or id(fn) in seen:break
   seen.add(id(fn));nonlocals=inspect.getclosurevars(fn).nonlocals
   implementation=nonlocals.get('implementation');module=getattr(implementation,'__module__','')
   if nonlocals.get('is_new_implementation') is True and (module==prefix or module.startswith(prefix+'.')):
    proof={'implementation_module':module,'implementation_name':getattr(implementation,'__name__',None),'transformers_original_package_dispatch':True};break
   fn=getattr(fn,'__wrapped__',None)
  if proof is None:raise ValueError(name+': optimized original-package dispatch not verified; reference fallback forbidden')
  result[name]=proof
 return result

def check(expected_pod):
 native=next((v.split(b'=',1)[1].decode() for v in Path('/proc/1/environ').read_bytes().split(b'\0') if v.startswith(b'RUNPOD_POD_ID=')),None)
 if native!=expected_pod:raise ValueError('kernel preflight native pod ID mismatch')
 import importlib.metadata
 import torch
 import causal_conv1d # Import must actually resolve the compiled extension, not just distribution metadata.
 import fla.ops.gated_delta_rule
 from transformers.models.qwen3_5 import modeling_qwen3_5 as model
 names=[*EXPECTED,'causal-conv1d','triton']
 meta={'pod_id':native,'packages':{n:importlib.metadata.version(n) for n in names},'system':platform.system(),'machine':platform.machine(),'python_minor':'.'.join(map(str,sys.version_info[:2])),'cxx11_abi':bool(torch._C._GLIBCXX_USE_CXX11_ABI),'cuda_version':torch.version.cuda,'cuda_available':torch.cuda.is_available(),'device':torch.cuda.get_device_name(0) if torch.cuda.is_available() else ''}
 validate_metadata(meta);meta['dispatch']=dispatch_proof({n:getattr(model,n) for n in SYMBOLS});meta['status']='IMPORT_AND_DISPATCH_ONLY_NO_SPEED_OR_NUMERICAL_CLAIM';return meta

def main():
 p=argparse.ArgumentParser();p.add_argument('--expected-pod',required=True);a=p.parse_args();print(json.dumps(check(a.expected_pod),indent=2))
if __name__=='__main__':main()
