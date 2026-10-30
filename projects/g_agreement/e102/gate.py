"""One-GPU E102 feasibility gate. Never produces a production adapter.

Requires a creation-based deadline and external stop guard in an I-4 admission.
Three sealed readouts must match before dev self-distillation or training.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
from datetime import datetime, timezone
from projects.g_agreement.e96.prepare_smoke_inputs import verify
from projects.g_agreement.e96.reconstructor_check import digest, write


def utc(): return datetime.now(timezone.utc).isoformat()


def execute(a):
    import numpy as np
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from mats.readers.olens import OracleLens
    from mats.readers.nla import Sampling
    a.out.mkdir(parents=True, exist_ok=False)
    admission = json.loads(a.admission.read_text())
    if admission['experiment'] != 'E102_GATE' or admission['gpu_count'] != 1 or not admission['external_guard_armed']:
        raise ValueError('single GPU guarded admission required')
    if admission['input_seal_sha256'] != digest(a.inputs / 'INPUT_SEAL.json'):
        raise ValueError('admission input binding')
    if admission['projected_all_track_upper_usd'] > 1500:
        raise ValueError('budget ceiling')
    end = admission['deadline_epoch']
    if end - admission['created_epoch'] > 3600:
        raise ValueError('gate maximum one GPU hour including staging')
    def check():
        if time.time() >= end - 180: raise TimeoutError('retrieval reserve')
    check()
    assets = json.loads(a.asset_manifest.read_text())
    if assets['revisions']['model'] != '6a9e13bd6fc8f0983b9b99948120bc37f49c13e9':
        raise ValueError('base model revision')
    model_files = [f for f in assets['files'] if Path(f['path']).is_relative_to(assets['model'])]
    if not model_files: raise ValueError('empty model manifest')
    for f in model_files:
        check()
        local = a.model / Path(f['path']).relative_to(assets['model'])
        if digest(local) != f['sha256']: raise ValueError('base model bytes: '+local.name)
    seal = verify(a.inputs, 'INPUT_SEAL.json')
    if set(seal['files']) != {'parity.json','parity.npy','dev_ids.json','dev.npy'} or seal['training_split'] != 'dev':
        raise ValueError('gate input schema')
    if torch.cuda.device_count() != 1: raise ValueError('exactly one GPU')
    torch.set_num_threads(8)
    torch.manual_seed(20261029); torch.cuda.manual_seed_all(20261029)
    cfg = json.loads((a.adapter / 'adapter_config.json').read_text())
    if cfg['r'] != 16 or cfg['peft_type'] != 'LORA': raise ValueError('rank16 LoRA only')
    if digest(a.adapter / 'adapter_model.safetensors') != '7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa':
        raise ValueError('pinned adapter bytes')
    model = AutoModelForCausalLM.from_pretrained(str(a.model), dtype=torch.bfloat16, device_map='cuda', local_files_only=True)
    for p in model.parameters(): p.requires_grad_(False)
    model = PeftModel.from_pretrained(model, str(a.adapter), is_trainable=True)
    model.eval()
    tok = AutoTokenizer.from_pretrained(str(a.model), local_files_only=True)
    lens = OracleLens(model=model, tok=tok)
    trainable = {n:p for n,p in model.named_parameters() if p.requires_grad}
    if not trainable or any('.lora_A.' not in n and '.lora_B.' not in n for n in trainable):
        raise ValueError('only original LoRA factors may train')
    write(a.out/'PARAMETERS.json', {'trainable_names': list(trainable), 'trainable_count':sum(p.numel() for p in trainable.values()), 'base_requires_grad':False, 'gpu':torch.cuda.get_device_name(0)})
    greedy = Sampling(temperature=0, max_new_tokens=128)
    parity = json.loads((a.inputs/'parity.json').read_text())
    pv = torch.from_numpy(np.load(a.inputs/'parity.npy',allow_pickle=False)).float()
    report = []
    first = None
    for i,r in enumerate(parity):
        check()
        actual = lens.verbalize(pv[i:i+1],44,k=1,sampling=greedy,batch=1)[0][0]
        if first is None: first = utc(); write(a.out/'FIRST_OUTPUT.json',{'first_output_utc':first})
        equal = actual.encode('utf-8') == r['expected_text'].encode('utf-8')
        report.append({'id':r['id'],'actual':actual,'expected_sha256':hashlib.sha256(r['expected_text'].encode()).hexdigest(),'byte_equal':equal})
        write(a.out/'PARITY.json',report)
    if len(report) != 3 or not all(r['byte_equal'] for r in report):
        raise RuntimeError('sealed greedy parity failed; no training performed')
    # Dev-only self-distillation targets, frozen before any optimizer exists.
    dev = torch.from_numpy(np.load(a.inputs/'dev.npy',allow_pickle=False)).float()
    ids = json.loads((a.inputs/'dev_ids.json').read_text())
    if len(ids)!=16 or dev.shape!=(16,5120) or set(ids)&{r['id'] for r in parity}:
        raise ValueError('disjoint 16 dev inputs')
    targets=[]
    for i in range(16):
        check(); targets.append(lens.verbalize(dev[i:i+1],44,k=1,sampling=greedy,batch=1)[0][0])
    write(a.out/'DEV_TEACHER.json',{'ids':ids,'text':targets,'split':'dev','sealed_before_optimizer_utc':utc()})
    write(a.out/'DEV_TEACHER_SEAL.json',{'files':{'DEV_TEACHER.json':digest(a.out/'DEV_TEACHER.json')}})
    def base_hash():
        h=hashlib.sha256()
        for n,p in model.named_parameters():
            if n not in trainable:
                h.update(n.encode());h.update(p.detach().cpu().contiguous().view(torch.uint8).numpy().tobytes())
        return h.hexdigest()
    check(); before = base_hash()
    old = {n:p.detach().cpu().clone() for n,p in trainable.items()}
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False})
    model.config.use_cache=False
    model.train()
    optimizer=torch.optim.AdamW(list(trainable.values()),lr=1e-4,weight_decay=0.0)
    carrier,slot=lens.carrier(44)
    losses=[]
    for step in range(10):
        check(); optimizer.zero_grad(set_to_none=True); total=0.
        # Effective batch16, fixed microbatch1; no search.
        for i in torch.randperm(16).tolist():
            check()
            answer=tok.encode(targets[i],add_special_tokens=False)+[tok.eos_token_id]
            seq=torch.tensor([carrier+answer],device='cuda')
            e=lens._embed(seq,slot,dev[i:i+1]).detach().requires_grad_(True)
            labels=seq.clone();labels[:,:len(carrier)]=-100
            loss=model(inputs_embeds=e,attention_mask=torch.ones_like(seq),labels=labels,use_cache=False).loss
            if not torch.isfinite(loss): raise ValueError('nonfinite loss')
            (loss/16).backward();total+=float(loss.detach())/16
        if any(p.grad is not None for n,p in model.named_parameters() if n not in trainable):
            raise ValueError('base gradient')
        if not all(p.grad is None or torch.isfinite(p.grad).all() for p in trainable.values()):
            raise ValueError('nonfinite adapter gradient')
        optimizer.step()
        losses.append({'step':step+1,'loss':total,'utc':utc()});write(a.out/'LOSS.json',losses)
        print(json.dumps(losses[-1]),flush=True)
    check(); after=base_hash()
    changed=sum(not torch.equal(old[n],p.detach().cpu()) for n,p in trainable.items())
    if before!=after or changed==0: raise ValueError('frozen-base or adapter-update check failed')
    model.save_pretrained(a.out/'disposable_adapter')
    write(a.out/'REPORT.json',{'status':'PASS','steps':10,'parity_byte_equal':3,'base_before_sha256':before,'base_after_sha256':after,'adapter_tensors_changed':changed,'first_output_utc':first,'production_initialization':'original pinned checkpoint, never this disposable adapter'})


def main():
    p=argparse.ArgumentParser()
    for name in ('inputs','out','model','adapter','admission','asset-manifest'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise FileExistsError('refuse to overwrite prior gate outputs')
    try: execute(a)
    except Exception as e:
        if a.out.exists(): write(a.out/'FAILURE.json',{'status':'GATE_DID_NOT_PASS','reason':str(e),'type':type(e).__name__,'utc':utc()})
        raise
    finally:
        if a.out.exists():write(a.out/'OUTPUT_SEAL.json',{'files':{str(f.relative_to(a.out)):digest(f) for f in sorted(a.out.rglob('*')) if f.is_file() and f.name!='OUTPUT_SEAL.json'}})

if __name__=='__main__':main()
