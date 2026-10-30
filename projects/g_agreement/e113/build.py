"""Public original dev/test carriers and CPU-only labels, independently sealed."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import numpy as np
from projects.g_agreement.e101.contract import read,write,sha,verify
from projects.g_agreement.e101.bind_owner import member
ROOT=Path(__file__).resolve().parents[3]
ROWS={'nesting_depth':'E57','indent_level':'E57','page_range_digit':'E57','fact_recall':'E56','format_plan':'E59','language_plan':'E59'}


def build(out):
    owner=ROOT/'results/g_agreement/understand/e101/vectors';seal=read(owner/'VECTOR_SEAL.json')
    sources=owner/'cpu_only/SOURCES.json'
    if sha(sources)!=seal['files']['cpu_only/SOURCES.json']:raise ValueError('original sealed source census')
    s=read(sources);items=[];labels=[];vectors=[];provenance=[]
    for row,bank in ROWS.items():
        src=s[bank];meta=Path(src['metadata_path']);member(meta.parent,'BANK_SEAL.json',src['bank_seal_sha256'],[meta.name])
        if sha(meta)!=src['metadata_sha256']:raise ValueError('sealed original bank metadata')
        selected=[x for x in read(meta) if x['feature']==row and x['split'] in ('dev','test')]
        mapping={}
        for cap in src['captures']:
            p=Path(cap['path']);verify(p.parent,p.name,cap['sha256'])
            order=read(p.parent/'items.order.json');h=np.load(p.parent/'acts44.npy',allow_pickle=False,mmap_mode='r')
            if sha(p.parent/'acts44.npy')!=cap['files']['acts44.npy'] or h.shape!=(len(order),5120):raise ValueError('sealed carrier order/dimensions')
            for i,ident in enumerate(order):
                if ident in mapping:raise ValueError('duplicate original carrier')
                mapping[ident]=(h[i].copy(),cap['sha256'],i)
        for split in ('dev','test'):
            xs=[x for x in selected if x['split']==split]
            if len(xs)!=84 or len({x['id'] for x in xs})!=84:raise ValueError('84 original dev and test per row')
            for x in xs:
                h,cap_sha,slot=mapping[x['id']]
                ident=hashlib.sha256(f'E113:{bank}:{x["id"]}'.encode()).hexdigest()
                base=hashlib.sha256(f'E101:{bank}:{x["id"]}'.encode()).hexdigest()
                items.append(dict(id=ident,base_id=base,row=row,split=split,vector_index=len(vectors),block=44))
                labels.append(dict(id=ident,base_id=base,row=row,split=split,label=x['label'],source_id=x['id'],bank=bank,
                   source_capture_sha256=cap_sha,source_vector_index=slot))
                vectors.append(h)
        provenance.append(dict(row=row,bank=bank,bank_seal_sha256=src['bank_seal_sha256'],metadata_sha256=sha(meta),captures=[dict(sha256=c['sha256'],files=c['files']) for c in src['captures']]))
    h=np.asarray(vectors,np.float32)
    if h.shape!=(1008,5120) or not np.isfinite(h).all():raise ValueError('complete six-row dev/test carrier grid')
    out.mkdir(parents=True,exist_ok=False);public=out/'inputs';public.mkdir();cpu=out/'cpu_only';cpu.mkdir()
    write(public/'items.json',items);np.save(public/'h44.npy',h,allow_pickle=False)
    write(public/'MANIFEST.json',dict(experiment='E113',authority='14e408dcf',rows=list(ROWS),source_block=44,dev_per_row=84,test_per_row=84,
       positions=['injected_activation','first_generated_token'],lens_layers='all decoder-block outputs',labels_on_pod=False,
       source_vector_seal_sha256=sha(owner/'VECTOR_SEAL.json'),source_provenance=provenance))
    write(public/'INPUT_SEAL.json',dict(experiment='E113',labels_on_pod=False,files={p.name:sha(p) for p in public.iterdir()}))
    write(cpu/'LABELS.json',labels);write(cpu/'LABEL_SEAL.json',dict(experiment='E113',files={'LABELS.json':sha(cpu/'LABELS.json')},input_sha256=sha(public/'INPUT_SEAL.json')))
    archive=out/'inputs.tar.gz'
    with tarfile.open(archive,'w:gz',compresslevel=1) as t:
        for p in public.iterdir():t.add(p,arcname='inputs/'+p.name,recursive=False)
    return dict(experiment='E113',public_root=str(public),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),
       cpu_label_seal=str(cpu/'LABEL_SEAL.json'),cpu_label_sha256=sha(cpu/'LABEL_SEAL.json'),rows=list(ROWS),items=1008,labels_on_pod=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.out),indent=2))
