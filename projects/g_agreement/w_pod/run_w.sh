#!/usr/bin/env bash
# Phase W pod session (PREREG_WV.md "Pod session"; brief "Operating constraints"). One detached tmux session:
#   tmux new -d -s w "bash /workspace/activation-readers/projects/g_agreement/w_pod/run_w.sh"
# Phase A: s1 -> s2 -> s3 A (+v6) -> s3v1 A (if results/g_agreement/v/v12_pod_requests.json exists) -> s4 A
# Phase B: s3 B -> s3v1 B -> s4 B.   S5: STATUS, RSYNC_READY marker, stop the pod (RunPod REST, $RUNPOD_API_KEY from /workspace/.env)
# or write results/g_agreement/w/STOP_REQUESTED. Each stage: run; on failure retry once; on a second failure the traceback goes to
# STATUS.md, the pod is stopped, the script exits. Before each stage the elapsed pod minutes are checked; >= 150 -> skip to S5.
# Every stage finds its DONE marker on a rerun and is skipped by its own CLI. All stdout -> results/g_agreement/w/w_collection.log.
# Env knobs: W_BUDGET_MIN (150), W_SKIP_STOP=1 (never call the RunPod API), W_DRY_RUN=1 (print the stage commands, run nothing),
#            W_PY (python), W_REPO (repo root; default: the directory two levels above this script's project).
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${W_REPO:-$(cd "$HERE/../../.." && pwd)}"
cd "$REPO"
[ -f /workspace/.env ] && source /workspace/.env >/dev/null 2>&1 || true
export PYTHONPATH="$REPO:$REPO/third_party/workspace-bench/src:$REPO/third_party/jacobian-lens:$REPO/third_party/EasyNLA:${PYTHONPATH:-}"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
PY="${W_PY:-$( [ -x "$REPO/.venv/bin/python" ] && echo "$REPO/.venv/bin/python" || command -v python3 || echo python)}"
GM=projects.g_agreement.w_pod
OUT="$REPO/results/g_agreement/w"
LOG="$OUT/w_collection.log"
BUDGET="${W_BUDGET_MIN:-150}"
mkdir -p "$OUT"
exec > >(tee -a "$LOG") 2>&1
echo "[run_w] $(date -u +%FT%TZ) start; repo $REPO; python $PY; budget ${BUDGET} min"

ts() { date -u +%FT%TZ; }
status() { $PY -m $GM.status "$@" || true; }

stop_pod() {
  # S5: stop the pod through the RunPod REST API (POST /v1/pods/{id}/stop) when the key and the pod id are known; else leave a marker.
  echo "[run_w] $(ts) stop_pod requested"
  touch "$OUT/RSYNC_READY"
  if [ "${W_SKIP_STOP:-0}" = "1" ]; then echo "[run_w] W_SKIP_STOP=1: not stopping"; return 0; fi
  local pid="${RUNPOD_POD_ID:-}"
  if [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "$pid" ]; then
    local code
    code=$(curl -s -o "$OUT/stop_response.json" -w '%{http_code}' -X POST "https://rest.runpod.io/v1/pods/$pid/stop" -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" || echo 000)
    echo "[run_w] $(ts) RunPod stop pod $pid -> HTTP $code"
    if [ "$code" != "200" ] && [ "$code" != "201" ] && [ "$code" != "202" ] && [ "$code" != "204" ]; then
      echo "$(ts) stop API returned HTTP $code; stop the pod manually" > "$OUT/STOP_REQUESTED"
    fi
  else
    echo "$(ts) RUNPOD_API_KEY or RUNPOD_POD_ID unset; stop the pod manually" > "$OUT/STOP_REQUESTED"
    echo "[run_w] wrote $OUT/STOP_REQUESTED"
  fi
}

finish_s5() {
  local why="$1"
  echo "[run_w] $(ts) S5 ($why)"
  status --stage "S5 ($why)" --started "$(ts)" --finished "$(ts)" --keep-errors --notes "rsync results/g_agreement/w/**/*.{md,csv,json,png} and cache/g_agreement/w/*.jsonl"
  stop_pod
  echo "[run_w] $(ts) done"
}

budget_ok() {
  # exit 0 continue; 3 = skip to S5
  $PY -m $GM.status --check-budget --limit "$BUDGET"
  local rc=$?
  if [ $rc -eq 3 ]; then echo "[run_w] $(ts) pod budget reached (>= ${BUDGET} min): skipping to S5"; return 1; fi
  return 0
}

run_stage() {
  # run_stage <label> <python args...>: two attempts; the second failure is fatal (STATUS, stop pod, exit 2)
  local label="$1"; shift
  if ! budget_ok; then finish_s5 "budget"; exit 0; fi
  local started; started="$(ts)"
  status --stage "$label" --started "$started" --keep-errors
  echo "[run_w] $(ts) >>> $label: $PY -m $GM.$*"
  if [ "${W_DRY_RUN:-0}" = "1" ]; then return 0; fi
  local attempt rc tb="$OUT/traceback_$(echo "$label" | tr ' /' '__').txt"
  for attempt in 1 2; do
    $PY -m $GM."$@" 2> >(tee "$tb" >&2)
    rc=$?
    if [ $rc -eq 0 ]; then
      status --stage "$label" --started "$started" --finished "$(ts)" --keep-errors
      echo "[run_w] $(ts) <<< $label ok (attempt $attempt)"
      return 0
    fi
    echo "[run_w] $(ts) !!! $label failed (rc $rc, attempt $attempt)"
    [ $attempt -eq 1 ] && sleep 20
  done
  status --append-error "$label" "$tb"
  echo "[run_w] $(ts) $label failed twice; stopping the pipeline"
  finish_s5 "failure in $label"
  exit 2
}

# ---------------------------------------------------------------- go
$PY -m $GM.status --mark-pod-start
status --stage "S0 start" --started "$(ts)" --notes "phase A: s1 s2 s3A(+v6) s3v1A s4A; phase B: s3B s3v1B s4B; S5 stop"

run_stage "S1 capture"            s1_capture --phase A
run_stage "S2 steering matrix"    s2_steer --phase A --family all --alphas 0.5,1.0 --k-random 10 --n-states 64
run_stage "S3 reader scoring A"   s3_score --phase A --readers jlens,olens,skip_a,probe --v6
if [ -f "$REPO/results/g_agreement/v/v12_pod_requests.json" ]; then
  run_stage "S3v1 requests A"     s3v1_requests --phase A
else
  echo "[run_w] $(ts) no v12_pod_requests.json: S3v1 skipped"
fi
run_stage "S4 consistency A"      s4_consistency --phase A
run_stage "S3 reader scoring B"   s3_score --phase B --readers nla
if [ -f "$REPO/results/g_agreement/v/v12_pod_requests.json" ]; then
  run_stage "S3v1 requests B"     s3v1_requests --phase B
fi
run_stage "S4 consistency B"      s4_consistency --phase B
finish_s5 "complete"
exit 0
