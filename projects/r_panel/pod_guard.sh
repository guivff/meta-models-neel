#!/usr/bin/env bash
# PODS.md rule (Guiv, scaffold @ ba590a8): every pod gets, addressed to its OWN id (never /workspace/.env's RUNPOD_POD_ID):
#   (1) a hard timeout;  (2) an idle watchdog — stop after 15 consecutive min at 0 % GPU unless the job PID is alive AND a
#   declared output grew in the last 5 min; stop after 45 consecutive min at 0 % regardless.
#   nohup bash projects/r_panel/pod_guard.sh <own_pod_id> <hard_timeout_s> <job_pid_pattern> <output_glob…> &
set -u
POD="$1"; HARD="$2"; PAT="$3"; shift 3; OUTS=("$@")
LOG=/root/rp_guard.log
KEY="$(tr '\0' '\n' < /proc/1/environ | sed -n 's/^RUNPOD_API_KEY=//p')"
stop() {
  echo "[$(date -u +%FT%TZ)] stop $POD reason=$1" >> "$LOG"
  curl -s -o /dev/null -w '%{http_code}\n' -X POST "https://rest.runpod.io/v1/pods/$POD/stop" -H "Authorization: Bearer $KEY" >> "$LOG"
  exit 0
}
echo "[$(date -u +%FT%TZ)] armed on $POD: hard ${HARD}s; idle 15 min (unless pid~'$PAT' alive and outputs grew < 5 min), 45 min regardless; outputs: ${OUTS[*]}" >> "$LOG"
( sleep "$HARD"; stop "hard_timeout_${HARD}s" ) &
idle=0
while true; do
  u=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1 | tr -d ' ')
  if [ "${u:-0}" = "0" ]; then idle=$((idle + 1)); else idle=0; fi
  if [ "$idle" -ge 45 ]; then stop "idle_45min"; fi
  if [ "$idle" -ge 15 ]; then
    alive=0; pgrep -f "$PAT" >/dev/null && alive=1
    grew=0; [ -n "$(find ${OUTS[@]} -newermt '-5 minutes' -print -quit 2>/dev/null)" ] && grew=1
    if [ "$alive" = 0 ] || [ "$grew" = 0 ]; then stop "idle_15min(alive=$alive,grew=$grew)"; fi
  fi
  sleep 60
done
