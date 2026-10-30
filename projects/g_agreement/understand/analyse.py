"""Analyze sealed E3/E4 runs locally; never join labels before integrity checks."""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from projects.g_agreement.blindspot import protocol as P
from . import analysis as A
from .inputs import load_inputs, join_labels

PHASES = {"E3": ("olens", "nla", "jlens"), "E4": ("olens", "nla", "jlens", "target")}
NATIVE = {"olens": 44, "nla": 42, "jlens": 44}
PREDICTIONS = {
    "E3": "Prediction: Oracle-lens structure information is present after injection and either decays through reader layers or remains decodable despite weak verbal output; NLA decays less.",
    "E4": "Prediction: Oracle-lens receptive directions exclude structure and include meaning; NLA includes both with weaker structure sensitivity; J-lens sensitivity follows next-token relevance.",
}


def _read(path):
    return json.loads(Path(path).read_text())


def verify_run(experiment, inputs, scores, *, missing_arrays=()):
    """Verify aggregate, perphase coverage and input bindings BEFORE label IO."""
    inputs, scores = Path(inputs), Path(scores)
    from .custody import verify_available
    if missing_arrays and experiment != "E3":
        raise ValueError("missing-array exception is E3-only")
    aggregate, missing = verify_available(scores, allowed_missing=missing_arrays)

    if aggregate.get("status") != "SCORES_SEALED_EXPLORATORY_"+experiment or "provenance.json" not in aggregate["files"]:
        raise ValueError("wrong or incomplete aggregate score seal")
    provenance = _read(scores/"provenance.json")
    primary = inputs/experiment.lower()
    primary_sha = P.sha(primary/"INPUT_SEAL.json")
    if provenance.get("experiment") != experiment or provenance.get("input_seal_sha256") != primary_sha:
        raise ValueError("aggregate score/input binding mismatch")
    if set(provenance.get("phases", {})) != set(PHASES[experiment]):
        raise ValueError("aggregate must explicitly enumerate every phase")
    data = {"primary": load_inputs(primary)}
    if experiment == "E4":
        data["e9"] = load_inputs(inputs/"e9")
        if provenance.get("input_seals", {}).get("e9") != P.sha(inputs/"e9/INPUT_SEAL.json"):
            raise ValueError("E9 aggregate input binding mismatch")
    indices = {}
    capture_sources = None
    for phase, status in provenance["phases"].items():
        if status != "SEALED":
            indices[phase] = None
            continue
        directory = scores/phase
        if phase+"/SCORE_SEAL.json" not in aggregate["files"]:
            raise ValueError("aggregate lacks declared phase seal")
        seal, phase_missing = verify_available(directory, allowed_missing=[
            name.split("/", 1)[1] for name in missing_arrays if name.startswith(phase+"/")])
        if seal.get("status") != "SCORES_SEALED_EXPLORATORY_"+experiment or not {"index.json","provenance.json"} <= set(seal["files"]):
            raise ValueError("wrong or incomplete phase seal")
        for name, digest in seal["files"].items():
            if aggregate["files"].get(phase+"/"+name) != digest:
                raise ValueError("aggregate/phase file coverage mismatch")
        phase_prov=_read(directory/"provenance.json")
        expected_input = inputs/"e9" if phase == "target" else primary
        if (phase_prov.get("input_seal_sha256") != P.sha(expected_input/"INPUT_SEAL.json")
                or phase_prov.get("experiment") != experiment or phase_prov.get("phase") != phase):
            raise ValueError("phase/input binding mismatch")
        sources=phase_prov.get("source_files")
        if not isinstance(sources,dict) or not sources:
            raise ValueError("phase lacks capture source receipt")
        if capture_sources is not None and sources != capture_sources:
            raise ValueError("capture source receipts differ between phases")
        capture_sources=sources
        index = _read(directory/"index.json")
        phase_data = data["e9"] if phase == "target" else data["primary"]
        expected_features = {r["feature"] for r in phase_data["rows"]}
        seen=set()
        for record in index:
            f=record["feature"]
            if f not in expected_features or f in seen or record["reader"] != phase:
                raise ValueError("unknown, duplicate, or mismatched indexed row")
            seen.add(f)
            expected_ids=[it["id"] for it in phase_data["items"] if it["feature"] == f]
            if record["item_ids"] != expected_ids or record["n"] != len(expected_ids):
                raise ValueError("indexed row item order/count differs from frozen inputs")
            for key,name in record.get("arrays",{}).items():
                if name not in seal["files"] or record.get("array_sha256",{}).get(key) != seal["files"][name]:
                    raise ValueError("indexed array is not sealed or has a mismatched hash")
        complete_statuses=all(r["status"]=="COMPLETE" or
                              (phase=="jlens" and experiment=="E3" and r["status"].startswith("NOT_APPLICABLE"))
                              for r in index)
        if (seen != expected_features or not complete_statuses) and phase_prov.get("population_status") != "PARTIAL":
            raise ValueError("sealed phase lacks full row grid; explicit PARTIAL provenance required")
        for record in index:
            record["missing_arrays"] = {key: name for key, name in record.get("arrays", {}).items()
                                        if name in phase_missing}
        indices[phase] = {r["feature"]:r for r in index}
    provenance = {**provenance, "missing_arrays": missing,
                  "custody_exception": "§91 amendment 4af1004b" if missing_arrays else None}
    return data, indices, provenance


def _array(scores,phase,record,key):
    name=record.get("arrays",{}).get(key)
    if name is None:
        raise ValueError("complete record lacks "+key)
    a=np.load(Path(scores)/phase/name,mmap_mode="r",allow_pickle=False)
    if len(a)!=record["n"] or not np.isfinite(a).all():
        raise ValueError("invalid scored array shape/finiteness")
    return a


def _csv(path,rows,fields):
    with Path(path).open("x",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        writer.writeheader();writer.writerows(rows)


def _row_status(row,reader,record):
    return {"row":row["feature"],"class":row["class"],"reader":reader,
            "status":"NOT_RUN_OR_INCOMPLETE" if record is None else record["status"],
            "reason":"phase/row has no complete score seal" if record is None else record.get("reason"),
            "n":0 if record is None else record["n"]}


def _strip_probe(value,cache_arrays,key):
    if "oof_scores" in value:
        cache_arrays[key+"__oof"] = np.array(value.pop("oof_scores"),dtype=np.float64)
        cache_arrays[key+"__fold"] = np.array(value.pop("fold_assignment"),dtype=np.int16)
        value["folds"] = [{k:v for k,v in fold.items() if k not in ("train_indices","test_indices")}
                          for fold in value["folds"]]


def analyze_e3(data,indices,labels,scores,out,cache):
    lookup={r["id"]:r for r in labels}
    cells,rows,stages=[],[],[]
    for reader in NATIVE:
        index=indices[reader]
        for row in data["rows"]:
            feature=row["feature"]
            record=index.get(feature) if index is not None else None
            summary=_row_status(row,reader,record);rows.append(summary)
            if record is None or record["status"] == "INCOMPLETE":
                continue
            ids=record["item_ids"]
            y=[lookup[i]["y"] for i in ids]; groups=[lookup[i]["cluster"] for i in ids]
            asked=row.get("asked",{}).get(reader,{}).get("auroc")
            cache_arrays={}
            if record["status"] == "COMPLETE":
                missing = record.get("missing_arrays", {})
                if missing:
                    summary.update(status="MISSING", reason="lost sealed arrays: "+", ".join(missing.values()))
                if "residuals" not in missing:
                    residuals=_array(scores,reader,record,"residuals")
                    these=A.analyze_e3_cell(residuals,y,groups,reader=reader,row=feature,row_class=row["class"],
                             layers=record["layers"],positions=record["positions"],asked_auroc=asked)
                    for j,cell in enumerate(these):
                        _strip_probe(cell,cache_arrays,"cell_"+str(j))
                    cells.extend(these)
                    if any(c["status"] != "COMPLETE" for c in these):
                        summary["status"]="PARTIAL_ANALYSIS"
                else:
                    cells.extend({"reader":reader,"row":feature,"class":row["class"],
                                  "layer":layer,"position":position,"status":"MISSING","n":0,
                                  "auroc":None,"w1_asked_auroc":asked,
                                  "reason":"lost sealed array: "+missing["residuals"]}
                                 for layer in record["layers"] for position in record["positions"])
                stage_arrays={}
                if "input_stage" not in missing:
                    input_stage=_array(scores,reader,record,"input_stage")
                    stage_arrays={"input_embedding_"+pos:input_stage[:,j,:] for j,pos in enumerate(record["positions"])}
                else:
                    stages.extend({"reader":reader,"row":feature,"class":row["class"],
                                   "stage":"input_embedding_"+pos,"status":"MISSING","n":0,
                                   "auroc":None,"w1_asked_auroc":asked,
                                   "reason":"lost sealed array: "+missing["input_stage"]}
                                  for pos in record["positions"])
            elif record["status"].startswith("NOT_APPLICABLE") and reader == "jlens":
                stage_arrays={key.removeprefix("stage_"):_array(scores,reader,record,key)
                              for key in record["arrays"] if key.startswith("stage_")}
            else:
                continue
            for stage,value in stage_arrays.items():
                rec={"reader":reader,"row":feature,"class":row["class"],"stage":stage,
                     "interpretation":"named native representation, not a decoder layer",
                     "w1_asked_auroc":asked}
                try:
                    rec.update(A.grouped_cv_probe(value,y,groups));rec["status"]="COMPLETE"
                    _strip_probe(rec,cache_arrays,"stage_"+stage)
                except (ValueError,RuntimeError) as error:
                    rec.update(status="NOT_EVALUABLE",reason=str(error),auroc=None)
                stages.append(rec)
            if cache_arrays:
                path=cache/(reader+"."+feature+".oof.npz")
                np.savez_compressed(path,**cache_arrays,item_ids=np.array(ids))
                summary["oof_file"]=str(path)
    # Preserve the full row grid in heatmaps whenever a reader layer schema is
    # known from any completed row. Missing rows must not disappear visually.
    for reader in NATIVE:
        known=[c for c in cells if c["reader"]==reader]
        schema=sorted({(c["layer"],c["position"]) for c in known})
        present={(c["row"],c["layer"],c["position"]) for c in known}
        for row in data["rows"]:
            for layer,position in schema:
                if (row["feature"],layer,position) not in present:
                    cells.append({"reader":reader,"row":row["feature"],"class":row["class"],
                                  "layer":layer,"position":position,"status":"NOT_RUN_OR_INCOMPLETE",
                                  "n":0,"auroc":None,"w1_asked_auroc":row.get("asked",{}).get(reader,{}).get("auroc"),
                                  "reason":"no sealed complete capture for this requested row"})
    P.dump(out/"metrics.json",{"experiment":"E3","exploratory":True,"rows":rows,"cells":cells,"named_stages":stages,
                               "orientation":"A positive; no AUROC flips","cv":"5 folds grouped by W1 template cluster; all168 dev+test; train-only scaling; lambda=.001",
                               "j_lens_note":"J-lens has no residual stream/token positions. Named input/J_h stages are not decoder layers."})
    _csv(out/"rows.csv",rows,["reader","row","class","status","n","reason","oof_file"])
    _csv(out/"cells.csv",cells,["reader","row","class","layer","position","status","n","auroc","w1_asked_auroc"])
    _csv(out/"named_stages.csv",stages,["reader","row","class","stage","status","n","auroc","w1_asked_auroc"])
    figures=A.plot_e3(cells,out/"figures") if cells else []
    complete=sum(c["status"]=="COMPLETE" for c in cells)
    changes={}
    for reader in ("olens","nla"):
        first_post=0 if reader=="olens" else 1
        subset=[c for c in cells if c["reader"]==reader and c["position"]=="preanswer" and c["class"]!="semantic" and c["auroc"] is not None]
        if not subset:continue
        last=max(c["layer"] for c in subset)
        first={c["row"]:c["auroc"] for c in subset if c["layer"]==first_post}
        final={c["row"]:c["auroc"] for c in subset if c["layer"]==last}
        shared=sorted(first.keys() & final.keys())
        if shared:
            changes[reader]={"rows":shared,"first_post_layer":first_post,"last_layer":last,
                             "first_mean":float(np.mean([first[r] for r in shared])),
                             "last_mean":float(np.mean([final[r] for r in shared])),
                             "changes":{r:final[r]-first[r] for r in shared}}
    assessment="Prediction assessment: NOT RUN / no evaluable sealed residual-layer evidence."
    if complete:
        assessment="Prediction assessment: Oracle representation-versus-verbalisation remains unresolved by probe AUROC alone."
        if "olens" in changes:
            delta=float(np.mean(list(changes["olens"]["changes"].values())))
            assessment+=f" Oracle structure preanswer AUROC changed by {delta:+.4f} from the first post-injection block to the last: {'decline observed' if delta<0 else 'no decline observed'}."
        if set(changes)=={"olens","nla"}:
            shared=sorted(set(changes["olens"]["rows"])&set(changes["nla"]["rows"]))
            if shared:
                od=float(np.mean([changes["olens"]["changes"][r] for r in shared]))
                nd=float(np.mean([changes["nla"]["changes"][r] for r in shared]))
                assessment+=f" On {len(shared)} matched structure rows, the NLA-decays-less prediction {'held' if nd>od else 'did not hold'} descriptively (NLA change {nd:+.4f}, Oracle change {od:+.4f})."
    lines=[PREDICTIONS["E3"],"",assessment,"",
           f"Reported {complete}/{len(cells)} evaluable layer-position cells; all {len(rows)} requested reader×row entries retained.",
           "The first post-injection block is Oracle 0 and NLA 1. NLA block 0 and embedding stages precede its injection and cannot locate information loss after injection.",
           "W1 asked AUROCs use test items; internal grouped-CV AUROCs use all 168 dev+test items, so the side-by-side difference is descriptive. No threshold decision or mechanistic identification is imposed.",
           "J-lens has no decoder residual stream or token positions. Its input and J_h are separately labelled native stages; no residual heatmap is fabricated.","",
           "| Reader | Class | Position | Input embedding | First post-injection mean | Last-layer mean | Change | W1 asked mean |",
           "|---|---|---|---:|---:|---:|---:|---:|"]
    for reader in ("olens","nla"):
        first_post=0 if reader=="olens" else 1
        for cls in sorted({r["class"] for r in data["rows"]}):
            for pos in ("injection","preanswer"):
                subset=[c for c in cells if c["reader"]==reader and c["class"]==cls and c["position"]==pos and c["auroc"] is not None]
                if not subset:continue
                last=max(c["layer"] for c in subset)
                first={c["row"]:c for c in subset if c["layer"]==first_post}
                final={c["row"]:c for c in subset if c["layer"]==last}
                shared=sorted(first.keys() & final.keys())
                if not shared:continue
                means=[np.mean([table[r]["auroc"] for r in shared]) for table in (first,final)]
                asked=[first[r]["w1_asked_auroc"] for r in shared if first[r]["w1_asked_auroc"] is not None]
                embedding=[r["auroc"] for r in stages if r["reader"]==reader and r["row"] in shared and r["stage"]=="input_embedding_"+pos and r["auroc"] is not None]
                av=f"{np.mean(asked):.3f}" if asked else "unavailable"
                ev=f"{np.mean(embedding):.3f}" if embedding else "unavailable"
                lines.append(f"| {reader} | {cls} | {pos} | {ev} | {means[0]:.3f} | {means[1]:.3f} | {means[1]-means[0]:+.3f} | {av} |")
    lines += ["","All individual cells, including failures: `cells.csv`; full requested population: `rows.csv`; native stages: `named_stages.csv`.",
              "Heatmaps use a fixed 0–1 AUROC scale; missing cells are grey. Class curves average rows equally."]
    lost=[reader+"/"+name for reader,index in indices.items() if index
          for record in index.values() for name in record.get("missing_arrays",{}).values()]
    if lost:
        lines += ["", "§91 custody exception (4af1004b): these sealed arrays were lost during pull; affected cells are MISSING, never imputed:", ""]
        lines += ["- `"+name+"`" for name in sorted(lost)]
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    return {"experiment":"E3","rows":len(rows),"layer_cells":len(cells),"evaluable_layer_cells":complete,"figures":figures}


def analyze_e4(data,e9,indices,labels,scores,out,cache):
    lookup={r["id"]:r for r in labels}
    rows,subspaces,fractions=[],{},[]
    for reader,layer in NATIVE.items():
        index=indices[reader]; pooled=[];pooled_features=[]
        for row in data["rows"]:
            feature=row["feature"];record=index.get(feature) if index is not None else None
            rec=_row_status(row,reader,record);rows.append(rec)
            if record is None or record["status"] != "COMPLETE":continue
            gradients=_array(scores,reader,record,"gradients")
            scores_array=_array(scores,reader,record,"scores")
            if gradients.ndim!=2 or len(gradients)!=84:
                raise ValueError("E4 complete row needs all84 test gradients")
            if scores_array.shape != (84,):
                raise ValueError("E4 scores must contain the mean W1 asked contrast per test item")
            references={r["id"]:r for r in data.get("native_reference",[]) if r["reader"]==reader}
            available=[i for i,item_id in enumerate(record["item_ids"]) if item_id in references and references[item_id]["status"]=="COMPLETE"]
            if available:
                old=np.array([np.mean(references[record["item_ids"][i]]["scores"]) for i in available])
                delta=np.abs(np.asarray(scores_array)[available]-old)
                rec.update(score_parity_status="DESCRIPTIVE_COMPLETE" if len(available)==84 else "DESCRIPTIVE_PARTIAL",
                           score_parity_n=len(available),score_parity_mean_absolute_difference=float(delta.mean()),
                           score_parity_max_absolute_difference=float(delta.max()))
            else:
                rec.update(score_parity_status="W1_REFERENCE_UNAVAILABLE",score_parity_n=0)
            stats=A.summarize_gradients(gradients,data["directions"][feature+f"__L{layer}"],
                                       groups=[lookup[i]["cluster"] for i in record["item_ids"]])
            itemkeys=("item_abs_cos","item_random_mean_abs_cos","item_gradient_norm")
            path=cache/(reader+"."+feature+".items.npz")
            np.savez_compressed(path,**{k:np.array(stats.pop(k)) for k in itemkeys},
                                scores=scores_array,item_ids=np.array(record["item_ids"]))
            rec.update(stats);rec.update(native_layer=layer,item_metrics_file=str(path))
            pooled.append(gradients);pooled_features.append(feature)
        if pooled:
            basis=cache/(reader+".receptive_subspace.npz")
            directions={r["feature"]:data["directions"][r["feature"]+f"__L{layer}"] for r in data["rows"]}
            subspace=A.receptive_subspace(np.concatenate(pooled),directions,basis_out=basis)
            subspace.update(reader=reader,native_layer=layer,pooled_features=pooled_features,
                            missing_features=[r["feature"] for r in data["rows"] if r["feature"] not in pooled_features],
                            population_status="COMPLETE" if len(pooled_features)==len(data["rows"]) else "PARTIAL_EXPLORATORY_POOL")
            subspaces[reader]=subspace
            classes={r["feature"]:r["class"] for r in data["rows"]}
            fractions.extend({**r,"reader":reader,"class":classes[r["row"]],"pool_status":subspace["population_status"]} for r in subspace["rows"])
        else:
            missing=[{"reader":reader,"row":r["feature"],"class":r["class"],
                      "pool_status":"NOT_RUN_OR_INCOMPLETE","k_requested":k,
                      "k_effective":None,"rank_limited":None,"fraction_inside":None,
                      "random_mean_fraction":None,"isotropic_expected_fraction":None}
                     for r in data["rows"] for k in (16,64,256)]
            fractions.extend(missing)
            subspaces[reader]={"reader":reader,"status":"NOT_RUN_OR_INCOMPLETE","pooled_features":[],
                               "missing_features":[r["feature"] for r in data["rows"]],"rows":missing}
    e9rows=[]
    index=indices["target"]
    for row in e9["rows"]:
        feature=row["feature"];record=index.get(feature) if index is not None else None
        rec=_row_status(row,"target",record);e9rows.append(rec)
        if record is None or record["status"]!="COMPLETE":continue
        derivative=_array(scores,"target",record,"derivatives")
        rms=_array(scores,"target",record,"rms");l2=_array(scores,"target",record,"l2")
        if derivative.ndim!=2 or len(derivative)!=84 or rms.shape!=(84,) or l2.shape!=(84,):
            raise ValueError("E9 needs all84 item-by-vocabulary directional derivatives")
        if not np.allclose(l2,np.linalg.norm(derivative,axis=1),rtol=5e-4,atol=1e-5) or not np.allclose(rms,l2/np.sqrt(derivative.shape[1]),rtol=5e-4,atol=1e-5):
            raise ValueError("E9 RMS/L2 do not match sealed full-vocabulary derivatives")
        rec.update(native_layer=44,mean_rms=float(np.mean(rms)),mean_l2=float(np.mean(l2)),
                   mean_rms_ci95=A._ci(rms),mean_l2_ci95=A._ci(l2),vocabulary_size=derivative.shape[1],
                   objective=record.get("target_objective"),
                   raw_derivatives_file=str(Path(scores)/"target"/record["arrays"]["derivatives"]),
                   raw_derivatives_sha256=record["array_sha256"]["derivatives"])
    P.dump(out/"metrics.json",{"experiment":"E4","exploratory":True,"alignment_rows":rows,
                               "receptive_subspaces":subspaces,"e9_target_rows":e9rows,
                               "orientation":"W1 A-minus-B; absolute cosine does not alter the underlying scores/directions"})
    _csv(out/"alignment.csv",rows,["reader","row","class","status","n","native_layer","mean_abs_cos","mean_abs_cos_nonzero","zero_gradient_n","random_mean_abs_cos","alignment_minus_random","mean_abs_cos_ci95","alignment_minus_random_ci95","score_parity_status","score_parity_n","score_parity_mean_absolute_difference","score_parity_max_absolute_difference","reason"])
    _csv(out/"subspace_fractions.csv",fractions,["reader","row","class","pool_status","k_requested","k_effective","rank_limited","fraction_inside","random_mean_fraction","isotropic_expected_fraction"])
    _csv(out/"e9_target.csv",e9rows,["row","class","status","n","native_layer","mean_rms","mean_rms_ci95","mean_l2","mean_l2_ci95","vocabulary_size","raw_derivatives_file","raw_derivatives_sha256","reason"])
    complete=[r for r in rows if r["status"]=="COMPLETE"]
    lines=[PREDICTIONS["E4"],"", "Prediction assessment: NOT RUN / no evaluable sealed gradients." if not complete else "Prediction assessment: the descriptive class ordering is reported below; no pass/fail threshold or causal conclusion is imposed.","",
           f"All {len(rows)} reader×row entries retained; {len(complete)} complete. E9 retains all {len(e9rows)} target rows ({sum(r['status']=='COMPLETE' for r in e9rows)} complete).", "",
           "| Reader | Class | Rows | Mean absolute cosine | Random baseline |", "|---|---|---:|---:|---:|"]
    for reader in NATIVE:
        for cls in sorted({r["class"] for r in data["rows"]}):
            part=[r for r in complete if r["reader"]==reader and r["class"]==cls]
            if part:
                lines.append(f"| {reader} | {cls} | {len(part)} | {np.mean([r['mean_abs_cos'] for r in part]):.5f} | {np.mean([r['random_mean_abs_cos'] for r in part]):.5f} |")
    oracle=[r for r in fractions if r["reader"]=="olens" and r["fraction_inside"] is not None]
    if oracle:
        lines += ["","Oracle receptive-subspace prediction, by requested k (descriptive arithmetic mean across rows):"]
        for k in (16,64,256):
            structure=[r["fraction_inside"] for r in oracle if r["k_requested"]==k and r["class"]!="semantic"]
            meaning=[r["fraction_inside"] for r in oracle if r["k_requested"]==k and r["class"]=="semantic"]
            if structure and meaning:
                s,m=float(np.mean(structure)),float(np.mean(meaning))
                lines.append(f"- k={k}: structure {s:.5f}, meaning {m:.5f}; predicted ordering {'held' if s<m else 'did not hold'} descriptively.")
    lines += ["","Full outcomes: `alignment.csv`, `subspace_fractions.csv`, `e9_target.csv`, and `metrics.json`.",
              "Gradient SVD is uncentered and preserves gradient magnitudes. Requested k above numerical rank uses only the available gradient span, with effective k reported. Random baselines use 200 seeded isotropic directions.",
              "Exactly zero gradients contribute zero to alignment and random baseline; their undefined cosine is disclosed through the zero count and nonzero-only mean. Alignment CIs resample W1 template clusters; E9 CIs resample items.",
              "Fresh gradient-pass scores are compared with the mean of W1’s two frozen asked contrasts; mean/max absolute differences are descriptive parity diagnostics, with no sign changes or score tuning.",
              "Raw derivatives remain in the sealed score cache; the E9 table records each file and hash. J-lens next-token relevance still requires the descriptive cross-row comparison in E9."]
    (out/"RESULTS.md").write_text("\n".join(lines)+"\n")
    return {"experiment":"E4","rows":len(rows),"complete_rows":len(complete),"e9_rows":len(e9rows),"e9_complete":sum(r["status"]=="COMPLETE" for r in e9rows)}


def analyze(experiment, inputs, scores, labels, out, cache_out, allow_e3_missing_arrays=False):
    inputs,scores,labels,out,cache=map(Path,(inputs,scores,labels,out,cache_out))
    from .custody import E3_LOST_ARRAYS
    missing_arrays = E3_LOST_ARRAYS if allow_e3_missing_arrays else ()
    data,indices,provenance=verify_run(experiment,inputs,scores,missing_arrays=missing_arrays)
    # This is deliberately the first label read, after *all* phase checks.
    joined=join_labels(inputs/experiment.lower(),scores,labels,missing_arrays=missing_arrays)
    out.mkdir(parents=True,exist_ok=False);cache.mkdir(parents=True,exist_ok=False)
    if experiment=="E3":
        summary=analyze_e3(data["primary"],indices,joined,scores,out,cache)
    else:
        summary=analyze_e4(data["primary"],data["e9"],indices,joined,scores,out,cache)
    P.dump(out/"provenance.json",{"experiment":experiment,"input_seal_sha256":P.sha(inputs/experiment.lower()/"INPUT_SEAL.json"),
                                 "score_seal_sha256":P.sha(scores/"SCORE_SEAL.json"),"source_score_status":provenance["status"],
                                 "label_sha256":P.sha(labels),"exploratory":True,"summary":summary,
                                 "missing_arrays":provenance["missing_arrays"],"custody_exception":provenance["custody_exception"]})
    names=[str(p.relative_to(out)) for p in out.rglob("*") if p.is_file()]
    P.dump(out/"ANALYSIS_SEAL.json",{"status":"EXPLORATORY_ANALYSIS_REPORTED_ALL_OUTCOMES",
                                    "files":{name:P.sha(out/name) for name in names}})
    return summary


def run_logged(arguments, *, log_root=None):
    """Log the local CPU analysis, including failed attempts, without GPU charge."""
    start=time.perf_counter();stamp=datetime.now(timezone.utc).isoformat();status="FAILED"
    try:
        result=analyze(**arguments);status="COMPLETE";return result
    finally:
        elapsed=time.perf_counter()-start
        root=Path(log_root) if log_root is not None else P.ROOT
        directory=root/"results/g_agreement";directory.mkdir(parents=True,exist_ok=True)
        record={"module":"understand","step":arguments["experiment"].lower()+"_cpu_analysis",
                "started":stamp,"wall_s":elapsed,"gpu_hours":0,"gpu":"cpu","seed":A.SEED,
                "status":status,"command":sys.argv,"accounting_scope":"CPU only"}
        with (directory/"compute.jsonl").open("a") as handle:
            handle.write(json.dumps(record,sort_keys=True)+"\n")
        with (directory/"log.md").open("a") as handle:
            handle.write(f"\n- {stamp} understand `{record['step']}`; seed {A.SEED}; {elapsed:.3f}s; {status}; GPU-h 0.000000.\n")


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--experiment",choices=tuple(PHASES),required=True)
    for name in ("inputs","scores","labels","out","cache-out"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--allow-e3-missing-arrays",action="store_true",help="§91 4af1004b: only the three named lost E3 arrays")
    a=p.parse_args(argv)
    print(json.dumps(run_logged(vars(a)),indent=2))


if __name__=="__main__":
    main()
