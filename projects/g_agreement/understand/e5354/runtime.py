"""Thin extensions to the pinned E36 backend; no row question in native carriers."""
import sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'vendor'))
from e36_worker import NativeBackend

class Backend(NativeBackend):
 def native(self,reader,h):
  import torch
  from mats.readers.nla import Sampling,extract_explanation
  sampling=Sampling(temperature=0,top_p=1.,top_k=0,max_new_tokens=128)
  with torch.no_grad():
   if reader=='oracle':
    raw=self.oracle.verbalize(torch.as_tensor(h),44,k=1,sampling=sampling,batch=8)
    return [{'raw':x[0],'text':x[0],'malformed':False} for x in raw]
   raw=self.nla.verbalize_raw(torch.as_tensor(h),k=1,sampling=sampling,batch=8)
   result=[]
   for x in raw:
    payload=extract_explanation(x[0]);result.append({'raw':x[0],'text':payload if payload is not None else x[0],'malformed':payload is None})
   return result
