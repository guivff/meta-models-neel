"""E103 CORE worker: sealed E81 base runtime, serial sampling, one fixed custody clock."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,math,os,re,signal,sys,threading,time
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT),str(ROOT/'results/g_agreement/understand/late198')]
from projects.g_agreement.e103 import sampler as S
CAP_SECONDS=11200
PUBLIC_SHA='061c5772d49f9d4ab4c219b7010a9fd53944e69e4030e7b1f50f6dbad74d4619'
REFERENCE_SHA='1d81f57f735fd5defe8f3ab63ff7e4073d7d3b9efd15f1adbf93482ad3b0c0a3'

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for z in iter(lambda:f.read(1048576),b''):h.update(z)
    return h.hexdigest()

def validate_assignment(a,now,assets):
    S.require(a.get('operational_authorization')=='GUIV_DIRECT_CAP_RULING' and re.fullmatch('[0-9a-f]{40}',a.get('operational_authorization_commit','')),'PROPOSAL NOT AUTHORIZED: direct cap ruling required')
    S.require(a.get('timing_pilot_output_seal_sha256')=='44c4d8586126afec07fd855a6af5c57cc4a865e6f528fbb4954775bce2a0328c'and a.get('timing_pilot_disposition')=='TIMING_ONLY_ARCHIVE_EXCLUDED_FROM_JUDGE','Explicit original pilot disposition')
    S.require(a['experiment']=='E103'and a['gpu_count']==1 and a['gpu_type']in ('H200','B200'),'Assigned CORE E103 device')
    S.require(a['cap_seconds']==CAP_SECONDS and a.get('prior_seconds',0)==0,'Explicitly approved new full-bank allocation, prior pilot cost separately booked')
    xs=[a[k]for k in ['pod_created_epoch','custody_start_epoch','absolute_deadline_epoch']]
    S.require(all(type(x)in (int,float)and math.isfinite(x)for x in xs),'Finite original custody')
    S.require(a['custody_start_epoch']==a['pod_created_epoch']<=now and a['absolute_deadline_epoch']==a['pod_created_epoch']+CAP_SECONDS,'Creation-based fixed deadline')
    S.require(a['daily_budget_verified']is True and 0<=a['projected_daily_USD']<=1500,'Shared budget admission')
    S.require(sha(assets)==a['assets']['sha256']and a['pod_id']==os.environ.get('RUNPOD_POD_ID'),'Assets/provider identity')
    S.require(a['analysis_unit_gpu_types']=={'E103_primary':a['gpu_type']},'Own/control full analysis unit same GPU type')

def first_output(out):
    paths=list((out/'jobs').glob('*.json'))+list(out.glob('FIRST_SMOKE.*.json'))
    if not paths:return dict(first_output_utc='unknown',first_output_evidence=dict(reason='No new readout or analysis file'))
    p=min(paths,key=lambda p:p.stat().st_mtime_ns)
    return dict(first_output_utc=datetime.fromtimestamp(p.stat().st_mtime,timezone.utc).isoformat(),first_output_evidence=dict(source='archived_file_mtime',path=str(p.relative_to(out)),mtime_ns=p.stat().st_mtime_ns,scope='hardware smoke'if p.name.startswith('FIRST_SMOKE')else'first retained E103 sample'))

def smoke_base(backend,original_text,reference,out):
    import torch
    S.require(reference['gpu_type']=='H200'and len(reference['items'])==3,'Three sealed H200 references')
    head=backend.model.get_output_embeddings();seen=[];results=[]
    def finite(module,args,value):
        S.require(bool(torch.isfinite(value).all()),'Nonfinite B200 smoke logits');seen.append(True)
    handle=head.register_forward_hook(finite)
    try:
        for i,item in enumerate(reference['items']):
            values=original_text(backend,[item['input_ids']],max_new_tokens=item['max_new_tokens'])
            S.require(len(values)==1 and seen,'Finite serial B200 smoke')
            actual=values[0]['raw'];S.write(out/f'FIRST_SMOKE.{i}.json',dict(id=item['id'],raw=actual))
            old=item['H200_raw'];div=next((j for j,(x,y)in enumerate(zip(actual,old))if x!=y),min(len(actual),len(old)))if actual!=old else None
            results.append(dict(id=item['id'],exact_match=actual==old,first_divergence_character=div,H200_raw=old,B200_raw=actual))
    finally:handle.remove()
    S.write(out/'B200_SMOKE.json',dict(status='PASS',items=3,loads=True,finite_outputs=True,gpu_type='B200',source_output_seal_sha256=reference['source_output_seal_sha256'],comparisons=results,first_divergence=next((dict(item=x['id'],character=x['first_divergence_character'])for x in results if not x['exact_match']),None),scope='Original E81 greedy base path before registered E103 stochastic production'))

def main():
    if sys.argv[1:]==['--cpu-import-preflight']:
        from runtime import Runtime
        from worker import Clock,NoFit
        from batch_parity import trim_generated
        print('E103_EXACT_IMPORTS_PASS_NO_MODEL_LOAD');return
    p=argparse.ArgumentParser()
    for k in ['inputs','assets','assignment','out','source-seal','hardware-reference']:p.add_argument('--'+k,type=Path,required=True)
    for k in ['source-sha']:p.add_argument('--'+k,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);status='FAILED';timer=None;ass={}
    try:
        S.require(sha(a.source_seal)==a.source_sha,'Source seal identity');source=json.loads(a.source_seal.read_text())
        for n,h in source['files'].items():
            path=(ROOT/n).resolve();S.require(path.is_relative_to(ROOT)and sha(path)==h,'Frozen source member')
        S.require(sha(a.inputs)==PUBLIC_SHA and sha(a.hardware_reference)==REFERENCE_SHA,'Exact owner prefixes and hardware reference')
        items=json.loads(a.inputs.read_text());S.validate_public(items);S.require(len(items)==314,'Frozen314source items; no thinning')
        ass=json.loads(a.assignment.read_text());validate_assignment(ass,time.time(),a.assets);S.write(a.out/'ASSIGNMENT.json',ass)
        from runtime import Runtime
        from worker import Clock,NoFit
        class Backend(Runtime):
            def load_base(self):
                import torch,transformers
                S.require(torch.cuda.is_available()and torch.cuda.device_count()==1 and ass['gpu_type']in torch.cuda.get_device_name(0),'Exact actual CUDA hardware')
                super().load_base()
                S.write(a.out/'HARDWARE.json',dict(gpu_type=ass['gpu_type'],actual_gpu_name=torch.cuda.get_device_name(0),image_name=ass['image_name'],torch=torch.__version__,transformers=transformers.__version__,reader_adapter_loaded=False))
                if ass['gpu_type']=='B200':smoke_base(self,Runtime.text,json.loads(a.hardware_reference.read_text()),a.out)
        b=Backend(a.assets);end=ass['absolute_deadline_epoch']-60
        clock=Clock(a.out,end,{},b) # Original Clock reserves another60s: total120s retrieval.
        timer=threading.Timer(max(0,end-time.time()),lambda:os.kill(os.getpid(),signal.SIGKILL));timer.daemon=True;timer.start()
        S.acquire(items,b,clock,a.out,ROOT/'results/g_agreement/understand/late198/runtime.py')
        S.require(len(list((a.out/'jobs').glob('*.json')))==2512,'Complete2512samples');status='COMPLETE'
    except BaseException as error:
        status='NO_FIT'if type(error).__name__=='NoFit'else'FAILED'
        S.write(a.out/'FAILURE.json',dict(type=type(error).__name__,message=str(error)[:240]));raise
    finally:
        if timer:timer.cancel()
        S.write(a.out/'OUTPUT_SEAL.json',dict(experiment='E103',status=status,gpu_type=ass.get('gpu_type','unknown'),pod_id=ass.get('pod_id','unknown'),source_seal_sha256=a.source_sha,public_source_sha256=PUBLIC_SHA,expected_items=314,expected_samples=2512,completed_samples=len(list((a.out/'jobs').glob('*.json'))),reader_adapter_loads=0,seed=S.SEED,temperature=1.0,top_p=.95,top_k=0,max_new_tokens=64,serial_batch_size=1,completed_utc=datetime.now(timezone.utc).isoformat(),**first_output(a.out),files={str(q.relative_to(a.out)):sha(q)for q in sorted(a.out.rglob('*'))if q.is_file()and q.name!='OUTPUT_SEAL.json'}))

if __name__=='__main__':main()
