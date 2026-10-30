"""Lossless pre-output §252 deviation2 fallback; no model/answer/label access."""
import hashlib,json,tarfile
from pathlib import Path
PARENT_SEAL='5daa0c676bb9cbe561ba1e37e698ac807b38b4eb8965376e7a6e9d5f8fad5819'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def first300(raw):
    rows=json.loads(raw)
    if len(rows)!=1200:raise ValueError('original600 pairs required')
    pairs=[]
    for i in range(0,1200,2):
        a,b=rows[i:i+2]
        if a['pair_id']!=b['pair_id'] or [a['member'],b['member']]!=[0,1]:raise ValueError('original interleaved order')
        if a['pair_id'] in pairs:raise ValueError('unique pairs')
        pairs.append(a['pair_id'])
    # Preserve exact original serialized record bytes, not a regenerated bank.
    decoder=json.JSONDecoder();pos=raw.index('[')+1
    for i in range(600):
        while raw[pos].isspace() or raw[pos]==',':pos+=1
        _,pos=decoder.raw_decode(raw,pos)
    result=raw[:pos]+'\n]\n'
    if json.loads(result)!=rows[:600]:raise ValueError('lossless prefix proof')
    return result

def build(parent,out):
    parent=Path(parent);out=Path(out)
    if sha(parent/'INPUT_SEAL.json')!=PARENT_SEAL:raise ValueError('pinned original parent seal')
    seal=json.loads((parent/'INPUT_SEAL.json').read_text())
    for f,h in seal['files'].items():
        if sha(parent/f)!=h:raise ValueError('original member hash')
    raw=first300((parent/'items.json').read_text());out.mkdir(parents=True,exist_ok=False)
    pub=out/'public';pub.mkdir();(pub/'items.json').write_text(raw)
    manifest=dict(experiment='E140',stage='screen',labels_on_pod=False,pairs=300,prompts=600,
        authority='section252 deviation2 b10b2694e',parent_input_sha256=PARENT_SEAL,
        parent_items_sha256=sha(parent/'items.json'),subset='first600 original interleaved records; exact serialized record bytes',
        screen_contract='complete600 answers; first84 source-order nonempty-different pairs; <40 SCREEN_RESULTS_ONLY; unchanged parser')
    dump(pub/'MANIFEST.json',manifest)
    dump(pub/'INPUT_SEAL.json',dict(experiment='E140',stage='screen',status='COMPLETE',labels_on_pod=False,
        files={f:sha(pub/f)for f in ('MANIFEST.json','items.json')}))
    with tarfile.open(out/'PUBLIC_INPUTS.tar.gz','w:gz')as t:
        for p in sorted(pub.iterdir()):t.add(p,arcname=p.name)
    receipt=dict(**manifest,public_root=str(pub),input_sha256=sha(pub/'INPUT_SEAL.json'),archive=str(out/'PUBLIC_INPUTS.tar.gz'),archive_sha256=sha(out/'PUBLIC_INPUTS.tar.gz'),models_opened=False,CPU_labels_opened=False)
    dump(out/'SUBSET_RECEIPT.json',receipt);return receipt
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--parent',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.parent,a.out),sort_keys=True))
