"""§212 dev-only anomaly diagnostics. No dose selection, test input, or rerun."""
import argparse,hashlib,json,sys,time
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify
ROWS=('format_plan','nesting_depth','page_range_digit')
ROOT=Path(__file__).resolve().parents[3]


def cpu_audit(out):
    binding=read(ROOT/'results/g_agreement/understand/e101/DEV_INPUT_BINDING.json')
    key=read(binding['cpu_key_path'])
    assert sha(binding['cpu_key_path'])==binding['cpu_key_sha256']
    sources=read(ROOT/'results/g_agreement/understand/e101/vectors/cpu_only/SOURCES.json')
    shards={s['row']:s for s in read(ROOT/'results/g_agreement/understand/e101/doses/SHARDS.json')['shards']}
    original={};carriers={};summaries=[];per_item=[];public=[];smoke_vectors=[]
    for bank in ('E59','E57'):
        src=sources[bank];meta=Path(src['metadata_path'])
        assert sha(meta)==src['metadata_sha256']
        xs=[x for x in read(meta) if x['split']=='dev' and x['feature'] in ROWS]
        by={x['id']:x for x in xs}
        for x in xs:
            opaque=hashlib.sha256(f'E101:{bank}:{x["id"]}'.encode()).hexdigest();original[opaque]=x
        for cap in src['captures']:
            folder=Path(cap['path']).parent
            assert sha(cap['path'])==cap['sha256']
            order=read(folder/'items.order.json')
            for block in (42,44):
                h=np.load(folder/f'acts{block}.npy',mmap_mode='r')
                for i,oid in enumerate(order):
                    if oid in by:
                        opaque=hashlib.sha256(f'E101:{bank}:{oid}'.encode()).hexdigest();carriers[opaque,block]=h[i].copy()
    for row in ROWS:
        spec=next(p for p in binding['packages'] if p['row']==row);inp=Path(spec['input_root'])
        verify(inp,'INPUT_SEAL.json',spec['input_sha256'])
        xs=read(inp/'items.json');hp=np.load(inp/'vectors.npy',mmap_mode='r')
        ss=shards[row];res=Path(ss['output_root']);verify(res,'OUTPUT_SEAL.json',ss['output_sha256'])
        records={r['id']:r for f in (res/'jobs').glob('*.json') for r in read(f)}
        for block in (44,42):
            unit=np.load(ROOT/f'results/g_agreement/understand/e101/vectors/public/{row}.d{block}.npy')
            raw=np.load(ROOT/f'results/g_agreement/understand/e101/vectors/cpu_only/{row}.raw_d{block}.npy')
            means=[np.mean([carriers[i,b] for (i,b) in carriers if b==block and original[i]['feature']==row and original[i]['label']==label],axis=0,dtype=np.float64) for label in (0,1)]
            assert np.allclose(raw,means[1]-means[0],rtol=1e-5,atol=1e-6)
            for alpha in (.5,1.,2.,4.):
                sub=[x for x in xs if x['block']==block and x['alpha']==alpha];contrasts=[];counts=0
                for x in sub:
                    i=x['base_id'];h=carriers[i,block].astype(np.float64);edited=hp[x['vector_index']].astype(np.float64);delta=edited-h
                    sigma=1-2*original[i]['label'];expected=alpha*sigma*raw
                    err=float(np.linalg.norm(delta-expected));norm=float(np.linalg.norm(delta));cos=float(delta@unit/norm)
                    assert norm>0 and cos*sigma>.99999 and np.linalg.norm(delta-expected)<1e-4*np.linalg.norm(expected)
                    assert key[i]['contrast_target_sign']==sigma
                    rs=records[x['id']];contrast=float(np.mean([a-b for a,b in rs['pair_logprobs']]));counts+=contrast*sigma>0;contrasts.append(contrast)
                    per_item.append(dict(id=x['id'],base_id=i,row=row,block=block,alpha=alpha,delta_norm=norm,expected_delta_norm=float(np.linalg.norm(expected)),delta_dot_d=float(delta@unit),target_signed_cosine=cos*sigma,fp32_composition_error=err,contrast=contrast,target_signed_contrast=contrast*sigma))
                    if alpha==4.:
                        public.append({k:x[k] for k in ('id','base_id','row','block','ids','read_index','candidate_ids')});smoke_vectors.append(edited.astype(np.float32))
                summaries.append(dict(row=row,block=block,alpha=alpha,n=len(sub),target_side=counts,contrast_min=min(contrasts),contrast_max=max(contrasts)))
    out.mkdir(parents=True,exist_ok=False)
    write(out/'CPU_PER_ITEM.json',per_item);write(out/'CPU_SUMMARY.json',dict(status='CPU_CHECKS_PASS_GPU_BASELINE_PENDING',summaries=summaries,
        checks=['sealed dev inputs/outputs','nonzero composed deltas','delta points toward opposite dev class','raw d equals dev mean1-mean0','CPU target signs agree with candidate A=label1 mapping'],
        note='CPU vector arithmetic is not an observation inside the full checkpoint. GPU smoke will record actual hook deltas and unsteered dev contrasts.',GPU_calls=0))
    write(out/'smoke_items.json',public);np.save(out/'smoke_vectors.npy',np.stack(smoke_vectors))
    write(out/'SMOKE_INPUT_SEAL.json',dict(experiment='E101_ANOMALY_212',split='dev',labels_on_pod=False,files={n:sha(out/n) for n in ('smoke_items.json','smoke_vectors.npy')}))


def plain_behaviour(model,items):
    """Frozen candidate token-sum score, with no intervention hook installed."""
    import torch
    device=model.get_input_embeddings().weight.device
    out=[]
    for x in items:
        scores=[]
        for pair in x['candidate_ids']:
            pp=[]
            for candidate in pair:
                ids=torch.tensor([x['ids']+candidate[:-1]],device=device)
                with torch.inference_mode():
                    z=model(input_ids=ids,attention_mask=torch.ones_like(ids),use_cache=False,logits_to_keep=len(candidate)).logits.float()
                    lp=z.log_softmax(-1)
                    pp.append(float(lp[0,torch.arange(len(candidate),device=device),torch.tensor(candidate,device=device)].sum()))
            scores.append(pp)
        out.append(dict(base_id=x['base_id'],row=x['row'],pair_logprobs=scores))
    return out


def observe_patch(model,xs,vectors):
    """Observe production hook input/output without modifying its implementation."""
    import torch
    from .acquisition import patched_forward
    from mats.capture import decoder_blocks
    blocks=decoder_blocks(model);block=xs[0]['block'];before=[];after=[]
    assert block+1<len(blocks),'following block required for observer'
    def pre(module,args,output):
        z=output[0] if isinstance(output,tuple) else output
        before.append(torch.stack([z[i,x['read_index']].float() for i,x in enumerate(xs)]).cpu().numpy())
    def post(module,args,kwargs):
        z=kwargs.get('hidden_states',args[0] if args else None)
        after.append(torch.stack([z[i,x['read_index']].float() for i,x in enumerate(xs)]).cpu().numpy())
    a=blocks[block].register_forward_hook(pre);c=blocks[block+1].register_forward_pre_hook(post,with_kwargs=True)
    try:patched_forward(model,[x['ids'] for x in xs],[x['read_index'] for x in xs],vectors,block,1)
    finally:a.remove();c.remove()
    assert len(before)==len(after)==1
    return before[0],after[0]


def gpu_smoke(inputs,model_path,out,deadline):
    import torch,uuid
    run_id=str(uuid.uuid4())
    from transformers import AutoModelForCausalLM
    from .acquisition import patched_forward,batches
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.capture import decoder_blocks
    verify(inputs,'SMOKE_INPUT_SEAL.json',sha(inputs/'SMOKE_INPUT_SEAL.json'))
    items=read(inputs/'smoke_items.json');vectors=np.load(inputs/'smoke_vectors.npy')
    assert len(items)==504 and {x['block'] for x in items}=={42,44} and {x['row'] for x in items}==set(ROWS)
    assert torch.cuda.is_available() and torch.cuda.device_count()==1
    out.mkdir(parents=True,exist_ok=False);write(out/'HARDWARE.json',dict(actual_gpu_name=torch.cuda.get_device_name(),GPU_count=1))
    model=AutoModelForCausalLM.from_pretrained(model_path,dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
    blocks=decoder_blocks(model);records=[]
    for batch in batches(items,8):
        assert time.time()<deadline-60
        xs=[items[i] for i in batch];b=xs[0]['block']
        before,after=observe_patch(model,xs,vectors[batch])
        for j,(x,h,hp) in enumerate(zip(xs,before,after)):
            records.append(dict(id=x['id'],base_id=x['base_id'],row=x['row'],block=b,alpha=4.,run_id=run_id,code_sha256=sha(__file__),run_kind='SMOKE_DIAGNOSTIC',delta_norm=float(np.linalg.norm(hp-h)),before_norm=float(np.linalg.norm(h)),after_norm=float(np.linalg.norm(hp)),after_matches_supplied_bf16=bool(np.array_equal(hp,torch.tensor(vectors[batch[j]]).to(torch.bfloat16).float().numpy()))))
        (out/'HOOK_DELTAS.json').write_text(json.dumps(records,allow_nan=False))
    unique=list({x['base_id']:x for x in items if x['block']==44}.values());baseline=[]
    for x in unique:
        assert time.time()<deadline-60
        baseline.extend([dict(r,run_id=run_id,code_sha256=sha(__file__),run_kind='SMOKE_DIAGNOSTIC') for r in plain_behaviour(model,[x])]);(out/'UNSTEERED_BASELINE.json').write_text(json.dumps(baseline,allow_nan=False))
    write(out/'OUTPUT_SEAL.json',dict(experiment='E101_ANOMALY_212',status='COMPLETE',split='dev',hook_cells=len(records),unsteered_items=len(baseline),dose_selection=False,post_defect_rerun=False,files={p.name:sha(p) for p in out.iterdir()}))

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('cpu');q.add_argument('--out',type=Path,required=True)
    q=sub.add_parser('gpu');q.add_argument('--inputs',type=Path,required=True);q.add_argument('--model',required=True);q.add_argument('--out',type=Path,required=True);q.add_argument('--deadline',type=float,required=True)
    a=p.parse_args()
    if a.mode=='cpu':cpu_audit(a.out)
    else:gpu_smoke(a.inputs,a.model,a.out,a.deadline)
