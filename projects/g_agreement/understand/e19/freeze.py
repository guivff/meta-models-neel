"""E19 dev-only Oracle layer selection and raw-coordinate steering freeze.

The fitting entry point accepts a separately sealed dev-only derivative and
never opens the source mixed label file. The derivative builder matches the
split field before JSON-decoding a record: test records are opaque bytes used
only to verify the upstream file hash. Residual files are hash-verified as bytes,
then memory-mapped; only the 84 dev item indices enter numerical reads/fits.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import time
import sys

import numpy as np

import common
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand import analysis as E3

ROWS = ("prose_paren", "python_string", "table_role", "python_depth", "prose_sentiment")
READER = "olens"
DEV_N = 84
TOTAL_N = 168
LAYERS = 64
SEED = E3.SEED
LAMBDA = 1e-3
FOLDS = 5
SIGMA_DDOF = 1
_DEV_PATTERN = re.compile(rb'"split"\s*:\s*"dev"(?:\s*[,}])')


def _read(path):
    return json.loads(Path(path).read_text())


def middle_third_layers(n_layers=LAYERS):
    """Zero-based [floor(L/3), floor(2L/3)); for 64 blocks, 21 through 41."""
    if type(n_layers) is not int or n_layers < 3:
        raise ValueError("at least three decoder blocks required")
    return list(range(n_layers//3, 2*n_layers//3))


def _input_metadata(directory):
    directory=Path(directory)
    seal=_read(directory/"INPUT_SEAL.json")
    required={"items.input.jsonl","templates.json","provenance.json"}
    if not required <= set(seal.get("files",{})):
        raise ValueError("E3 input seal lacks metadata")
    # Validate only metadata needed here; upstream target activation arrays are
    # not opened by E19 selection or fitting.
    for name in required:
        if P.sha(directory/name)!=seal["files"][name]:
            raise ValueError("E3 input metadata seal mismatch")
    provenance=_read(directory/"provenance.json")
    if provenance.get("experiment")!="E3":
        raise ValueError("E19 selection requires frozen E3 inputs")
    items=P.rows(directory/"items.input.jsonl")
    if len({it["id"] for it in items})!=len(items):
        raise ValueError("duplicate input item IDs")
    templates=_read(directory/"templates.json")
    selected={}
    for feature in ROWS:
        spec=templates[feature]
        if spec.get("score_orientation")!="value_A_positive" or len(spec["values"])!=2:
            raise ValueError("E19 requires W1's frozen binary A-positive orientation")
        records=[it for it in items if it["feature"]==feature]
        if len(records)!=TOTAL_N or Counter(it["split"] for it in records)!={"dev":DEV_N,"test":DEV_N}:
            raise ValueError("each E19 row must preserve 84 dev and 84 test items")
        selected[feature]=records
    return selected,templates,provenance


def stage_dev_labels(e3_inputs,source_labels,out):
    """Derive 420 dev labels without JSON-decoding any test-label record."""
    e3_inputs,source_labels,out=map(Path,(e3_inputs,source_labels,out))
    items,templates,provenance=_input_metadata(e3_inputs)
    if P.sha(source_labels)!=provenance["labels_sha256"]:
        raise ValueError("source-label bytes differ from the frozen E3 input lineage")
    dev_ids={it["id"] for records in items.values() for it in records if it["split"]=="dev"}
    found={}
    with source_labels.open("rb") as handle:
        for line in handle:
            if not _DEV_PATTERN.search(line):
                continue  # Do not JSON-decode or inspect fields of test records.
            record=json.loads(line)
            if record.get("split")!="dev":
                raise AssertionError("dev-only derivative isolation failed")
            if record.get("id") not in dev_ids:
                continue
            if record["id"] in found:
                raise ValueError("duplicate selected dev label")
            found[record["id"]]=record
    if set(found)!=dev_ids:
        raise ValueError("dev derivative does not cover the selected dev item IDs")
    ordered=[found[it["id"]] for feature in ROWS for it in items[feature] if it["split"]=="dev"]
    _validate_dev_labels(ordered,items,templates)
    out.mkdir(parents=True,exist_ok=False)
    P.jsonl(out/"labels.dev.jsonl",ordered)
    provenance={"schema":"e19-dev-label-derivative-v1","status":"DEV_ONLY",
                "e3_input_seal_sha256":P.sha(e3_inputs/"INPUT_SEAL.json"),
                "source_labels_sha256":P.sha(source_labels),"dev_labels_sha256":P.sha(out/"labels.dev.jsonl"),
                "rows":list(ROWS),"n":len(ordered),"ordered_ids":[r["id"] for r in ordered],
                "test_label_records_json_decoded":0,
                "source_access":"full file byte hash; split=dev match before JSON decoding; test values never parsed",
                "fit_entrypoint_access":"separate dev-only derivative only"}
    P.dump(out/"provenance.json",provenance)
    P.dump(out/"DEV_LABEL_SEAL.json",{"status":"E19_DEV_LABELS_ONLY",
        "files":{n:P.sha(out/n) for n in ("labels.dev.jsonl","provenance.json")}})
    return provenance


def _validate_dev_labels(labels,items,templates):
    ids=[r["id"] for r in labels]
    expected=[it["id"] for f in ROWS for it in items[f] if it["split"]=="dev"]
    if len(set(ids))!=len(ids) or set(ids)!=set(expected):
        raise ValueError("dev label identity coverage mismatch")
    for feature in ROWS:
        rows=[r for r in labels if r["feature"]==feature]
        if (len(rows)!=DEV_N or any(r["split"]!="dev" for r in rows)
                or len({r["cluster"] for r in rows})!=6
                or Counter(r["value"] for r in rows)!={v:42 for v in templates[feature]["values"]}):
            raise ValueError("each row requires exactly 84 dev labels, six clusters, 42 per value")
    return {r["id"]:r for r in labels}


def _load_dev_labels(directory,e3_inputs,items,templates,e3_provenance):
    directory,e3_inputs=Path(directory),Path(e3_inputs)
    seal=P.verify(directory,"DEV_LABEL_SEAL.json")
    if seal.get("status")!="E19_DEV_LABELS_ONLY" or set(seal["files"])!={"labels.dev.jsonl","provenance.json"}:
        raise ValueError("separate sealed dev-only labels required")
    provenance=_read(directory/"provenance.json")
    if (provenance.get("e3_input_seal_sha256")!=P.sha(e3_inputs/"INPUT_SEAL.json")
            or provenance.get("source_labels_sha256")!=e3_provenance["labels_sha256"]
            or provenance.get("dev_labels_sha256")!=P.sha(directory/"labels.dev.jsonl")
            or provenance.get("test_label_records_json_decoded")!=0):
        raise ValueError("dev-label derivative lineage mismatch")
    records=P.rows(directory/"labels.dev.jsonl")
    # Test rows are rejected before values/clusters can reach any fitter.
    if any(r.get("split")!="dev" for r in records):
        raise ValueError("test label found in the dev-only derivative")
    lookup=_validate_dev_labels(records,items,templates)
    if [r["id"] for r in records]!=provenance["ordered_ids"]:
        raise ValueError("dev-label order differs from derivative receipt")
    return lookup,provenance


def _capture_records(e3_inputs,e3_scores,items):
    e3_inputs,e3_scores=Path(e3_inputs),Path(e3_scores)
    outer=_read(e3_scores/"SCORE_SEAL.json")
    outer_prov=_read(e3_scores/"provenance.json")
    directory=e3_scores/READER
    phase=_read(directory/"SCORE_SEAL.json")
    if (outer.get("status")!="SCORES_SEALED_EXPLORATORY_E3"
            or phase.get("status")!="SCORES_SEALED_EXPLORATORY_E3"
            or outer_prov.get("input_seal_sha256")!=P.sha(e3_inputs/"INPUT_SEAL.json")
            or outer_prov.get("phases",{}).get(READER)!="SEALED"):
        raise ValueError("E19 requires input-bound E3 Oracle capture seals")
    for name in ("provenance.json",READER+"/SCORE_SEAL.json"):
        if outer.get("files",{}).get(name)!=P.sha(e3_scores/name):
            raise ValueError("E3 aggregate receipt mismatch")
    for name in ("index.json","provenance.json"):
        digest=P.sha(directory/name)
        if phase.get("files",{}).get(name)!=digest or outer["files"].get(READER+"/"+name)!=digest:
            raise ValueError("E3 Oracle metadata lineage mismatch")
    phase_prov=_read(directory/"provenance.json")
    if phase_prov.get("input_seal_sha256")!=P.sha(e3_inputs/"INPUT_SEAL.json") or phase_prov.get("phase")!=READER:
        raise ValueError("E3 Oracle capture input mismatch")
    records=_read(directory/"index.json")
    lookup={r["feature"]:r for r in records}
    if len(lookup)!=len(records):
        raise ValueError("duplicate E3 capture rows")
    selected={}
    for feature in ROWS:
        record=lookup[feature]
        if (record["status"]!="COMPLETE" or record["reader"]!=READER or record["n"]!=TOTAL_N
                or record["item_ids"]!=[it["id"] for it in items[feature]]
                or record["layers"]!=list(range(LAYERS)) or record["positions"]!=["injection","preanswer"]):
            raise ValueError("E3 Oracle selected row metadata is incomplete or mismatched")
        name=record["arrays"]["residuals"]
        if Path(name).is_absolute() or ".." in Path(name).parts:
            raise ValueError("invalid E3 residual path")
        digest=phase["files"].get(name)
        if (not digest or outer["files"].get(READER+"/"+name)!=digest
                or record["array_sha256"]["residuals"]!=digest or P.sha(directory/name)!=digest):
            raise ValueError("selected E3 Oracle residual seal mismatch")
        selected[feature]=record
    return selected,phase_prov


def select_and_refit(dev_residuals,labels,groups,*,layers=None):
    """Pure dev-array API: [84,64,hidden], with no test inputs accepted."""
    import torch
    from mats.probes import fit_logreg
    h=np.asarray(dev_residuals)
    y=np.asarray(labels,dtype=int);groups=np.asarray(groups)
    layers=middle_third_layers() if layers is None else list(layers)
    if (h.ndim!=3 or h.shape[0]!=DEV_N or h.shape[1]!=LAYERS or y.shape!=(DEV_N,)
            or groups.shape!=(DEV_N,) or len(np.unique(groups))!=6 or Counter(y.tolist())!={0:42,1:42}
            or not np.isfinite(h[:,layers,:]).all()):
        raise ValueError("fitter accepts 84 finite dev items,64 layers,six clusters,balanced binary labels only")
    if layers!=middle_third_layers():
        raise ValueError("candidate layers differ from the frozen middle-third convention")
    candidates=[];oof={}
    for layer in layers:
        cv=E3.grouped_cv_probe(h[:,layer,:],y,groups,n_splits=FOLDS,seed=SEED,lam=LAMBDA)
        candidates.append({"layer":layer,"dev_grouped_cv_auroc":cv["auroc"],
                           "n":cv["n"],"n_clusters":cv["n_clusters"]})
        oof[f"L{layer}__oof"]=np.asarray(cv["oof_scores"],dtype=np.float64)
        oof[f"L{layer}__fold"]=np.asarray(cv["fold_assignment"],dtype=np.int16)
    selected=min(candidates,key=lambda r:(-r["dev_grouped_cv_auroc"],r["layer"]))
    x=np.array(h[:,selected["layer"],:],dtype=np.float32,copy=True)
    model=fit_logreg(torch.as_tensor(x),torch.as_tensor(y),lam=LAMBDA)
    raw=(model.w/model.sd).detach().cpu().numpy().astype(np.float64)
    norm=float(np.linalg.norm(raw))
    if not np.isfinite(raw).all() or norm<=0:
        raise ValueError("selected dev logistic direction is degenerate")
    unit=raw/norm
    projection=x.astype(np.float64)@unit
    sigma=float(np.std(projection,ddof=SIGMA_DDOF))
    if not np.isfinite(sigma) or sigma<=0:
        raise ValueError("selected dev projection sigma is degenerate")
    meta={"selected_layer":selected["layer"],"selected_dev_cv_auroc":selected["dev_grouped_cv_auroc"],
          "candidates":candidates,"sigma":sigma,"sigma_ddof":SIGMA_DDOF,
          "raw_coefficient_norm":norm,"raw_intercept":float(model.b-(model.mu*model.w/model.sd).sum()),
          "dev_projection_mean":float(projection.mean()),"dev_projection_mean_A":float(projection[y==1].mean()),
          "dev_projection_mean_B":float(projection[y==0].mean()),"n_dev":DEV_N,"n_dev_clusters":6,
          "fit_split":"dev","positive_label":"value_A","orientation_flipped":False}
    return meta,unit.astype(np.float32),raw.astype(np.float32),oof


def freeze_directions(e3_inputs,e3_scores,dev_labels,registration,out,cache_out):
    e3_inputs,e3_scores,dev_labels,registration,out,cache=map(Path,(e3_inputs,e3_scores,dev_labels,registration,out,cache_out))
    registration_text=registration.read_text()
    if "§111" not in registration_text or "E19" not in registration_text or not all(f in registration_text for f in ROWS):
        raise ValueError("exact §111 E19 registration snapshot required")
    if out.exists() or cache.exists():
        raise FileExistsError("refusing to overwrite an E19 freeze or selection cache")
    items,templates,e3_provenance=_input_metadata(e3_inputs)
    captures,capture_prov=_capture_records(e3_inputs,e3_scores,items)
    labels,label_prov=_load_dev_labels(dev_labels,e3_inputs,items,templates,e3_provenance)
    started=time.perf_counter();rows=[];vectors={};all_oof={}
    for feature in ROWS:
        record=captures[feature]
        # mmap reads its header; advanced indexing below materialises DEV ONLY.
        h=np.load(e3_scores/READER/record["arrays"]["residuals"],mmap_mode="r",allow_pickle=False)
        if h.ndim!=4 or h.shape[:3]!=(TOTAL_N,LAYERS,2):
            raise ValueError("E3 residual shape mismatch")
        dev_indices=[i for i,it in enumerate(items[feature]) if it["split"]=="dev"]
        ids=[record["item_ids"][i] for i in dev_indices]
        dev_h=np.asarray(h[dev_indices,:,1,:],dtype=np.float32)
        y=[int(labels[i]["value"]==templates[feature]["values"][0]) for i in ids]
        groups=[labels[i]["cluster"] for i in ids]
        fitted,unit,raw,oof=select_and_refit(dev_h,y,groups)
        vectors[feature+"__unit"]=unit;vectors[feature+"__raw_coefficient"]=raw
        vectors[feature+"__sigma"]=np.array(fitted["sigma"],dtype=np.float64)
        for key,value in oof.items():all_oof[feature+"__"+key]=value
        rows.append({"feature":feature,"class":templates[feature]["class"],"reader":READER,"position":"preanswer",
                     "positive_value":templates[feature]["values"][0],"negative_value":templates[feature]["values"][1],
                     "ordered_dev_ids":ids,"dev_capture_indices":dev_indices,"hidden_size":h.shape[-1],
                     "residual_sha256":record["array_sha256"]["residuals"],
                     "arrays":{"unit":feature+"__unit","raw_coefficient":feature+"__raw_coefficient","sigma":feature+"__sigma"},**fitted})
        del h,dev_h
    out.mkdir(parents=True,exist_ok=False);cache.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(out/"directions.npz",**vectors)
    np.savez_compressed(cache/"dev_selection_oof.npz",**all_oof)
    receipt={"schema":"e19-dev-direction-freeze-v1","status":"FROZEN_DEV_ONLY_BEFORE_TEST",
             "experiment":"E19","registration":{"path":str(registration),"sha256":P.sha(registration)},
             "source":{"e3_inputs":str(e3_inputs),"e3_scores":str(e3_scores),
                       "e3_input_seal_sha256":P.sha(e3_inputs/"INPUT_SEAL.json"),
                       "e3_aggregate_score_seal_sha256":P.sha(e3_scores/"SCORE_SEAL.json"),
                       "e3_oracle_score_seal_sha256":P.sha(e3_scores/READER/"SCORE_SEAL.json"),
                       "capture_source_files":capture_prov.get("source_files"),
                       "dev_label_seal_sha256":P.sha(dev_labels/"DEV_LABEL_SEAL.json"),
                       "dev_labels_sha256":label_prov["dev_labels_sha256"]},
             "selection":{"metric":"dev-only template-grouped out-of-fold AUROC",
                          "candidate_layers":middle_third_layers(),"layer_indexing":"zero-based decoder block outputs",
                          "middle_third":"range(L//3,2*L//3): 21..41 for L=64",
                          "tie_break":"smallest zero-based layer at the exact maximum AUROC",
                          "n_splits":FOLDS,"seed":SEED,"lambda":LAMBDA,
                          "fitter":"E3 grouped_cv_probe and pinned mats.probes.fit_logreg",
                          "standardisation":"within each CV training fold; final refit on all84dev",
                          "raw_direction":"unit(w / training_sd); A-positive without sign flips",
                          "sigma":"sample standard deviation of84dev raw projections; ddof=1"},
             "rows":rows,"directions_file":"directions.npz","directions_sha256":P.sha(out/"directions.npz"),
             "selection_cache":{"path":str(cache/"dev_selection_oof.npz"),"sha256":P.sha(cache/"dev_selection_oof.npz")},
             "test_access":{"labels_decoded":0,"residual_items_materialised_for_fit":0,
                            "residual_file_byte_hashes":"whole sealed files hashed for integrity; test vectors never numerically read"},
             "commit_required_before_test":True,"gpu_hours":0,"fit_wall_seconds":time.perf_counter()-started}
    P.dump(out/"FREEZE.json",receipt)
    P.dump(out/"FREEZE_SEAL.json",{"status":"E19_DEV_DIRECTIONS_FROZEN_BEFORE_TEST",
                                 "files":{n:P.sha(out/n) for n in ("FREEZE.json","directions.npz")}})
    return receipt


def load_freeze(directory):
    """Return (receipt, feature -> {layer, u, sigma}) after strict integrity checks.

    The launch receipt separately binds the commit containing this freeze;
    its own commit hash cannot be embedded in a file committed by that commit.
    """
    directory=Path(directory)
    seal=P.verify(directory,"FREEZE_SEAL.json")
    if seal.get("status")!="E19_DEV_DIRECTIONS_FROZEN_BEFORE_TEST" or set(seal["files"])!={"FREEZE.json","directions.npz"}:
        raise ValueError("invalid E19 freeze seal")
    receipt=_read(directory/"FREEZE.json")
    if (receipt.get("status")!="FROZEN_DEV_ONLY_BEFORE_TEST" or receipt.get("experiment")!="E19"
            or receipt.get("directions_sha256")!=P.sha(directory/"directions.npz")
            or receipt.get("selection",{}).get("candidate_layers")!=middle_third_layers()
            or receipt.get("test_access",{}).get("labels_decoded")!=0
            or receipt.get("test_access",{}).get("residual_items_materialised_for_fit")!=0
            or receipt.get("commit_required_before_test") is not True):
        raise ValueError("E19 freeze provenance mismatch")
    rows=receipt["rows"]
    if len(rows)!=len(ROWS) or {r["feature"] for r in rows}!=set(ROWS):
        raise ValueError("E19 freeze must contain the five registered rows")
    directions={}
    with np.load(directory/"directions.npz",allow_pickle=False) as arrays:
        for row in rows:
            feature=row["feature"];unit=np.array(arrays[row["arrays"]["unit"]],copy=True)
            sigma=float(arrays[row["arrays"]["sigma"]])
            if (row["reader"]!=READER or row["position"]!="preanswer"
                    or row["fit_split"]!="dev" or row["n_dev"]!=DEV_N
                    or row["positive_label"]!="value_A" or row["orientation_flipped"] is not False
                    or row["selected_layer"] not in middle_third_layers()
                    or unit.shape!=(row["hidden_size"],) or not np.isfinite(unit).all()
                    or not np.isclose(np.linalg.norm(unit),1,atol=2e-5)
                    or not np.isfinite(sigma) or sigma<=0 or sigma!=row["sigma"]):
                raise ValueError("invalid E19 frozen direction")
            directions[feature]={"layer":row["selected_layer"],"u":unit,"sigma":sigma}
    return receipt,directions


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action",required=True)
    stage=sub.add_parser("stage-dev")
    for name in ("e3-inputs","source-labels","out"):stage.add_argument("--"+name,type=Path,required=True)
    freeze=sub.add_parser("freeze")
    for name in ("e3-inputs","e3-scores","dev-labels","registration","out","cache-out"):
        freeze.add_argument("--"+name,type=Path,required=True)
    args=vars(parser.parse_args(argv));action=args.pop("action")
    start=time.perf_counter();stamp=datetime.now(timezone.utc).isoformat();status="FAILED"
    try:
        result=stage_dev_labels(**args) if action=="stage-dev" else freeze_directions(**args)
        status="COMPLETE"
        print(json.dumps({"status":result["status"],"rows":len(ROWS),"out":str(args["out"]),
                          "selected_layers":{r["feature"]:r["selected_layer"] for r in result["rows"]} if action=="freeze" else {}},indent=2))
    finally:
        elapsed=time.perf_counter()-start
        record={"module":"understand","step":"e19_"+action,"started":stamp,"wall_s":elapsed,
                "gpu_hours":0,"gpu":"cpu","seed":SEED,"status":status,"command":sys.argv}
        with (P.ROOT/"results/g_agreement/compute.jsonl").open("a") as handle:handle.write(json.dumps(record,sort_keys=True)+"\n")
        with (P.ROOT/"results/g_agreement/log.md").open("a") as handle:handle.write(f"\n- {stamp} E19 `{action}`; {status}; {elapsed:.3f}s CPU; GPU-h0; seed{SEED}.\n")


if __name__=="__main__":main()
