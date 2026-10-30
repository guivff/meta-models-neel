"""Build §49 attempt-2 operational chain and fetch pinned public assets on the pod."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sys, time
from pathlib import Path
from projects.g_agreement.r_bench.section49_supervisor import read,save,sha

REG=Path(__file__).resolve().parents[1]/'registrations/section49'
CODE=REG.parents[3]

def pins():
    from projects.g_agreement.core import config as C
    # No source/science mutation; exact pins from the frozen configuration.
    return [(C.TARGET_MODEL_ID,C.TARGET_MODEL_SHA,['*.json','*.safetensors','*.model','*.txt','*.jinja']),
            (C.OLENS_REPO,C.OLENS_SHA,[C.OLENS_SUBFOLDER+'/*']),
            (C.NLA_REPO,C.NLA_SHA,[C.NLA_BASE_SUBFOLDER+'/*',C.NLA_ADAPTER_SUBFOLDER+'/*',C.NLA_META_FILE]),
            (C.SKIPLENS_REPOS['a'],C.SKIPLENS_SHAS['a'],list(C.SKIPLENS_FILES)),
            (C.JLENS_REPO,C.JLENS_SHA,[C.JLENS_FILE]),(C.RLENS_REPO,C.RLENS_SHA,[C.RLENS_FILE]),
            ('koayon/jpp-lenses','237dab6ea0e611d964bf407f13ba1655f1a6ae43',['qwen3.6-27b/lens.pt'])]

def fetch(root):
    import fnmatch
    from huggingface_hub import HfApi,snapshot_download
    inventory=[]
    for repo,rev,patterns in pins():
        print('FETCH',repo,rev,flush=True)
        info=HfApi(token=False).model_info(repo,revision=rev,files_metadata=True)
        if info.sha!=rev: raise ValueError('Revision mismatch '+repo)
        selected=[s for s in info.siblings if any(fnmatch.fnmatch(s.rfilename,p) for p in patterns)]
        if not selected: raise ValueError('Empty asset selection '+repo)
        local=Path(snapshot_download(repo,revision=rev,allow_patterns=patterns,max_workers=4,token=False))
        for s in selected:
            if s.lfs:
                h=s.lfs.sha256; kind='sha256'
            else: h=s.blob_id;kind='git-sha1'
            if not h: raise ValueError('Missing pinned Hub hash '+s.rfilename)
            inventory.append({'repo':repo,'revision':rev,'path':str(local/s.rfilename),'hash':h,'kind':kind})
    save(Path(root)/'output/assets_inventory.json',inventory)
    print('DOWNLOAD_COMPLETE',flush=True)

def verify(root):
    for a in read(Path(root)/'output/assets_inventory.json'):
        p=Path(a['path'])
        if a['kind']=='sha256': got=sha(p)
        else:
            h=hashlib.sha1();h.update(('blob '+str(p.stat().st_size)+'\0').encode())
            with p.open('rb') as f:
                for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
            got=h.hexdigest()
        if got!=a['hash']:raise ValueError('Pinned asset hash mismatch '+a['path'])
    # Also enforce the preregistered artifact SHA256 pins, independent of Hub metadata.
    from projects.g_agreement.core import config as C
    from projects.g_agreement.r_bench.section49 import JPP,BASIS_SHA
    required={(C.JLENS_REPO,C.JLENS_FILE):C.JLENS_FILE_SHA256,(C.RLENS_REPO,C.RLENS_FILE):C.RLENS_FILE_SHA256,(JPP[0],JPP[2]):JPP[3],
              (C.OLENS_REPO,C.OLENS_SUBFOLDER+'/adapter_model.safetensors'):C.OLENS_ADAPTER_SHA256,
              (C.NLA_REPO,C.NLA_ADAPTER_SUBFOLDER+'/adapter_model.safetensors'):C.NLA_ADAPTER_SHA256,
              (C.SKIPLENS_REPOS['a'],'adapter_model.safetensors'):C.SKIPLENS_ADAPTER_SHA256['a']}
    inv=read(Path(root)/'output/assets_inventory.json')
    for (repo,rel),h in required.items():
        matches=[a for a in inv if a['repo']==repo and a['path'].endswith('/'+rel)]
        if len(matches)!=1 or sha(matches[0]['path'])!=h:raise ValueError('Registered hash mismatch '+repo+'/'+rel)
    for rel,h in read(REG/'source_manifest_shards.json').items():
        if sha(CODE/rel)!=h:raise ValueError('Frozen source mismatch '+rel)
    if sha(Path(root)/'inputs/jspace_L38_r384.pt')!=BASIS_SHA:raise ValueError('Basis mismatch')
    save(Path(root)/'output/hash_check.json',{'status':'PASS','asset_files':len(inv),'source_files':len(read(REG/'source_manifest_shards.json')),'time':time.time()})

def stage(root):
    import torch
    root=Path(root);out=root/'output';b=read(root/'booking.json')
    if not torch.cuda.is_available() or torch.cuda.device_count()!=1:raise ValueError('Single GPU runtime unavailable')
    if len(read(REG/'plan.json')['records'])!=196:raise ValueError('Bank count')
    if not (out/'hash_check.json').exists():raise ValueError('Missing hash gate')
    (out/'inputs').mkdir(exist_ok=True);shutil.copy2(root/'inputs/jspace_L38_r384.pt',out/'inputs/jspace_L38_r384.pt')
    save(out/'booking.json',b)
    from projects.g_agreement.r_bench.section49 import Guard
    Guard(out)
    save(out/'staging_check.json',{'status':'PASS','torch':torch.__version__,'time':time.time()})

def build(root):
    root=Path(root).resolve();b=read(root/'booking.json');code=root/'code';py=str(root/'venv/bin/python')
    reserve=max(600, __import__('math').ceil(2*512*1024**2/b['verified_pull_bytes_per_second']))
    if b['cap_seconds']!=9000 or b['deadline']>b['created_epoch']+9000:raise ValueError('Invalid fresh booking')
    from projects.g_agreement.r_bench.section49 import shard_plan
    shard_plan(b['shard_id'])
    if b['shards_sha256']!=sha(REG/'shards.json'):raise ValueError('Shard assignment mismatch')
    cfg=dict(cap_seconds=9000,shard_id=b['shard_id'],root=str(root),cwd=str(code),pod_id=b['pod_id'],gpu_count=1,created_epoch=b['created_epoch'],deadline=b['deadline'],pull_reserve_s=reserve,stall_s=600,poll_s=2,custody_acknowledged=b['custody_acknowledged'],own_account_http200=b['own_account_http200'],
             env={'HF_HOME':str(root/'hf'),'PIP_CACHE_DIR':str(root/'pip-cache'),'HF_HUB_DISABLE_IMPLICIT_TOKEN':'1','HF_HUB_DISABLE_XET':'1','PYTHONUNBUFFERED':'1'})
    mod='projects.g_agreement.r_bench.section49_deploy'
    cfg['steps']=[{'name':'runtime-venv','argv':[sys.executable,'-m','venv',str(root/'venv')],'byte_roots':[str(root/'venv')]},
      {'name':'runtime-download','argv':[py,'-m','pip','install','-r',str(code/'requirements.txt')],'byte_roots':[str(root/'venv'),str(root/'pip-cache')]},
      {'name':'download','argv':[py,'-m',mod,'fetch','--root',str(root)],'byte_roots':[str(root/'hf')]},
      {'name':'hash-check','argv':[py,'-m',mod,'verify','--root',str(root)]},
      {'name':'staging','argv':[py,'-m',mod,'stage','--root',str(root)]}]
    for name in ['target-smoke','nla-smoke','projection','target-full','nla-full','analyze']:
        cfg['steps'].append({'name':name,'argv':[py,'-m','projects.g_agreement.r_bench.section49',name,'--run',str(root/'output')]})
    save(root/'supervisor.json',cfg)
    return cfg

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['build','fetch','verify','stage']);p.add_argument('--root',required=True);a=p.parse_args()
    {'build':build,'fetch':fetch,'verify':verify,'stage':stage}[a.action](a.root)
if __name__=='__main__':main()
