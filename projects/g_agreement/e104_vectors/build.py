"""E104 dev-only one-time block40 capture packet and E101-rule CPU fit.
GPU owner calls capture_once ONLY inside its admitted E104 runtime/clock.
"""
import argparse,hashlib,json,time
from pathlib import Path
import numpy as np
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
ROOT=Path(__file__).resolve().parents[3]
SOURCES=ROOT/'results/g_agreement/understand/e101/vectors/cpu_only/SOURCES.json'
HERE=ROOT/'results/g_agreement/understand/e104/vectors'
ROWS={'E56':'fact_recall','E59':'language_plan'}

def seal(out,name,**meta):
    write(out/name,dict(meta,files={f.name:sha(f) for f in out.iterdir() if f.is_file() and f.name!=name}))

def prepare(out):
    sources=read(SOURCES);items=[];private=[]
    for bank,row in ROWS.items():
        s=sources[bank];require(sha(s['metadata_path'])==s['metadata_sha256'],'E101 metadata binding')
        records=read(s['metadata_path'])
        if isinstance(records,dict):records=records['items']
        dev=sorted((x for x in records if x['feature']==row and x['split']=='dev'),key=lambda x:x['id'])
        require(len(dev)==84 and all(sum(x['label']==y for x in dev)==42 for y in (0,1)),'same84 balanced frozen dev items')
        for x in dev:
            opaque=hashlib.sha256(('E104:dev40:'+x['id']).encode()).hexdigest()
            require(len(x['ids'])>=9,'eight earlier write positions exist')
            items.append(dict(id=opaque,ids=x['ids'],read_index=len(x['ids'])-1))
            private.append(dict(id=opaque,original_id=x['id'],row=row,label=x['label'],split='dev'))
    require(len({x['id'] for x in items})==168,'unique original dev IDs')
    out=Path(out);out.mkdir(parents=True,exist_ok=False);public=out/'public';public.mkdir()
    write(out/'PRIVATE.json',private);(out/'PRIVATE.json').chmod(0o600)
    write(public/'items.json',items)
    seal(public,'INPUT_SEAL.json',experiment='E104',stage='dev_direction40',block=40,position='read_token',labels_on_pod=False,records=168)
    write(out/'CPU_BINDING.json',dict(source_sha256=sha(SOURCES),sources={b:dict(metadata_sha256=sources[b]['metadata_sha256']) for b in ROWS},input_sha256=sha(public/'INPUT_SEAL.json'),private_sha256=sha(out/'PRIVATE.json')))
    return dict(input=str(public/'INPUT_SEAL.json'),input_sha256=sha(public/'INPUT_SEAL.json'))

def capture_once(runtime,inputs,input_sha,out,clock):
    """Call from admitted runner: outer owner retains hardware gate/deadline/guards.
    No labels/targets. Output-dir exclusivity forbids replay on same receipt.
    """
    from mats.capture import capture
    for name,digest in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==digest,'frozen capture recipe')
    inputs=Path(inputs);s=verify(inputs/'INPUT_SEAL.json',input_sha)
    require(s['experiment']=='E104' and s['stage']=='dev_direction40' and s['block']==40 and s['labels_on_pod'] is False,'dev40-only packet')
    xs=read(inputs/'items.json');require(len(xs)==168 and len({x['id'] for x in xs})==168 and all(set(x)=={'id','ids','read_index'} and x['read_index']==len(x['ids'])-1 for x in xs),'label-free frozen token inventory')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    with (inputs/'CAPTURE_ONCE.json').open('x') as guard:json.dump(dict(input_sha256=input_sha,started_epoch=time.time()),guard)
    write(out/'START.json',dict(experiment='E104',input_sha256=input_sha,started_epoch=time.time()))
    model,tok,cm=runtime.subject();values=[]
    import torch
    with cm,torch.inference_mode():
        for x in xs:
            clock.check()
            values.append(clock.call('dev40_capture',lambda:capture(model,[x['ids']],[40],[[x['read_index']]],batch_size=1,pad_id=tok.pad_token_id or 0))[40].numpy()[0,0])
    acts=np.stack(values);require(acts.shape==(168,5120) and np.isfinite(acts).all(),'finite168x5120 block40 residuals')
    np.save(out/'acts40.npy',acts);write(out/'items.order.json',[x['id'] for x in xs])
    seal(out,'CAPTURE_SEAL.json',experiment='E104',status='COMPLETE',stage='dev_direction40',block=40,input_sha256=input_sha,position='read_token',completed_epoch=time.time())

def fit_arrays(records,acts):
    require(len(records)==len(acts)==168 and acts.shape[1:]==(5120,) and np.isfinite(acts).all(),'finite original capture grid')
    require(len({x['original_id'] for x in records})==168 and all(x['split']=='dev' and x['row'] in ROWS.values() and x['label'] in (0,1) for x in records),'only unique original dev items')
    result={}
    for row in ROWS.values():
        groups={y:sorted((i for i,x in enumerate(records) if x['row']==row and x['split']=='dev' and x['label']==y),key=lambda i:records[i]['original_id']) for y in (1,0)}
        require(all(len(g)==42 for g in groups.values()),'42 frozen dev items per class')
        d=np.stack([acts[groups[y]].mean(0,dtype=np.float64) for y in (1,0)]);d=d[0]-d[1];norm=float(np.linalg.norm(d))
        require(norm>1e-12,'nonzero dev difference');result[row]=(d,d/norm,norm)
    return result

def fit(packet,capture_seal,capture_sha,out):
    packet=Path(packet);request=read(HERE/'REQUEST.json')
    require(sha(packet/'CPU_BINDING.json')==request['cpu_binding_sha256'],'frozen CPU binding')
    b=read(packet/'CPU_BINDING.json')
    verify(packet/'public/INPUT_SEAL.json',b['input_sha256']);require(sha(packet/'PRIVATE.json')==b['private_sha256'],'local CPU join')
    s=verify(capture_seal,capture_sha);require(s['experiment']=='E104' and s['status']=='COMPLETE' and s['block']==40 and s['stage']=='dev_direction40' and s['input_sha256']==b['input_sha256'] and s['position']=='read_token','sealed block40 capture matches dev-only input')
    capture_root=Path(capture_seal).parent;order=read(capture_root/'items.order.json');private=read(packet/'PRIVATE.json');require(order==[x['id'] for x in private],'exact frozen capture order')
    result=fit_arrays(private,np.load(capture_root/'acts40.npy',allow_pickle=False));out=Path(out);out.mkdir(parents=True,exist_ok=False)
    norms={}
    for row,(d,u,norm) in result.items():
        np.save(out/(row+'.d40.npy'),d);np.save(out/(row+'.unit_d40.npy'),u);norms[row]=norm
    r=np.random.default_rng(np.random.SeedSequence([20261029,40])).standard_normal(5120);np.save(out/'random40.npy',r/np.linalg.norm(r))
    write(out/'NORMS.json',norms)
    seal(out,'VECTOR_SEAL.json',experiment='E104',status='COMPLETE',block=40,fit_split='dev',class_count=42,orientation='mean(label1)-mean(label0)',capture_sha256=capture_sha,input_sha256=b['input_sha256'],random_seed=20261029,random_recipe='SeedSequence([20261029,40]), standard_normal5120, unit')

if __name__=='__main__':
    p=argparse.ArgumentParser();sp=p.add_subparsers(dest='action',required=True)
    a=sp.add_parser('prepare');a.add_argument('--out',required=True)
    a=sp.add_parser('fit');a.add_argument('--packet',required=True);a.add_argument('--capture-seal',required=True);a.add_argument('--capture-sha',required=True);a.add_argument('--out',required=True)
    a=p.parse_args()
    if a.action=='prepare':print(json.dumps(prepare(a.out)))
    else:fit(a.packet,a.capture_seal,a.capture_sha,a.out)
