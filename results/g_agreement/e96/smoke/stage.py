from pathlib import Path
import os,json,hashlib
from huggingface_hub import snapshot_download,HfApi,hf_hub_download
root=Path('/workspace/e96'); dst=root/'nla-root';dst.mkdir(exist_ok=True)
src=Path('/weights/hf_cache/hub/models--ceselder--qwen3.6-27b-nla-rl/snapshots/5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f')
for name in ('av_base','av_rl_adapters','nla_meta.yaml'):
 (dst/name).symlink_to(src/name)
print('NLA_AR_DOWNLOAD_START',flush=True)
snapshot_download('ceselder/qwen3.6-27b-nla-rl',revision='5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f',allow_patterns=['ar_reconstructor/*'],local_dir='/workspace/e96/downloads',token=False,max_workers=4)
(dst/'ar_reconstructor').symlink_to(root/'downloads/ar_reconstructor')
print('NLA_AR_DOWNLOAD_DONE',flush=True)
api=HfApi(token=False)
files=api.list_repo_tree('agu18dec/local-workspace',repo_type='dataset',recursive=True)
for f in files:
 if getattr(f,'lfs',None) and f.lfs.sha256=='178ceb36251e5e7ed2eb51aa54ccc4eac45dc928116b7498b46d22657a31c62a':
  print('PINNED_WHITENER',f.path,flush=True)
  p=hf_hub_download('agu18dec/local-workspace',filename=f.path,repo_type='dataset',token=False,cache_dir='/workspace/e96/hf-cache')
  (root/'whitener.pt').symlink_to(p)
  break
else:raise RuntimeError('Pinned whitener not found')
print('STAGING_DONE',flush=True)
