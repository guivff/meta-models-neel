#!/usr/bin/env bash
# Pod chain for text arm v3 (BRIEF_R §13 note "text arm v3"; PODS.md items 1–5). Runs in the v2 tree on the volume, where
# states_v2/ lives. Guards (ws2_hardstop.sh <id> 5400, ws2_watchdog.sh) are armed BEFORE this chain, by the first SSH command.
# Launch detached from SSH:
#   setsid nohup bash /workspace/activation-readers-txt2/projects/g_agreement/r_bench/text_arm_v3_pod.sh <POD_ID> \
#     > /workspace/txt3_logs/chain.log 2>&1 < /dev/null &
# Chain: id check → smoke (must show every arm × render × bank, else "SMOKE FAILED", exit, no full run) → full run under
# `timeout 70m` → 10-min pull window → explicit stop by id (ws2_hardstop.sh <id> 0). No trap; failures are the guards' job.
set -uo pipefail
POD_ID=$1
ROOT=/workspace/activation-readers-txt2
L=/workspace/txt3_logs
mkdir -p "$L"
st() { echo "[$(date -u +%FT%TZ)] $*" >> "$L/status"; }
OWN=$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_POD_ID=//p' | head -1)
if [ "$OWN" != "$POD_ID" ]; then st "ABORT: given id $POD_ID != own RUNPOD_POD_ID ${OWN:-unreadable}"; exit 2; fi
echo $$ > "$L/job.pid"
set -a; source /workspace/.env >/dev/null 2>&1; set +a   # venv, HF_HOME (keys never printed)
cd "$ROOT"
export R_GIT_SHA=$(cat GIT_SHA) HF_HUB_DISABLE_XET=1 OMP_NUM_THREADS=4
st "start on $POD_ID ($(hostname)), sha $R_GIT_SHA"
python -m projects.g_agreement.r_bench.text_arm_v3 --smoke 2 \
  --datasets 92_glue_sst2 5_hist_fig_ismale rb_context_system_fact rb_khop_3hop_middle --pod "TXT3-$POD_ID" >> "$L/smoke.log" 2>&1
rc=$?
grep -h "SMOKE" "$L/smoke.log" >> "$L/status"
if [ $rc != 0 ]; then st "smoke exit $rc: full run NOT launched"; exit $rc; fi
st "smoke exit 0"
timeout 70m python -m projects.g_agreement.r_bench.text_arm_v3 --pod "TXT3-$POD_ID" >> "$L/run.log" 2>&1
rc=$?
st "full exit $rc"
st "pull window 600s, then explicit stop by id"
sleep 600
st "stopping $POD_ID"
bash "$ROOT/results/g_agreement/r/pod_tools/ws2_hardstop.sh" "$POD_ID" 0 >> "$L/status" 2>&1
