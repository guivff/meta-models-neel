"""Sealed W1 derivatives and integrator-only scoring for exploratory E5/E8."""
from __future__ import annotations
import argparse
from collections import defaultdict
import hashlib,json,math,os,signal,statistics,subprocess,time
from pathlib import Path
import numpy as np
from projects.g_agreement.blindspot import protocol as P,run as W

RESULTS=P.ROOT/'results/g_agreement/understand'
W1=P.ROOT/'results/g_agreement/blindspot/w1/analysis'
BRIEF='projects/g_agreement/BRIEF_UNDERSTAND.md'
READERS=(('olens',44),('nla',42),('jlens',44))


def load_w1():
    P.verify(W1,'ANALYSIS_SEAL.json')
    bank=P.ROOT/'cache/g_agreement/blindspot/w1-bank';P.verify(bank,'INPUT_SEAL.json')
    manifest=json.loads((bank/'manifest.json').read_text())
    if P.sha(bank/'items.DO_NOT_STAGE.jsonl')!=manifest['files']['items.DO_NOT_STAGE.jsonl']:raise ValueError('W1 full items changed')
    items=P.rows(bank/'items.DO_NOT_STAGE.jsonl');receipt=json.loads((W1/'activations.json').read_text())
    ids=json.loads(Path(receipt['item_order_path']).read_text())
    if ids!=[x['id'] for x in items]:raise ValueError('W1 activation order mismatch')
    acts={}
    for r in receipt['files']:
        path=Path(r['path'])
        if P.sha(path)!=r['sha256']:raise ValueError('W1 activation hash mismatch')
        acts[r['layer']]=np.load(path,mmap_mode='r',allow_pickle=False)
    return items,acts,json.loads((bank/'templates.json').read_text())


def source_hashes(experiment):
    paths=['common/__init__.py','common/stats.py',BRIEF,'results/g_agreement/understand/REGISTRATION.json',
        'projects/g_agreement/understand/__init__.py','projects/g_agreement/understand/core.py',
        'projects/g_agreement/understand/'+experiment.lower()+'.py']
    if experiment=='PACKED':paths += ['projects/g_agreement/understand/'+n+'.py' for n in ('e5','e8','e6')]
    paths+=['projects/g_agreement/blindspot/'+n for n in ('__init__.py','run.py','protocol.py','analysis.py','items.py','w1_templates.py')]
    paths+=['projects/g_agreement/manifest/assets.json','external/PINS.md']
    paths += [str(p.relative_to(P.ROOT)) for p in (P.ROOT/'external/mats-nla-workspace/src').rglob('*.py')]
    return {p:P.sha(P.ROOT/p) for p in sorted(paths)}


def prepare(experiment,features,select,templates,cap,extra=None):
    items,acts,_=load_w1();indices=select(items);subset=[items[i] for i in indices]
    bank=P.ROOT/f'cache/g_agreement/understand/{experiment.lower()}-stage-v1'
    frozen=RESULTS/experiment.lower()/'freeze'
    bank.mkdir(parents=True,exist_ok=False);frozen.mkdir(parents=True,exist_ok=False)
    for layer in (42,44):np.save(bank/f'acts{layer}.npy',np.asarray(acts[layer][indices]),allow_pickle=False)
    P.jsonl(bank/'items.input.jsonl',[{'id':x['id'],'feature':x['feature']} for x in subset])
    private=P.ROOT/f'cache/g_agreement/understand/{experiment.lower()}.labels.DO_NOT_STAGE.jsonl'
    P.jsonl(private,[{k:x[k] for k in ('id','feature','value','split','cluster','class','domain')} for x in subset])
    P.dump(bank/'templates.json',templates)
    plan={'experiment':experiment,'status':'EXPLORATORY; every result reported','source_files':source_hashes(experiment),
        'registration_commit':'2254a0a6e7d656b141207586c83c67513c0dcf4e','brief_sha256':P.sha(P.ROOT/BRIEF),
        'features':features,'items':len(subset),'labels_local':str(private),'labels_sha256':P.sha(private),
        'w1_analysis_seal_sha256':P.sha(W1/'ANALYSIS_SEAL.json'),'w1_activation_receipt_sha256':P.sha(W1/'activations.json'),
        'cap_seconds':cap,'setup_allowance_seconds':1500,'batch':16,'seed':P.SEED,
        'no_new_capture':True,'forecast':'min(1.5F+360,cap), one unscored warm-up then median3 timed units',**(extra or {})}
    P.dump(bank/'plan.json',plan)
    names=['items.input.jsonl','templates.json','plan.json','acts42.npy','acts44.npy']
    P.seal(bank,names,'EXPLORATORY_INPUTS_FROZEN')
    for name in ('templates.json','plan.json','INPUT_SEAL.json'):(frozen/name).write_bytes((bank/name).read_bytes())
    return bank,frozen,plan


def request(bank,frozen,archive):
    bank,frozen,archive=map(Path,(bank,frozen,archive));P.verify(bank,'INPUT_SEAL.json')
    plan=json.loads((bank/'plan.json').read_text());git=lambda *a:subprocess.check_output(['git',*a],cwd=P.ROOT)
    source=git('rev-parse','HEAD').decode().strip();relative=str((frozen/'plan.json').relative_to(P.ROOT))
    commit=git('log','-1','--format=%H','--',relative).decode().strip()
    if not commit or git('show',commit+':'+relative)!=(bank/'plan.json').read_bytes():raise ValueError('commit freeze first')
    for path,digest in plan['source_files'].items():
        if hashlib.sha256(git('show',source+':'+path)).hexdigest()!=digest:raise ValueError('source not committed: '+path)
    if archive.exists():raise ValueError('preserve existing archive')
    git('archive','--format=tar.gz','--output='+str(archive.resolve()),source,'--',*sorted(plan['source_files']))
    return {'experiment':plan['experiment'],'status':'REQUESTED_NOT_ASSIGNED','exploratory':True,
        'source_commit':source,'source_files':plan['source_files'],'source_archive_local':str(archive.resolve()),
        'source_archive_sha256':P.sha(archive),'manifest_commit':commit,'plan_sha256':P.sha(bank/'plan.json'),
        'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'stage_local':str(bank.resolve()),
        'science_cap_gpu_seconds':plan['cap_seconds'],'staging_allowance_seconds':1500,'no_new_capture':True,
        'command':'python -m projects.g_agreement.understand.core run --bank STAGED_BANK --assignment ASSIGNMENT.json --assets VERIFIED_ASSETS.json --out NEW_OUTPUT',
        'timing':plan['forecast'],'required_assignment':['issuer=integrator','experiment','pod_id','source_files','plan_sha256',
            'provider_created_epoch','deadline_epoch','allocated_gpu_seconds','science_cap_gpu_seconds','staging_allowance_seconds=1500',
            'brief_registered=true','brief_pushed=true','manifest_committed=true','external_hardstop_verified=true','previous_gpu_seconds=0'],
        'priority':'W10/section84/section87 analysis first; E5 before other E-runs',
        'operations':'Integrator alone publishes and operates; persistent first-science clock, absolute hardstop,180s retrieval reserve; no automatic retry or scope reduction.'}


def score(name,obj,h,pairs):
    if name=='olens':return obj.paired_logodds_templates(h,44,pairs)
    if name=='nla':
        from mats.readers.nla import paired_logodds_templates
        return paired_logodds_templates(obj,h,pairs,batch=32)
    return W.native_baseline_contrasts(obj,h,44,pairs)


def run(bank,assignment,assets,out):
    import torch
    bank,assignment,out=map(Path,(bank,assignment,out));P.verify(bank,'INPUT_SEAL.json');W._labels_absent(bank)
    plan=json.loads((bank/'plan.json').read_text());a=json.loads(assignment.read_text());now=time.time()
    if (a.get('issuer')!='integrator' or a.get('pod_id')!=os.environ.get('RUNPOD_POD_ID') or not a.get('pod_id')
        or a.get('experiment')!=plan['experiment'] or a.get('source_files')!=plan['source_files']
        or a.get('plan_sha256')!=P.sha(bank/'plan.json') or a.get('previous_gpu_seconds')!=0
        or any(a.get(k) is not True for k in ('brief_registered','brief_pushed','manifest_committed','external_hardstop_verified'))):
        raise ValueError('exact published integrator assignment required')
    if not 0<P._science_budget(a)<=plan['cap_seconds'] or a['staging_allowance_seconds']!=1500:raise ValueError('wrong allocation')
    if not float(a['provider_created_epoch'])<=now<float(a['provider_created_epoch'])+1500:raise ValueError('setup expired')
    for path,digest in plan['source_files'].items():
        if P.sha(P.ROOT/path)!=digest:raise ValueError('run archived source: '+path)
    a['_science_clock_path']=str(assignment.resolve().with_suffix('.science-clock.json'));a['_assignment_sha256']=P.sha(assignment)
    if Path(a['_science_clock_path']).exists():raise ValueError('existing clock; no duplicate run')
    items=P.rows(bank/'items.input.jsonl');specs=json.loads((bank/'templates.json').read_text())
    acts={s:torch.from_numpy(np.load(bank/f'acts{s}.npy',allow_pickle=False)) for s in (42,44)}
    if any(h.ndim!=2 or len(h)!=len(items) or not torch.isfinite(h).all() for h in acts.values()):raise ValueError('invalid staged vectors')
    groups={f:[i for i,x in enumerate(items) if x['feature']==f] for f in plan['features']}
    out.mkdir(parents=True,exist_ok=False)
    with P.logged(plan['experiment'].lower()+'_scoring_only',gpu=True),P.compute_window(a):
        assets=W._assets(assets);ol=W._load_oracle(assets)
        from mats.readers.nla import load_nla
        nla=load_nla(root=assets['nla'],load_ar=False,enable_thinking=False)
        jl=None
        if any(specs[f].get('jlens_supported',True) for f in groups):
            from mats.readers.jlens import load_jlens
            jl=load_jlens(ol.model,ol.tok,layers=[44],path=assets['jlens'])
        objects={'olens':ol,'nla':nla,'jlens':jl};batch=16
        # One unscored synthetic warm-up per native path; no target capture.
        synthetic=torch.ones(batch,acts[42].shape[1])
        first_spec=specs[plan['features'][0]]
        for name,site in READERS:
            P.science_deadline(a)
            if objects[name] is not None:score(name,objects[name],synthetic,first_spec[name])
        torch.cuda.synchronize();P.science_checkpoint(a);clock=json.loads(Path(a['_science_clock_path']).read_text())
        first=clock['first_science_epoch'];deadline=[clock['science_deadline_epoch']]
        def check():
            P.science_checkpoint(a)
            if time.time()>=deadline[0]:raise TimeoutError('science exhausted')
            signal.setitimer(signal.ITIMER_REAL,max(.01,deadline[0]-time.time()))
        def timed(fn):
            check();torch.cuda.synchronize();t=time.monotonic();fn();torch.cuda.synchronize();return time.monotonic()-t
        timings=[];remaining=0
        alphas=plan.get('alphas',[0])
        directions=np.load(bank/'directions.npz',allow_pickle=False) if plan['experiment']=='E8' else None
        for f,indices in groups.items():
            for name,site in READERS:
                if objects[name] is None:continue
                times=[timed(lambda:score(name,objects[name],acts[site][indices[:batch]],specs[f][name])) for _ in range(3)]
                projected=statistics.median(times)*math.ceil(len(indices)/batch)*len(alphas)
                remaining+=projected;timings.append({'feature':f,'reader':name,'units_s':times,'median_s':statistics.median(times)})
        F=time.time()-first+remaining;budget=min(1.5*F+360,plan['cap_seconds'],P._science_budget(a))
        fit=F<=budget and time.time()+remaining<=deadline[0]
        P.dump(out/'FORECAST.json',{'status':'FIT' if fit else 'NO_FIT','forecast_s':F,'allocation_s':budget,'timings':timings})
        if not fit:raise ValueError('NO_FIT; unchanged full scope does not fit')
        deadline[0]=min(deadline[0],first+budget);records=[]
        for f,indices in groups.items():
            for name,site in READERS:
                for alpha in alphas:
                    if objects[name] is None:
                        records.extend({'id':items[i]['id'],'feature':f,'reader':name,'layer':site,'alpha':alpha,
                            'scores':None,'status':'UNSUPPORTED_SEQUENCE_QUERY_WITH_W1_J_LENS'} for i in indices)
                        continue
                    chunks=[]
                    for start in range(0,len(indices),batch):
                        check();idx=indices[start:start+batch];h=acts[site][idx]
                        if directions is not None:h=h+float(alpha)*torch.from_numpy(directions[f+'__L'+str(site)])
                        chunks.append(score(name,objects[name],h,specs[f][name]))
                    values=torch.cat(chunks,dim=1)
                    if values.shape!=(len(specs[f][name]),len(indices)) or not torch.isfinite(values).all():raise ValueError('invalid native score output')
                    records.extend({'id':items[i]['id'],'feature':f,'reader':name,'layer':site,'alpha':alpha,
                        'scores':values[:,j].tolist(),'status':'COMPLETE'} for j,i in enumerate(indices))
                    with (out/'scores.partial.jsonl').open('a') as stream:
                        for r in records[-len(indices):]:stream.write(json.dumps(r,sort_keys=True)+'\n')
                        stream.flush();os.fsync(stream.fileno())
        P.jsonl(out/'scores.jsonl',records)
        P.dump(out/'provenance.json',{'experiment':plan['experiment'],'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
            'source_files':plan['source_files'],'assignment_sha256':P.sha(assignment),'first_science_epoch':first,'no_new_capture':True})
        P.dump(out/'SCORE_SEAL.json',{'status':'EXPLORATORY_SCORES_SEALED_BEFORE_LABEL_JOIN',
            'files':{n:P.sha(out/n) for n in ('scores.jsonl','provenance.json','FORECAST.json')}})


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    r=sub.add_parser('run')
    for n in ('bank','assignment','assets','out'):r.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.bank,a.assignment,a.assets,a.out)
