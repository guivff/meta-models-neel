"""§100 W12 asked-only scoring; release bound to frozen E29 values and predictions."""
import argparse,json,math,os,signal,statistics,sys,time
from pathlib import Path
import numpy as np
from . import protocol as P,run as W
from projects.g_agreement.understand.e24_worker import seal
READERS={'olens':44,'nla':42,'jlens':44,'logit':44}

def verify_release(bank,plan):
    P.verify(bank,'INPUT_SEAL.json')
    if P.sha(bank/'INPUT_SEAL.json')!=plan['input_seal_sha256']:raise ValueError('input binding')
    f=json.loads((bank/'FREEZE.json').read_text());v=json.loads((bank/'VALUES_SEAL.json').read_text());p=json.loads((bank/'PREDICTIONS_SEAL.json').read_text());pred=json.loads((bank/'PREDICTIONS.json').read_text())
    if P.sha(bank/'FREEZE.json')!=plan['freeze_sha256'] or v['freeze']['sha256']!=plan['freeze_sha256'] or p['freeze']['sha256']!=plan['freeze_sha256']:raise ValueError('freeze release mismatch')
    if not v['complete'] or not p['complete'] or p['values_seal_sha256']!=P.sha(bank/'VALUES_SEAL.json'):raise ValueError('values release binding')
    if p['files']['PREDICTIONS.json']!=P.sha(bank/'PREDICTIONS.json') or pred['values_seal_sha256']!=P.sha(bank/'VALUES_SEAL.json'):raise ValueError('prediction binding')
    if P.sha(bank/'VALUES_SEAL.json')!=plan['values_seal_sha256'] or P.sha(bank/'PREDICTIONS_SEAL.json')!=plan['predictions_seal_sha256']:raise ValueError('release pins')
    if {x['feature'] for x in pred['rows']}!=set(f['rows']):raise ValueError('prediction row coverage')

def budget(first,remaining,now,absolute):
    F=now-first+remaining;end=min(first+min(1.5*F+360,2400),absolute)
    if remaining<0 or not math.isfinite(F) or now+remaining>end:raise ValueError('NO_FIT: full W12 scope cannot fit')
    return end,F

class Engine:
    def __init__(self,assets):
        import torch
        if torch.cuda.get_device_properties(0).total_memory<140_000_000_000:raise ValueError('H200 >=140GB required')
        a=W._assets(assets);W._offline();self.ol=W._load_oracle(a)
        from mats.readers.jlens import load_jlens
        from mats.readers.nla import load_nla
        self.jlens=load_jlens(self.ol.model,self.ol.tok,layers=[44],path=a['jlens']);self.logit=W.LogitLens(self.jlens)
        self.nla=load_nla(root=a['nla'],load_ar=False,enable_thinking=False)
    def capture(self,items):
        from projects.g_agreement.understand.e24_clone_capture import capture
        with self.ol.base():h=capture(self.ol.model,[x['ids'] for x in items],[42,44],[[-1]]*len(items),batch_size=32,pad_id=self.ol.tok.pad_token_id or 0)
        return {l:x[:,0] for l,x in h.items()}
    def score(self,reader,h,pairs):
        if reader=='olens':return self.ol.paired_logodds_templates(h,44,pairs).cpu()
        if reader=='nla':
            from mats.readers.nla import paired_logodds_templates
            return paired_logodds_templates(self.nla,h,pairs,batch=32).cpu()
        try:return W.native_baseline_contrasts(getattr(self,reader),h,44,pairs).cpu()
        except ValueError as exc:
            if 'single-token variant' in str(exc):return None
            raise

def run(a):
    import torch
    plan=json.loads(a.plan.read_text());q=json.loads(a.assignment.read_text());verify_release(a.bank,plan)
    if sys.prefix!='/weights/venv':raise ValueError('W12 pinned W1 environment required')
    if q.get('issuer')!='integrator' or q.get('experiment')!='W12' or not q.get('pod_id') or q['pod_id']!=os.environ.get('RUNPOD_POD_ID') or q.get('plan_sha256')!=P.sha(a.plan):raise ValueError('integrator assignment')
    if q.get('previous_gpu_seconds')!=0 or not all(q.get(k) is True for k in ('source_published','external_hardstop_verified','release_seals_verified')):raise ValueError('publication/release/runonce')
    created=q['provider_created_epoch'];absolute=q['deadline_epoch']-120
    if not created<=time.time()<absolute or not 0<q['deadline_epoch']-created<=2880:raise ValueError('0.8GPUh total cap')
    for n,h in plan['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('source changed:'+n)
    with a.assignment.with_suffix('.w12.lock').open('x') as f:f.write(P.sha(a.plan))
    a.out.mkdir(parents=True,exist_ok=False);first=None;end=absolute
    def stop(*_):raise TimeoutError('W12 custody/science deadline')
    signal.signal(signal.SIGALRM,stop)
    def check():
        if time.time()>=end:stop()
        signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    def call(fn,*args):
        check();v=fn(*args);torch.cuda.synchronize();check();return v
    try:
        check();engine=Engine(a.assets);check();first=time.time();end=min(absolute,first+2400)
        P.dump(a.out/'CLOCK.json',{'first_science_epoch':first,'provider_created_epoch':created})
        # §139: W1 asked-score reproduction before any W12 capture/reader scoring.
        from projects.g_agreement.understand.e24_analysis import auc
        gate=json.loads((a.bank/'W1_GATE.json').read_text());gh=torch.from_numpy(np.load(a.bank/'W1_GATE44.npy',allow_pickle=False));gresults={}
        for row,g in gate.items():
            scores=call(engine.score,'olens',gh[g['indices']],g['pairs']).mean(0).numpy();observed=auc(g['labels'],scores)
            gresults[row]={'observed':observed,'reference':g['reference'],'absolute_delta':abs(observed-g['reference']),'pass':abs(observed-g['reference'])<=.02}
        P.dump(a.out/'W1_PARITY.json',gresults);seal(a.out,['W1_PARITY.json'],'W1_PARITY_SEAL.json','PASS' if all(x['pass'] for x in gresults.values()) else 'FAIL')
        if not all(x['pass'] for x in gresults.values()):raise ValueError('W1 score parity failed; no W12 scoring')
        items=P.rows(a.bank/'items.input.jsonl');specs=json.loads((a.bank/'templates.json').read_text());idx={x['id']:i for i,x in enumerate(items)}
        if len(items)!=1008 or len(idx)!=1008 or len(specs)!=6:raise ValueError('W12 fixed scope')
        acts=call(engine.capture,items)
        for l,h in acts.items():np.save(a.out/f'acts{l}.npy',h.numpy(),allow_pickle=False)
        P.dump(a.out/'ORDER.json',[x['id'] for x in items]);metadata=[]
        for start in range(0,len(items),32):
            batch=items[start:start+32];width=max(len(x['ids']) for x in batch)
            metadata += [{'id':x['id'],'row':x['feature'],'length':len(x['ids']),'padding':width-len(x['ids']),'batch_position':j,'environment':sys.prefix} for j,x in enumerate(batch)]
        P.jsonl(a.out/'ITEM_ENVIRONMENT.jsonl',metadata);seal(a.out,['acts42.npy','acts44.npy','ORDER.json','ITEM_ENVIRONMENT.jsonl'],'CAPTURE_SEAL.json','W12_CAPTURE')
        groups={f:[i for i,x in enumerate(items) if x['feature']==f] for f in specs};timing={};remaining=0
        for f,ii in groups.items():
            for reader,l in READERS.items():
                sample=ii[:32];call(engine.score,reader,acts[l][sample],specs[f][reader]);times=[]
                for _ in range(3):
                    start=time.monotonic();call(engine.score,reader,acts[l][sample],specs[f][reader]);times.append(time.monotonic()-start)
                projected=statistics.median(times)*math.ceil(len(ii)/32);remaining+=projected;timing[f+':'+reader]={'units':times,'projected_s':projected}
        end,F=budget(first,remaining,time.time(),absolute);P.dump(a.out/'FORECAST.json',{'status':'FIT','F':F,'deadline_epoch':end,'timings':timing});check()
        records=[]
        for f,ii in groups.items():
            for reader,l in READERS.items():
                values={}
                for start in range(0,len(ii),32):
                    batch=ii[start:start+32];v=call(engine.score,reader,acts[l][batch],specs[f][reader])
                    if v is not None and (v.shape!=(2,len(batch)) or not torch.isfinite(v).all()):raise ValueError('score shape/value')
                    for j,i in enumerate(batch):values[items[i]['id']]=None if v is None else v[:,j].tolist()
                for i in ii:
                    x=items[i]
                    for arm,key in [('true',x['id']),('mismatched',x['donor_id'])]:
                        if key not in values:raise ValueError('donor crosses row')
                        records.append({'id':x['id'],'feature':f,'reader':reader,'layer':l,'arm':arm,'scores':values[key],'status':'COMPLETE' if values[key] is not None else 'NOT_EVALUABLE_NO_TOKEN_VARIANT'})
                P.jsonl(a.out/f'partial.{f}.{reader}.jsonl',records[-2*len(ii):])
        assert len(records)==1008*4*2
        P.jsonl(a.out/'scores.jsonl',records);P.dump(a.out/'BINDING.json',{'plan_sha256':P.sha(a.plan),'input_seal_sha256':plan['input_seal_sha256'],'freeze_sha256':plan['freeze_sha256'],'values_seal_sha256':plan['values_seal_sha256'],'predictions_seal_sha256':plan['predictions_seal_sha256'],'assignment_sha256':P.sha(a.assignment)})
        seal(a.out,['scores.jsonl','BINDING.json','CAPTURE_SEAL.json','W1_PARITY_SEAL.json','FORECAST.json','CLOCK.json'],'SCORE_SEAL.json','W12_ASKED_ONLY_COMPLETE');check()
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','reason':str(exc),'retry_authorized':False});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);P.dump(a.out/'RECEIPT.json',{'total_provider_seconds':time.time()-created,'science_seconds':None if first is None else time.time()-first,'cap_total':2880,'cap_science':2400})
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bank','plan','assignment','assets','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
