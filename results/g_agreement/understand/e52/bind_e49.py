"""Bind Integrator's pre-reader capture; never open a reader output."""
from pathlib import Path
import argparse
import json
import numpy as np
from build_basis import ROOT,HERE,CACHE,sha,read,dump

def bind(receipt):
    r=read(receipt)
    if (r.get('issuer')!='integrator' or r.get('status')!='VERIFIED_CAPTURE_BEFORE_READERS'
            or r.get('reader_scores_exist') is not False or r.get('readers_paused_until_forecast_commit') is not True
            or r.get('bank_seal_sha256')!='ccc2b3b6e27d0227f2d17f1de0efe2cb9a33cfd4d299656f19d7e4a4e3db43c9'):
        raise ValueError('sealed prospective capture and reader pause required')
    for key in ('acts44','order','capture_seal'):
        if sha(r[key]['path'])!=r[key]['sha256']:raise ValueError('verified capture bytes differ')
    cap=read(r['capture_seal']['path'])
    for key in ('acts44','order'):
        relative=Path(r[key]['path']).resolve().relative_to(Path(r['capture_seal']['path']).resolve().parent).as_posix()
        if cap['files'][relative]!=r[key]['sha256']:raise ValueError('capture seal does not bind supplied data')
    frozen=ROOT.parent/'wt-wtext/results/g_agreement/understand/e49/cache/frozen_2026-10-26'
    if sha(frozen/'BANK_SEAL.json')!=r['bank_seal_sha256']:raise ValueError('frozen E49 bank drift')
    bankseal=read(frozen/'BANK_SEAL.json')
    if sha(frozen/'items.PRIVATE.json')!=bankseal['files']['items.PRIVATE.json']:raise ValueError('bank records drift')
    records=read(frozen/'items.PRIVATE.json');selected=sorted((x for x in records if x['split']=='test'),key=lambda x:(x['feature'],x['id']))
    order=read(r['order']['path']);ix={k:i for i,k in enumerate(order)};acts=np.load(r['acts44']['path'],allow_pickle=False,mmap_mode='r')
    if len(ix)!=len(order) or acts.shape!=(len(order),5120) or not {x['id'] for x in selected}<=set(ix):raise ValueError('complete capture order/grid required')
    defs=read(HERE/'VALUE_WORD_SETS_2026-10-27.json')['banks']['E49']
    if len(selected)!=1344 or {x['feature'] for x in selected}!=set(defs):raise ValueError('all16 frozen test rows')
    metadata=[{'id':x['id'],'feature':x['feature'],'y':x['label'],'cluster':x['cluster']} for x in selected]
    for row,spec in defs.items():
        rr=[x for x in selected if x['feature']==row]
        if len(rr)!=84 or sum(x['label'] for x in rr)!=42 or any(x['value']!=spec['values'][0 if x['label'] else 1] for x in rr):raise ValueError('frozen A/B orientation')
    matrix=np.asarray(acts[[ix[x['id']] for x in selected]],dtype=np.float32)
    if not np.isfinite(matrix).all():raise ValueError('finite test captures')
    out=CACHE/'E49-input';out.mkdir(exist_ok=False);np.save(out/'acts44.npy',matrix,allow_pickle=False);dump(out/'items.json',metadata)
    dump(out/'DELIVERY_RECEIPT.json',r)
    dump(out/'INPUT_SEAL.json',{'bank':'E49','layer':44,'split':'test','rows':{k:{'values':v['values'],'class':v['class']} for k,v in defs.items()},'files':{n:sha(out/n) for n in ('acts44.npy','items.json','DELIVERY_RECEIPT.json')}})
    dump(HERE/'E49_CAPTURE_BINDING_2026-10-27.json',{'directory':str(out.relative_to(ROOT)),'input_seal_sha256':sha(out/'INPUT_SEAL.json'),'reader_scores_exist':False,'readers_paused_until_forecast_commit':True,'delivery_receipt_sha256':sha(out/'DELIVERY_RECEIPT.json'),'bank_seal_sha256':r['bank_seal_sha256']})
    print('E49 pre-reader capture bound; no reader outputs accessed')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);a=p.parse_args();bind(a.receipt)
