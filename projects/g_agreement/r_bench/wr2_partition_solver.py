#!/usr/bin/env python3
"""Standalone metadata-only Stage 2 partition MILP; never loads model data.

Input: {"mode": str, "test": [{item_id,capture,alias,template,block,source,
        prefix,component}], "pool": [{item_id,capture,aliases,template,source}]}.
The producer must conservatively close aliases/templates and fix components.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
import math
from pathlib import Path
import time
import warnings

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix, vstack, save_npz
import scipy

DEFAULT_GATES = {"pool": 512, "names": 32, "prefixes": 8,
                 "components": 8, "sources": 2, "test": 256}
TIE_SALT = "wr2-partition-tie-v1"


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _or(builder, members, name):
    """y is exactly OR(members) for binary variables, including empty OR."""
    y = builder.var(name)
    for x in members:
        builder.row({x: 1, y: -1}, -np.inf, 0)
    builder.row({y: 1, **{x: -1 for x in members}}, -np.inf, 0)
    return y


class Builder:
    def __init__(self):
        self.names = []
        self.rows = []
        self.lo = []
        self.hi = []

    def var(self, name):
        i = len(self.names)
        self.names.append(name)
        return i

    def row(self, terms, lo, hi):
        self.rows.append(terms)
        self.lo.append(float(lo))
        self.hi.append(float(hi))

    def matrix(self):
        ri, ci, vs = [], [], []
        for i, terms in enumerate(self.rows):
            for j, v in terms.items():
                if v:
                    ri.append(i)
                    ci.append(j)
                    vs.append(v)
        return coo_matrix((vs, (ri, ci)), shape=(len(self.rows), len(self.names)),
                          dtype=float).tocsc()


def _require_text(row, key):
    if key not in row or row[key] is None or str(row[key]) == "":
        raise ValueError(f"Missing {key!r} on {row.get('item_id')!r}")
    return str(row[key])


def normalize_input(data):
    out = {"mode": str(data.get("mode", "unspecified")), "test": [], "pool": []}
    seen = set()
    suffix_present = ["suffix" in r for r in data["test"]]
    if any(suffix_present) and not all(suffix_present):
        raise ValueError("Suffix metadata must be present on every test row or absent on all")
    out["suffix_source"] = "explicit_token_sequences" if all(suffix_present) and suffix_present else "alias_fallback_for_legacy_synthetic_inputs"
    for role in ("test", "pool"):
        for r in data[role]:
            keys = ("item_id", "capture", "alias", "template", "block", "source",
                    "prefix", "component") if role == "test" else (
                    "item_id", "capture", "template", "source")
            row = {k: _require_text(r, k) for k in keys}
            if role == "test":
                if "suffix" in r:
                    suffix = json.loads(r["suffix"]) if isinstance(r["suffix"], str) else r["suffix"]
                    if not isinstance(suffix, list) or not suffix or any(type(x) is not int or x < 0 for x in suffix):
                        raise ValueError(f"Suffix must be a nonempty token-ID list: {row['item_id']}")
                    row["suffix"] = json.dumps(suffix, separators=(",", ":"))
                else:
                    row["suffix"] = "alias:" + row["alias"]
            if row["item_id"] in seen:
                raise ValueError(f"Duplicate input item ID: {row['item_id']}")
            seen.add(row["item_id"])
            if role == "pool":
                if not isinstance(r.get("aliases"), list):
                    raise ValueError(f"Pool aliases must be a list: {row['item_id']}")
                if any(x is None or str(x) == "" for x in r["aliases"]):
                    raise ValueError(f"Empty pool alias: {row['item_id']}")
                row["aliases"] = sorted({str(x) for x in r["aliases"]})
            out[role].append(row)
        out[role].sort(key=lambda r: r["item_id"])
    blocks = collections.defaultdict(list)
    for r in out["test"]:
        blocks[r["block"]].append(r)
    for block, rs in blocks.items():
        if len({r["prefix"] for r in rs}) != 1:
            raise ValueError(f"Block has multiple first-token prefixes: {block}")
        if len({r["component"] for r in rs}) != 1:
            raise ValueError(f"Block has multiple independence components: {block}")
    return out


def build_problem(data, gates):
    b = Builder()
    tests, pools = data["test"], data["pool"]
    tx = [b.var(f"test:{r['item_id']}") for r in tests]
    px = [b.var(f"pool:{r['item_id']}") for r in pools]
    by = {k: collections.defaultdict(list) for k in
          ("alias", "template", "block", "prefix", "source")}
    capture = collections.defaultdict(list)
    block_alias = collections.defaultdict(list)
    block_suffix = collections.defaultdict(list)
    for r, x in zip(tests, tx):
        for k in by:
            by[k][r[k]].append(x)
        capture[r["capture"]].append(x)
        block_alias[(r["block"], r["alias"])].append(x)
        block_suffix[(r["block"], r["suffix"])].append(x)
    aux = {}
    for k in by:
        aux[k] = {s: _or(b, members, f"{k}:{s}")
                  for s, members in sorted(by[k].items())}
    suffix = collections.defaultdict(list)
    for (block, alias), members in sorted(block_alias.items()):
        suffix[block].append(_or(b, members, f"block_alias:{block}:{alias}"))
    for block, y in aux["block"].items():
        b.row({y: -2, **{z: 1 for z in suffix[block]}}, 0, np.inf)
    token_suffix = collections.defaultdict(list)
    for (block, seq), members in sorted(block_suffix.items()):
        token_suffix[block].append(_or(b, members, f"block_token_suffix:{block}:{seq}"))
    for block, y in aux["block"].items():
        b.row({y: -2, **{z: 1 for z in token_suffix[block]}}, 0, np.inf)
    component_blocks = collections.defaultdict(set)
    for r in tests:
        component_blocks[r["component"]].add(aux["block"][r["block"]])
    aux["component"] = {
        c: _or(b, sorted(members), f"component:{c}")
        for c, members in sorted(component_blocks.items())}
    for r, p in zip(pools, px):
        capture[r["capture"]].append(p)
        if r["template"] in aux["template"]:
            b.row({p: 1, aux["template"][r["template"]]: 1}, -np.inf, 1)
        for alias in r["aliases"]:
            if alias in aux["alias"]:
                b.row({p: 1, aux["alias"][alias]: 1}, -np.inf, 1)
    for members in capture.values():
        if len(members) > 1:
            b.row({x: 1 for x in members}, -np.inf, 1)
    requirements = {"pool": px, "names": list(aux["alias"].values()),
                    "prefixes": list(aux["prefix"].values()),
                    "components": list(aux["component"].values()),
                    "sources": list(aux["source"].values())}
    for name, variables in requirements.items():
        b.row({x: 1 for x in variables}, gates[name], np.inf)
    return b, tx, px


def counts_and_checks(data, selected, gates):
    ts = [r for r in data["test"] if r["item_id"] in selected["test"]]
    ps = [r for r in data["pool"] if r["item_id"] in selected["pool"]]
    names = {r["alias"] for r in ts}
    templates = {r["template"] for r in ts}
    groups = collections.defaultdict(set)
    suffixes = collections.defaultdict(set)
    for r in ts:
        groups[r["block"]].add(r["alias"])
        suffixes[r["block"]].add(r.get("suffix", "alias:" + r["alias"]))
    counts = {"test": len(ts), "pool": len(ps), "names": len(names),
              "prefixes": len({r["prefix"] for r in ts}),
              "components": len({r["component"] for r in ts}),
              "sources": len({r["source"] for r in ts}), "blocks": len(groups)}
    pool_aliases = {a for r in ps for a in r["aliases"]}
    captures = [r["capture"] for r in ts + ps]
    checks = {
        "unique_captures_within_and_across_roles": len(captures) == len(set(captures)),
        "zero_alias_overlap": not bool(names & pool_aliases),
        "zero_template_overlap": not bool(templates & {r["template"] for r in ps}),
        "every_selected_block_has_two_aliases": all(len(v) >= 2 for v in groups.values()),
        "every_selected_block_has_two_suffix_sequences": all(len(v) >= 2 for v in suffixes.values()),
        "original_roles_preserved": True,
    }
    passed = {k: counts[k] >= v for k, v in gates.items()}
    return counts, checks, passed


def _number(x):
    if x is None:
        return None
    x = float(x)
    return x if math.isfinite(x) else None


def save_problem(prefix, b, matrix, low, high, tx, px):
    """Save the exact base MILP; later count-fixing rows derive from stage records."""
    prefix = Path(prefix)
    matrix_path = Path(str(prefix) + "_milp_matrix.npz")
    bounds_path = Path(str(prefix) + "_milp_bounds.npz")
    metadata_path = Path(str(prefix) + "_milp_metadata.json")
    save_npz(matrix_path, matrix, compressed=True)
    np.savez_compressed(bounds_path, constraint_lower=low, constraint_upper=high,
                        variable_lower=np.zeros(len(b.names)), variable_upper=np.ones(len(b.names)),
                        integrality=np.ones(len(b.names), dtype=np.uint8))
    metadata = {"variable_names": b.names, "test_variable_indices": tx, "pool_variable_indices": px,
                "matrix_shape": list(matrix.shape), "matrix_nonzeros": int(matrix.nnz),
                "matrix_path": str(matrix_path), "matrix_sha256": digest(matrix_path),
                "bounds_path": str(bounds_path), "bounds_sha256": digest(bounds_path),
                "primary_objective": "-1 at test indices, zero elsewhere; minimize",
                "secondary_objective": "-1 at pool indices, zero elsewhere; minimize",
                "secondary_added_constraint": "sum(test indices) equals primary certified optimum recorded in stages",
                "tertiary_added_constraint": "sum(pool indices) equals secondary certified optimum recorded in stages",
                "tertiary_objective": f"SHA256-rank of {TIE_SALT}|role|item_id over test/pool variables, divided by n(n+1)/2+1; zero elsewhere",
                "constraint_format": "constraint_lower <= matrix @ binary_variables <= constraint_upper"}
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    return {"matrix_path": str(matrix_path), "matrix_sha256": digest(matrix_path),
            "bounds_path": str(bounds_path), "bounds_sha256": digest(bounds_path),
            "metadata_path": str(metadata_path), "metadata_sha256": digest(metadata_path)}


def solve(data, time_limit=180.0, gates=None, matrix_artifact_prefix=None):
    began_wall, began_cpu = time.monotonic(), time.process_time()
    deadline = began_wall + float(time_limit)
    gates = dict(DEFAULT_GATES if gates is None else gates)
    data = normalize_input(data)
    b, tx, px = build_problem(data, gates)
    matrix = b.matrix()
    low, high = np.array(b.lo), np.array(b.hi)
    matrix_artifacts = (save_problem(matrix_artifact_prefix, b, matrix, low, high, tx, px)
                        if matrix_artifact_prefix is not None else None)
    stages = []
    incumbent = None
    primary_optimal = False
    primary_bound = None
    secondary_optimal = False

    def stage(name, objective, mat, lo, hi):
        remain = deadline - time.monotonic()
        if remain <= 0:
            return None, None
        sw, sc = time.monotonic(), time.process_time()
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", RuntimeWarning)
            result = milp(objective, integrality=np.ones(len(b.names), dtype=np.uint8),
                          bounds=Bounds(np.zeros(len(b.names)), np.ones(len(b.names))),
                          constraints=LinearConstraint(mat, lo, hi),
                          options={"time_limit": remain, "mip_rel_gap": 0.0,
                                   "presolve": True, "threads": 1, "random_seed": 0})
        candidate, error = None, None
        if getattr(result, "x", None) is not None:
            raw = np.asarray(result.x)
            rounded = np.rint(raw)
            activity = mat @ rounded
            if (np.isfinite(raw).all() and np.max(np.abs(raw - rounded)) <= 1e-5
                    and (rounded >= 0).all() and (rounded <= 1).all()
                    and (activity >= lo - 1e-7).all() and (activity <= hi + 1e-7).all()):
                candidate = rounded.astype(np.int8)
            else:
                error = "Returned incumbent failed binary/constraint validation"
        record = {"stage": name, "scipy_status": int(result.status),
                  "message": str(result.message), "optimal": int(result.status) == 0,
                  "objective": _number(getattr(result, "fun", None)),
                  "dual_bound": _number(getattr(result, "mip_dual_bound", None)),
                  "mip_gap": _number(getattr(result, "mip_gap", None)),
                  "node_count": _number(getattr(result, "mip_node_count", None)),
                  "validated_incumbent": candidate is not None,
                  "validation_error": error,
                  "warnings": [str(w.message) for w in caught],
                  "remaining_time_at_start_seconds": remain,
                  "wall_seconds": time.monotonic() - sw,
                  "cpu_seconds": time.process_time() - sc}
        if candidate is not None:
            record["test_count"] = int(candidate[tx].sum())
            record["pool_count"] = int(candidate[px].sum())
        stages.append(record)
        return result, candidate

    if not b.names:
        # Empty universe is an exact infeasibility certificate for fixed positive gates.
        primary_bound = 0
        status = "INFEASIBLE_EMPTY_UNIVERSE"
    else:
        primary_c = np.zeros(len(b.names))
        primary_c[tx] = -1
        res, candidate = stage("maximize_test", primary_c, matrix, low, high)
        incumbent = candidate
        if res is not None:
            dual = _number(getattr(res, "mip_dual_bound", None))
            if dual is not None:
                primary_bound = max(0, math.floor(-dual + 1e-6))
            primary_optimal = int(res.status) == 0 and candidate is not None
            if primary_optimal:
                primary_bound = int(candidate[tx].sum())
            status = ("PRIMARY_OPTIMAL" if primary_optimal else
                      "INFEASIBLE" if int(res.status) == 2 else
                      "FEASIBLE_WITH_UNRESOLVED_OPTIMUM" if candidate is not None else
                      "NO_FEASIBLE_WITNESS_UNRESOLVED")
        else:
            status = "BUDGET_EXHAUSTED_BEFORE_SOLVE"
        if primary_optimal and deadline - time.monotonic() > 0.05:
            ntest = int(incumbent[tx].sum())
            fixed = coo_matrix((np.ones(len(tx)), (np.zeros(len(tx), dtype=int), tx)),
                               shape=(1, len(b.names))).tocsc()
            m2 = vstack([matrix, fixed], format="csc")
            l2, h2 = np.r_[low, ntest], np.r_[high, ntest]
            secondary_c = np.zeros(len(b.names))
            secondary_c[px] = -1
            res2, candidate2 = stage("maximize_pool_given_max_test", secondary_c, m2, l2, h2)
            if candidate2 is not None and candidate2[px].sum() >= incumbent[px].sum():
                incumbent = candidate2
            secondary_optimal = res2 is not None and int(res2.status) == 0 and candidate2 is not None
            if secondary_optimal:
                status = "LEX_COUNTS_OPTIMAL"
                if deadline - time.monotonic() > 0.05:
                    npool = int(incumbent[px].sum())
                    fixed_pool = coo_matrix((np.ones(len(px)),
                                            (np.zeros(len(px), dtype=int), px)),
                                           shape=(1, len(b.names))).tocsc()
                    m3 = vstack([m2, fixed_pool], format="csc")
                    l3, h3 = np.r_[l2, npool], np.r_[h2, npool]
                    # Bounded [0,1) tie objective cannot change either fixed count.
                    records = [("test", r["item_id"], x) for r, x in zip(data["test"], tx)]
                    records += [("pool", r["item_id"], x) for r, x in zip(data["pool"], px)]
                    ranked = sorted(records, key=lambda r: (
                        hashlib.sha256(f"{TIE_SALT}|{r[0]}|{r[1]}".encode()).hexdigest(), r[:2]))
                    denom = len(ranked) * (len(ranked) + 1) / 2 + 1
                    tie_c = np.zeros(len(b.names))
                    for rank, (_, _, x) in enumerate(ranked, 1):
                        tie_c[x] = rank / denom
                    res3, candidate3 = stage("bounded_sha_rank_tie", tie_c, m3, l3, h3)
                    if candidate3 is not None and tie_c @ candidate3 <= tie_c @ incumbent + 1e-12:
                        incumbent = candidate3
                    if res3 is not None and int(res3.status) == 0 and candidate3 is not None:
                        status = "LEX_COUNTS_AND_TIE_OPTIMAL"

    selected = {"test": [], "pool": []}
    if incumbent is not None:
        selected = {"test": [r["item_id"] for r, x in zip(data["test"], tx) if incumbent[x]],
                    "pool": [r["item_id"] for r, x in zip(data["pool"], px) if incumbent[x]]}
    counts, checks, gate_results = counts_and_checks(data, selected, gates)
    if incumbent is not None and not all(checks.values()):
        raise AssertionError(("Independent selected-row checks failed", checks))
    required_pass = all(v for k, v in gate_results.items() if k != "test")
    if incumbent is not None and not required_pass:
        raise AssertionError(("Returned feasible witness violates fixed gates", gate_results))
    if incumbent is not None and primary_bound is not None and primary_bound < counts["test"]:
        raise AssertionError("Dual bound contradicts feasible test count")
    return {"mode": data["mode"], "status": status, "gates": gates, "suffix_source": data["suffix_source"],
            "coverage_pass": incumbent is not None and all(gate_results.values()) and all(checks.values()),
            "has_feasible_witness_for_non_test_gates": incumbent is not None,
            "primary_test_optimum_certified": primary_optimal,
            "primary_test_upper_bound": primary_bound,
            "test_gate_refuted_by_bound": primary_bound is not None and primary_bound < gates["test"],
            "pool_tiebreak_optimum_certified": secondary_optimal,
            "counts": counts, "gate_results": gate_results, "checks": checks,
            "selected_ids": selected, "stages": stages, "matrix_artifacts": matrix_artifacts,
            "solver": {"scipy_version": scipy.__version__, "threads": 1, "random_seed": 0,
                       "mip_rel_gap": 0.0, "time_limit_seconds": time_limit,
                       "variables": len(b.names), "constraints": matrix.shape[0],
                       "nonzeros": int(matrix.nnz), "binary_variables": True,
                       "input_order": "item_id ascending within original role",
                       "tie_rule": f"bounded SHA256 ranks of {TIE_SALT}|role|item_id; fixed test/pool optima"},
            "limits": ["Feasibility is conditional on the producer's alias/template closure and fixed independence components.",
                       "No alias-completeness or model-performance conclusion is inferred by this solver.",
                       "A time-limited incumbent is a witness, not a maximum; only a valid solver bound can refute the test gate."],
            "cpu_seconds": time.process_time() - began_cpu,
            "wall_seconds": time.monotonic() - began_wall}


def self_test():
    # Synthetic metadata only: independent brute-force enumeration validates every optimum.
    import itertools
    lowg = {"pool": 2, "names": 2, "prefixes": 1, "components": 1, "sources": 1, "test": 3}
    def tr(i, alias, block="b", template="held", capture=None, component="c", prefix="7", source="s"):
        return dict(item_id=i, capture=capture or i, alias=alias, template=template,
                    block=block, source=source, prefix=prefix, component=component)
    def pr(i, aliases=(), template="train", capture=None):
        return dict(item_id=i, capture=capture or i, aliases=list(aliases), template=template, source="s")
    cases = [
        {"test": [tr("t1", "a"), tr("t2", "b"), tr("t3", "a")],
         "pool": [pr("p1"), pr("p2"), pr("p3", ["a"])]},
        {"test": [tr("t1", "a"), tr("t2", "a")], "pool": [pr("p1"), pr("p2")]},
        {"test": [tr("t1", "a", capture="same"), tr("t2", "b"), tr("t3", "a", capture="same")],
         "pool": [pr("p1"), pr("p2"), pr("p3", template="held")]},
        {"test": [tr("t1", "a"), tr("t2", "b"), tr("t3", "c", block="b2", template="extra", component="c2", prefix="8")],
         "pool": [pr("p1"), pr("p2"), pr("p3")]},
        {"test": [tr("t1", "a"), tr("t2", "b")],
         "pool": [pr("p1", capture="t1"), pr("p2"), pr("p3")]},
        {"test": [tr("t1", "a"), tr("t2", "b"), tr("t3", "c", block="b2", component="c2", prefix="8"), tr("t4", "d", block="b2", component="c2", prefix="8")],
         "pool": [pr("p1", ["a"]), pr("p2", ["b"]), pr("p3", ["c"]), pr("p4", ["d"]) ]},
    ]
    results = []
    for index, case in enumerate(cases):
        case["mode"] = f"synthetic-{index}"
        best = None
        for bits in itertools.product((0, 1), repeat=len(case["test"]) + len(case["pool"])):
            nt = len(case["test"])
            ids = {"test": [r["item_id"] for r, bit in zip(case["test"], bits[:nt]) if bit],
                   "pool": [r["item_id"] for r, bit in zip(case["pool"], bits[nt:]) if bit]}
            counts, checks, gates = counts_and_checks(case, ids, lowg)
            if all(checks.values()) and all(v for k, v in gates.items() if k != "test"):
                candidate = counts["test"], counts["pool"]
                if best is None or candidate > best:
                    best = candidate
        answer = solve(case, time_limit=10, gates=lowg)
        if best is None:
            assert answer["status"] == "INFEASIBLE", answer
        else:
            assert (answer["counts"]["test"], answer["counts"]["pool"]) == best, (answer, best)
            assert answer["primary_test_optimum_certified"]
            assert answer["pool_tiebreak_optimum_certified"]
            assert answer["coverage_pass"] == (best[0] >= lowg["test"])
        results.append({"case": index, "brute_force_optimum": best, "status": answer["status"],
                        "test_count": answer["counts"]["test"], "pool_count": answer["counts"]["pool"]})
    # Independently exercise the distinct group/prefix/source gates, not just total rows.
    strict_gates = {"pool": 2, "names": 4, "prefixes": 2, "components": 2,
                    "sources": 2, "test": 4}
    separate = {"mode": "synthetic-multiple-gates", "test": [
        tr("t1", "a", source="s1"), tr("t2", "b", source="s1"),
        tr("t3", "c", block="b2", component="c2", prefix="8", source="s2"),
        tr("t4", "d", block="b2", component="c2", prefix="8", source="s2")],
        "pool": [pr("p1"), pr("p2")]}
    answer = solve(separate, time_limit=10, gates=strict_gates)
    assert answer["coverage_pass"], answer
    results.append({"case": "all_distinct_gates", "status": answer["status"]})
    for field, value in (("source", "s1"), ("component", "c"), ("prefix", "7")):
        collapsed = json.loads(json.dumps(separate))
        for row in collapsed["test"]:
            row[field] = value
        answer = solve(collapsed, time_limit=10, gates=strict_gates)
        assert answer["status"] == "INFEASIBLE", (field, answer)
        results.append({"case": f"collapsed_{field}_fails", "status": answer["status"]})
    # Distinct aliases cannot stand in for distinct token suffixes on explicit metadata.
    explicit = {"mode": "synthetic-suffix", "test": [tr("t1", "a"), tr("t2", "b")],
                "pool": [pr("p1"), pr("p2")]}
    for r in explicit["test"]:
        r["suffix"] = "[12,13]"
    answer = solve(explicit, time_limit=10, gates=lowg)
    assert answer["status"] == "INFEASIBLE", answer
    explicit["test"][1]["suffix"] = "[12,14]"
    answer = solve(explicit, time_limit=10, gates=lowg)
    assert answer["primary_test_optimum_certified"] and answer["counts"]["test"] == 2, answer
    results.append({"case": "explicit_token_suffix_gate", "status": "PASS"})
    # Validate explicit input rejection rather than silently merging invalid blocks.
    invalid = {"test": [tr("t1", "a"), tr("t2", "b", prefix="8")], "pool": []}
    try:
        normalize_input(invalid)
    except ValueError:
        pass
    else:
        raise AssertionError("Mixed-prefix block was accepted")
    print(json.dumps({"synthetic_self_test": "PASS", "cases": results}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--time-limit", type=float, default=180)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.input is None or args.out is None:
        parser.error("--input and --out are required except with --self-test")
    if not math.isfinite(args.time_limit) or args.time_limit <= 0:
        parser.error("--time-limit must be finite and positive")
    run_wall, run_cpu = time.monotonic(), time.process_time()
    result = solve(json.loads(args.input.read_text()), time_limit=args.time_limit,
                   matrix_artifact_prefix=args.out.with_suffix(""))
    result["input_sha256"] = digest(args.input)
    result["script_sha256"] = digest(__file__)
    result["runtime_boundary"] = {"metadata_only": True, "model_imports": False,
                                  "activation_payload_reads": 0, "gpu_hours": 0,
                                  "new_fits": 0, "downloads": 0}
    result["run_cpu_seconds_before_result_write"] = time.process_time() - run_cpu
    result["run_wall_seconds_before_result_write"] = time.monotonic() - run_wall
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: result[k] for k in ("mode", "status", "counts", "coverage_pass",
                      "primary_test_upper_bound", "cpu_seconds", "wall_seconds")}, indent=2))


if __name__ == "__main__":
    main()
