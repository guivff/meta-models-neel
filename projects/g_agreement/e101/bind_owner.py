"""CPU adapter for W-internals-B's E101 vectors and sealed original captures."""
import argparse,hashlib,tarfile
from pathlib import Path
import numpy as np
from .contract import read,write,sha,verify,ROWS,committed_dose
from .materialize import compose,save
ROOT=Path(__file__).resolve().parents[3]
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'
BANKS={'language_plan':'E59','format_plan':'E59','fact_recall':'E56','language_continuation':'E56','nesting_depth':'E57','indent_level':'E57','page_range_digit':'E57'}
PAIRS={'language_plan':[['Je','The'],['Le','The']],'format_plan':[['-','The']],
       'fact_recall':[[' Paris',' Lima']],'language_continuation':[[' et',' und']],
       'nesting_depth':[[' ]',' ]]]']],'indent_level':[['\n    pass','\n            pass']]}
RULING='88b74af5a'


def member(root,seal_name,expected,names):
    root=Path(root)
    if sha(root/seal_name)!=expected:raise ValueError('source seal identity')
    s=read(root/seal_name)
    for n in names:
        if sha(root/n)!=s['files'][n]:raise ValueError('sealed source member')
    return s


def build(owner,owner_sha,model,out,stage,dose_path=None,dose_commit=None,dose_sha=None):
    if stage=='test':committed_dose(ROOT,dose_path,dose_commit,dose_sha)
    seal=verify(owner,'VECTOR_SEAL.json',owner_sha)
    pub=owner/'public';verify(pub,'INPUT_SEAL.json',seal['files']['public/INPUT_SEAL.json'])
    if sha(model/'tokenizer.json')!=TOKENIZER_SHA:raise ValueError('pinned tokenizer')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True)
    sources=read(owner/'cpu_only/SOURCES.json');manifest=read(pub/'MANIFEST.json')
    if manifest['experiment']!='E101' or manifest['random_seed']!=20261028 or {(x['row'],x['block']) for x in manifest['rows']}!={(r,b) for r in ROWS for b in (42,44)}:raise ValueError('owner exact fourteen directions')
    directions={};norms={};randoms={}
    for x in manifest['rows']:
        k=(x['row'],x['block']);directions[k]=np.load(pub/x['d'],allow_pickle=False);norms[k]=x['raw_norm']
        r=np.load(pub/x['r'],allow_pickle=False)
        if x['block'] in randoms and not np.array_equal(r,randoms[x['block']]):raise ValueError('one shared random per block')
        randoms[x['block']]=r
    records=[];carriers={};original={};candidate_audit={}
    for bank,src in sources.items():
        meta=Path(src['metadata_path']);names=[meta.name]+(['ANNOTATIONS.PRIVATE.json'] if bank=='E57' else [])
        member(meta.parent,'BANK_SEAL.json',src['bank_seal_sha256'],names)
        if sha(meta)!=src['metadata_sha256']:raise ValueError('metadata identity')
        ann=read(meta.parent/'ANNOTATIONS.PRIVATE.json') if bank=='E57' else {}
        xs=[x for x in read(meta) if x['split']==stage and BANKS.get(x['feature'])==bank]
        by={x['id']:x for x in xs};seen=set()
        for x in xs:
            row=x['feature'];identity=hashlib.sha256(f'E101:{bank}:{x["id"]}'.encode()).hexdigest()
            pairs=[[' '+s for s in ann[x['id']]['answer_pair']]] if row=='page_range_digit' else PAIRS[row]
            candidates=[[tok.encode(s,add_special_tokens=False) for s in p] for p in pairs]
            if not candidates or any(not c for p in candidates for c in p):raise ValueError('frozen nonempty continuation')
            # All seven frozen banks encode candidate A as label 1. Preserve the
            # original label, never infer truth from a generated continuation.
            records.append(dict(id=identity,row=row,split=stage,ids=x['ids'],candidate_ids=candidates,label=x['label'],contrast_target_sign=1-2*x['label']))
            original[x['id']]=identity;candidate_audit[identity]=dict(source_item_id=x['id'],bank=bank,row=row,strings=pairs,token_ids=candidates)
        for cap in src['captures']:
            path=Path(cap['path']);member(path.parent,path.name,cap['sha256'],['acts42.npy','acts44.npy','items.order.json'])
            order=read(path.parent/'items.order.json')
            for block in (42,44):
                h=np.load(path.parent/f'acts{block}.npy',mmap_mode='r',allow_pickle=False)
                if h.shape!=(len(order),5120):raise ValueError('capture shape')
                for i,ident in enumerate(order):
                    if ident not in by:continue
                    row=by[ident]['feature'];key=(row,block);dest=carriers.setdefault(key,{})
                    if original[ident] in dest:raise ValueError('duplicate captured item')
                    dest[original[ident]]=h[i].copy()
        if any(len(carriers.get((r,b),{}))!=84 for r in ROWS if BANKS[r]==bank for b in (42,44)):raise ValueError('complete captured split')
    out.mkdir(parents=True,exist_ok=False);cpu=out/'cpu_only';cpu.mkdir();key_all={};packages=[]
    for row in sorted(ROWS):
        xs,h,key,selected=compose([x for x in records if x['row']==row],carriers,directions,norms,randoms,stage,repo=ROOT,dose_path=dose_path,dose_commit=dose_commit,dose_sha=dose_sha,ruling_commit=RULING)
        key_all.update(key)
        if not xs:
            packages.append(dict(row=row,status='NOT_EVALUABLE_BOTH_BLOCKS'));continue
        dest=out/row;save(dest,xs,h,stage,selected,RULING,owner_sha,dose_commit,dose_sha)
        archive=out/(row+'.tar.gz')
        with tarfile.open(archive,'w:gz',compresslevel=1) as t:t.add(dest,arcname='inputs')
        packages.append(dict(row=row,input_root=str(dest),input_sha256=sha(dest/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),bytes=archive.stat().st_size,cells=len(xs)))
    write(cpu/'KEY.json',key_all);write(cpu/'CANDIDATE_AUDIT.json',candidate_audit)
    write(out/'BINDING.json',dict(experiment='E101',stage=stage,owner_seal_sha256=owner_sha,tokenizer_sha256=TOKENIZER_SHA,
        ruling_commit=RULING,packages=packages,cpu_key_path=str(cpu/'KEY.json'),cpu_key_sha256=sha(cpu/'KEY.json'),candidate_audit_sha256=sha(cpu/'CANDIDATE_AUDIT.json'),GPU_calls=0))


def main():
    p=argparse.ArgumentParser()
    for n in ('owner','model','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--owner-sha',required=True);p.add_argument('--stage',choices=['dev','test'],required=True)
    p.add_argument('--dose-path',type=Path);p.add_argument('--dose-commit');p.add_argument('--dose-sha')
    a=p.parse_args();build(a.owner,a.owner_sha,a.model,a.out,a.stage,a.dose_path,a.dose_commit,a.dose_sha)
if __name__=='__main__':main()
