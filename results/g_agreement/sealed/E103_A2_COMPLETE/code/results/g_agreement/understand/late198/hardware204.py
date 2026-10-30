"""§204 hardware receipt and smoke gate; no credentials or provider actions on pods."""
import math
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from contract import read,write,sha,require,digest
AUTHORITY='cb76843cc777c90e3fab8056f2f0abab68731e3d'


def actual_gpu(assignment):
    import torch
    require(assignment['gpu_type'] in ('H200','B200'),'authorized GPU type')
    require(torch.cuda.is_available() and torch.cuda.device_count()==1,'one visible GPU')
    name=torch.cuda.get_device_name(0)
    require(assignment['gpu_type'] in name,'actual device matches assignment')
    return name


def bind_units(assignment,units,reused=None):
    require(assignment['hardware_authority']==AUTHORITY and assignment['gpu_type'] in ('H200','B200'),'hardware authority')
    hardware=assignment['analysis_unit_gpu_types']
    require(set(hardware)==set(map(str,units)) and all(v==assignment['gpu_type'] for v in hardware.values()),'same GPU type for each whole analysis unit')
    if reused:
        require(set(reused)==set(map(str,units)),'all reused rows need original hardware evidence')
        for unit,old in reused.items():
            require(set(old)=={'gpu_type','output_seal_sha256'} and digest(old['output_seal_sha256']) and
                old['gpu_type']==hardware[unit],'reused row placebo must match original hardware')
    return hardware


def production_gate(assignment,receipt_path,assets_path,capabilities):
    actual=actual_gpu(assignment)
    if assignment['gpu_type']=='B200':
        require(receipt_path and sha(receipt_path)==assignment['b200_smoke_receipt_sha256'],'B200 smoke identity')
        r=read(receipt_path)
        require(r['status']=='PASS' and r['gpu_type']=='B200' and r['items']==3 and r['finite_outputs'] is True and
            r['image_digest']==assignment['image_digest'] and r['stack_sha256']==assignment['stack_sha256'] and
            r['assets_sha256']==sha(assets_path) and set(capabilities)<=set(r['capabilities']) and
            len(r['comparisons'])==3*len(r['capabilities']),'same-image/stack/assets three-item smoke required')
    return dict(gpu_type=assignment['gpu_type'],actual_gpu_name=actual,image_digest=assignment.get('image_digest'),
        stack_sha256=assignment.get('stack_sha256'),b200_smoke_receipt_sha256=assignment.get('b200_smoke_receipt_sha256'))


def load_oracle(runtime):
    """Reuse exact registered loaders without the superseded fallback wait policy."""
    import gc,os,sys,torch
    from contract import ROOT
    actual_gpu(runtime.hardware_assignment)
    runtime.model=runtime.tok=None;gc.collect();torch.cuda.empty_cache()
    sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e56/job'))
    from worker56 import Backend
    from projects.g_agreement.blindspot import run as operational
    class AuthorizedBackend(Backend):
        def load_oracle(self):
            actual_gpu(self.assignment)
            os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
            self.oracle=operational._load_oracle(operational._assets(self.assets_path,names=('model','olens')))
    runtime.readers=AuthorizedBackend(ROOT,runtime.assets,runtime.hardware_assignment)
    runtime.readers.load_oracle()


def divergence(a,b):
    x=a.encode('utf-8');y=b.encode('utf-8')
    index=next((i for i,(u,v) in enumerate(zip(x,y)) if u!=v),None)
    if index is None and len(x)!=len(y):index=min(len(x),len(y))
    return dict(equal=x==y,first_divergence_position=index,position_unit='UTF-8 byte',candidate_length=len(x),h200_length=len(y))


def finite(value):
    if isinstance(value,dict):return all(finite(x) for x in value.values())
    if isinstance(value,(list,tuple)):return all(finite(x) for x in value)
    if isinstance(value,(float,np.floating)):return math.isfinite(value)
    if isinstance(value,np.ndarray):return bool(np.isfinite(value).all())
    return True


def smoke(items,reference,assignment,backend,out,assets_sha256):
    """Three sealed public items; divergence reported, never an equality gate."""
    require(len(items)==3 and len({x['id'] for x in items})==3,'three distinct sealed items')
    require(reference['status']=='VERIFIED_H200_REFERENCE' and reference['gpu_type']=='H200' and
        reference['source_output_seals'] and all(digest(h) for h in reference['source_output_seals']),'CPU-verified original H200 reference')
    require(assignment['gpu_type']=='B200' and digest(assignment['stack_sha256']) and
        assignment['image_digest'].startswith('sha256:') and digest(assignment['image_digest'][7:]),'immutable B200 image/stack identity')
    mode=reference['mode'];require(mode in ('text','readers'),'smoke capability')
    comparisons=[];outputs=[]
    def save_first(item,reader,result):
        if not (out/'FIRST_READOUT.json').exists():
            write(out/'FIRST_READOUT.json',dict(id=item['id'],reader=reader,**result))
    try:
        if mode=='text':backend.load_base()
        else:backend.load_oracle()
        reader_values=[];nla_vectors=[]
        for item in items:
            require(set(item)=={'id','ids','max_new_tokens','h200'},'smoke public allowlist')
            require(item['ids'] and all(type(t)is int and t>=0 for t in item['ids']),'sealed tokens')
            if mode=='text':
                require(item['max_new_tokens'] in (32,128),'registered text limit')
                result=backend.text([item['ids']],max_new_tokens=item['max_new_tokens'])[0]
                require(finite(backend.next_token([item['ids']])) and finite(result),'finite model outputs')
                values={'text':result}
                save_first(item,'text',result)
            else:
                h=backend.capture_all(dict(ids=item['ids']),(42,44))
                require(all(np.asarray(v).shape==(len(item['ids']),5120) and finite(v) for v in h.values()),'finite capture')
                values={'oracle':backend.sweep('oracle',h[44][-1:],44)[0]}
                save_first(item,'oracle',values['oracle'])
                nla_vectors.append(h[42][-1:].copy())
            reader_values.append(values)
        if mode=='readers':
            backend.load_nla()
            for values,h in zip(reader_values,nla_vectors):values['nla']=backend.sweep('nla',h,42)[0]
        for item,values in zip(items,reader_values):
            require(finite(values),'finite reader outputs')
            require(set(item['h200'])==set(values) and all(set(v)=={'raw'} for v in item['h200'].values()),'matching original H200 capabilities')
            for reader,result in values.items():
                require(isinstance(result['raw'],str) and isinstance(item['h200'][reader]['raw'],str),'native raw text')
                comparisons.append(dict(id=item['id'],reader=reader,**divergence(result['raw'],item['h200'][reader]['raw'])))
                outputs.append(dict(id=item['id'],reader=reader,**result))
        write(out/'SMOKE_OUTPUTS.json',outputs)
        receipt=dict(status='PASS',authority=AUTHORITY,gpu_type='B200',actual_gpu_name=assignment['actual_gpu_name'],
            image_digest=assignment['image_digest'],stack_sha256=assignment['stack_sha256'],assets_sha256=assets_sha256,
            items=3,finite_outputs=True,capabilities=['text'] if mode=='text' else ['oracle','nla'],
            comparisons=comparisons,reference_source_output_seals=reference['source_output_seals'],
            smoke_outputs_sha256=sha(out/'SMOKE_OUTPUTS.json'))
        receipt.update(smoke_provenance(out))
        receipt['e95_validation']=dict(verified=True,before_production=True,model_loaded=True,reader_loaded=mode=='readers',
            finite_outputs=True,decoding_unchanged=True,image_id=assignment['image_digest'],seal_sha256=assignment['source_seal_sha256'],
            items=[dict(id=item['id'],sealed_h200_readout_sha256=reference['h200_readout_sha256'][item['id']],
                first_divergence_position=next((c['first_divergence_position'] for c in comparisons
                    if c['id']==item['id'] and c['first_divergence_position'] is not None),None)) for item in items])
        require(all(digest(x['sealed_h200_readout_sha256']) for x in receipt['e95_validation']['items']),'sealed original H200 readouts')
        write(out/'SMOKE_RECEIPT.json',receipt)
        return receipt
    except BaseException as error:
        write(out/'STOP_REQUIRED.json',dict(status='FAILED_STOP_POD',pod_id=assignment['pod_id'],gpu_type='B200',
            reason_type=type(error).__name__,production_allowed=False))
        raise


def operator_gate(receipt_path,stop_own_pod):
    """Operator passes its existing verified stop routine; never a pod-side token."""
    if receipt_path.exists() and read(receipt_path).get('status')=='PASS':return
    proof=stop_own_pod()
    require(proof.get('status')=='EXITED','failed smoke requires verified own-pod stop')
    raise RuntimeError('B200 smoke failed; own pod stopped; production forbidden')


def smoke_provenance(out):
    p=out/'FIRST_READOUT.json'
    if not p.exists():return dict(first_output_utc='unknown',first_output_evidence=None)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        first_output_evidence=dict(member=p.name,sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,source='file mtime'))


def validate_e95(assignment,plan,reused,receipt_path,hardware):
    import sys
    from contract import ROOT
    sys.path.insert(0,str(ROOT))
    from projects.g_agreement.e95.hardware import validate_assignment
    observed=hardware['actual_gpu_name']
    gpu=next(t for t in ('H200','B200') if t in observed)
    a=dict(assignment,observed_gpu_type=gpu,image_id=assignment.get('image_digest'),row_indices=plan['row_indices'])
    smoke_receipt=read(receipt_path)['e95_validation'] if receipt_path else None
    return validate_assignment(a,plan['row_roster'],{int(k):v['gpu_type'] for k,v in (reused or {}).items()},smoke_receipt)
