#!/usr/bin/env bash
# Integrator entrypoint; root-relative modules and /workspace environment like repro.
# Usage: pod_run.sh plan
#        pod_run.sh target|nla|sweep|free-target|free-nla ASSIGNMENT BANK ASSETS OUT [TARGET]
# All raw stdout/artifacts stay in cache. No provisioning, API calls or model downloads.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
cd "$REPO"
if [[ -f /workspace/.env ]]; then source /workspace/.env >/dev/null 2>&1; fi
export PYTHONPATH="$REPO${PYTHONPATH:+:$PYTHONPATH}"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 WANDB_MODE=disabled
export TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
PY="${BLINDSPOT_PYTHON:-python3}"
PHASE="${1:-plan}"
if [[ "$PHASE" == plan ]]; then
    exec "$PY" -m projects.g_agreement.blindspot.run plan
fi
[[ $# -ge 5 ]] || { echo "usage: $0 target|nla|sweep|free-target|free-nla ASSIGNMENT BANK ASSETS OUT [TARGET]" >&2; exit 2; }
ASSIGNMENT="$2"; BANK="$3"; ASSETS="$4"; OUT="$5"
EXECUTION_ARGS=()
if [[ "$PHASE" == sweep ]]; then
    : "${BLINDSPOT_W1_ANALYSIS:?W5 requires the sealed complete W1 analysis}"
    EXECUTION_ARGS+=(--w1-analysis "$BLINDSPOT_W1_ANALYSIS")
fi
if [[ -n "${BLINDSPOT_EXECUTION_PLAN:-}" ]]; then
    EXECUTION_ARGS+=(--execution-plan "$BLINDSPOT_EXECUTION_PLAN")
    if [[ "$PHASE" != sweep ]]; then
        : "${BLINDSPOT_UNIT:?set priority, remainder_a or remainder_b}"
        EXECUTION_ARGS+=(--unit "$BLINDSPOT_UNIT")
        if [[ -n "${BLINDSPOT_PRIORITY_ROOT:-}" ]]; then
            EXECUTION_ARGS+=(--priority-root "$BLINDSPOT_PRIORITY_ROOT")
        fi
    fi
fi
mkdir -p "$REPO/cache/g_agreement/blindspot/logs"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
exec > >(tee -a "$REPO/cache/g_agreement/blindspot/logs/$PHASE-$STAMP.log") 2>&1
case "$PHASE" in
    target)
        "$PY" -m projects.g_agreement.blindspot.run target --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" --asked-only --experiment "${BLINDSPOT_EXPERIMENT:-W1}" "${EXECUTION_ARGS[@]}"
        ;;
    nla)
        [[ $# -ge 6 ]] || exit 2
        ASKED_ARGS=()
        if [[ -n "${BLINDSPOT_EXECUTION_PLAN:-}" ]]; then ASKED_ARGS+=(--asked-only); fi
        "$PY" -m projects.g_agreement.blindspot.run nla --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" --target "$6" --experiment "${BLINDSPOT_EXPERIMENT:-W1}" "${EXECUTION_ARGS[@]}" "${ASKED_ARGS[@]}"
        ;;
    sweep)
        "$PY" -m projects.g_agreement.blindspot.run sweep --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" "${EXECUTION_ARGS[@]}"
        ;;
    free-target)
        "$PY" -m projects.g_agreement.blindspot.run free-target --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" --experiment "${BLINDSPOT_EXPERIMENT:-W1}" "${EXECUTION_ARGS[@]}"
        ;;
    free-nla)
        [[ $# -ge 6 ]] || exit 2
        "$PY" -m projects.g_agreement.blindspot.run free-nla --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" --target "$6" --experiment "${BLINDSPOT_EXPERIMENT:-W1}" "${EXECUTION_ARGS[@]}"
        ;;
    ar)
        [[ $# -ge 6 ]] || exit 2
        : "${BLINDSPOT_OFFICIAL:?integrator must stage pinned official AR source}"
        : "${BLINDSPOT_WHITENER:?integrator must stage pinned P3 whitener}"
        "$PY" -m projects.g_agreement.blindspot.ar_tests collect --assignment "$ASSIGNMENT" --bank "$BANK" --assets "$ASSETS" --out "$OUT" --target "$6" --official "$BLINDSPOT_OFFICIAL" --whitener "$BLINDSPOT_WHITENER"
        ;;
    *) echo "unknown phase" >&2; exit 2 ;;
esac
touch "$OUT/RSYNC_READY"
