import requests,json,hashlib,concurrent.futures,time,os
from pathlib import Path
base='https://huggingface.co/Qwen/Qwen3-4B/resolve/1cfa9a7208912126459214e8b04321603b3df60c/'
out=Path('cache/g_agreement/understand/e98/jlens/assets');refs={}
for file,key,name in [('model-00001-of-00003.safetensors','model.embed_tokens.weight','unembedding.bf16'),('model-00003-of-00003.safetensors','model.norm.weight','norm.bf16')]:
 h=json.loads((out/(file+'.header.json')).read_text());spec=h['header'][key];offset=8+h['header_length'];start,end=spec['data_offsets'];length=end-start;dest=out/name
 if not dest.exists() or dest.stat().st_size!=length:
  parts=list(range(0,length,32*1024*1024));folder=out/(name+'.parts');folder.mkdir(exist_ok=True)
  def get(pos):
   n=min(32*1024*1024,length-pos);a=offset+start+pos;b=a+n-1;p=folder/str(pos)
   if p.exists() and p.stat().st_size==n:return
   r=requests.get(base+file+f'?e98_offset={a}',headers={'Range':f'bytes={a}-{b}'},timeout=180);r.raise_for_status()
   assert r.status_code==206 and r.headers.get('Content-Range','').startswith(f'bytes {a}-{b}/'),r.headers
   assert len(r.content)==n;(p.with_suffix('.tmp')).write_bytes(r.content);p.with_suffix('.tmp').replace(p)
  with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(get,parts))
  with dest.open('wb') as f:
   for pos in parts:
    with (folder/str(pos)).open('rb') as src:
     while data:=src.read(8*1024*1024):f.write(data)
 refs[name]=dict(path=str(dest.resolve()),sha256=hashlib.file_digest(dest.open('rb'),'sha256').hexdigest(),shape=spec['shape'],dtype=spec['dtype'],source_repo='Qwen/Qwen3-4B',revision='1cfa9a7208912126459214e8b04321603b3df60c',file=file,tensor=key,byte_range=[offset+start,offset+end-1],header_sha256=hashlib.sha256((out/(file+'.header.json')).read_bytes()).hexdigest())
 print(name,'verified bytes',length,flush=True)
(out/'WEIGHT_RANGES.json').write_text(json.dumps(refs,indent=2)+'\n')
