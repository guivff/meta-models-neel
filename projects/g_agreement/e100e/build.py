"""Lossless original E49 carriers, deterministic different-value donors; CPU only."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha,verify,require
ROWS=('container_after_move','holder_after_handovers')
SEED=20261029

def pairings(xs,rng):
    require(len(xs)==84 and len({x['id'] for x in xs})==84,'84 original unique test items')
    pairs=[]
    for i,x in enumerate(xs):
        eligible=[j for j,y in enumerate(xs) if y['value']!=x['value']]
        require(bool(eligible),'different-value donor exists')
        pairs.append(int(rng.choice(eligible)))
    return pairs

def build(capture,private,private_sha,out):
    require(sha(private)==private_sha,'original private bank binding')
    bankseal=read(private.parent/'BANK_SEAL.json')
    require(bankseal['files']['items.PRIVATE.json']==private_sha,'bank-sealed private metadata')
    cap=read(capture/'CAPTURE_SEAL.json')
    require(sha(private.parent/'BANK_SEAL.json')==cap['bank_seal_sha256'],'capture and original private bank same seal')
    verify(capture,'CAPTURE_SEAL.json',sha(capture/'CAPTURE_SEAL.json'))
    require(cap['experiment']=='E49' and cap['stage']=='CAPTURE_COMPLETE_WAITING_FOR_GO','original sealed E49 capture')
    order=read(capture/'items.order.json');require(len(set(order))==len(order),'unique original order')
    mapping={ident:i for i,ident in enumerate(order)}
    arrays={b:np.load(capture/f'acts{b}.npy',allow_pickle=False,mmap_mode='r') for b in (42,44)}
    require(all(h.shape==(len(order),5120) for h in arrays.values()),'native dimensions/order')
    bank=read(private);items=[];labels=[];selected=[];rng=np.random.default_rng(SEED)
    for row in ROWS:
        xs=[x for x in bank if x['feature']==row and x['split']=='test'];pairs=pairings(xs,rng);offset=len(items)
        ids=[hashlib.sha256(('E100e:E49:'+x['id']).encode()).hexdigest() for x in xs]
        for i,(x,donor) in enumerate(zip(xs,pairs)):
            slot=mapping[x['id']];selected.append(slot)
            items.append(dict(id=ids[i],row=row,slot=offset+i,row_slot=i,donor_slot=offset+donor))
            labels.append(dict(id=ids[i],row=row,source_id=x['id'],source_slot=slot,source_value=x['value'],source_label=x['label'],donor_id=ids[donor],donor_source_id=xs[donor]['id'],donor_value=xs[donor]['value'],donor_label=xs[donor]['label'],split='test'))
    out.mkdir(parents=True,exist_ok=False);public=out/'inputs';public.mkdir();cpu=out/'cpu_only';cpu.mkdir()
    write(public/'items.json',items)
    for b,h in arrays.items():np.save(public/f'H{b}.npy',np.asarray(h[selected],np.float32),allow_pickle=False)
    write(public/'MANIFEST.json',dict(experiment='E100e',authority='14e408dcf',seed=SEED,rows=list(ROWS),test_per_row=84,condition='transplant',read_blocks={'oracle':44,'nla':42},labels_on_pod=False,original_capture_sha256=sha(capture/'CAPTURE_SEAL.json'),original_bank_seal_sha256=cap['bank_seal_sha256'],original_capture_files=cap['files'],pairing='single default_rng(20261029), row order as listed, frozen private-bank test order, choice uniformly with replacement from same-row different-value test items'))
    write(public/'INPUT_SEAL.json',dict(experiment='E100e',labels_on_pod=False,files={p.name:sha(p) for p in public.iterdir()}))
    write(cpu/'LABELS.json',labels);write(cpu/'LABEL_SEAL.json',dict(experiment='E100e',files={'LABELS.json':sha(cpu/'LABELS.json')},original_private_sha256=private_sha,original_capture_root=str(capture),input_sha256=sha(public/'INPUT_SEAL.json')))
    archive=out/'inputs.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in public.iterdir():t.add(p,arcname='inputs/'+p.name,recursive=False)
    return dict(public_root=str(public.resolve()),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(archive.resolve()),archive_sha256=sha(archive),cpu_labels=str(cpu.resolve()),label_seal_sha256=sha(cpu/'LABEL_SEAL.json'),items=168,readouts=336,labels_on_pod=False)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('capture','private','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--private-sha',required=True);a=p.parse_args();print(json.dumps(build(a.capture,a.private,a.private_sha,a.out),indent=2))
