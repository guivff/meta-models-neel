"""CPU-only exact E81 generic framing of E101's four unchanged content banks."""
import argparse,hashlib,tarfile
from pathlib import Path
from .contract import read,write,sha,verify
from .bind_owner import TOKENIZER_SHA,member
from .text_baseline import CONTENT,load
GENERIC='Describe what is going on in this text and what comes next.'
E81_FRAME_SOURCE_SHA='7abdafd07935df5d2bd8169a8baac2457281850e14f242d643428d2900dae140'


def build(owner,owner_sha,model,frame_source,out):
    verify(owner,'VECTOR_SEAL.json',owner_sha)
    if sha(model/'tokenizer.json')!=TOKENIZER_SHA or sha(frame_source)!=E81_FRAME_SOURCE_SHA:raise ValueError('frozen tokenizer and E81 framing source')
    from transformers import PreTrainedTokenizerFast
    tok=PreTrainedTokenizerFast(tokenizer_file=str(model/'tokenizer.json'))
    sources=read(owner/'cpu_only/SOURCES.json');items=[]
    for bank in ('E59','E56'):
        src=sources[bank];meta=Path(src['metadata_path'])
        member(meta.parent,'BANK_SEAL.json',src['bank_seal_sha256'],[meta.name])
        if sha(meta)!=src['metadata_sha256']:raise ValueError('frozen metadata')
        for x in read(meta):
            if x['split']!='test' or x['feature'] not in CONTENT:continue
            prompt=x['text']+'\n'+GENERIC
            ident=hashlib.sha256(f'E101_TEXT:{bank}:{x["id"]}'.encode()).hexdigest()
            items.append(dict(id=ident,row=x['feature'],prompt=prompt,input_ids=tok.encode(prompt,add_special_tokens=False)))
    out.mkdir(parents=True,exist_ok=False);public=out/'inputs';public.mkdir()
    write(public/'items.json',items)
    write(public/'MANIFEST.json',dict(experiment='E101_TEXT',generic_arm='E81',owner_source_sha256=owner_sha,
        e81_frame_source_sha256=E81_FRAME_SOURCE_SHA,tokenizer_sha256=TOKENIZER_SHA,max_new_tokens=128,batch_size=1))
    write(public/'INPUT_SEAL.json',dict(experiment='E101_TEXT',labels_on_pod=False,files={p.name:sha(p) for p in public.iterdir()}))
    load(public)
    archive=out/'text_inputs.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(public,arcname='inputs')
    write(out/'BINDING.json',dict(experiment='E101_TEXT',items=len(items),input_root=str(public),input_sha256=sha(public/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),GPU_calls=0))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('owner','model','frame-source','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--owner-sha',required=True);a=p.parse_args();build(a.owner,a.owner_sha,a.model,a.frame_source,a.out)
