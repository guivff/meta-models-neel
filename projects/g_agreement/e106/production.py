"""Post-PASS E106 NLA teacher/train/evaluation worker; no judging or rule analysis."""
import argparse,json,time,math,gc
from pathlib import Path
from . import runtime
from .worker import Clock,frozen_hash,setup_binding
from projects.g_agreement.e96.reconstructor_check import write,digest
from projects.g_agreement.e96.prepare_smoke_inputs import verify


def verified_gate(root):
    verify(root,'OUTPUT_SEAL.json');report=json.loads((root/'REPORT.json').read_text())
    if report.get('status')!='PASS' or report.get('steps')!=10 or report.get('parity_byte_equal')!=3:raise ValueError('NLA gate PASS required')
    if report['frozen_before_sha256']!=report['frozen_after_sha256'] or report['adapter_tensors_changed']<=0:raise ValueError('gate frozen/update proof')
    parity=json.loads((root/'PARITY.json').read_text())
    if len(parity)!=3 or any(not x['byte_equal'] or x['expected_sha256']!=x['actual_sha256'] for x in parity):raise ValueError('three exact gate reads')
    losses=[json.loads((root/f'STEP_{i:02d}.json').read_text())['loss'] for i in range(1,11)]
    if not all(math.isfinite(x) for x in losses):raise ValueError('ten finite gate losses')
    return report


def check_admission(a,phase,inputs,gate):
    if a['experiment']!='E106' or a['phase']!=phase or a['gpu_count']!=1 or not a['external_guard_armed'] or not a['incremental_backup_armed']:raise ValueError('guarded admitted phase')
    if a['planning_envelope_usd']>2500 or a['input_seal_sha256']!=digest(inputs/'INPUT_SEAL.json') or a['gate_seal_sha256']!=digest(gate/'OUTPUT_SEAL.json'):raise ValueError('financial/input/gate binding')
    if not a['analysis_adapter_cpu_tests_passed'] or len(a['analysis_adapter_commit'])!=40 or len(a['analysis_adapter_seal_sha256'])!=64:raise ValueError('sole pre-output adapter')
    cap=a['deadline_epoch']-a['created_epoch'];prior=a['closed_T_custody_seconds']
    if not math.isfinite(prior) or not math.isfinite(cap) or prior<0 or cap<=0 or cap+prior>14400:raise ValueError('T total4GPUh includes gate and every allocation')
    bucket=a['closed_phase_bucket_seconds'];limit=9000 if phase=='evaluate' else 3600
    if not math.isfinite(bucket) or bucket<0 or cap+bucket>limit:raise ValueError('shared teacher/train1h or evaluation2.5h cap')
    if phase=='train' and (len(a['dataset_manifest_commit'])!=40 or len(a['dataset_manifest_sha256'])!=64):raise ValueError('committed final dataset manifest required')
    if phase=='evaluate' and (not math.isfinite(a['max_measured_setup_including_staging_seconds']) or a['max_measured_setup_including_staging_seconds']<=0 or len(a['inventory_seal_sha256'])!=64):raise ValueError('measured paired evaluation setup and inventory binding')
    setup_binding(a)  # Reject invalid prior-profile/staging metadata before model load.


def vectors(inputs,expected):
    import numpy as np
    a=np.load(inputs/'acts42.npy',allow_pickle=False)
    if a.shape!=(expected,5120) or not np.isfinite(a).all():raise ValueError('native vector grid')
    return a


def setup_record(a,elapsed):
    prior,staging,source=setup_binding(a)
    normalized=elapsed+staging
    maximum=max([normalized]+[v for values in prior.values() for v in values])
    return {'verify_and_load_seconds':elapsed,'staging_seconds':staging,'staging_source':source,
            'setup_including_staging_seconds':normalized,'max_own_setup_including_staging_seconds':maximum}


def teacher(inputs,assets,a,c):
    pairs=json.loads((inputs/'DEV_PAIRS.json').read_text());h=vectors(inputs,504)
    if len(pairs)!=504 or any(x['split']!='dev' for x in pairs):raise ValueError('dev selection')
    indices=[i for i,x in enumerate(pairs) if x['role']=='replay']
    if len(indices)!=252:raise ValueError('252replay items')
    t=time.monotonic();runtime.verify_assets(assets,'nla',c.check);nla=runtime.load(assets,'nla')
    c.save('SETUP.json',setup_record(a,time.monotonic()-t))
    for p in nla.av.parameters():p.requires_grad_(False)
    times=[]
    for start in range(0,252,8):
        c.check();t=time.monotonic();ix=indices[start:start+8];raw=runtime.generate('nla',nla,h[ix])
        if len(raw)!=len(ix):raise ValueError('teacher output grid')
        c.save(f'TEACHER_{start:03d}.json',[{'key':pairs[i]['key'],'split':'dev','role':'replay',**x} for i,x in zip(ix,raw)],generated=True)
        times.append(time.monotonic()-t)
        remaining=math.ceil((252-start-len(ix))/8)
        if time.time()+1.25*max(times)*remaining>c.end-120:raise TimeoutError('remaining teacher forecast exceeds admitted training bucket')
    c.save('REPORT.json',{'status':'COMPLETE','phase':'teachers','items':252,'reader':'nla','original_adapter_sha256':runtime.NLA_ADAPTER,'decoding':{'do_sample':False,'batch':8,'max_new_tokens':512,'stop':'</explanation>'},'first_output_utc':c.first})


def train(inputs,assets,a,c,manifest):
    import torch
    if digest(manifest)!=a['dataset_manifest_sha256']:raise ValueError('committed final dataset manifest bytes')
    d=json.loads(manifest.read_text())
    if d['status']!='FINAL_DEV_TRAINING_DATASET_READY' or d['input_seal_sha256']!=digest(inputs/'INPUT_SEAL.json'):raise ValueError('final training dataset lineage')
    records=json.loads((inputs/'TRAINING.json').read_text());h=vectors(inputs,504)
    if len(records)!=504 or any(x['split']!='dev' or not isinstance(x.get('text'),str) or not x['text'] for x in records) or sum(x['role']=='target' for x in records)!=252 or sum(x['role']=='replay' for x in records)!=252 or len({x['key'] for x in records})!=504:raise ValueError('504 unique balanced dev optimizer items')
    t=time.monotonic();runtime.verify_assets(assets,'nla',c.check);nla=runtime.load(assets,'nla');trainable=runtime.attach_rank16(nla)
    c.save('SETUP.json',setup_record(a,time.monotonic()-t))
    t=time.monotonic();before=frozen_hash(nla.av,trainable);hash_seconds=time.monotonic()-t
    old={n:p.detach().cpu().clone() for n,p in trainable.items()}
    c.save('INITIALIZATION.json',{'original_adapter_sha256':runtime.NLA_ADAPTER,'fresh_zero_rank16':True,'disposable_gate_checkpoint_used':False,'frozen_before_sha256':before,'dataset_manifest_commit':a['dataset_manifest_commit'],'dataset_manifest_sha256':digest(manifest),'trainable_names':list(trainable)})
    nla.av.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant':False});nla.av.enable_input_require_grads();nla.av.config.use_cache=False;nla.av.train()
    optimizer=torch.optim.AdamW(list(trainable.values()),lr=1e-4,weight_decay=0.)
    index_rng=torch.Generator(device='cpu').manual_seed(20261029);times=[];losses=[]
    for step in range(300):
        c.check();t=time.monotonic();optimizer.zero_grad(set_to_none=True);total=0.;indices=torch.randint(0,504,(16,),generator=index_rng).tolist()
        for i in indices:
            c.check();answer=nla.tok.encode(records[i]['text'],add_special_tokens=False)+[nla.tok.eos_token_id]
            seq=torch.tensor([nla.prompt_ids+answer],device=nla.device);labels=seq.clone();labels[:,:len(nla.prompt_ids)]=-100
            with nla._inject(torch.as_tensor(h[i:i+1],device=nla.device).float()):
                loss=nla.av(input_ids=seq,attention_mask=torch.ones_like(seq),labels=labels,use_cache=False).loss
                if not torch.isfinite(loss):raise ValueError('nonfinite loss')
                (loss/16).backward();total+=float(loss.detach())/16
        if any(p.grad is not None for n,p in nla.av.named_parameters() if n not in trainable):raise ValueError('frozen gradient')
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in trainable.values()):raise ValueError('nonfinite gradient')
        optimizer.step();losses.append(total);times.append(time.monotonic()-t)
        c.save(f'STEP_{step+1:03d}.json',{'step':step+1,'loss':total,'dev_pair_ids':[records[i]['key'] for i in indices],'seconds':times[-1]})
        if time.time()+1.25*(max(times)*(299-step)+hash_seconds)>c.end-120:raise TimeoutError('remaining fixed training forecast exceeds admitted cap; no automatic retry')
    c.check();after=frozen_hash(nla.av,trainable);changed=sum(not torch.equal(old[n],p.detach().cpu()) for n,p in trainable.items())
    if before!=after or changed<=0:raise ValueError('frozen/update proof')
    nla.av.save_pretrained(c.out/'checkpoint',selected_adapters=['e106_repair']);c.check()
    c.save('LOSS.json',losses)
    c.save('REPORT.json',{'status':'COMPLETE','phase':'train','steps':300,'losses':losses,'frozen_before_sha256':before,'frozen_after_sha256':after,'adapter_tensors_changed':changed,'fresh_production_adapter':True,'dev_only':True,'equal_replay':True,'test_optimizer_items':0,'recipe':{'rank':16,'lr':1e-4,'steps':300,'batch_size':16,'seed':20261029},'first_output_utc':c.first})


def evaluate(inputs,assets,a,c,checkpoint):
    import torch
    verify(checkpoint,'OUTPUT_SEAL.json');r=json.loads((checkpoint/'REPORT.json').read_text())
    if digest(checkpoint/'OUTPUT_SEAL.json')!=a['trained_output_seal_sha256'] or r['status']!='COMPLETE' or r['steps']!=300:raise ValueError('complete trained checkpoint')
    if r['frozen_before_sha256']!=r['frozen_after_sha256'] or r['adapter_tensors_changed']<=0:raise ValueError('trained checkpoint proof')
    items=json.loads((inputs/'EVAL_ITEMS.json').read_text());h=vectors(inputs,1208)
    if len(items)!=1208 or sum(x['split']=='placebo' for x in items)!=200 or any({'label','value','target_by_cell'}&x.keys() for x in items):raise ValueError('label-free1008test+200placebo grid')
    for cell in ('original','intervention'):
        c.check();t=time.monotonic();runtime.verify_assets(assets,'nla',c.check);nla=runtime.load(assets,'nla')
        if cell=='intervention':
            runtime.attach_rank16(nla)
            nla.av.load_adapter(str(checkpoint/'checkpoint/e106_repair'),adapter_name='e106_repair',is_trainable=False)
            original=next(x for x in nla.av.peft_config if x!='e106_repair');nla.av.base_model.set_adapter([original,'e106_repair'])
        for p in nla.av.parameters():p.requires_grad_(False)
        nla.av.eval();setup_seconds=time.monotonic()-t;times=[]
        setup=setup_record(a,setup_seconds)
        max_setup=max(a['max_measured_setup_including_staging_seconds'],setup['max_own_setup_including_staging_seconds'])
        c.save(cell+'_SETUP.json',dict(setup,native_unprefixed=True,reader='nla',block=42,max_own_setup_including_staging_seconds=max_setup))
        for start in range(0,1208,32):
            c.check();t=time.monotonic();raw=runtime.generate('nla',nla,h[start:start+32])
            if len(raw)!=min(32,1208-start):raise ValueError('evaluation grid')
            c.save(f'{cell}_{start:04d}.json',[{'key':x['key'],'id':x['id'],'row':x['row'],'split':x['split'],'reader':'nla','cell':cell,'block':42,**v} for x,v in zip(items[start:start+32],raw)],generated=True)
            times.append(time.monotonic()-t)
            # I-4's admission supplies full measured setup/profile forecast; this
            # retained pilot adds a live conservative remaining-work stop check.
            batches=math.ceil((1208-start-len(raw))/32)+(38 if cell=='original' else 0)
            future_setup=max_setup if cell=='original' else 0
            if time.time()+future_setup+1.25*max(times)*batches>c.end-120:raise TimeoutError('complete paired evaluation forecast exceeds cap')
        del nla;gc.collect();torch.cuda.empty_cache()
    c.save('REPORT.json',{'status':'COMPLETE','phase':'evaluate','reader':'nla','items':1208,'outputs':2416,'paired':True,'inventory_seal_sha256':a['inventory_seal_sha256'],'first_output_utc':c.first})


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['teachers','train','evaluate'],required=True)
    for k in ('inputs','assets','admission','gate','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--manifest',type=Path);p.add_argument('--checkpoint',type=Path);x=p.parse_args()
    if x.out.exists():raise FileExistsError('no output replacement')
    verified_gate(x.gate);verify(x.inputs,'INPUT_SEAL.json');a=json.loads(x.admission.read_text());check_admission(a,x.phase,x.inputs,x.gate)
    if x.phase=='train' and x.manifest is None:raise ValueError('final committed manifest')
    if x.phase=='evaluate' and x.checkpoint is None:raise ValueError('trained output directory')
    assets=json.loads(x.assets.read_text());x.out.mkdir(parents=True);c=Clock(x.out,a['deadline_epoch'])
    try:
        import torch
        if torch.cuda.device_count()!=1:raise ValueError('one visible GPU')
        torch.set_num_threads(8);torch.manual_seed(20261029);torch.cuda.manual_seed_all(20261029)
        if x.phase=='teachers':teacher(x.inputs,assets,a,c)
        elif x.phase=='train':train(x.inputs,assets,a,c,x.manifest)
        else:evaluate(x.inputs,assets,a,c,x.checkpoint)
    except Exception as e:
        c.save('FAILURE.json',{'status':'INCOMPLETE_OPERATIONAL','phase':x.phase,'reason':str(e),'type':type(e).__name__,'first_output_utc':c.first});raise
    finally:
        write(x.out/'OUTPUT_SEAL.json',{'phase':x.phase,'first_output_utc':c.first,'gate_seal_sha256':digest(x.gate/'OUTPUT_SEAL.json'),'input_seal_sha256':digest(x.inputs/'INPUT_SEAL.json'),'files':{str(f.relative_to(x.out)):digest(f) for f in sorted(x.out.rglob('*')) if f.is_file() and f.name!='OUTPUT_SEAL.json'}})

if __name__=='__main__':main()
