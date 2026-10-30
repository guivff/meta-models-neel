"""Label-free E-run collectors. Pods and assignments are owned by the integrator."""
import argparse
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .runtime import Gate, run_batches


def jsonl(path,records):
    import json
    path.write_text(''.join(json.dumps(r,ensure_ascii=False,sort_keys=True)+'\n' for r in records))


RESIDENT=None


def gate_for(path,experiment):
    return RESIDENT.gates[experiment] if RESIDENT is not None else Gate(path,experiment)


def bound_input(gate,path):
    digest=sha(path/'INPUT_SEAL.json')
    return digest==gate.assignment.get('input_seal_sha256') or (RESIDENT is not None and digest in RESIDENT.derived_inputs.get(gate.experiment,set()))


def asset_manifest(path,names):
    # Exact registered revisions and full hash coverage; no downloads or guessed weights.
    if RESIDENT is not None:return RESIDENT.assets
    from projects.g_agreement.blindspot.run import _assets
    return _assets(path,names)


def decoder_only(assets_path):
    if RESIDENT is not None:return RESIDENT.get('decoder')
    return load_decoder_only(assets_path)


def load_decoder_only(assets_path):
    import common
    import torch,yaml
    from transformers import AutoTokenizer
    from mats.readers.nla import _load_ar,NLA
    assets=asset_manifest(assets_path,('nla',));root=Path(assets['nla'])
    if not (root/'ar_reconstructor/value_head.safetensors').is_file():raise FileNotFoundError('pinned NLA repo has no staged decoder value_head')
    meta=yaml.safe_load((root/'nla_meta.yaml').read_text());tok=AutoTokenizer.from_pretrained(root/'av_base',local_files_only=True)
    ar,head=_load_ar(root,'cuda')
    if tok.pad_token_id is None:tok.pad_token_id=tok.eos_token_id
    return NLA(av=None,tok=tok,ar=ar,value_head=head,meta=meta,prompt_ids=[],marker=0,device='cuda')


def decoder_probe(a):
    gate=gate_for(a.assignment,'E1');a.out.mkdir(exist_ok=False,parents=True)
    try:
        gate.setup_guard();decoder=decoder_only(a.assets);sample=decoder.reconstruct(['The current text is inside parentheses.','An unfinished prefix ('],batch=2)
        gate.setup_guard()
        if sample.shape!=(2,5120) or not np.isfinite(sample.numpy()).all():raise ValueError('invalid native decoder output')
        np.save(a.out/'probe.npy',sample.numpy(),allow_pickle=False)
        dump(a.out/'report.json',{'status':'LOADED_NATIVE42','assets_sha256':sha(a.assets),'assignment_sha256':sha(a.assignment),'n_samples':2,'raw_value_head_output':True,'AV_loaded':False})
        seal(a.out,['probe.npy','report.json'],'EXPLORATORY_DECODER_LOAD_VERIFIED')
    except Exception as exc:
        dump(a.out/'report.json',{'status':'DECODER_LOAD_FAILED','error_type':type(exc).__name__,'error':str(exc),'assets_sha256':sha(a.assets),'AV_loaded':False})
        seal(a.out,['report.json'],'EXPLORATORY_DECODER_LOAD_FAILED')
        raise


def require_decoder_probe(path,assets=None):
    verify(path)
    report=read(path/'report.json')
    if report['status']!='LOADED_NATIVE42':raise ValueError('successful decoder-only native preflight required')
    if assets is not None and report['assets_sha256']!=sha(assets):raise ValueError('decoder preflight asset manifest mismatch')


def reconstruct(a):
    gate=gate_for(a.assignment,a.experiment);verify(a.inputs,'INPUT_SEAL.json')
    if not bound_input(gate,a.inputs):raise ValueError('assignment/input seal mismatch')
    if any(a.inputs.rglob('*.DO_NOT_STAGE.*')):raise ValueError('private labels in worker package')
    records=rows(a.inputs/a.records)
    if a.records not in read(a.inputs/'INPUT_SEAL.json')['files']:raise ValueError('record file not sealed')
    a.out.mkdir(exist_ok=False,parents=True)
    if a.reader=='nla':
        require_decoder_probe(a.decoder_probe,a.assets)
        decoder=decoder_only(a.assets);fn=lambda batch:decoder.reconstruct([r['text'] for r in batch],batch=len(batch)).numpy()
    else:
        from projects.g_agreement.blindspot.ar_tests import _assets
        from projects.g_agreement.w_claims.ar import load_reconstructor,reconstruct as ar_reconstruct
        if RESIDENT is not None:ar,tok,_=RESIDENT.get('ar')
        else:
            assets=_assets(a.assets,('model','ar'));ar,tok,_=load_reconstructor(a.official,a.whitener,assets['ar'],assets['model'])
        fn=lambda batch:ar_reconstruct(ar,tok,[r['text'] for r in batch]).numpy()
    vectors=np.concatenate(run_batches(records,fn,a.batch,gate,a.out))
    if vectors.shape!=(len(records),5120) or not np.isfinite(vectors).all():raise ValueError('incomplete/nonfinite reconstruction grid')
    np.save(a.out/'recon.npy',vectors,allow_pickle=False);dump(a.out/'ids.json',[r['id'] for r in records])
    dump(a.out/'provenance.json',{'reader':a.reader,'layer':42 if a.reader=='nla' else 44,'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'records':a.records,'assignment_sha256':sha(a.assignment),'assets_sha256':sha(a.assets),'source_sha256':sha(Path(__file__))})
    seal(a.out,['recon.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_RECONSTRUCTIONS_SEALED_BEFORE_LABEL_JOIN')


def capture(a):
    import common,torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from mats.capture import capture as run_capture
    gate=gate_for(a.assignment,'E2');verify(a.inputs,'INPUT_SEAL.json');records=rows(a.inputs/'spans.input.jsonl');assert len(records)==5000
    if not bound_input(gate,a.inputs):raise ValueError('assignment/input seal mismatch')
    assets=asset_manifest(a.assets,('model',))
    if RESIDENT is not None:model,tok=RESIDENT.get('target')
    else:
        model=AutoModelForCausalLM.from_pretrained(assets['model'],dtype=torch.bfloat16,device_map='cuda',local_files_only=True).eval()
        tok=AutoTokenizer.from_pretrained(assets['model'],local_files_only=True)
    a.out.mkdir(exist_ok=False,parents=True)
    def fn(batch):
        result=run_capture(model,[r['ids'] for r in batch],[42,44],[[-1]]*len(batch),batch_size=len(batch),pad_id=tok.pad_token_id or 0)
        return {layer:result[layer][:,0].float().cpu().numpy() for layer in [42,44]}
    values=run_batches(records,fn,a.batch,gate,a.out)
    for layer in [42,44]:
        h=np.concatenate([v[layer] for v in values]);assert h.shape==(5000,5120) and np.isfinite(h).all();np.save(a.out/f'acts{layer}.npy',h,allow_pickle=False)
    dump(a.out/'ids.json',[r['id'] for r in records]);dump(a.out/'provenance.json',{'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'assignment_sha256':sha(a.assignment),'assets_sha256':sha(a.assets)})
    seal(a.out,['acts42.npy','acts44.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_SAME_SPAN_TARGET_CAPTURES_SEALED')


def nla_readouts(a):
    import common,torch
    from mats.readers.nla import load_nla,Sampling
    gate=gate_for(a.assignment,'E7');require_decoder_probe(a.decoder_probe,a.assets);verify(a.inputs,'INPUT_SEAL.json')
    if not bound_input(gate,a.inputs):raise ValueError('assignment/input seal mismatch')
    assets=asset_manifest(a.assets,('nla',));nla=RESIDENT.get('nla') if RESIDENT is not None else load_nla(root=assets['nla'],load_ar=False)
    ids=read(a.inputs/'ids.json');h=np.load(a.inputs/'acts42.npy',allow_pickle=False)
    records=[{'id':key,'index':i} for i,key in enumerate(ids)];a.out.mkdir(exist_ok=False,parents=True)
    def fn(batch):
        raw=nla.verbalize_raw(torch.tensor(h[[r['index'] for r in batch]]),k=1,sampling=Sampling(temperature=0,max_new_tokens=128),batch=len(batch))
        # W1-native extraction retains all completions including truncated explanations.
        return [{'id':r['id'],'text':v[0].split('</explanation>')[0].removeprefix('<explanation>').strip(),'raw':v[0]} for r,v in zip(batch,raw)]
    output=[r for unit in run_batches(records,fn,a.batch,gate,a.out) for r in unit]
    jsonl(a.out/'readouts.jsonl',output);dump(a.out/'provenance.json',{'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'assignment_sha256':sha(a.assignment),'assets_sha256':sha(a.assets),'decoding':{'k':1,'temperature':0,'max_new_tokens':128,'layer':42}})
    seal(a.out,['readouts.jsonl','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_NLA_READOUTS_SEALED')


def prepare_e7_decode(a):
    verify(a.inputs,'INPUT_SEAL.json');verify(a.readouts)
    if read(a.readouts/'provenance.json')['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('NLA readout/input lineage mismatch')
    ids=read(a.inputs/'ids.json');ol=rows(a.inputs/'ol.input.jsonl');nla=rows(a.readouts/'readouts.jsonl')
    if [r['id'] for r in ol]!=ids or [r['id'] for r in nla]!=ids:raise ValueError('readout item order mismatch')
    records=[{'id':prefix+':'+r['id'],'text':r['text']} for prefix,rs in [('ol',ol),('nla',nla)] for r in rs]
    a.out.mkdir(exist_ok=False,parents=True);jsonl(a.out/'decode.input.jsonl',records)
    dump(a.out/'provenance.json',{'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'NLA_readout_seal_sha256':sha(a.readouts/'SCORE_SEAL.json')})
    dump(a.out/'INPUT_SEAL.json',{'status':'EXPLORATORY_E7_DECODE_INPUTS_FROZEN','files':{n:sha(a.out/n) for n in ['decode.input.jsonl','provenance.json']}})


def e7_arms(ol,nla,pairs):
    delta=nla-ol
    r=np.array([p['recipient'] for p in pairs]);j=np.array([p['donor'] for p in pairs]);random=np.array([p['random'] for p in pairs])
    return {'swap':ol[r]+delta[j],'self':ol[r]+delta[r],'ol_only':ol[r],'nla_only':nla[r],'delta_only':delta[r],'random':ol[r]+delta[random]}


def score_e7(a):
    import common,torch
    from mats.readers.nla import load_nla,paired_logodds_templates
    gate=gate_for(a.assignment,'E7');require_decoder_probe(a.decoder_probe,a.assets);verify(a.inputs,'INPUT_SEAL.json');verify(a.reconstruction)
    decode=read(a.reconstruction/'provenance.json');verify(a.decode_inputs,'INPUT_SEAL.json')
    if decode['reader']!='nla' or decode['input_seal_sha256']!=sha(a.decode_inputs/'INPUT_SEAL.json') or read(a.decode_inputs/'provenance.json')['input_seal_sha256']!=sha(a.inputs/'INPUT_SEAL.json'):raise ValueError('E7 decoder lineage mismatch')
    ids=read(a.inputs/'ids.json');rec=np.load(a.reconstruction/'recon.npy',allow_pickle=False)
    if read(a.reconstruction/'ids.json')!=[prefix+':'+i for prefix in ['ol','nla'] for i in ids] or rec.shape!=(2*len(ids),5120):raise ValueError('E7 recon order mismatch')
    ol,nla_recon=np.split(rec,2);pairs=rows(a.inputs/'pairs.input.jsonl');templates=read(a.inputs/'templates.json');arms=e7_arms(ol,nla_recon,pairs)
    if not bound_input(gate,a.inputs):raise ValueError('assignment/input seal mismatch')
    assets=asset_manifest(a.assets,('nla',));nla=RESIDENT.get('nla') if RESIDENT is not None else load_nla(root=assets['nla'],load_ar=False);a.out.mkdir(exist_ok=False,parents=True)
    records=[{'id':p['id'],'index':i,'arm':arm,'feature':p['feature']} for arm in arms for i,p in enumerate(pairs)]
    def fn(batch):
        output=[]
        for f in sorted({r['feature'] for r in batch}):
            selected=[r for r in batch if r['feature']==f]
            vec=torch.tensor(np.stack([arms[r['arm']][r['index']] for r in selected]))
            values=paired_logodds_templates(nla,vec,templates[f]['nla'],batch=2*a.batch).mean(0).numpy()
            output.extend({**r,'score':float(v)} for r,v in zip(selected,values))
        return output
    scores=[r for unit in run_batches(records,fn,a.batch,gate,a.out) for r in unit]
    if len(scores)!=6000 or len({(r['id'],r['arm']) for r in scores})!=6000:raise ValueError('incomplete E7 six-arm score grid')
    jsonl(a.out/'scores.jsonl',scores);np.save(a.out/'delta.npy',nla_recon-ol,allow_pickle=False);dump(a.out/'ids.json',ids)
    dump(a.out/'provenance.json',{'input_seal_sha256':sha(a.inputs/'INPUT_SEAL.json'),'reconstruction_score_seal_sha256':sha(a.reconstruction/'SCORE_SEAL.json'),'assignment_sha256':sha(a.assignment),'assets_sha256':sha(a.assets),'site':'NATIVE42','score_orientation':'W1valueAminusB;no flips'})
    seal(a.out,['scores.jsonl','delta.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_E7_SCORES_SEALED_BEFORE_LABEL_JOIN')



def reconstruction_session(a):
    """One load, one in-process setup warm-up, persistent AR/decoder across E1/E2 jobs."""
    from types import SimpleNamespace
    import os,time
    plan=read(a.plan)
    if not plan or len({j['reader'] for j in plan})!=1:raise ValueError('session must use exactly one reconstruction backend')
    jobs=[];preceding=None;assets_path=None
    for row in plan:
        j=SimpleNamespace(**{k:Path(v) if k in ['inputs','assets','assignment','official','whitener','out'] and v is not None else v for k,v in row.items()})
        if assets_path is None:assets_path=j.assets
        if sha(j.assets)!=sha(assets_path):raise ValueError('same pinned asset manifest required across resident jobs')
        gate=Gate(j.assignment,j.experiment)
        if preceding is None:preceding=gate.assignment.get('preceding_science_gpu_seconds',0)
        if gate.assignment.get('preceding_science_gpu_seconds',0)!=preceding:raise ValueError('resident phase science accounting mismatch')
        preceding+=gate.allocation
        verify(j.inputs,'INPUT_SEAL.json')
        if gate.assignment.get('input_seal_sha256')!=sha(j.inputs/'INPUT_SEAL.json'):raise ValueError('assignment/input seal mismatch')
        if any(j.inputs.rglob('*.DO_NOT_STAGE.*')) or j.records not in read(j.inputs/'INPUT_SEAL.json')['files']:raise ValueError('unsealed/private session input')
        records=rows(j.inputs/j.records)
        if len(records)<3*j.batch:raise ValueError('need three production timing units')
        j.out.mkdir(exist_ok=False,parents=True);jobs.append((j,gate,records))
    for _,gate,_ in jobs:gate.setup_guard()
    reader=plan[0]['reader'];loaded_at=time.time();loads=1
    if reader=='nla':
        decoder=decoder_only(assets_path)
        fn=lambda batch:decoder.reconstruct([r['text'] for r in batch],batch=len(batch)).numpy()
    else:
        from projects.g_agreement.blindspot.ar_tests import _assets
        from projects.g_agreement.w_claims.ar import load_reconstructor,reconstruct as ar_reconstruct
        assets=_assets(assets_path,('model','ar'));first=jobs[0][0]
        ar,tok,_=load_reconstructor(first.official,first.whitener,assets['ar'],assets['model'])
        fn=lambda batch:ar_reconstruct(ar,tok,[r['text'] for r in batch]).numpy()
    # Warm the longest padded unit across every resident dataset; same backend/code path.
    warm=max([records[i:i+j.batch] for j,gate,records in jobs for i in range(0,len(records),j.batch)],key=lambda u:max(len(r['text']) for r in u))
    for _,gate,_ in jobs:gate.setup_guard()
    discarded=fn(warm)
    if discarded.shape!=(len(warm),5120) or not np.isfinite(discarded).all():raise ValueError('native reconstructor warm-up failed')
    del discarded;setup_completed=time.time()
    for _,gate,_ in jobs:gate.setup_guard();gate.setup_complete=True
    a.out.mkdir(exist_ok=False,parents=True)
    if reader=='nla':
        probe=a.out/'decoder-probe';probe.mkdir()
        dump(probe/'report.json',{'status':'LOADED_NATIVE42','assets_sha256':sha(assets_path),'raw_value_head_output':True,'AV_loaded':False,'PID':os.getpid(),'loads':loads,'setup_completed_epoch':setup_completed})
        seal(probe,['report.json'],'EXPLORATORY_DECODER_LOAD_VERIFIED')
    for j,gate,records in jobs:
        vectors=np.concatenate(run_batches(records,fn,j.batch,gate,j.out,already_warmed=True))
        if vectors.shape!=(len(records),5120) or not np.isfinite(vectors).all():raise ValueError('invalid reconstruction output grid')
        np.save(j.out/'recon.npy',vectors,allow_pickle=False);dump(j.out/'ids.json',[r['id'] for r in records])
        dump(j.out/'provenance.json',{'reader':reader,'layer':42 if reader=='nla' else 44,'input_seal_sha256':sha(j.inputs/'INPUT_SEAL.json'),'records':j.records,'assignment_sha256':sha(j.assignment),'assets_sha256':sha(j.assets),'source_sha256':sha(Path(__file__)),'resident_PID':os.getpid(),'reconstructor_load_count':loads,'load_started_epoch':loaded_at,'setup_completed_epoch':setup_completed,'science_clock_started_after_setup':True})
        seal(j.out,['recon.npy','ids.json','provenance.json','WARMED_FORECAST.json'],'EXPLORATORY_RECONSTRUCTIONS_SEALED_BEFORE_LABEL_JOIN')
    dump(a.out/'session.json',{'PID':os.getpid(),'reader':reader,'reconstructor_load_count':loads,'setup_completed_epoch':setup_completed,'jobs':[str(j.out) for j,_,_ in jobs],'plan_sha256':sha(a.plan)})
    seal(a.out,['session.json'],'EXPLORATORY_RESIDENT_RECONSTRUCTION_SESSION_COMPLETE')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['decoder-probe','reconstruct','capture','nla-readouts','prepare-e7-decode','score-e7','reconstruction-session'])
    for name in ['inputs','assets','assignment','official','whitener','decoder-probe','readouts','reconstruction','decode-inputs','plan']:p.add_argument('--'+name,type=Path)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--reader',choices=['ar','nla'],default='ar');p.add_argument('--experiment',choices=['E1','E2','E7']);p.add_argument('--records',default='enactment.input.jsonl');p.add_argument('--batch',type=int,default=8)
    a=p.parse_args()
    if a.batch<1:raise ValueError('positive batch required')
    {'decoder-probe':decoder_probe,'reconstruct':reconstruct,'capture':capture,'nla-readouts':nla_readouts,'prepare-e7-decode':prepare_e7_decode,'score-e7':score_e7,'reconstruction-session':reconstruction_session}[a.command](a)


if __name__=='__main__':main()
