#!/usr/bin/env bash
# Final-step self-stop (PODS.md item 1 as amended 2026-10-19 19:36Z): call it as the LAST line of a job chain that runs detached
# (`setsid nohup bash <chain> > /workspace/ws2_logs/<chain>.log 2>&1 < /dev/null &`), after the outputs are on the volume or pulled.
# Never from an EXIT trap: a trap also fires on a passing pre-check, an early error or a closing SSH session.
#   bash /workspace/ws2_selfstop.sh <podId>
# v3: hands off to ws2_hardstop.sh <podId> 0, so the stop gets the own-id refusal (exit 2 if <podId> is not this pod's own
# RUNPOD_POD_ID), retries until 2xx, and the "desiredStatus": "EXITED" field check.
# v4 (2026-10-20): v2's wait-for-PULLED_<podId> branch (night-1 wave, jrojwkwxli7upe) is removed. A pull marker must never
# trigger a stop: the operator stops only after the pull AND the rule 7b queue check (the panel's rA3 stopped early at 02:24:21Z
# when its marker fired a self-stop before its queue check). This script now stops at once, so call it only as that final step.
# The stop credential is checked by ws2_hardstop.sh before it stops (GET with the account key from /workspace/.env; any non-2xx
# → exit 2, logged "REFUSING TO ARM: stop credential rejected (http N)"), so a rejected key shows up here as "exit 2", never silently.
ID=$1
LOGD=${WD_LOGDIR:-/workspace/ws2_logs}
HARDSTOP=${WD_HARDSTOP:-/workspace/ws2_hardstop.sh}
mkdir -p "$LOGD"
log() { echo "[$(date -u +%FT%TZ)] selfstop $ID: $*" >> "$LOGD/selfstop.log"; }
log "final step → ws2_hardstop.sh $ID 0"
bash "$HARDSTOP" "$ID" 0 >> "$LOGD/selfstop.log" 2>&1
rc=$?
log "ws2_hardstop.sh exit $rc"
exit $rc
