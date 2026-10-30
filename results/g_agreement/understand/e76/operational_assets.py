"""Byte-identical operational loader functions; registered asset path resolved in own archive."""
import json,os
from pathlib import Path
from types import SimpleNamespace
from common76 import HERE,sha
P=SimpleNamespace(ROOT=HERE/'registry_root',sha=sha)

def _assets(path,names=("model","olens","nla","jlens")):
    a=json.loads(Path(path).read_text())
    pinned=json.loads((P.ROOT/"projects/g_agreement/manifest/assets.json").read_text())
    expected_revisions={"model":pinned["target"]["revision"],
        **{name:pinned["readers"][name]["revision"] for name in ("olens","nla","jlens")}}
    for name in names:
        if not Path(a[name]).exists(): raise ValueError("missing local "+name)
        if a.get("revisions",{}).get(name)!=expected_revisions[name]:
            raise ValueError("asset revision differs from registration: "+name)
    if not a.get("files"): raise ValueError("asset file hashes required")
    actual={}
    for item in a["files"]:
        digest=P.sha(item["path"])
        if digest!=item["sha256"]: raise ValueError("asset hash mismatch")
        actual[str(Path(item["path"]).resolve())]=digest
    covered={str(Path(f["path"]).resolve()) for f in a["files"]};required=set()
    for name in names:
        path=Path(a[name])
        if path.is_dir(): required.update(str(p.resolve()) for p in path.rglob("*") if p.is_file())
        else: required.add(str(path.resolve()))
    if not required<=covered: raise ValueError("asset hash manifest lacks file coverage")
    known={}
    if "model" in names:known[Path(a["model"])/"tokenizer.json"]=pinned["target"]["files_needed"]["tokenizer.json_sha256"]
    if "olens" in names:known[Path(a["olens"])/"adapter_model.safetensors"]=pinned["readers"]["olens"]["adapter_model_sha256"]
    if "nla" in names:known[Path(a["nla"])/pinned["readers"]["nla"]["adapter"]/"adapter_model.safetensors"]=pinned["readers"]["nla"]["adapter_model_sha256"]
    if "jlens" in names:known[Path(a["jlens"])]=pinned["readers"]["jlens"]["file_sha256"]
    for path,expected in known.items():
        if actual.get(str(path.resolve()))!=expected:
            raise ValueError("asset differs from registered SHA256: "+path.name)
    return a

def _offline():
    os.environ["HF_HUB_OFFLINE"]="1";os.environ["TRANSFORMERS_OFFLINE"]="1"

def _load_oracle(assets):
    _offline()
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from mats.readers.olens import load_olens
    model=AutoModelForCausalLM.from_pretrained(assets["model"],dtype=torch.bfloat16,device_map="cuda",local_files_only=True).eval()
    tok=AutoTokenizer.from_pretrained(assets["model"],local_files_only=True)
    return load_olens(model,tok,lora_dir=assets["olens"])
