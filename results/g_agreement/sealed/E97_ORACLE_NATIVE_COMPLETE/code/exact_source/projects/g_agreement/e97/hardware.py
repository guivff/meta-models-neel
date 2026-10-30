"""Hardware-note smoke checks using sealed historical native readouts only."""
from pathlib import Path
import json
import numpy as np
from projects.g_agreement.e97.capture42 import load_b200

def smoke(backend,reader,inputs,out,write):
    import torch
    ref=json.loads((inputs/f'SMOKE_{reader}.json').read_text())
    h=np.load(inputs/f'SMOKE_{reader}.npy',allow_pickle=False)
    if ref['gpu_type']!='H200' or len(ref['records'])!=3 or h.shape!=(3,5120) or h.dtype!=np.float32 or not np.isfinite(h).all():raise ValueError('Exact three-item H200 reference required')
    model=backend.oracle.model if reader=='oracle' else backend.nla.av
    seen=[]
    def finite(module,args,value):
        if not torch.isfinite(value).all():raise ValueError('Nonfinite hardware-smoke logits')
        seen.append(True)
    hook=model.get_output_embeddings().register_forward_hook(finite)
    try:groups=backend.native_one(reader,h)
    finally:hook.remove()
    if len(groups)!=3 or any(len(x)!=1 for x in groups)or not seen:raise ValueError('Three finite native smoke outputs required')
    comparisons=[]
    for expected,group in zip(ref['records'],groups):
        old,actual=expected['raw'],group[0]['raw'];at=next((i for i,(a,b)in enumerate(zip(old,actual))if a!=b),min(len(old),len(actual)))if old!=actual else None
        comparisons.append(dict(id=expected['id'],exact_match=old==actual,first_divergence_character=at,H200_raw=old,B200_raw=actual))
    write(out/f'B200_SMOKE.{reader}.json',dict(status='PASS',gpu_type='B200',reader=reader,loads=True,finite_logits=True,items=3,hardware_note='cb76843c',reference_seal_sha256=ref['source_reader_seal_sha256'],reference_batch=ref['reference_batch'],smoke_batch=3,batch_context_may_also_affect_byte_parity=True,first_divergence=next((dict(item=x['id'],character=x['first_divergence_character'])for x in comparisons if not x['exact_match']),None),comparisons=comparisons))
