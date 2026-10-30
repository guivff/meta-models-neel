"""Pre-launch check: load the REAL Track B directions through the S2 loader and assert what S2 relies on.

    python -m projects.g_agreement.w_pod.check_directions [--families ownership,mapping,errors] [--n 3]

Per family: index resolves every pair file; positions are ints inside the render (ownership/mapping: n_tokens; errors: [-1]); every
direction in {d_cm, d_pw, d_J, d_res, full} comes through as unit rows [P, d]; ‖Δ(pos)‖ equals the file's delta_norm and the index's;
the first random direction reproduces w_directions.directions.random_directions (when importable); the shared.pt probe loads with a
held-out fold for every pair; the S2 entry vectors build for one state (X2 full capture / Y1 capture present)."""

from __future__ import annotations

import argparse
import json
import sys

from . import common as W
from . import s2_steer as S2


def check_family(family: str, n: int = 3) -> dict:
    import torch

    idx = W.directions_index(family)
    rep = {"family": family, "layer": idx["layer"], "site": idx["site"], "n_pairs": len(idx["files"]), "shared": str(idx["shared_path"]), "checked": [], "problems": []}
    missing = [k for k, f in idx["files"].items() if not f.exists()]
    if missing:
        rep["problems"].append(f"{len(missing)} files missing e.g. {missing[:3]}")
    try:
        from projects.g_agreement.w_directions.directions import random_directions as rd_ref
    except Exception:
        rd_ref = None
    for pid in list(idx["files"])[:n]:
        f = W.load_direction_file(idx["files"][pid])
        e = idx["entries"].get(pid, {})
        P, d = f["n_positions"], f["d"]
        item = {"pair_id": pid, "P": P, "d": d, "positions": f["positions"][:6], "norm": [round(float(x), 3) for x in f["norm"][:4]], "names": f["names_in_file"], "random_seed": f["random_seed"], "fold": f["fold"], "sign": f["sign"]}
        for name in W.S2_DIRECTIONS:
            u = f[name]
            assert u.shape == (P, d), (pid, name, tuple(u.shape))
            assert torch.allclose(u.norm(dim=1), torch.ones(P), atol=1e-4), (pid, name, "not unit")
        assert torch.allclose(f["norm"], f["delta"].norm(dim=1), rtol=1e-3, atol=1e-3), (pid, "delta_norm != ||delta||")
        if e.get("delta_norm") is not None:
            assert torch.allclose(f["norm"], torch.tensor([float(x) for x in e["delta_norm"]]), rtol=1e-3, atol=1e-2), (pid, "index delta_norm != file")
        if e.get("positions") is not None:
            assert [int(x) for x in e["positions"]] == f["positions"], (pid, "index positions != file")
        nt = int(e.get("n_tokens", -1))
        if nt > 0:
            assert all(0 <= p < nt for p in f["positions"]), (pid, "positions outside the render")
        else:
            assert f["positions"] == [-1] and P == 1, (pid, "errors must be the single last-token position")
        # the full swap direction equals unit(delta); cos of each component to it recorded
        assert torch.allclose(f["full"], f["delta"] / f["delta"].norm(dim=1, keepdim=True), atol=1e-5)
        item["cos_to_delta"] = {name: round(float((f[name] * f["full"]).sum(1).mean()), 3) for name in ("d_cm", "d_pw", "d_J", "d_res")}
        r0 = W.random_unit_directions(pid, 0, P, d, seed=f["random_seed"])
        assert torch.allclose(r0.norm(dim=1), torch.ones(P), atol=1e-5)
        if rd_ref is not None and f["random_seed"] is not None:
            ref = rd_ref(int(f["random_seed"]), P, d, 1)[0]
            assert torch.allclose(ref, r0, atol=1e-6), (pid, "random recipe mismatch")
            item["random_matches_track_b"] = True
        rep["checked"].append(item)
    pr = W.load_probe_shared(idx["shared_path"], layer=idx["layer"], site=idx["site"])
    if pr is None:
        rep["problems"].append("no probe in shared.pt")
    else:
        held = sum(1 for pid in idx["files"] if pid in pr["fold_of_pair"])
        rep["probe"] = {"kind": pr["kind"], "n_folds": pr["n_folds"], "binary": pr["binary"], "classes": pr["classes"], "label": pr["label"], "held_out_for": f"{held}/{len(idx['files'])}",
                        "w_shape": list(next(iter(pr["folds"].values())).shape)}
        if held != len(idx["files"]):
            rep["problems"].append(f"{len(idx['files']) - held} pairs have no held-out fold")
    # one S2 state end to end (tensor-free) when the captures exist
    try:
        _, states = S2.load_states(family, n_states=1)
        if states:
            s = states[0]
            cap = S2.base_capture(s, idx["layer"])
            T = cap["n_tokens"]
            f = W.load_direction_file(s["direction_file"])
            tab = S2.condition_table([s], k_random=1)
            vecs = {e["direction"]: S2.entry_vectors(e, f, cap, T) for e in tab if e["alpha"] in (0.0, 1.0)}
            rep["s2_state"] = {"state": f"{s['pair_id']}|{s['source']}", "T": T, "positions": vecs["full"]["positions"][:6], "dose_full": round(vecs["full"]["dose_abs"], 3),
                               "dose_d_cm": round(vecs["d_cm"]["dose_abs"], 3), "dose_random": round(vecs["random"]["dose_abs"], 3), "cand": [s["cand_A"], s["cand_B"]]}
            assert abs(vecs["full"]["dose_abs"] - float(f["norm"].norm())) < 1e-2 and abs(vecs["d_cm"]["dose_abs"] - float(f["norm"].norm())) < 1e-2
            if cap["h"] is not None and s["source"] == "A":
                other = S2.base_capture(dict(s, cap_path=str(s["cap_path"]).replace(f"{s['pair_id']}A", f"{s['pair_id']}B")), idx["layer"])["h"]
                err = float((vecs["full"]["vector"] - other[vecs["full"]["positions"]]).norm() / other[vecs["full"]["positions"]].norm())
                rep["s2_state"]["full_alpha1_lands_on_hB_rel_err"] = round(err, 4)
                assert err < 0.05, "full swap at alpha 1 does not land on h_B"
    except FileNotFoundError as exc:
        rep["s2_state"] = f"captures not on this machine: {exc}"
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--families", default=",".join(W.S2_FAMILIES))
    ap.add_argument("--n", type=int, default=3)
    a = ap.parse_args(argv)
    ok = True
    for fam in (f.strip() for f in a.families.split(",") if f.strip()):
        rep = check_family(fam, a.n)
        ok &= not rep["problems"]
        print(json.dumps(rep, indent=1, default=str))
    print("DIRECTIONS CHECK", "OK" if ok else "PROBLEMS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
