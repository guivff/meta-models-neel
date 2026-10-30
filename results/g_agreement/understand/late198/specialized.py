"""Owner bindings: E82 every read position; E86 complete-answer filtering and ranks.

Uses the existing Runtime, native adapters, timing/deadline and sealing code.
No private truth, question category, or behavioural label enters these workers.
"""
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import math
from pathlib import Path
import sys
import time
import numpy as np
from contract import *
from runtime import Runtime
from worker import Clock,batches
from batch_parity import check_outputs,trim_generated
HERE=Path(__file__).resolve().parent


def provenance(out):
    files=[p for p in out.rglob('*.json') if p.parent.name=='jobs' or p.name.startswith('PARITY_')]
    if not files:return dict(first_output_utc='unknown',first_output_evidence=None)
    p=min(files,key=lambda p:p.stat().st_mtime_ns)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),
        first_output_evidence=dict(member=str(p.relative_to(out)),sha256=sha(p),mtime_ns=p.stat().st_mtime_ns,source='file mtime'))


def validate_public(items,exp):
    require(items and len({x['id'] for x in items})==len(items),'unique public records')
    for x in items:
        require(set(x)==({'id','input_ids','prompt','benchmark_offsets','read_positions'} if exp=='E82' else
                         {'id','input_ids','prompt','read_position','max_new_tokens'}),'strict owner public allowlist')
        require(x['input_ids'] and all(type(t)is int and t>=0 for t in x['input_ids']),'token IDs')
        if exp=='E82':
            ps=x['read_positions'];require(ps and ps==sorted(set(ps)) and all(type(p)is int and 0<=p<len(x['input_ids']) for p in ps),'positions')
            require(x['benchmark_offsets']==[p-len(x['input_ids']) for p in ps],'registered negative offsets')
        else:
            require(x['max_new_tokens'] in (1,16) and x['read_position']==len(x['input_ids'])-1,'frozen E86 filter')
    if exp=='E82':require(len(items)==209 and sum(len(x['read_positions']) for x in items)==6790,'E82 full209/6790')
    else:require(len(items)==12465,'E86 full reserve')
    return items


class BoundRuntime(Runtime):
    def complete_answer(self,sequences,limit):
        import torch
        require(limit in (1,16),'frozen E86 generation length')
        model,tok,cm,tokens=self.token_batch(sequences)
        with cm,torch.inference_mode():
            output=model.generate(input_ids=tokens,attention_mask=torch.ones_like(tokens),do_sample=False,
                max_new_tokens=limit,pad_token_id=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id)
        eos=getattr(model.generation_config,'eos_token_id',None)
        if eos is None:eos=tok.eos_token_id
        eos=set(eos if isinstance(eos,(list,tuple)) else [eos])
        result=[]
        for row in output[:,tokens.shape[1]:].cpu().tolist():
            ids=trim_generated(row,eos);ended=bool(ids and ids[-1] in eos)
            result.append(dict(token_ids=ids[:-1] if ended else ids,finish_reason='eos' if ended else 'length'))
        return result

    def capture_positions(self,item,positions):
        import torch
        sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
        from mats.capture import capture
        model,tok,cm=self.subject()
        with cm,torch.inference_mode():
            result=capture(model,[item['input_ids']],(42,44),[positions],batch_size=1,pad_id=tok.pad_token_id or 0)
        return {l:h[0].float().cpu().numpy() for l,h in result.items()}

    def rank_distributions(self,item,h44):
        """Full-vocabulary logits: no requested truth ID, truncation or top-k."""
        import torch
        sys.path.insert(0,str(ROOT))
        from projects.g_agreement.core.model import final_norm,unembed_weight
        model,tok,cm,tokens=self.token_batch([item['input_ids']])
        with cm,torch.inference_mode():
            full=model(input_ids=tokens,attention_mask=torch.ones_like(tokens),use_cache=False,logits_to_keep=1).logits[0,-1].float()
            norm=final_norm(model);p=next(norm.parameters())
            h=torch.as_tensor(h44,device=p.device,dtype=p.dtype)
            lens=norm(h).float() @ unembed_weight(model).float().T
        require(full.ndim==lens.ndim==1 and full.shape==lens.shape,'complete matching vocabulary')
        return dict(next_token_logits=full.cpu().numpy(),block44_logit_lens=lens.cpu().numpy())


def filter_jobs(items):
    buckets=defaultdict(list)
    for x in items:buckets[x['max_new_tokens'],len(x['input_ids'])].append(x)
    jobs=[(limit,chunk) for (limit,_),xs in buckets.items() for chunk in batches(xs,64)]
    return sorted(jobs,key=lambda x:(-len(x[1]),x[0],-len(x[1][0]['input_ids'])))


def filter86(items,b,c,out,binding,profile=False):
    jobs=filter_jobs(items);full=jobs
    if profile:
        jobs=[]
        for limit in (1,16):
            choices=[job for job in full if job[0]==limit and len(job[1])>=32]
            require(len(choices)>=3,'three batch>=32 timing samples per filter phase');jobs+=choices[:3]
    c.call('base_setup',b.load_base)
    b.check_tokens([dict(text=x['prompt'],ids=x['input_ids']) for x in items])
    stage=out/'jobs';stage.mkdir();warmed=set();all_rows=[]
    for number,(limit,chunk) in enumerate(jobs):
        phase=f'filter{limit}'
        if limit not in warmed:
            dummy=[b.synthetic()[0]]*64
            c.call(phase+'_warmup_discarded',lambda:b.complete_answer(dummy,limit))
        values=c.call(phase,lambda:b.complete_answer([x['input_ids'] for x in chunk],limit),real=True)
        require(len(values)==len(chunk),'filter output count')
        if limit not in warmed:
            require(len(chunk)>=8,'eight real filter parity items')
            serial=[c.call(phase+'_serial_parity',lambda x=x:b.complete_answer([x['input_ids']],limit))[0] for x in chunk[:8]]
            check_outputs(values[:8],serial,out/f'PARITY_{limit}.json',[x['id'] for x in chunk[:8]],64);warmed.add(limit)
        rows=[dict(id=x['id'],**v) for x,v in zip(chunk,values)]
        write(stage/f'filter_{number:05d}.json',rows);all_rows+=rows
    if profile:
        forecast=sum(sum(k==limit for k,_ in full)*np.mean(c.observed[f'filter{limit}']) for limit in (1,16))
        overhead=sum(x['seconds'] for x in c.events if not x['real'])
        write(out/'MEASURED_PROFILE.json',dict(binding,status='TIMING_ONLY_NOT_SCIENCE',phase='E86_filter',
            forecast_seconds=1.25*(forecast+overhead+60),margin=1.25,parity_items_per_phase=8,
            batches_per_phase=3,batch_size=64,**provenance(out)))
    else:
        require({x['id'] for x in all_rows}=={x['id'] for x in items} and len(all_rows)==len(items),'complete filter reserve')
        ordered={x['id']:x for x in all_rows};write(out/'FILTER_OUTPUTS.json',[ordered[x['id']] for x in items])
        seal(out,'FILTER_SEAL.json',**binding,status='COMPLETE',**provenance(out))


def selected86(items,selection):
    byid={x['id']:x for x in items};seen=set()
    for x in selection:
        require(set(x)=={'id','split','reader_allowed','full_rank_vectors_required'},'public CPU selection allowlist')
        require(x['id'] in byid and x['id'] not in seen and x['split'] in ('dev','test'),'unique selected records');seen.add(x['id'])
        require(type(x['reader_allowed'])is bool and type(x['full_rank_vectors_required'])is bool,'public permissions')
        require(not x['reader_allowed'] or x['split']=='test','dev never gets readers')
    return [byid[x['id']] for x in selection]


def capture_bound(items,exp,b,c,out,binding,selection=None):
    selected=items if exp=='E82' else selected86(items,selection)
    c.call('base_setup',b.load_base)
    b.check_tokens([dict(text=x['prompt'],ids=x['input_ids']) for x in selected])
    stage=out/'capture';stage.mkdir();index=[];permissions={x['id']:x for x in selection or []}
    c.call('capture_warmup_discarded',lambda:b.capture_positions(dict(input_ids=b.synthetic()[0]),[0]))
    for i,x in enumerate(selected):
        positions=x['read_positions'] if exp=='E82' else [x['read_position']]
        values=c.call('capture',lambda:b.capture_positions(x,positions),real=True)
        files={}
        for l in (42,44):
            h=values[l];require(h.shape==(len(positions),5120) and np.isfinite(h).all(),'captured exact positions')
            name=f'{i:05d}_{l}.npy';np.save(stage/name,h,allow_pickle=False);files[str(l)]=name
        ranks={}
        if exp=='E86' and permissions[x['id']]['full_rank_vectors_required']:
            ds=c.call('full_rank_distributions',lambda:b.rank_distributions(x,values[44][0]),real=True)
            for name,v in ds.items():
                require(v.ndim==1 and np.isfinite(v).all(),'full vocabulary finite logits')
                path=f'{i:05d}_{name}.npy';np.save(stage/path,v.astype(np.float32),allow_pickle=False);ranks[name]=path
        index.append(dict(id=x['id'],positions=positions,files=files,rank_distributions=ranks))
    write(stage/'INDEX.json',index)
    seal(stage,'CAPTURE_SEAL.json',**binding,reader_outputs=0,rank_format='float32 full-vocabulary logits; CPU truth ranking only')
    return stage


def read_bound(items,exp,b,c,out,binding,root,selection=None,release=None,profile=False):
    s=verify(root,'CAPTURE_SEAL.json',sha(root/'CAPTURE_SEAL.json'))
    require(s['input_archive_sha256']==binding['input_archive_sha256'] and s['experiment']==exp,'capture bank identity')
    allowed={x['id'] for x in items}
    if exp=='E86':
        selected86(items,selection)
        permitted=[x['id'] for x in selection if x['reader_allowed']]
        require(release and set(release)=={'capture_seal_sha256','selection_sha256','released_ids','cpu_gate_receipt_sha256','authorized'},'CPU reader gate required')
        require(release['authorized'] is True and release['capture_seal_sha256']==sha(root/'CAPTURE_SEAL.json') and
                release['selection_sha256']==binding['selection_sha256'] and digest(release['cpu_gate_receipt_sha256']),'capture-bound CPU gate')
        require(len(set(release['released_ids']))==len(release['released_ids']) and set(release['released_ids'])<=set(permitted),'only permitted test IDs')
        allowed=set(release['released_ids'])
    index=read(root/'INDEX.json');expected={x['id'] for x in (items if exp=='E82' else selected86(items,selection))}
    require({x['id'] for x in index}==expected and len(index)==len(expected),'complete capture bank')
    cell_list=[(row,p,j) for row in index if row['id'] in allowed for j,p in enumerate(row['positions'])]
    require(cell_list,'no eligible readers')
    stage=out/'jobs';stage.mkdir();b.native_batch_size=32
    profile_rows=[]
    for reader,l in (('oracle',44),('nla',42)):
        c.call(reader+'_setup',b.load_oracle if reader=='oracle' else b.load_nla)
        c.call(reader+'_warmup_discarded',lambda:b.native(reader,np.random.default_rng(20261028).standard_normal((32,5120)).astype(np.float32)))
        chunks=batches(cell_list,32);selected=chunks[:3] if profile else chunks
        require(len(selected[0])>=8,'eight real reader parity cells')
        cache={};count=0
        for i,chunk in enumerate(selected):
            for row,_,_ in chunk:
                if row['id'] not in cache:cache[row['id']]=np.load(root/row['files'][str(l)],allow_pickle=False)
            h=np.stack([cache[row['id']][j] for row,p,j in chunk]);before=h.tobytes()
            values=c.call(reader+'_native',lambda:b.native(reader,h),real=True)
            require(h.tobytes()==before and len(values)==len(chunk) and all(len(v)==1 for v in values),'one native output/cell')
            if i==0:
                serial=[c.call(reader+'_serial_parity',lambda j=j:b.native(reader,h[j:j+1]))[0] for j in range(8)]
                check_outputs(values[:8],serial,out/f'PARITY_{reader}.json',[f'{x[0]["id"]}:{x[1]}' for x in chunk[:8]],32)
            write(stage/f'{reader}_{i:05d}.json',[dict(id=f'{row["id"]}:{p}',unit_id=row['id'],position=p,reader=reader,layer=l,**v[0]) for (row,p,j),v in zip(chunk,values)])
            count+=len(chunk)
        if not profile:require(count==len(cell_list),'all registered reader cells')
        profile_rows.append(dict(reader=reader,total_batches=len(chunks),measured_batches=len(selected),mean_seconds=float(np.mean(c.observed[reader+'_native']))))
    if profile:
        overhead=sum(x['seconds'] for x in c.events if not x['real'])
        write(out/'MEASURED_PROFILE.json',dict(binding,status='TIMING_ONLY_NOT_SCIENCE',phase=exp+'_readers',margin=1.25,
            forecast_seconds=1.25*(sum(x['total_batches']*x['mean_seconds'] for x in profile_rows)+overhead+60),
            rows=profile_rows,batch_size=32,parity_items=8,**provenance(out)))
    else:write(out/'COUNTS.json',dict(items=len(allowed),positions=len(cell_list),oracle=len(cell_list),nla=len(cell_list)))


def main():
    p=argparse.ArgumentParser()
    for k in ('inputs','assets','assignment','out'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('source-sha','input-sha'):p.add_argument('--'+k,required=True)
    p.add_argument('--stage',choices=('filter','capture','read'),required=True);p.add_argument('--profile-only',action='store_true')
    for k in ('capture-root','selection','release'):p.add_argument('--'+k,type=Path)
    a=p.parse_args();verify(HERE,'SOURCE_SEAL.json',a.source_sha)
    for n,h in read(HERE/'DEPENDENCIES.json').items():require(sha(ROOT/n)==h,'dependency '+n)
    s=verify(a.inputs,'INPUT_SEAL.json',a.input_sha);limits=read(a.inputs/'STAGE_REQUEST.json');exp=limits['experiment']
    require(exp in ('E82','E86') and limits['status']=='READY','specialized READY binding')
    require(set(s['files'])=={'PUBLIC_INPUTS.json','STAGE_REQUEST.json'} and {x.name for x in a.inputs.iterdir()}==set(s['files'])|{'INPUT_SEAL.json'},'public input archive')
    items=validate_public(read(a.inputs/'PUBLIC_INPUTS.json'),exp);ass=read(a.assignment)
    require(ass['stage']==a.stage and ass['profile_only']==a.profile_only,'assignment stage')
    end=deadline(ass,limits,time.time());a.out.mkdir(parents=True,exist_ok=False);write(a.out/'ASSIGNMENT.json',ass)
    binding=dict(experiment=exp,input_archive_sha256=limits['owner_public_archive_sha256'],source_seal_sha256=a.source_sha,input_seal_sha256=a.input_sha,pod_id=ass['pod_id'])
    selection=read(a.selection) if a.selection else None
    if exp=='E86' and a.stage!='filter':
        require(a.selection and sha(a.selection)==ass['selection_sha256'],'CPU selection identity')
        binding['selection_sha256']=sha(a.selection)
    if a.release:require(sha(a.release)==ass['release_sha256'],'CPU release identity')
    b=BoundRuntime(a.assets);c=Clock(a.out,end,{},b)
    import os,signal,threading
    timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start();status='FAILED'
    try:
        if a.stage=='filter':
            require(exp=='E86','filter belongs to E86 only');filter86(items,b,c,a.out,binding,a.profile_only)
        elif a.stage=='capture':capture_bound(items,exp,b,c,a.out,binding,selection)
        else:
            require(a.capture_root,'sealed capture required');read_bound(items,exp,b,c,a.out,binding,a.capture_root,selection,read(a.release) if a.release else None,a.profile_only)
        status='PROFILE_ONLY' if a.profile_only else ('CAPTURE_ONLY' if a.stage=='capture' else 'COMPLETE')
    finally:
        timer.cancel();seal(a.out,'OUTPUT_SEAL.json',**binding,status=status,**provenance(a.out))

if __name__=='__main__':main()
