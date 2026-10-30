"""Label-free registered W1/W1b native scoring and W5 layer sweep.

Asked scores are sealed before labels. Unasked readouts have a separate completion
seal, preserving asked evidence if generation reaches the compute deadline.
Production batches are frozen at 32. Unasked sample seeds are the registered
sample seed plus the zero-based batch-start item index.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import time
from . import protocol as P

W5_LAYERS = (20, 28, 36, 44, 52, 60)
NATIVE_READERS = (("olens",44),("jlens",44),("logit",44),("nla",42))
UNASKED_POLICY = P.DECODING
DEFAULT_BATCH = 32


def _pairs(spec, reader):
    pairs=spec.get(reader)
    if not isinstance(pairs,list) or len(pairs)<2:
        raise ValueError("at least two frozen phrasing pairs required")
    if any(not isinstance(p,(tuple,list)) or len(p)!=2 or any(not isinstance(c,str) or not c.strip() for c in p) for p in pairs):
        raise ValueError("invalid frozen phrasing pair")
    return pairs


def _inputs(bank):
    bank=Path(bank); receipt=P.verify(bank,"INPUT_SEAL.json")
    if not {"items.input.jsonl","templates.json","provenance.json"}<=set(receipt["files"]):
        raise ValueError("input seal lacks required files")
    items=P.rows(bank/"items.input.jsonl");templates=json.loads((bank/"templates.json").read_text())
    ids=[it["id"] for it in items]
    if not items or len(ids)!=len(set(ids)): raise ValueError("empty bank or duplicate item IDs")
    if set(templates)!={it["feature"] for it in items}: raise ValueError("template/item feature coverage mismatch")
    index={key:i for i,key in enumerate(ids)};donors=[]
    for it in items:
        if set(it)!={"id","feature","ids","donor_id"}: raise ValueError("worker input schema forbids labels or metadata")
        if not it["ids"] or any(type(t) is not int or t<0 for t in it["ids"]): raise ValueError("invalid token IDs")
        spec=templates[it["feature"]];ordinal=spec.get("kind")=="ordinal" or spec.get("ordinal") is True
        if it["donor_id"] is None:
            if not ordinal: raise ValueError("binary item lacks opposite-value donor")
            donors.append(None)
        else:
            if ordinal or it["donor_id"] not in index: raise ValueError("invalid ordinal/binary donor")
            donors.append(index[it["donor_id"]])
        for reader in ("olens","nla","jlens","logit"): _pairs(spec,reader)
    for i,j in enumerate(donors):
        if j is not None and (j==i or donors[j]!=i or items[i]["feature"]!=items[j]["feature"] or len(items[i]["ids"])!=len(items[j]["ids"])):
            raise ValueError("invalid donor pairing")
    return items,donors,templates


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


def _remaining(assignment):
    if time.time()>=float(assignment["deadline_epoch"])-180:
        raise TimeoutError("integrator allocation retrieval reserve reached")


def _offline():
    os.environ["HF_HUB_OFFLINE"]="1";os.environ["TRANSFORMERS_OFFLINE"]="1"


def _score_rows(items,indices,values,reader,layer,arm,kind):
    import torch
    if values is None:
        if reader not in {"jlens","logit"} or kind not in {"max_token_cosine_contrast","max_token_logodds"}:
            raise ValueError("missing scores allowed only for unavailable native token baselines")
        return [{"id":items[i]["id"],"reader":reader,"layer":layer,"arm":arm,"scores":None,
                 "score_kind":kind,"status":"NOT_EVALUABLE_NO_TOKEN_VARIANT"} for i in indices]
    if values.ndim!=2 or values.shape[0]<2 or values.shape[1]!=len(indices) or not torch.isfinite(values).all():
        raise ValueError("invalid asked score shape/value")
    return [{"id":items[i]["id"],"reader":reader,"layer":layer,"arm":arm,"scores":values[:,k].tolist(),
             "score_kind":kind,"status":"COMPLETE"} for k,i in enumerate(indices)]


def _arms(indices,donors):
    yield "true",indices
    if all(donors[i] is not None for i in indices): yield "mismatched",[donors[i] for i in indices]
    elif any(donors[i] is not None for i in indices): raise ValueError("mixed binary/ordinal feature")


def native_baseline_contrasts(reader,h,layer,pairs):
    """Use the pinned native max-over-single-token-variants contrast per pair.

    J's native paired_logodds is a cosine-score analogue, not a log probability.
    Logit lens uses the same frozen token variants and its actual logit scores.
    Missing variants make the whole baseline cell unavailable; no fallback
    tokenization or choice of a surviving phrasing occurs after capture.
    """
    import torch
    return torch.stack([reader.paired_logodds(h,layer,[a],[b]) for a,b in pairs])


class LogitLens:
    """Final norm/unembedding with no J transform and no adapter."""
    def __init__(self,jl):
        if jl.final_norm is None: raise ValueError("logit lens requires target final norm")
        self.W_U,self.norm,self.tok,self.device=jl.W_U,jl.final_norm,jl.tok,jl.device
    def scores(self,acts,layer=44,ids=None):
        import torch
        with torch.no_grad():
            p=next(self.norm.parameters());z=self.norm(acts.to(self.device,p.dtype)).float()
            w=self.W_U if ids is None else self.W_U[torch.as_tensor(ids,device=self.device)]
            return (z@w.T).cpu()
    def readout(self,acts,layer=44,k=10):
        import torch
        values,ids=torch.topk(self.scores(acts,layer),k,dim=1)
        return [[(self.tok.decode([int(i)]),float(v)) for v,i in zip(vs,ix)] for vs,ix in zip(values,ids)]
    def paired_logodds(self,acts,layer=44,cand_a=(),cand_b=()):
        from mats.readers.jlens import token_variants
        ia,ib=token_variants(self.tok,cand_a),token_variants(self.tok,cand_b)
        if not ia or not ib:raise ValueError("a candidate has no single-token variant")
        scores=self.scores(acts,layer,ids=ia+ib)
        return scores[:,:len(ia)].max(1).values-scores[:,len(ia):].max(1).values


def capture_and_score(items,donors,templates,ol,jl,batch=8,logit=None,checkpoint=None,on_capture=None,on_scores=None):
    """CPU-mockable native scoring; the base adapter is off during capture only."""
    from mats.capture import capture
    check=checkpoint or (lambda:None);check()
    with ol.base():
        acts=capture(ol.model,[it["ids"] for it in items],[42,44],[[-1]]*len(items),batch_size=batch,pad_id=ol.tok.pad_token_id or 0)
    by_layer={L:h[:,0] for L,h in acts.items()};scores=[]
    if on_capture is not None:on_capture(by_layer)
    def record(rows):
        scores.extend(rows)
        if on_scores is not None:on_scores(rows)
    for feature,spec in sorted(templates.items()):
        indices=[i for i,it in enumerate(items) if it["feature"]==feature]
        for arm,idx in _arms(indices,donors):
            check();h=by_layer[44][idx]
            v=ol.paired_logodds_templates(h,44,_pairs(spec,"olens"))
            record(_score_rows(items,indices,v,"olens",44,arm,"summed_sequence_logodds"))
            for name,reader,kind in (("jlens",jl,"max_token_cosine_contrast"),("logit",logit,"max_token_logodds")):
                if reader is not None:
                    check()
                    try:v=native_baseline_contrasts(reader,h,44,_pairs(spec,name))
                    except ValueError as exc:
                        if "single-token variant" not in str(exc):raise
                        v=None
                    record(_score_rows(items,indices,v,name,44,arm,kind))
    return by_layer,scores


def capture_sweep(items,donors,templates,ol,batch=8,checkpoint=None,on_capture=None,on_scores=None):
    from mats.capture import capture
    check=checkpoint or (lambda:None);check()
    with ol.base():
        acts=capture(ol.model,[it["ids"] for it in items],list(W5_LAYERS),[[-1]]*len(items),batch_size=batch,pad_id=ol.tok.pad_token_id or 0)
    by_layer={L:h[:,0] for L,h in acts.items()};scores=[]
    if on_capture is not None:on_capture(by_layer)
    for feature,spec in sorted(templates.items()):
        indices=[i for i,it in enumerate(items) if it["feature"]==feature]
        for L in W5_LAYERS:
            for arm,idx in _arms(indices,donors):
                check();v=ol.paired_logodds_templates(by_layer[L][idx],L,_pairs(spec,"olens"))
                rows=_score_rows(items,indices,v,"olens",L,arm,"summed_sequence_logodds")
                scores.extend(rows)
                if on_scores is not None:on_scores(rows)
    return by_layer,scores


def _load_oracle(assets):
    _offline()
    import torch
    from transformers import AutoModelForCausalLM,AutoTokenizer
    from mats.readers.olens import load_olens
    model=AutoModelForCausalLM.from_pretrained(assets["model"],dtype=torch.bfloat16,device_map="cuda",local_files_only=True).eval()
    tok=AutoTokenizer.from_pretrained(assets["model"],local_files_only=True)
    return load_olens(model,tok,lora_dir=assets["olens"])


def _labels_absent(bank):
    if list(Path(bank).rglob("*.DO_NOT_STAGE.jsonl")): raise ValueError("label-bearing files must not be staged to a GPU worker")


def _save_capture(a,items,by_layer):
    import numpy as np
    import torch
    for L,h in by_layer.items():
        if h.ndim!=2 or len(h)!=len(items) or not torch.isfinite(h).all():
            raise ValueError("invalid capture shape/value")
        np.save(a.out/f"acts{L}.npy",h.numpy(),allow_pickle=False)
    P.dump(a.out/"items.order.json",[it["id"] for it in items])
    P.dump(a.out/"provenance.capture.json",{"input_seal_sha256":P.sha(a.bank/"INPUT_SEAL.json"),
        "assignment_sha256":P.sha(a.assignment),"source_files":P.code_hashes()})
    names=[f"acts{L}.npy" for L in by_layer]+["items.order.json","provenance.capture.json"]
    P.dump(a.out/"CAPTURE_SEAL.json",{"status":"CAPTURE_COMPLETE_SCORES_PENDING",
        "files":{n:P.sha(a.out/n) for n in names}})


def _append_partial(a,phase,rows):
    # This explicitly partial file never receives SCORE_SEAL coverage. The final
    # complete grid is separate, so interrupts cannot masquerade as full scores.
    with (a.out/f"scores.{phase}.partial.jsonl").open("a") as f:
        for row in rows:f.write(json.dumps(row,sort_keys=True,allow_nan=False)+"\n")
        f.flush();os.fsync(f.fileno())


def _store_asked(a,assignment,items,by_layer,scores,phase,extra=None):
    import numpy as np
    for L,h in by_layer.items(): np.save(a.out/f"acts{L}.npy",h.numpy(),allow_pickle=False)
    P.dump(a.out/"items.order.json",[it["id"] for it in items])
    P.jsonl(a.out/f"scores.{phase}.jsonl",scores)
    P.dump(a.out/f"provenance.{phase}.json",{"input_seal_sha256":P.sha(a.bank/"INPUT_SEAL.json"),
        "assignment_sha256":P.sha(a.assignment),"assets_sha256":P.sha(a.assets),"source_files":P.code_hashes(),
        "experiment":assignment["experiment"],"batch":a.batch,
        "hook":"zero-based decoder block output, raw last-prefix-token state",**(extra or {})})
    P.seal(a.out,[f"scores.{phase}.jsonl","items.order.json",f"provenance.{phase}.json"]+[f"acts{L}.npy" for L in by_layer],f"SCORES_SEALED_{phase.upper()}_BEFORE_LABEL_JOIN")


def _decoding(bank):
    receipt=P.verify(bank,"INPUT_SEAL.json")
    if "decoding.json" not in receipt["files"]: raise ValueError("unasked decoding policy is not frozen")
    policy=json.loads((Path(bank)/"decoding.json").read_text())
    if policy!=UNASKED_POLICY: raise ValueError("frozen decoding policy differs from runner")
    return policy


def _runtime(bank,batch):
    receipt=P.verify(bank,"INPUT_SEAL.json")
    if "runtime.json" not in receipt["files"]:
        raise ValueError("runtime batch policy is not frozen")
    policy=json.loads((Path(bank)/"runtime.json").read_text())
    if (policy!=P.RUNTIME or policy.get("batch")!=DEFAULT_BATCH
            or policy.get("oracle_pair_native_batch")!=32):
        raise ValueError("frozen runtime policy differs from runner")
    if type(batch) is not int or batch!=policy["batch"]:
        raise ValueError("runtime --batch differs from frozen bank batch")
    return policy


def collect_unasked(items,h,reader,layer,name,policy,batch=8,checkpoint=None):
    """Yield incrementally; retain raw NLA text when explanation extraction fails."""
    import torch
    from mats.readers.nla import Sampling,extract_explanation
    check=checkpoint or (lambda:None)
    for start in range(0,len(items),batch):
        check();chunk=items[start:start+batch];vectors=h[start:start+batch]
        if name in {"jlens","logit"}:
            native=reader.readout(vectors,layer,k=policy["baseline_top_k"])
            for it,tokens in zip(chunk,native):
                for sample in range(2):
                    yield {"id":it["id"],"reader":name,"layer":layer,"sample":sample,"text":" ".join(t for t,_ in tokens),
                        "tokens":tokens,"readout_kind":policy["baseline_repeats"],"status":"COMPLETE"}
            continue
        for sample,kw in enumerate(policy["samples"]):
            check();seed=policy["seeds"][sample]+start;torch.manual_seed(seed)
            if name=="olens": raw=reader.verbalize(vectors,layer,k=1,sampling=Sampling(**kw),batch=batch)
            else: raw=reader.verbalize_raw(vectors,k=1,sampling=Sampling(**kw),batch=batch)
            if len(raw)!=len(chunk) or any(len(row)!=1 for row in raw): raise ValueError("unasked readout coverage mismatch")
            for it,row in zip(chunk,raw):
                text=row[0] if name=="olens" else extract_explanation(row[0])
                yield {"id":it["id"],"reader":name,"layer":layer,"sample":sample,"raw":row[0],"text":text,
                    "seed":seed,"sampling":kw,"status":"COMPLETE" if text is not None else "EXTRACTION_FAILED"}


def _unasked_file(a,items,readers,phase,checkpoint):
    policy=_decoding(a.bank);name=f"unasked.{phase}.jsonl"
    with (a.out/name).open("x") as f:
        for reader_name,layer,obj,h in readers:
            for record in collect_unasked(items,h,obj,layer,reader_name,policy,a.batch,checkpoint):
                f.write(json.dumps(record,sort_keys=True,allow_nan=False)+"\n");f.flush()
        os.fsync(f.fileno())
    provenance=f"provenance.unasked.{phase}.json"
    P.dump(a.out/provenance,{"input_seal_sha256":P.sha(a.bank/"INPUT_SEAL.json"),
        "asked_score_seal_sha256":P.sha(a.out/"SCORE_SEAL.json"),"batch":a.batch,"decoding":policy,
        "judge_status":"PENDING_BLINDED_JUDGE","expected_per_item_per_reader":2})
    P.dump(a.out/"FREE_SEAL.json",{"status":"UNASKED_COMPLETE_BEFORE_LABEL_JOIN","files":{n:P.sha(a.out/n) for n in (name,provenance)}})


def target_phase(a):
    experiment=getattr(a,"experiment","W1")
    assignment=P.admit(a.assignment,experiment=experiment,bank=getattr(a,"bank",None))
    _labels_absent(a.bank);items,donors,templates=_inputs(a.bank);_decoding(a.bank);_runtime(a.bank,a.batch)
    a.out.mkdir(parents=True,exist_ok=False)
    with P.logged("target",gpu=True,extra={"pod_id":assignment["pod_id"],"experiment":experiment}),P.compute_window(assignment):
        assets=_assets(a.assets,names=("model","olens","jlens"));ol=_load_oracle(assets)
        from mats.readers.jlens import load_jlens
        jl=load_jlens(ol.model,ol.tok,layers=[44],path=assets["jlens"]);logit=LogitLens(jl)
        check=lambda:_remaining(assignment)
        by_layer,scores=capture_and_score(items,donors,templates,ol,jl,a.batch,logit,check,
            on_capture=lambda h:_save_capture(a,items,h),on_scores=lambda rows:_append_partial(a,"target",rows))
        _store_asked(a,assignment,items,by_layer,scores,"target")
        if not getattr(a,"asked_only",False):
            _unasked_file(a,items,[("olens",44,ol,by_layer[44]),("jlens",44,jl,by_layer[44]),("logit",44,logit,by_layer[44])],"target",check)


def nla_phase(a):
    experiment=getattr(a,"experiment","W1")
    assignment=P.admit(a.assignment,experiment=experiment,bank=a.bank)
    _labels_absent(a.bank);items,donors,templates=_inputs(a.bank);_decoding(a.bank);_runtime(a.bank,a.batch)
    receipt=P.verify(a.target,"SCORE_SEAL.json")
    if not {"provenance.target.json","acts42.npy","items.order.json","scores.target.jsonl"}<=set(receipt["files"]): raise ValueError("target seal missing required score/capture files")
    if json.loads((a.target/"provenance.target.json").read_text())["input_seal_sha256"]!=P.sha(a.bank/"INPUT_SEAL.json"): raise ValueError("target/bank seal mismatch")
    if json.loads((a.target/"items.order.json").read_text())!=[it["id"] for it in items]: raise ValueError("target item order mismatch")
    a.out.mkdir(parents=True,exist_ok=False)
    with P.logged("nla",gpu=True,extra={"pod_id":assignment["pod_id"],"experiment":experiment}),P.compute_window(assignment):
        assets=_assets(a.assets,names=("nla",));_offline()
        import numpy as np
        import torch
        from mats.readers.nla import load_nla,paired_logodds_templates
        nla=load_nla(root=assets["nla"],load_ar=False,enable_thinking=False)
        h=torch.from_numpy(np.load(a.target/"acts42.npy",allow_pickle=False))
        if h.ndim!=2 or len(h)!=len(items) or not torch.isfinite(h).all(): raise ValueError("invalid NLA capture shape/value")
        scores=[]
        for feature,spec in sorted(templates.items()):
            indices=[i for i,it in enumerate(items) if it["feature"]==feature]
            for arm,idx in _arms(indices,donors):
                _remaining(assignment);v=paired_logodds_templates(nla,h[idx],_pairs(spec,"nla"),batch=a.batch)
                rows=_score_rows(items,indices,v,"nla",42,arm,"summed_sequence_logodds")
                scores.extend(rows);_append_partial(a,"nla",rows)
        _store_asked(a,assignment,items,{},scores,"nla",{"target_score_seal_sha256":P.sha(a.target/"SCORE_SEAL.json")})
        if not getattr(a,"asked_only",False):
            _unasked_file(a,items,[("nla",42,nla,h)],"nla",lambda:_remaining(assignment))


def free_phase(a,phase):
    """Add frozen unasked readouts to an existing, verified asked-score directory.

    Intended order: target --asked-only; nla; free-target. This prioritizes all
    four readers' asked scores before the expensive second generative phase.
    Existing partial unasked output is never overwritten or silently resumed.
    """
    experiment=getattr(a,"experiment","W1")
    assignment=P.admit(a.assignment,experiment=experiment,bank=a.bank)
    _labels_absent(a.bank);items,_,_=_inputs(a.bank);_decoding(a.bank);_runtime(a.bank,a.batch)
    receipt=P.verify(a.out,"SCORE_SEAL.json")
    needed={f"scores.{phase}.jsonl",f"provenance.{phase}.json","items.order.json"}
    if phase=="target":needed|={"acts42.npy","acts44.npy"}
    if not needed<=set(receipt["files"]):raise ValueError("free phase requires the complete asked-score seal")
    provenance=json.loads((a.out/f"provenance.{phase}.json").read_text())
    if (provenance["input_seal_sha256"]!=P.sha(a.bank/"INPUT_SEAL.json")
            or provenance["assets_sha256"]!=P.sha(a.assets)
            or provenance["source_files"]!=P.code_hashes()
            or provenance["experiment"]!=experiment
            or provenance["batch"]!=a.batch):
        raise ValueError("free phase provenance differs from frozen asked run")
    if json.loads((a.out/"items.order.json").read_text())!=[it["id"] for it in items]:
        raise ValueError("free phase item order mismatch")
    if (a.out/"FREE_SEAL.json").exists() or (a.out/f"unasked.{phase}.jsonl").exists():
        raise ValueError("unasked output exists; preserve it, do not overwrite or silently resume")
    capture_dir=a.out if phase=="target" else a.target
    if phase=="nla":
        target_seal=P.verify(a.target,"SCORE_SEAL.json")
        if not {"acts42.npy","items.order.json","provenance.target.json"}<=set(target_seal["files"]):
            raise ValueError("free NLA requires sealed target captures")
        if provenance["target_score_seal_sha256"]!=P.sha(a.target/"SCORE_SEAL.json"):
            raise ValueError("free NLA target seal mismatch")
        if json.loads((a.target/"items.order.json").read_text())!=[it["id"] for it in items]:
            raise ValueError("free NLA capture order mismatch")
    with P.logged("free-"+phase,gpu=True,extra={"pod_id":assignment["pod_id"],"experiment":experiment}),P.compute_window(assignment):
        names=("model","olens","jlens") if phase=="target" else ("nla",)
        assets=_assets(a.assets,names=names);_offline()
        import numpy as np
        import torch
        layer=44 if phase=="target" else 42
        h=torch.from_numpy(np.load(capture_dir/f"acts{layer}.npy",allow_pickle=False))
        if h.ndim!=2 or len(h)!=len(items) or not torch.isfinite(h).all():raise ValueError("invalid free-phase capture")
        if phase=="target":
            ol=_load_oracle(assets)
            from mats.readers.jlens import load_jlens
            jl=load_jlens(ol.model,ol.tok,layers=[44],path=assets["jlens"])
            readers=[("olens",44,ol,h),("jlens",44,jl,h),("logit",44,LogitLens(jl),h)]
        else:
            from mats.readers.nla import load_nla
            nla=load_nla(root=assets["nla"],load_ar=False,enable_thinking=False)
            readers=[("nla",42,nla,h)]
        _unasked_file(a,items,readers,phase,lambda:_remaining(assignment))


def sweep_phase(a):
    assignment=P.admit(a.assignment,experiment="W5",bank=a.bank)
    _labels_absent(a.bank);all_items,_,all_templates=_inputs(a.bank);_runtime(a.bank,a.batch)
    if "sweep.input.json" not in P.verify(a.bank,"INPUT_SEAL.json")["files"]: raise ValueError("W5 test subset not frozen")
    ids=json.loads((a.bank/"sweep.input.json").read_text());index={it["id"]:it for it in all_items}
    if not ids or len(ids)!=len(set(ids)) or not set(ids)<=set(index): raise ValueError("invalid frozen W5 subset")
    items=[index[i] for i in ids];local={key:i for i,key in enumerate(ids)}
    if any(it["donor_id"] not in local for it in items): raise ValueError("W5 subset must retain both sides of binary pairs")
    donors=[local[it["donor_id"]] for it in items];templates={f:all_templates[f] for f in sorted({it["feature"] for it in items})}
    a.out.mkdir(parents=True,exist_ok=False)
    with P.logged("sweep",gpu=True,extra={"pod_id":assignment["pod_id"],"experiment":"W5"}),P.compute_window(assignment):
        assets=_assets(a.assets,names=("model","olens"));ol=_load_oracle(assets)
        by_layer,scores=capture_sweep(items,donors,templates,ol,a.batch,lambda:_remaining(assignment),
            on_capture=lambda h:_save_capture(a,items,h),on_scores=lambda rows:_append_partial(a,"sweep",rows))
        _store_asked(a,assignment,items,by_layer,scores,"sweep",{"sweep_input_sha256":P.sha(a.bank/"sweep.input.json")})


def probe_scores(h, labels, groups, donors, k=5):
    """Train-only standardisation; donors belong to the same held-out cluster."""
    import numpy as np
    import torch
    from mats import probes
    y, groups, donors = np.asarray(labels), np.asarray(groups), np.asarray(donors)
    if len(np.unique(groups)) < k:
        raise ValueError("too few clusters for grouped CV")
    if not np.array_equal(groups, groups[donors]):
        raise ValueError("probe donors cross cluster boundaries")
    s, mis = np.empty(len(y)), np.empty(len(y))
    for te in probes.group_folds(groups, k=k, seed=P.SEED):
        tr = np.setdiff1d(np.arange(len(y)), te)
        if len(np.unique(y[tr])) != 2:
            raise ValueError("single-class training fold")
        model = probes.fit_logreg(h[tr], torch.as_tensor(y[tr]), lam=1e-3)
        s[te] = model.decision(h[te]).cpu().numpy()
        mis[te] = model.decision(h[donors[te]]).cpu().numpy()
    # Required upstream summary is independently checked against these OOF predictions.
    summary = probes.cv_auroc(h, y, groups, k=k, lam=1e-3, seed=P.SEED)
    from mats.metrics import auroc_labels
    if not np.isclose(summary["auroc"], auroc_labels(s, y), atol=1e-6):
        raise ValueError("upstream CV summary mismatch")
    return s, mis



def analyse(a):
    P.verify(a.target,"SCORE_SEAL.json")
    P.verify(a.nla,"SCORE_SEAL.json")
    from .analysis import analyse as registered_analyse
    return registered_analyse(a)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="phase",required=True)
    sub.add_parser("plan")
    for phase in ("target","nla","sweep","free-target","free-nla"):
        s=sub.add_parser(phase)
        for name in ("assignment","bank","assets","out"): s.add_argument("--"+name,type=Path,required=True)
        s.add_argument("--batch",type=int,default=DEFAULT_BATCH)
        if phase!="sweep": s.add_argument("--experiment",choices=("W1","W1b"),default="W1")
        if phase in ("target","nla"):s.add_argument("--asked-only",action="store_true")
        if phase in ("nla","free-nla"): s.add_argument("--target",type=Path,required=True)
    for phase in ("analyse","analyse-sweep"):
        s=sub.add_parser(phase)
        for name in (("bank","target","nla","labels","out") if phase=="analyse" else ("bank","sweep","labels","out","w1")):
            s.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args(argv)
    if getattr(a,"batch",1)<1: p.error("--batch must be positive")
    if a.phase=="plan":
        print(json.dumps({"status":"BLOCKED_UNTIL_COMMITTED_MANIFEST_AND_INTEGRATOR_POD","registration":P.BRIEF,
            "source_files":P.code_hashes(),"native_readers":NATIVE_READERS,"W5_layers":W5_LAYERS,
            "caps_gpu_hours":{"W1":2.0,"W5":0.5,"W1b":1.0},"runtime":P.RUNTIME,"unasked":UNASKED_POLICY},indent=2))
    elif a.phase=="target":target_phase(a)
    elif a.phase=="nla":nla_phase(a)
    elif a.phase=="sweep":sweep_phase(a)
    elif a.phase in ("free-target","free-nla"):free_phase(a,a.phase.removeprefix("free-"))
    elif a.phase=="analyse-sweep":
        from .analysis import analyse_sweep
        analyse_sweep(a)
    else:analyse(a)


if __name__=="__main__":main()
