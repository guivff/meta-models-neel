"""E40 single-capture calibration/training pipeline; bounded host/GPU buffers."""
from __future__ import annotations
import time
import numpy as np
from calibration import norms64, calibrate, eligible, FilteredGate


def captured_stream(model, source, capture, clock, progress, ledger, *, device='cuda'):
    import torch
    for item in source:
        clock.check()
        started=time.monotonic()
        ids=item['ids']; positions=np.asarray(item['positions'])
        if not 0<len(ids)<=512 or positions.shape!=(len(ids),):
            raise ValueError('complete unpadded document-local chunk required')
        h=capture(model,ids,list(range(len(ids))),device=device)
        with torch.inference_mode(False):
            raw=h.detach().to(device='cpu',dtype=torch.float32).clone()
        if raw.shape!=(len(ids),5120):
            raise ValueError('raw block44 width mismatch')
        norm=norms64(raw.numpy())
        elapsed=time.monotonic()-started
        progress['raw_captured']+=len(ids);progress['capture_chunks']+=1
        progress['position_zero_excluded']+=int((positions==0).sum())
        if len(ids)==512 and len(progress['full_chunk_seconds'])<3:
            progress['full_chunk_seconds'].append(elapsed)
        ledger({'source_id':item['source_id'],'document_token_start':int(positions[0]),
                'length':len(ids),'padding':0,'capture_chunk':progress['capture_chunks'],
                'target_dtype':'bfloat16','residual_dtype':'float32','environment':'RUNTIME.json'})
        yield raw,positions,norm


def collect_calibration(stream, *, count=1_000_000, d_model=5120):
    """Capture once; preserve the chunk remainder after the exact first1M nonzero positions."""
    import torch
    buffer=torch.empty((count,d_model),dtype=torch.float32,device='cpu')
    norm=np.empty(count,dtype=np.float64)
    filled=0;pending=None
    for raw,positions,nn in stream:
        ix=np.flatnonzero(positions!=0)
        take=min(count-filled,len(ix))
        if take:
            buffer[filled:filled+take].copy_(raw[ix[:take]])
            norm[filled:filled+take]=nn[ix[:take]];filled+=take
        if filled==count:
            if take<len(ix):
                rest=ix[take:];pending=(raw[rest],positions[rest],nn[rest])
            break
    if filled!=count:
        raise ValueError('source exhausted before fixed calibration population')
    return buffer,norm,pending


def eligible_batches(buffer, norms, pending, stream, calibration, progress, *,
                     target=100_000_000,batch_size=4096):
    """The buffered prefix is trained first; source capture resumes once afterwards."""
    import torch
    def pieces():
        for start in range(0,len(buffer),batch_size):
            x=buffer[start:start+batch_size]
            yield x,np.ones(len(x),dtype=np.int64),norms[start:start+len(x)]
        if pending is not None:yield pending
        yield from stream
    batch=torch.empty((batch_size,buffer.shape[1]),dtype=torch.float32,device='cpu')
    used=done=0
    for raw,positions,nn in pieces():
        mask=eligible(nn,positions,calibration)
        progress['norm_excluded']+=int(((positions!=0)&(~mask)).sum())
        selected=raw[np.flatnonzero(mask)]
        offset=0
        while offset<len(selected) and done<target:
            capacity=min(batch_size,target-done)
            take=min(capacity-used,len(selected)-offset)
            batch[used:used+take].copy_(selected[offset:offset+take]);used+=take;offset+=take
            if used==capacity:
                yield batch[:used]
                done+=used;used=0
        if done==target:
            progress['untrained_eligible_tail']+=len(selected)-offset
            return
    raise ValueError('source exhausted before100M eligible unique training positions')


def evaluate_gate(sae,h,positions,calibration,clock,*,batch_size=256,expected=50000,device='cuda'):
    import torch
    if h.shape!=(expected,sae.d_model) or len(positions)!=expected:
        raise ValueError('same sealed heldout gate population required')
    full=FilteredGate(sae.d_model,sae.d_sae);retained=FilteredGate(sae.d_model,sae.d_sae)
    n_zero=n_high=n_overlap=0
    with torch.inference_mode():
        for start in range(0,len(h),batch_size):
            clock.check()
            x=np.array(h[start:start+batch_size],copy=True)
            pos=positions[start:start+len(x)];nn=norms64(x)
            mask=eligible(nn,pos,calibration)
            z=sae.encode(torch.from_numpy(x).to(device))
            r=sae.decode(z).cpu().numpy()
            if not torch.isfinite(z).all():raise ValueError('nonfinite gate code')
            full.update(x,r,active_latents=z.gt(0).any(dim=0).cpu().numpy())
            if mask.any():
                retained.update(x[mask],r[mask],active_latents=z[torch.from_numpy(mask).to(device)].gt(0).any(dim=0).cpu().numpy())
            zero=pos==0;high=nn>calibration['outlier_threshold_raw_norm']
            n_zero+=int(zero.sum());n_high+=int(high.sum());n_overlap+=int((zero&high).sum())
    filtered=retained.result();all_tokens=full.result()
    all_tokens['rule_applied']=False
    return {'filtered':filtered,'all_tokens':all_tokens,'excluded':{
        'position_zero':n_zero,'norm_above_threshold':n_high,'overlap':n_overlap,
        'union':expected-filtered['n_tokens']}}
