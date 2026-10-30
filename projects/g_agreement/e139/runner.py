"""§251 reconstructor acquisition only; exact frozen texts, no reward scoring."""
import time
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,verify,sha
from projects.g_agreement.e130.runner import load_model,resolve_snapshot,AR_REV,BASE_REV
from projects.g_agreement.e130.olens_ar import OLensAR


def validate_items(items):
    if not items or len({x['id']for x in items})!=len(items):raise ValueError('unique nonempty frozen opaque IDs')
    if any(set(x)!={'id','text'}or not isinstance(x['id'],str)or not isinstance(x['text'],str)for x in items):
        raise ValueError('opaque id/exact frozen text only; no roles/targets')


def load(root,digest):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s.get('experiment')!='E139'or s.get('labels_on_pod')is not False or set(s['files'])!={'items.json','MANIFEST.json'}:
        raise ValueError('sealed public strings only')
    items=read(root/'items.json');m=read(root/'MANIFEST.json');validate_items(items)
    if m.get('experiment')!='E139'or m.get('prompts')!=len(items)or m.get('labels_on_pod')is not False:
        raise ValueError('exact frozen owner census')
    if m.get('tokenizer_revision')!=BASE_REV or m.get('tokenization')!=dict(add_special_tokens=False,truncation=False,strip=False,tag_added_by='original OLensAR.reconstruct tag44'):
        raise ValueError('explicit original token policy; no hidden truncation or rewriting')
    return items,m


def contract_gate(contract):
    if set(contract)!={'source_commit','source_sha256','tests_passed','reward_mode'}or contract['tests_passed']is not True:
        raise ValueError('prospective committed tested owner scoring contract before any output')
    if len(contract['source_commit'])!=40 or any(c not in '0123456789abcdef'for c in contract['source_commit'])or len(contract['source_sha256'])!=64 or any(c not in '0123456789abcdef'for c in contract['source_sha256']):
        raise ValueError('literal source commit/seal pin')
    if contract['reward_mode']not in ('pinned_training_joint_bullet_FVE','proxy_whitened_FVE'):
        raise ValueError('owner pins exact reward or explicitly registered proxy; no guessed reward')


def acquire(model,items,out,check_work,*,gpu_type,owner_contract,batch=16):
    """E130's unchanged native AR method, once per full exact owner string.

    No reader, text generation, reward arithmetic, whitening or calibration.
    The sole operator callback owns original creation clock and whole-need gate.
    """
    validate_items(items);contract_gate(owner_contract)
    out=Path(out)
    if out.exists():raise FileExistsError('fresh E139 attempt only; no partial reuse')
    if batch!=16 or not gpu_type or not callable(check_work):raise ValueError('original batch16/operator clock/actual GPU type')
    rows=[dict(id=x['id'],ids=model.tok.encode(x['text'],add_special_tokens=False))for x in items]
    if any(any(type(t)is not int or t<0 for t in x['ids'])for x in rows):raise ValueError('full literal tokenizer IDs')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'ONCE.json',dict(experiment='E139',rows=len(rows),owner_contract=owner_contract,reader_calls=0,generation_calls=0,scoring=False))
    write(out/'TOKEN_ROWS.json',rows)
    jobs=[rows[i:i+16]for i in range(0,len(rows),16)];durations=[];index=[];started=time.monotonic();status='COMPLETE'
    for j,job in enumerate(jobs):
        if not check_work(len(jobs)-j,time.monotonic()-started,max(durations,default=0.0)):
            status='NO_FIT';break
        t=time.monotonic();values=model.reconstruct([x['ids']for x in job],44,variant=('li','ln'),batch=16)
        if hasattr(values,'numpy'):values=values.numpy()
        values=np.asarray(values)
        if values.shape!=(len(job),5120)or values.dtype!=np.float32 or not np.isfinite(values).all():raise ValueError('native finite fp32 whitened rebuild; no transform')
        name=f'rebuild-{j:04d}.npy';np.save(out/name,values,allow_pickle=False)
        durations.append(time.monotonic()-t);index.extend(dict(id=x['id'],file=name,index=k,gpu_type=gpu_type)for k,x in enumerate(job));write(out/'INDEX.json',index)
    write(out/'TIMING.json',dict(batch_seconds=durations,elapsed_seconds=time.monotonic()-started))
    write(out/'OUTPUT_SEAL.json',dict(experiment='E139',status=status,tag=44,variant=['li','ln'],rows_expected=len(rows),rows_written=len(index),reader_calls=0,generation_calls=0,reward_scored=False,whitening_applied=False,calibration=False,space='native AR whitened output; no raw activation comparison by runner',owner_contract=owner_contract,files={p.name:sha(p)for p in out.iterdir()if p.is_file()}))
    return status


def source_gate():
    root=Path(__file__).resolve().parents[3]
    for n,h in read(Path(__file__).with_name('SOURCE_SEAL.json'))['files'].items():
        if sha(root/n)!=h:raise ValueError('changed E139 sealed source '+n)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();items,_=load(a.input,a.input_sha)
    if a.validate_only:print('E139 VALIDATE_OK',len(items),'reconstructor only; no weights loaded');return
    raise SystemExit('TrackQ original1800s creation-clock/custody required; no standalone production')

if __name__=='__main__':main()
