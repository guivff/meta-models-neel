#!/usr/bin/env bash
# V7 confirmatory pod session (2026-10-12; design banks/w/items_v7_confirmatory_design.md, PREREG_WV.md "V7 confirmatory").
#   tmux new -d -s v7c "bash /workspace/activation-readers/projects/g_agreement/w_pod/run_v7c.sh"
# S1 capture of the 192 items_v7c.json items (resumable; the pilot/W items are already captured) -> S3 phase A on the V7 S1 states only
# (jlens/olens at 42 + 38, skip_a at 42, probe held-out) -> S3 phase B (NLA at 42 on V7 pilot + confirmatory) -> S5 (stop the pod).
# Budget 60 min from this script's start; two failures in a stage -> stop. All stdout -> results/g_agreement/w/v7c_collection.log.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${W_REPO:-$(cd "$HERE/../../.." && pwd)}"
cd "$REPO"
[ -f /workspace/.env ] && source /workspace/.env >/dev/null 2>&1 || true
export PYTHONPATH="$REPO:$REPO/third_party/workspace-bench/src:$REPO/third_party/jacobian-lens:$REPO/third_party/EasyNLA:${PYTHONPATH:-}"
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4 TOKENIZERS_PARALLELISM=false
export W_ITEMS_V7_EXTRA="$REPO/projects/g_agreement/banks/w/items_v7c.json"
export W_S1_FAMILIES=v7
PY="${W_PY:-$( [ -x "$REPO/.venv/bin/python" ] && echo "$REPO/.venv/bin/python" || command -v python3 || echo python)}"
GM=projects.g_agreement.w_pod
OUT="$REPO/results/g_agreement/w"
LOG="$OUT/v7c_collection.log"
BUDGET="${W_BUDGET_MIN:-60}"
T0=$(date +%s)
mkdir -p "$OUT"
exec > >(tee -a "$LOG") 2>&1
ts() { date -u +%FT%TZ; }
mins() { echo $(( ($(date +%s) - T0) / 60 )); }
echo "[v7c] $(ts) start; repo $REPO; python $PY; budget ${BUDGET} min"
stop_pod() {
  touch "$OUT/V7C_RSYNC_READY"
  if [ "${W_SKIP_STOP:-0}" = "1" ]; then echo "[v7c] W_SKIP_STOP=1: not stopping"; return 0; fi
  local pid="${RUNPOD_POD_ID:-}"
  if [ -n "${RUNPOD_API_KEY:-}" ] && [ -n "$pid" ]; then
    local code; code=$(curl -s -o "$OUT/v7c_stop_response.json" -w '%{http_code}' -X POST "https://rest.runpod.io/v1/pods/$pid/stop" -H "Authorization: Bearer $RUNPOD_API_KEY" -H "Content-Type: application/json" || echo 000)
    echo "[v7c] $(ts) RunPod stop pod $pid -> HTTP $code"
  else
    echo "$(ts) RUNPOD_API_KEY or RUNPOD_POD_ID unset; stop the pod manually" > "$OUT/V7C_STOP_REQUESTED"
  fi
}
run_stage() {
  local label="$1"; shift
  if [ "$(mins)" -ge "$BUDGET" ]; then echo "[v7c] $(ts) budget reached ($(mins) min): skipping $label"; return 1; fi
  echo "[v7c] $(ts) >>> $label at $(mins) min: $PY -m $GM.$*"
  local attempt rc
  for attempt in 1 2; do
    $PY -m $GM."$@"; rc=$?
    if [ $rc -eq 0 ]; then echo "[v7c] $(ts) <<< $label ok at $(mins) min (attempt $attempt)"; return 0; fi
    echo "[v7c] $(ts) $label failed rc=$rc (attempt $attempt)"
  done
  echo "[v7c] $(ts) $label failed twice; stopping" > "$OUT/V7C_FAILED_$label"
  stop_pod; exit 2
}
run_stage s1 s1_capture --phase A --families v7 --force
run_stage s3A s3_score --phase A --readers jlens,olens,skip_a,probe --force
run_stage s3B s3_score --phase B --readers nla --force || true
echo "[v7c] $(ts) done at $(mins) min; rows: s1 $(wc -l < cache/g_agreement/w/s1_target.jsonl) s3 $(wc -l < cache/g_agreement/w/s3_lo.jsonl)"
stop_pod
