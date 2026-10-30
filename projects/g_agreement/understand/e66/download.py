"""Anonymous pinned downloads; never inspect or print data rows."""
import argparse,hashlib,json,urllib.request
from pathlib import Path
DATASET='ceselder/glm-5.3-olens-wild-rollouts'
REVISION='226c6dce62ed88d5981ca864d0c99d3f082ccee6'
TOKENIZER_REVISION='ba32f8c19c8738e2c57c71798c601d477a7bf844'
FILES={'olens_wild_rollouts.parquet':'6e42c4ed8bab563394e585f15287e57d61ac95f78845cdc98730ba74e27e33a1',
       'transcripts.parquet':'c44efbb4860219b05b2d7e6be592f454a32c51aa66aa984531bf0f2acf61137b'}


def get(url,path,expected=None):
    # Plain public HTTPS; no credential-bearing client or auth header.
    request=urllib.request.Request(url,headers={'User-Agent':'E66-anonymous-schema-first'})
    with urllib.request.urlopen(request,timeout=120) as response,path.open('xb') as output:
        while chunk:=response.read(1024*1024):output.write(chunk)
    if expected and hashlib.sha256(path.read_bytes()).hexdigest()!=expected:raise ValueError('download hash mismatch')


def download(out):
    out.mkdir(parents=True,exist_ok=False);(out/'tokenizer').mkdir()
    for name,expected in FILES.items():get(f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{name}',out/name,expected)
    get(f'https://huggingface.co/api/datasets/{DATASET}/tree/{REVISION}',out/'FILES.json')
    get(f'https://huggingface.co/datasets/{DATASET}/raw/{REVISION}/README.md',out/'README.downloaded.md')
    for name in ('tokenizer.json','tokenizer_config.json'):
        get(f'https://huggingface.co/zai-org/GLM-5.3/resolve/{TOKENIZER_REVISION}/{name}',out/'tokenizer'/name)
    (out/'REVISION.json').write_text(json.dumps({'revision':REVISION,'anonymous':True})+'\n')
    (out/'TOKENIZER_META.json').write_text(json.dumps({'repository':'zai-org/GLM-5.3','revision':TOKENIZER_REVISION})+'\n')
    print('Anonymous files downloaded and verified. No rows inspected.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    root=Path(__file__).resolve().parents[4]
    if not a.out.resolve().is_relative_to(root/'cache'):raise ValueError('download destination must be cache')
    download(a.out)
