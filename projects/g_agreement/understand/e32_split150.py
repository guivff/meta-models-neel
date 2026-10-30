"""§150 two-stage E32: sealed G capture, parity-gated kernel scoring; science unchanged."""
import argparse,json,os,sys,signal,time,statistics,math,shutil,gc
from pathlib import Path
import numpy as np
from projects.g_agreement.blindspot import protocol as P,run as W
from .e32_relaunch import Engine,ARMS,summarise,rules
from . import e32_e25_reference as E
from .e24_worker import parity,seal
from .e24_analysis import auc


def verify_capture(source,bank,plan):
    P.verify(source,'CAPTURE_SEAL.json');P.verify(bank,'INPUT_SEAL.json')
    if P.sha(source/'CAPTURE_SEAL.json')!=plan['capture_seal_sha256'] or P.sha(bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('capture/input binding')
    items=P.rows(bank/'items.jsonl')
    if E.read(source/'ORDER.json')!=[x['id'] for x in items]:raise ValueError('capture item order')
    metadata=P.rows(source/'ITEM_ENVIRONMENT.jsonl')
    if {x['id'] for x in metadata}!={x['id'] for x in items} or len(metadata)!=2100 or any(x['capture_mode']!='G' or x['environment']!='/weights/venv' for x in metadata):raise ValueError('mode G provenance')
    for l in range(64):
        name=f'acts{l}.npy'
        if name not in E.read(source/'CAPTURE_SEAL.json')['files']:raise ValueError('Bprime layer missing')
        h=np.load(source/name,allow_pickle=False)
        if h.ndim!=2 or len(h)!=2100 or not np.isfinite(h).all():raise ValueError('invalid stored vectors')
    return parity(np.load(source/'acts44.npy',allow_pickle=False),np.load(bank/'reference44.npy',allow_pickle=False))


def score_parity(bank,assets,out,plan):
    import torch
    P.verify(bank,'INPUT_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json')!=plan['score_gate_input_seal_sha256']:raise ValueError('score gate input binding')
    gate=E.read(bank/'W1_GATE.json')
    if set(gate)!={'prose_paren','python_string','prose_sentiment'}:raise ValueError('three W1 rows required')
    ol=W._load_oracle(W._assets(assets,names=('model','olens')))
    h=torch.from_numpy(np.load(bank/'W1_GATE44.npy',allow_pickle=False));result={}
    for row,g in gate.items():
        scores=ol.paired_logodds_templates(h[g['indices']],44,g['pairs']).detach().cpu().numpy().mean(0)
        observed=auc(g['labels'],scores);delta=abs(observed-g['reference'])
        result[row]={'observed':observed,'reference':g['reference'],'absolute_delta':delta,'pass':delta<=.02}
    E.dump(out/'SCORE_PARITY.json',result);seal(out,['SCORE_PARITY.json'],'SCORE_PARITY_SEAL.json','PASS' if all(r['pass'] for r in result.values()) else 'FAIL')
    del ol,h;gc.collect();torch.cuda.empty_cache()
    if not all(r['pass'] for r in result.values()):raise ValueError('score parity failed; no E32 scoring')


def run(a):
    import torch
    plan=E.read(a.plan);assign=E.read(a.assignment);now=time.time()
    if (assign.get('issuer')!='integrator' or assign.get('experiment')!='E32' or not assign.get('pod_id') or assign['pod_id']!=os.getenv('RUNPOD_POD_ID') or assign.get('plan_sha256')!=P.sha(a.plan) or assign.get('assets_manifest_sha256')!=P.sha(a.assets) or assign.get('previous_gpu_seconds')!=0 or assign.get('external_hardstop_verified') is not True or assign.get('source_published') is not True):raise ValueError('integrator assignment')
    if sys.prefix!='/weights/venv-kernels':raise ValueError('scoring requires venv-kernels')
    if assign.get('gate_assets_manifest_sha256')!=P.sha(a.gate_assets):raise ValueError('gate assets binding')
    created=assign['provider_created_epoch'];end=assign['deadline_epoch']
    if not all(isinstance(v,(float,int)) and math.isfinite(v) for v in (created,end)) or not created<=now<end:raise ValueError('custody deadline')
    if assign.get('science_cap_seconds')!=3600 or plan['science_cap_seconds']!=3600:raise ValueError('science cap')
    verify_capture(a.capture,a.bank,plan)
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('source binding: '+n)
    P.verify(a.bank,'INPUT_SEAL.json')
    if P.sha(a.bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('input binding')
    with a.assignment.with_suffix('.e32-relaunch.lock').open('x') as f:f.write(P.sha(a.plan))
    a.out.mkdir(parents=True,exist_ok=False)
    def timeout(*_):raise TimeoutError('E32 deadline')
    signal.signal(signal.SIGALRM,timeout);signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()-120))
    try:
        if not torch.cuda.is_available():raise ValueError('CUDA required')
        first=time.time();science_end=min(end-120,first+3600)
        signal.setitimer(signal.ITIMER_REAL,max(.001,science_end-time.time()))
        E.dump(a.out/'SCIENCE_CLOCK.json',{'epoch':first,'science_cap_seconds':3600,'includes_score_gate':True})
        score_parity(a.gate_bank,a.gate_assets,a.out,plan)
        engine=Engine(a.assets)
        items=P.rows(a.bank/'items.jsonl');pairs=E.read(a.bank/'pairs.json');maps=E.read(a.bank/'DONORS.json');refs=E.read(a.bank/'references.json');index={x['id']:i for i,x in enumerate(items)}
        if engine.tok.encode('_',add_special_tokens=False)!=[62]:raise ValueError('frozen placeholder token changed')
        acts={l:torch.from_numpy(np.load(a.capture/f'acts{l}.npy',allow_pickle=False)) for l in range(64)}
        shutil.copyfile(a.capture/'CAPTURE_SEAL.json',a.out/'CAPTURE_SEAL.json')
        E.dump(a.out/'STAGE_BINDING.json',{'capture_seal_sha256':P.sha(a.capture/'CAPTURE_SEAL.json'),'capture_assignment_sha256':plan['capture_assignment_sha256'],'capture_environment':'/weights/venv','scoring_environment':sys.prefix,'score_parity_seal_sha256':P.sha(a.out/'SCORE_PARITY_SEAL.json')})
        records=[];jobs=[]
        for f in sorted(refs):
            group=[x for x in items if x['feature']==f]
            for cs in ('w1','e30'):
                for arm in ARMS:
                    for i in range(0,len(group),4):jobs.append((f,cs,arm,group[i:i+4]))
        # Unscored warm-up + three timed units per candidate set and arm. All costs count.
        timings={}
        for cs in ('w1','e30'):
            for arm in ARMS:
                eligible=[j for j in jobs if j[1:3]==(cs,arm)]
                warm=max(eligible,key=lambda j:max(len(x['ids']) for x in j[3]) if arm=='A' else max(len(engine.tok.encode(c,add_special_tokens=False)) for pair in pairs[cs][j[0]] for c in pair))
                f,_,_,ch=warm
                engine.score(ch,pairs[cs][f],arm,acts,index,maps);units=[]
                for _ in range(3):
                    torch.cuda.synchronize();start=time.monotonic();engine.score(ch,pairs[cs][f],arm,acts,index,maps);torch.cuda.synchronize();units.append(time.monotonic()-start)
                timings[cs+':'+arm]={'units':units,'median_s':statistics.median(units),'batches':len(eligible)}
        remaining=sum(t['median_s']*t['batches'] for t in timings.values())
        deadline=min(end-120,first+min(1.5*(time.time()-first+remaining)+360,3600))
        fit=time.time()+remaining<=deadline;E.dump(a.out/'FORECAST.json',{'remaining_s':remaining,'timings':timings,'deadline':deadline,'status':'FIT' if fit else 'NO_FIT'})
        if not fit:raise ValueError('NO_FIT, no scope reduction or retry')
        signal.setitimer(signal.ITIMER_REAL,max(.001,deadline-time.time()))
        def phase(j):
            f,cs,arm,ch=j
            return 0 if arm=='A' else 1 if arm=='B' and refs[f]['class']=='semantic' else 2
        for stage in range(3):
            for f,cs,arm,ch in (j for j in jobs if phase(j)==stage):
                v=engine.score(ch,pairs[cs][f],arm,acts,index,maps)
                records.extend(dict(id=x['id'],feature=f,set=cs,arm=arm,score=s) for x,s in zip(ch,v))
            if stage<2:
                gate=rules(summarise(records,items,refs),refs,plan['high_D_rows'])
                E.dump(a.out/f'GATE_PHASE_{stage}.json',gate)
                if not gate['A_reproduces_E25'] or (stage==1 and not any(v['interpretable'] for v in gate['candidate_sets'].values())):
                    P.jsonl(a.out/'gate_scores.jsonl',records)
                    seal(a.out,[f'GATE_PHASE_{stage}.json','gate_scores.jsonl','FORECAST.json','CAPTURE_SEAL.json','STAGE_BINDING.json','SCORE_PARITY_SEAL.json'],'GATE_SEAL.json','NOT_EVALUABLE_STOPPED')
                    return
        if len(records)!=25200 or len({(x['id'],x['set'],x['arm']) for x in records})!=25200:raise ValueError('incomplete grid')
        P.jsonl(a.out/'scores.jsonl',records);summary=summarise(records,items,refs);E.dump(a.out/'GATES.json',rules(summary,refs,plan['high_D_rows']))
        E.dump(a.out/'BINDING.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':plan['input_seal_sha256'],'assignment_sha256':P.sha(a.assignment)})
        seal(a.out,['scores.jsonl','GATES.json','BINDING.json','FORECAST.json','CAPTURE_SEAL.json','STAGE_BINDING.json','SCORE_PARITY_SEAL.json'],'SCORE_SEAL.json','COMPLETE_GATES_RECORDED')
    except Exception as e:
        E.dump(a.out/'INCOMPLETE.json',{'error':type(e).__name__,'message':str(e),'retry':False});raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('bank','plan','assignment','assets','out','capture','gate-bank','gate-assets'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
