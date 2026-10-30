#!/usr/bin/env bash
# WS4 / R5X (queue row 3) — the dose extension on S1's 30 confident facts + S2's 10 small-margin facts.
# Pre-registered: BRIEF_R §"WS4 / R5X" (2026-10-19 17:03Z, before any R5X compute) plus the dated S2 correction.
# Guiv 2026-10-20: "Four segments. Keep R5X as four 90-min dose segments; each segment pulls its outputs before the
# next starts, so a pod loss costs at most one dose." BRIEF_R already prescribes climbing dose-by-dose across facts,
# so this is the brief's own operational shape, not a change to it.
#
#   bash ws4_r5x_job.sh a4     # precheck (the §4.5 gate), then alpha=4 for all 40 facts, then the audit
#   bash ws4_r5x_job.sh a8     # alpha=8    ... a16, a32 likewise
#   bash ws4_r5x_job.sh b      # the NLA read-back pass, once, after the doses
# Each segment exits on its own. Every segment prints the per-dose FLIP RATES under d_probe, which is the
# pre-registered escalation signal (alpha*_50 and alpha*_75), so the decision to climb is visible in the log.
#
# R5X writes its OWN rows under its own root, as BRIEF_R requires: nothing here appends to R5's files.
set -uo pipefail
SEG=${1:?segment: a4 | a8 | a16 | a32 | b | record2}
if [ -f /workspace/.env ]; then set -a; . /workspace/.env; set +a; fi
if [ -z "${HF_HOME:-}" ] && [ -d /workspace/hf_cache ]; then export HF_HOME=/workspace/hf_cache; fi
PY=${WS4_PY:-/workspace/venv/bin/python}
REPO=${WS4_REPO:-/workspace/activation-readers-swap}
# PyTorch documents CUBLAS_WORKSPACE_CONFIG=:4096:8 as required for deterministic cuBLAS GEMMs, and it must be set
# BEFORE CUDA initialises, so it belongs here and not in Python after import. Chat 6 noticed the record-only run
# logged `cublas_workspace_config: None`: the draws agreed anyway, but a determinism claim resting on observed
# agreement rather than the documented configuration is luck, not a guarantee.
export CUBLAS_WORKSPACE_CONFIG=${CUBLAS_WORKSPACE_CONFIG:-:4096:8}
LOGDIR=${WS4_LOGDIR:-/workspace/ws2_logs}
mkdir -p "$LOGDIR"
cd "$REPO"
echo $$ > "$LOGDIR/ws4_r5x.pid"
SEL=results/g_agreement/r/r5x_selection_merged.json
OUT=cache/g_agreement/r/r5x
DIRS=$OUT/directions
K=10                                   # BRIEF_R §4.5's K; R5X keeps §4.5's controls
echo "[$(date -u +%FT%TZ)] ws4 row 3 (R5X) segment=$SEG HF_HOME=${HF_HOME:-<hf default>}"

# Inputs, checked before any model load. The staging that built $SEL and $DIRS runs on the MAC
# (`steer --phase stage`), because it reads WS3's own cache; the pod only ever sees the result.
if [ "$SEG" = "record2" ]; then
  echo "[$(date -u +%FT%TZ)] record-only stage: skipping the 35-fact input check, it uses its own selection"
else
[ -f "$SEL" ] || { echo "[$(date -u +%FT%TZ)] MISSING INPUT: $SEL (run --phase stage on the Mac and rsync it)"; exit 2; }
# The expected count comes from the SELECTION, never a literal: Guiv's 2026-10-20 decision excluded two facts under
# the pre-registered zero-delta gate, so the set is 38, and a hard-coded 40 would have passed while the dir and the
# selection disagreed — or failed once the stale npz were removed.
N_WANT=$("$PY" -c "import json,sys;print(len(json.load(open(sys.argv[1]))['datasets']))" "$SEL")
N_NPZ=$(ls "$DIRS"/*.npz 2>/dev/null | wc -l | tr -d ' ')
[ "$N_NPZ" = "$N_WANT" ] || { echo "[$(date -u +%FT%TZ)] MISSING INPUT: $DIRS holds $N_NPZ npz, the selection names $N_WANT"; exit 2; }
echo "[$(date -u +%FT%TZ)] selection names $N_WANT facts; $DIRS holds $N_NPZ npz"
"$PY" - "$SEL" <<'PY' || exit 2
import json, sys
from pathlib import Path
sel = json.loads(Path(sys.argv[1]).read_text())["datasets"]
missing = [f"{ds}/chat_L{L}.npy" for ds in sel for L in (38, 42)
           if not (Path("cache/g_agreement/r/states") / ds / f"chat_L{L}.npy").exists()]
missing += [f"{ds}.npz" for ds in sel if not (Path("cache/g_agreement/r/r5x/directions") / f"{ds}.npz").exists()]
if missing:
    print(f"MISSING INPUT: {len(missing)} state/direction files, e.g. {missing[:4]}")
    raise SystemExit(2)
print(f"inputs present: {len(sel)} facts, states at L38+L42, {len(sel)} directions npz")
PY
fi

run() { "$PY" - "$@" <<'PY'
import sys
from pathlib import Path
from projects.g_agreement.core import config as C
from projects.g_agreement.r_bench import steer as ST
C.COMPUTE_LEDGER = Path('results/g_agreement/compute.R5X.jsonl')
ST.LOG = Path('results/g_agreement/r/log.R5X.md')
sys.exit(ST.main(sys.argv[1:]))
PY
}
fail=0
step() {
  local label=$1; shift
  echo "[$(date -u +%FT%TZ)] === $label ==="
  local t0=$SECONDS
  run "$@"
  local rc=$?
  echo "[$(date -u +%FT%TZ)] === $label rc=$rc wall=$((SECONDS - t0))s ==="
  [ $rc -ne 0 ] && fail=$rc
  return 0
}
flip_rates() {                         # the escalation signal, from the rows only: no model, no GPU
  "$PY" - "$1" <<'PY'
import collections, json, sys
from pathlib import Path
alpha = float(sys.argv[1])
rows = [json.loads(l) for l in Path("cache/g_agreement/r/r5x/steer.jsonl").read_text().splitlines() if l.strip()]
nat = {(r["dataset"], r["item_id"]): r["lo"] for r in rows if r["direction"] == "natural"}
probe = [r for r in rows if r["direction"].startswith("d_probe") and float(r["alpha"]) == alpha]
by = collections.defaultdict(list)
for r in probe:
    base = nat.get((r["dataset"], r["item_id"]))
    if base is not None:
        by[r["dataset"]].append((base > 0) != (r["lo"] > 0))
if not by:
    print(f"no d_probe rows at alpha={alpha} yet"); raise SystemExit(0)
rates = {ds: sum(v) / len(v) for ds, v in sorted(by.items())}
n50 = sum(1 for v in rates.values() if v >= 0.50)
n75 = sum(1 for v in rates.values() if v >= 0.75)
print(f"FLIP RATES under d_probe at alpha={alpha}: {len(rates)} facts | >=50%: {n50} | >=75%: {n75} "
      f"| median {sorted(rates.values())[len(rates)//2]:.3f}")
print("  per fact: " + ", ".join(f"{ds}={v:.2f}" for ds, v in list(rates.items())[:12]) + (" ..." if len(rates) > 12 else ""))
print(f"  §4.5's verdicts need >=75% to evaluate; alpha*_75 is reached for {n75} of {len(rates)} facts at this dose.")
PY
}

COMMON=(--selection "$SEL" --out-dir "$OUT" --dir-dir "$DIRS" --k-random "$K" --run-kind real --allow-unfrozen)
case "$SEG" in
  a4)
    step "R5X precheck (the §4.5 gate, deterministic + replicated)" --phase precheck "${COMMON[@]}"
    # Guiv asked for the old-check vs new-check pass counts, descriptively. The record carries both per fact:
    # `pass_single_draw_old_check` (one draw, the pre-2026-10-20 behaviour) and `pass` (deterministic, or the median
    # of three). Neither changes the 0.3 tolerance; this only says how often the noise mattered.
    "$PY" - <<'PY' || true
import json
from pathlib import Path
f = Path("results/g_agreement/r/r5_prechecks.json")
if not f.exists():
    print("no precheck record to summarise"); raise SystemExit(0)
recs = json.loads(f.read_text())
recs = recs if isinstance(recs, list) else [recs]
recs = [r for r in recs if r.get("checks", {}).get("zero_delta")]
zd = [(r["dataset"], r["checks"]["zero_delta"]) for r in recs]
new_pass = sum(1 for _, z in zd if z.get("pass") is True)
old_pass = sum(1 for _, z in zd if z.get("pass_single_draw_old_check") is True)
det = sum(1 for _, z in zd if "deterministic" in str(z.get("vs_collected_decided_by", "")))
print(f"ZERO-DELTA, descriptive: {len(zd)} facts | new check passes {new_pass} | old single-draw check passes {old_pass}")
print(f"  decided deterministically: {det}/{len(zd)}; by median of three: {len(zd) - det}/{len(zd)}")
flips = [(d, z.get("vs_collected_single_draw"), z.get("max_abs_dlo_vs_collected"))
         for d, z in zd if z.get("pass") is not z.get("pass_single_draw_old_check")]
print(f"  facts where the two checks disagree: {len(flips)}")
for d, o, n in flips[:10]:
    print(f"    {d}: single draw {o} -> decided {n}")
PY
    [ $fail -ne 0 ] && { echo "[$(date -u +%FT%TZ)] PRECHECK FAILED — not steering. fail=$fail"; exit 1; }
    step "R5X alpha=4"  --phase A --alphas 4  "${COMMON[@]}"
    step "audit alpha=4" --phase audit --alphas 4 "${COMMON[@]}"; flip_rates 4 ;;
  a8)
    step "R5X alpha=8"  --phase A --alphas 8  "${COMMON[@]}"
    step "audit alphas 4 8" --phase audit --alphas 4 8 "${COMMON[@]}"; flip_rates 8 ;;
  a16)
    step "R5X alpha=16" --phase A --alphas 16 "${COMMON[@]}"
    step "audit alphas 4 8 16" --phase audit --alphas 4 8 16 "${COMMON[@]}"; flip_rates 16 ;;
  a32)
    step "R5X alpha=32" --phase A --alphas 32 "${COMMON[@]}"
    step "audit alphas 4 8 16 32" --phase audit --alphas 4 8 16 32 "${COMMON[@]}"; flip_rates 32 ;;
  b)
    # The audit must check the doses that RAN, not the doses originally approved. Guiv truncated the grid to {4, 8}
    # on 2026-10-20 (BRIEF_R, dated), so auditing against 4 8 16 32 would report ~70 empty conditions as failures for
    # doses deliberately not run. Derived from the rows rather than hard-coded, so it stays right whatever ran.
    DOSES=$("$PY" - <<'PY'
import json
from pathlib import Path
f = Path("cache/g_agreement/r/r5x/steer.jsonl")
a = sorted({float(json.loads(l)["alpha"]) for l in f.read_text().splitlines()
            if l.strip() and json.loads(l).get("direction") != "natural"}) if f.exists() else []
print(" ".join(f"{x:g}" for x in a))
PY
)
    [ -n "$DOSES" ] || { echo "[$(date -u +%FT%TZ)] no doses found in steer.jsonl; nothing to score"; exit 2; }
    echo "[$(date -u +%FT%TZ)] doses present in the rows: $DOSES"
    step "R5X phase B (NLA)" --phase B "${COMMON[@]}"
    step "audit the doses that ran ($DOSES)" --phase audit --alphas $DOSES "${COMMON[@]}" ;;
  record2)
    # Guiv 2026-10-20: "first run the deterministic precheck on Italy and code C for the record only, not for
    # re-admission." Those two were excluded on the 2026-10-19 23:44Z draw, which later runs showed to be the noisy
    # one, so their DETERMINISTIC values were never measured. This closes that gap in the record and nothing else:
    # its own selection, its own precheck file, its own output root, and the directions read from excluded_by_gate/
    # so the 35-fact count check cannot be confused. It writes NO steering rows and never touches the run's record.
    REC_SEL=results/g_agreement/r/r5x_selection_record_italy_codeC.json
    [ -f "$REC_SEL" ] || { echo "[$(date -u +%FT%TZ)] MISSING INPUT: $REC_SEL"; exit 2; }
    for d in 125_world_country_Italy 158_code_C; do
      [ -f "$OUT/excluded_by_gate/$d.npz" ] || { echo "[$(date -u +%FT%TZ)] MISSING INPUT: $OUT/excluded_by_gate/$d.npz"; exit 2; }
    done
    step "record-only precheck: Italy + code_C (NOT for re-admission)" \
         --phase precheck --selection "$REC_SEL" --out-dir "$OUT/record_only" \
         --dir-dir "$OUT/excluded_by_gate" \
         --precheck-out results/g_agreement/r/r5_prechecks.record_italy_codeC.json \
         --k-random "$K" --run-kind real --allow-unfrozen
    echo "[$(date -u +%FT%TZ)] record-only precheck written to results/g_agreement/r/r5_prechecks.record_italy_codeC.json"
    echo "[$(date -u +%FT%TZ)] these two facts REMAIN EXCLUDED whatever it says (Guiv, 2026-10-20)" ;;
  *) echo "unknown segment $SEG"; exit 2 ;;
esac
echo "[$(date -u +%FT%TZ)] SEGMENT $SEG COMPLETE fail=$fail"
echo "[$(date -u +%FT%TZ)] operator: pull $OUT/ plus results/g_agreement/{r/log.R5X.md,compute.R5X.jsonl} BEFORE the next segment"
# GUARDS.md rule 4 (Guiv, 2026-10-20): a segment's end hands the pod back warm; it never ends the pod itself.
echo "[$(date -u +%FT%TZ)] then VERIFY that pull and HOLD the pod warm under the reservation flag, guards live."
echo "[$(date -u +%FT%TZ)] No stop or terminate from this chain, and an empty queue does not clear one: only the"
echo "[$(date -u +%FT%TZ)] integrator's HANDOFF.md line saying no queued job fits this pod does (rule 4)."
exit $(( fail != 0 ))
