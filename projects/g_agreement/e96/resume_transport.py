"""Evidence-bound E96 resume for HTTP200 upstream429 with zero reported usage.

Original judge.py, packet, rubric, indices and route remain byte-identical. A
single runtime transport-ID correction makes its audit read the actual returned
retry ID, as the existing E80 resume channel does. Every retry has a new ledger
reservation, exact identical wire, preserved failure evidence and bounded delay.
No uncertain/charged/truncated response is resent. No result classification or
sample selection is changed. Executed original+patched source hashes are recorded.
"""
import argparse,datetime,hashlib,json,time,shutil
from decimal import Decimal
from pathlib import Path
from . import judge as frozen
from .reconstructor_check import digest,write

MAX_RETRIES=4
DELAYS=(5,10,20,40)


def proven_uncharged_rate_error(saved,protocol):
    body=saved.get('response') or {};usage=body.get('usage') or {};choices=body.get('choices') or []
    if saved.get('http_status')!=200 or body.get('model') not in (protocol.MODEL,protocol.MODEL+'-001') or body.get('provider')!=protocol.PROVIDER_NAME:return False
    if len(choices)!=1:return False
    c=choices[0];error=c.get('error') or {};message=c.get('message') or {}
    try:zero=Decimal(str(usage.get('cost')))==0
    except Exception:return False
    return zero and all(usage.get(k)==0 for k in ('prompt_tokens','completion_tokens','total_tokens')) and c.get('finish_reason')=='error' and error.get('code')==429 and error.get('metadata',{}).get('error_type')=='rate_limit_exceeded'


def retry_id(base,k):return hashlib.sha256(f'E96:UNCHARGED_UPSTREAM429:{base}:{k}'.encode()).hexdigest()


def patch_client(api,io,protocol):
    original=api.Client.one
    if getattr(original,'_e96_uncharged_rate_patch',False):return
    def one(self,stage,items,taxonomy=None):
        result=original(self,stage,items,taxonomy);base=result['id'];folder=self.root/stage
        for k in range(1,MAX_RETRIES+1):
            rid=result['id'];response=folder/(rid+'.response.json');request=folder/(rid+'.request.json')
            if not response.exists() or not proven_uncharged_rate_error(json.loads(response.read_text()),protocol):return result
            book,done=self.ledger.totals()
            if rid not in done or book[rid]!=0:raise RuntimeError('zero-reported-usage error must already be settled at0; no resend')
            new=retry_id(base,k)
            if new in book and new not in done:raise RuntimeError('uncertain prior retry reservation; never resend')
            wire=api.P.payload(stage,items,taxonomy)
            if json.loads(request.read_text())['wire']!=wire:raise ValueError('retry wire differs from preserved original')
            proof={'base_request_id':base,'failed_request_id':rid,'retry_request_id':new,'retry_number':k,'max_retries':MAX_RETRIES,'reason':'HTTP200 upstream429; zero reported prompt/completion/total tokens and settledcost0; incomplete message payload retained and ignored under existing E80c policy','request_sha256':digest(request),'response_sha256':digest(response),'wire_sha256':hashlib.sha256(io.canonical(wire).encode()).hexdigest(),'actual_usd':'0','scientific_change':False}
            evidence=folder/(rid+'.uncharged_rate_reconciliation.json')
            if evidence.exists() and json.loads(evidence.read_text())!=proof:raise ValueError('reconciliation evidence changed')
            if not evidence.exists():write(evidence,proof)
            if new not in book:time.sleep(DELAYS[k-1])
            saved=io.digest
            try:
                io.digest=lambda value,new=new:new
                result=original(self,stage,items,taxonomy)
            finally:io.digest=saved
        return result
    one._e96_uncharged_rate_patch=True
    api.Client.one=one


def runtime():
    original=Path(frozen.__file__).read_text()
    before="result=client.one(stage,batch);response=ledger/stage/(rid+'.response.json');request=ledger/stage/(rid+'.request.json')"
    after="result=client.one(stage,batch);rid=result['id'];response=ledger/stage/(rid+'.response.json');request=ledger/stage/(rid+'.request.json')"
    if original.count(before)!=1:raise ValueError('frozen transport ID patch anchor changed')
    patched=original.replace(before,after,1)
    ns={'__name__':__name__+'._runtime','__package__':frozen.__package__,'__file__':frozen.__file__}
    exec(compile(patched,str(frozen.__file__)+'[audited transport-id correction]','exec'),ns)
    load=ns['route_modules']
    def wrapped(route):
        api,privacy,protocol,io=load(route);patch_client(api,io,protocol);return api,privacy,protocol,io
    ns['route_modules']=wrapped
    return ns['run'],original,patched


def run(packet,allocation,receipt_dir):
    if (packet.parent/'judgments/JUDGMENT_SEAL.json').exists():raise ValueError('terminal judgments never resumed')
    original_sha=digest(Path(frozen.__file__));seal=json.loads((packet/'PACKET_SEAL.json').read_text())
    if original_sha!=seal['code_files']['projects/g_agreement/e96/judge.py']:raise ValueError('original frozen judge changed')
    run_f,original,patched=runtime();receipt_dir.mkdir(parents=True,exist_ok=True)
    doc={'experiment':'E96','kind':'OPERATIONAL_TRANSPORT_ONLY_NO_SCIENTIFIC_CHANGE','packet_seal_sha256':digest(packet/'PACKET_SEAL.json'),'allocation_sha256':digest(allocation),'original_judge_sha256':original_sha,'resume_transport_sha256':digest(__file__),'executed_runtime_sha256':hashlib.sha256(patched.encode()).hexdigest(),'patch':'afterClient.one use returned request id for saved request/response audit; all other frozen code unchanged','retry_policy':'only proven HTTP200 upstream429/zero reported tokens/zero settledcost; incomplete payload ignored; max4 distinct reservations with5/10/20/40s delays','cache_policy':'preserve every failure; reuse cached successes; no deletion/overwrite; never resenduncertainchargedresponse','first_output_utc':'unknown','first_output_note':'resumeplan; actualjudgment firstmtime retained in canonicalFIRST_OUTPUT.json'}
    p=receipt_dir/'RESUME_SOURCE_RECEIPT.json'
    if p.exists() and json.loads(p.read_text())!=doc:raise ValueError('resume source receipt changed')
    if not p.exists():
        (receipt_dir/'EXECUTED_JUDGE_RUNTIME.py').write_text(patched);write(p,doc)
    output=packet.parent/'judgments'
    suffix=digest(__file__)[:12]
    for src,name in [(p,'TRANSPORT_RESUME_'+suffix+'_SOURCE_RECEIPT.json'),(receipt_dir/'EXECUTED_JUDGE_RUNTIME.py','EXECUTED_JUDGE_RUNTIME_'+suffix+'.py'),(Path(__file__),'TRANSPORT_RESUME_DRIVER_'+suffix+'.py')]:
        dest=output/name
        if dest.exists() and digest(dest)!=digest(src):raise ValueError('resume source copy changed')
        if not dest.exists():shutil.copy2(src,dest)
    return run_f(packet,allocation)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--packet',type=Path,required=True);p.add_argument('--allocation',type=Path,required=True);p.add_argument('--receipt-dir',type=Path,required=True);a=p.parse_args();print(json.dumps(run(a.packet,a.allocation,a.receipt_dir),indent=2))
