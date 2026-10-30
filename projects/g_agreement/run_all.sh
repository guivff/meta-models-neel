#!/usr/bin/env bash
# G1–G4 runner: each stage is independent and idempotent; run them one at a time or all in order.
#   bash projects/g_agreement/run_all.sh <stage> [extra args]
# Stages (GPU = needs the pod; CPU = runs anywhere):
#   r0            GPU  reproduce the setup (K0 layer check, OLens/NLA positive controls, inputs dump, bench @L42)
#   g1-dev        GPU  G1 on the 8 dev states incl. controls (off-grid OLens, state-free, J-lens null)   [unfrozen]
#   freeze        CPU  write manifest/frozen_config.json (after dev checks, before any test collection)
#   g1            GPU  G1 on the 32 test states (phase A target/J-lens/OLens, phase B NLA) + controls
#   g3-collect    GPU  prompt-only baseline (dev + test); state-free rows are collected by g1 / g1-dev
#   g4-collect    GPU  two extra OLens (phase A) and NLA (phase B) samples on the 8 preselected states
#   claims        CPU  generations -> claims (rule-v1), shuffled table, blind sheet
#   g1-analyze | g2-analyze | g3-analyze | g4-analyze   CPU  one figure + csv + summary each
#   analyze       CPU  all four (+ consensus)
#   x2            GPU  X2 causal planting: full L38/L42 captures, ~74 edited decodes per pair + read-back, LO (phase A J-lens/OLens, phase B NLA)
#   x2-analyze    CPU  E4–E7 + K5, fig_main (S2 dose-response) + fig_flips (needs manifest/frozen_config_x.json or ANALYZE_FLAGS=--allow-unfrozen)
#   x3            GPU  X3 floor sets: selection decodes (target + prompt-only), capture, LO (phase A J-lens/OLens, phase B NLA)
#   x3-analyze    CPU  E8/E9 + fig_main (needs manifest/frozen_config_x.json or ANALYZE_FLAGS=--allow-unfrozen)
# Phase Y (BRIEF_Y.md):
#   y2            GPU  Y2 identity-free nulls + J-space split at S2: J-space basis (L38, r*=384), ~4,956 edited decodes over the 64 X2 pairs
#                      (name_only, name_removed, other_pair, Δ_J/Δ_⊥, 3 random controls; α 0.5/0.75/1), LO (phase A J-lens/OLens, phase B NLA)
#   y2-analyze    CPU  E12/E13 + decisions, fig_main (needs manifest/frozen_config_x.json or ANALYZE_FLAGS=--allow-unfrozen; reads the X2 files too)
#   y1-select     GPU  Y1: build dataset/items_y1_choice.json if absent (900 choice items, seed 20261009), target greedy + self-guess on the
#                      X3+Y1 choice union (X3 rows reused), dataset/items_y1_selected.json (X3 puzzles + new DISAGREE / AGREE_CONTROL)
#   y1-capture    GPU  Y1: block outputs L42..62 step 2 x {last..last-11, candA, candB} per selected item + logit-lens margins (phase A)
#   y1-analyze    CPU  Y1: E10 probe sweep, S*, K7, logit-lens curve, fig_main (ANALYZE_FLAGS=--allow-unfrozen for a dev run; JOBS=8 parallel cells)
#   y1-reread     GPU  Y1: E11 native LO at S* (SITE=L:P, default from results/g_agreement/y1/summary.json): phase A J-lens/OLens, phase B NLA
#   y3            GPU  Y3 new reader families (phase A only): skip-lens arms A/D (LoRA on the target) + R-lens + Qwen-Scope L42 SAE on the X1/X2/X3
#                      states -> cache/g_agreement/y/y3_{x1,x2,x3}_lo.jsonl, results/g_agreement/y3/sae_fve.json (Y3_READERS=skip_a,skip_d,sae,rlens; Y3_STAGE=all)
#   y3-analyze    CPU  Y3: E14 entry gate, E15 (X2 follow at alpha*, X3 E8 raw + symbol-bias-corrected), SAE table, fig_main; adds the gated readers to
#                      x/blindness_map.csv (needs manifest/frozen_config_x.json or ANALYZE_FLAGS=--allow-unfrozen, which never rewrites the map)
# Phase Z (BRIEF_Z.md):
#   z4            GPU  Z4 position dissection at L38 on the 64 X2 pairs: phase A stage single (≤ 15 positions/prompt × α 0.75/1 + 64 random-direction
#                      controls), then stage dependent (all_except / restore for the top-5 single positions per family), J-lens/OLens LO; phase B NLA LO.
#                      Prints the planned decodes and refuses above 6,500 (≈ 5,200 expected). Z4_STAGE=single|dependent|all (default all, one model load).
#   z4-analyze    CPU  per-position flip / Δ_model tables, the pre-registered single/redundant/joint classification, Z1-style rerun, fig_main
#                      (needs manifest/frozen_config_z.json or ANALYZE_FLAGS=--allow-unfrozen; reads the X2 and Y2 files too)
#   z4b           GPU  Z4b ownership follow-up (32 ownership X2 pairs × 2 sources, α 1): phase A L38 role spans (question_only, template_only, last3,
#                      question halves) + names_objects_only at L20/L28 (new full captures), 448 decodes (refuses above 600), J-lens/OLens LO;
#                      phase B the NLA reproduction gate on the 280 X1 test states through the Z4 phase-B scoring path → results/g_agreement/z4b/nla_gate.json
#   z4b-analyze   CPU  flip / Δ_model / reader f_r per arm × layer, the pre-registered decision text, fig_main (+ the NLA gate summary)
#                      (needs manifest/frozen_config_z.json or ANALYZE_FLAGS=--allow-unfrozen; reads the X2 and Y2 files too)
# Dev-only analysis: add ANALYZE_FLAGS="--allow-unfrozen --split dev" (writes to results/g_agreement/<module>/dev/).
# Phase X (BRIEF_X.md):
#   x-dataset     CPU  build dataset/items_x.json and dataset/items_x3_candidates.json (seed 20261008)
#   freeze-x      CPU  write manifest/frozen_config_x.json (items_x / items_x3 / code shas) before X test collection
#   x1-dev        GPU  X1 smoke on the dev pairs (phase A then B)                                         [unfrozen]
#   x1            GPU  X1 states + native LO on the test pairs (phase A target/J-lens/OLens, phase B NLA)
#   x1-analyze    CPU  E1 paired win, E2 LOO probe + two-half ceiling, E3 mean-state prior -> results/g_agreement/x1/
# Phase W (PREREG_WV.md; code in w_pod/, chain run_w.sh):
#   w-s1          GPU  S1 capture of the W bank (+ V7, mapping-8): layers 20/28/38/42/48/52 all positions, greedy answer, candidate log-probs
#   w-s2          GPU  S2 steering matrix (ownership/mapping at L38, errors at L48; d_cm/d_pw/d_J/d_res/full/random x10, alpha 0.5/1; <= 4,500 decodes)
#   w-s3          GPU  S3 reader scoring: phase A J-lens/Oracle/skip-lens A/probe (+ V6 multi-marker Oracle, + S3v1 requests if present), phase B NLA
#   w-s4          GPU  S4 consistency null: 8 Oracle (phase A) + 8 NLA (phase B) samples on 100 error + 50 counts states, 50 random vectors
#   w-s5          CPU  STATUS.md + RSYNC_READY (+ STOP_REQUESTED marker; the pod is stopped by run_w.sh, not here)
#   w-pipeline    GPU  the whole chain detached: tmux new -d -s w "bash projects/g_agreement/w_pod/run_w.sh"  (W_DRY_RUN=1 prints the commands)
#   w-test        CPU  pytest projects/g_agreement/tests/test_w_pod.py
set -euo pipefail
cd "$(dirname "$0")/../.."
export PYTHONPATH="$PWD:$PWD/third_party/workspace-bench/src:$PWD/third_party/jacobian-lens:$PWD/third_party/EasyNLA:${PYTHONPATH:-}"
PY=${PY:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || command -v python3 || echo python)}
stage=${1:-help}; shift || true
G=projects/g_agreement
GM=projects.g_agreement
case "$stage" in
  r0)
    $PY -m $GM.repro.r0_checks --phase A --checks lens_meta,k0,olens,inputs "$@"
    $PY -m $GM.repro.r0_checks --phase A --checks bench_capture,bench_olens --family "${BENCH_FAMILY:-typo_mt}" --batch "${BENCH_BATCH:-1}" --limit "${BENCH_LIMIT:-100}"
    $PY -m $GM.repro.r0_checks --phase B --checks nla,inputs
    $PY -m $GM.repro.r0_checks --phase B --checks bench_nla --family "${BENCH_FAMILY:-typo_mt}" --batch "${BENCH_BATCH:-1}" --limit "${BENCH_LIMIT:-100}" ;;
  g1-dev)
    $PY -m $GM.g1_agreement.collect --phase A --items dev --offgrid --state-free --jlens-null --allow-unfrozen "$@"
    $PY -m $GM.g1_agreement.collect --phase B --items dev --state-free --allow-unfrozen ;;
  freeze)
    $PY -m $GM.core.config --freeze "$@"; $PY -m $GM.core.config --status ;;
  g1)
    $PY -m $GM.core.config --status
    $PY -m $GM.g1_agreement.collect --phase A --items test --state-free --jlens-null "$@"
    $PY -m $GM.g1_agreement.collect --phase B --items test --state-free ;;
  g3-collect)
    $PY -m $GM.g3_activation_dependence.collect_prompt_only --items dev --allow-unfrozen "$@"
    $PY -m $GM.g3_activation_dependence.collect_prompt_only --items test ;;
  g4-collect)
    $PY -m $GM.g4_repeats.collect --phase A "$@"
    $PY -m $GM.g4_repeats.collect --phase B ;;
  claims)
    $PY -m $GM.core.make_claims --module g1 --sheet
    $PY -m $GM.core.make_claims --module g3 --shuffled --split "${SPLIT:-test}"
    $PY -m $GM.core.make_claims --module g4 ;;
  g1-analyze) $PY $G/g1_agreement/analyze.py ${ANALYZE_FLAGS:-} "$@"; $PY $G/g1_agreement/consensus.py ${ANALYZE_FLAGS:-} ;;
  g2-analyze) $PY $G/g2_relations/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  g3-analyze) $PY $G/g3_activation_dependence/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  g4-analyze) $PY $G/g4_repeats/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  analyze) for m in g1 g2 g3 g4; do bash "$0" "$m-analyze"; done ;;
  x2)
    $PY -m $GM.x2_causal.collect --phase A "$@"
    $PY -m $GM.x2_causal.collect --phase B "$@" ;;
  x2-analyze) $PY $G/x2_causal/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  x3)
    $PY -m $GM.x3_floor.collect --phase A "$@"
    $PY -m $GM.x3_floor.collect --phase B ;;
  x3-analyze) $PY $G/x3_floor/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  x-dataset)
    $PY $G/dataset/build_dataset_x.py --print "$@"
    $PY $G/dataset/build_x3.py ;;
  freeze-x) $PY -m $GM.x1_bank.collect --freeze-x "$@" ;;
  x1-dev)
    $PY -m $GM.x1_bank.collect --phase A --split dev --allow-unfrozen "$@"
    $PY -m $GM.x1_bank.collect --phase B --split dev --allow-unfrozen ;;
  x1)
    $PY -m $GM.x1_bank.collect --phase A "$@"
    $PY -m $GM.x1_bank.collect --phase B ;;
  x1-analyze) $PY $G/x1_bank/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  y2)
    $PY -m $GM.y2_identity.collect --phase A "$@"
    $PY -m $GM.y2_identity.collect --phase B "$@" ;;
  y2-analyze) $PY $G/y2_identity/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  y1-select)
    [ -f $G/dataset/items_y1_choice.json ] || $PY $G/dataset/build_y1_choice.py
    $PY -m $GM.y1_site.collect --phase A --stage select "$@" ;;
  y1-capture) $PY -m $GM.y1_site.collect --phase A --stage capture "$@" ;;
  y1-analyze) $PY $G/y1_site/analyze.py --jobs "${JOBS:-8}" ${ANALYZE_FLAGS:-} "$@" ;;
  y1-reread)
    SITE=${SITE:-$($PY -c "import json,sys; print(json.load(open('results/g_agreement/y1/summary.json'))['S_star']['site'])")}
    $PY -m $GM.y1_site.collect --phase A --stage reread --site "$SITE" "$@"
    $PY -m $GM.y1_site.collect --phase B --stage reread --site "$SITE" "$@"
    $PY $G/y1_site/analyze.py --reread-only --site "$SITE" ${ANALYZE_FLAGS:-} ;;
  y3) $PY -m $GM.y3_readers.collect --phase A --readers "${Y3_READERS:-skip_a,skip_d,sae,rlens}" --stage "${Y3_STAGE:-all}" "$@" ;;
  y3-analyze) $PY $G/y3_readers/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  z4)
    $PY -m $GM.z4_positions.collect --phase A --stage "${Z4_STAGE:-all}" "$@"
    $PY -m $GM.z4_positions.collect --phase B "$@" ;;
  z4-analyze) $PY $G/z4_positions/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  z4b)
    $PY -m $GM.z4b_followup.collect --phase A "$@"
    $PY -m $GM.z4b_followup.collect --phase B --nla-x1-check "$@" ;;
  z4b-analyze) $PY $G/z4b_followup/analyze.py ${ANALYZE_FLAGS:-} "$@" ;;
  w-s1) $PY -m $GM.w_pod.s1_capture --phase A "$@" ;;
  w-s2) $PY -m $GM.w_pod.s2_steer --phase A --family "${W_FAMILY:-all}" "$@" ;;
  w-s3)
    $PY -m $GM.w_pod.s3_score --phase A --readers "${W_READERS_A:-jlens,olens,skip_a,probe}" --v6 "$@"
    [ -f results/g_agreement/v/v12_pod_requests.json ] && $PY -m $GM.w_pod.s3v1_requests --phase A
    $PY -m $GM.w_pod.s3_score --phase B --readers nla
    [ -f results/g_agreement/v/v12_pod_requests.json ] && $PY -m $GM.w_pod.s3v1_requests --phase B || true ;;
  w-s4)
    $PY -m $GM.w_pod.s4_consistency --phase A "$@"
    $PY -m $GM.w_pod.s4_consistency --phase B "$@" ;;
  w-s5)
    $PY -m $GM.w_pod.status --stage "S5 (manual)" --started "$(date -u +%FT%TZ)" --finished "$(date -u +%FT%TZ)" --keep-errors
    touch results/g_agreement/w/RSYNC_READY; echo "$(date -u +%FT%TZ) manual S5" > results/g_agreement/w/STOP_REQUESTED ;;
  w-pipeline) tmux new -d -s "${W_TMUX:-w}" "bash $G/w_pod/run_w.sh"; echo "started tmux session ${W_TMUX:-w}; tail -f results/g_agreement/w/w_collection.log" ;;
  w-test) $PY -m pytest $G/tests/test_w_pod.py -q ;;
  test) $PY -m pytest $G/tests -q ;;
  *) sed -n 2,40p "$0" ;;
esac
