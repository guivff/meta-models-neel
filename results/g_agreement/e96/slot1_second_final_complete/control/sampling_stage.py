from pathlib import Path
import os,json,hashlib
from huggingface_hub import snapshot_download,HfApi,hf_hub_download
root=Path('/workspace/e96-sampling'); dst=root/'nla-root';dst.mkdir(exist_ok=True)
src=Path('/weights/hf_cache/hub/models--ceselder--qwen3.6-27b-nla-rl/snapshots/5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f')
for name in ('av_base','av_rl_adapters','nla_meta.yaml'):
 (dst/name).symlink_to(src/name)
print('NLA_AR_DOWNLOAD_START',flush=True)
snapshot_download('ceselder/qwen3.6-27b-nla-rl',revision='5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f',allow_patterns=['ar_reconstructor/*'],local_dir='/workspace/e96-sampling/downloads',token=False,max_workers=4)
(dst/'ar_reconstructor').symlink_to(root/'downloads/ar_reconstructor')
print('NLA_AR_DOWNLOAD_DONE',flush=True)
print("STAGING_DONE",flush=True)
