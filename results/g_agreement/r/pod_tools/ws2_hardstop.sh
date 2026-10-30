#!/usr/bin/env bash
# Hard-timeout self-stop (PODS.md rule item 1): stops the pod by its own id after <seconds>, whatever runs on it.
#   nohup bash ws2_hardstop.sh <podId> <seconds> > /workspace/ws2_logs/hardstop_<podId>.log 2>&1 &
# Refuses to arm (exit 2) unless <podId> equals this container's own RUNPOD_POD_ID from /proc/1/environ (PODS.md item 4).
# The stop is retried every RETRY s until the API answers 2xx or the pod reads EXITED (same loop as ws2_watchdog.sh).
ID=$1; T=$2; RETRY=${WD_RETRY:-60}
ENVFILE=${WD_ENVFILE:-/workspace/.env}
STOP=${WD_STOP_CMD:-"set -a; source $ENVFILE; set +a; curl -s -m 30 -X POST https://rest.runpod.io/v1/pods/$ID/stop -H \"Authorization: Bearer \$RUNPOD_API_KEY\" -o /dev/null -w '%{http_code}'"}
STATUS=${WD_STATUS_CMD:-"set -a; source $ENVFILE; set +a; curl -s -m 30 https://rest.runpod.io/v1/pods/$ID -H \"Authorization: Bearer \$RUNPOD_API_KEY\""}
# Only the JSON field "desiredStatus": "EXITED" counts as stopped, never the word alone (lastStatusChange says "Exited by user: ...").
EXITED_RE='"desiredStatus"[[:space:]]*:[[:space:]]*"EXITED"'
log() { echo "[$(date -u +%FT%TZ)] hardstop $ID: $*"; }
ENVF=${WD_ENVIRON:-/proc/1/environ}
OWN=$(tr '\0' '\n' < "$ENVF" 2>/dev/null | sed -n 's/^RUNPOD_POD_ID=//p' | head -1)
if [ -z "$ID" ] || [ "$OWN" != "$ID" ]; then
  log "REFUSING TO ARM: given id '$ID' != this pod's own RUNPOD_POD_ID '${OWN:-unreadable}' ($ENVF)"; exit 2
fi
# Stop credential (PODS.md, 2026-10-20 00:4xZ): RunPod's in-container RUNPOD_API_KEY is refused by the REST API (HTTP 403,
# P8 00:33Z), so the stop uses the account key from $ENVFILE. Before arming, GET this pod with the exact credential the stop
# will use; anything but 2xx refuses to arm (exit 2). The armed line names the credential's source, never the key.
if [ -n "${WD_STOP_CMD:-}" ]; then CRED="override (WD_STOP_CMD)"; else CRED="$ENVFILE RUNPOD_API_KEY"; fi
CHECK=${WD_CHECK_CMD:-}
if [ -z "$CHECK" ]; then
  if [ -n "${WD_STOP_CMD:-}" ]; then
    log "REFUSING TO ARM: WD_STOP_CMD is overridden without WD_CHECK_CMD, so its credential cannot be checked"; exit 2
  fi
  grep -Eq '^(export )?RUNPOD_API_KEY=.' "$ENVFILE" 2>/dev/null || { log "REFUSING TO ARM: no RUNPOD_API_KEY in $ENVFILE"; exit 2; }
  CHECK="set -a; source $ENVFILE; set +a; curl -s -m 30 https://rest.runpod.io/v1/pods/$ID -H \"Authorization: Bearer \$RUNPOD_API_KEY\" -o /dev/null -w '%{http_code}'"
fi
HC=$(eval "$CHECK" 2>/dev/null | tr -d '[:space:]'); HC=${HC: -3}
case "$HC" in 2[0-9][0-9]) ;; *) log "REFUSING TO ARM: stop credential rejected (http ${HC:-none}) [$CRED]"; exit 2 ;; esac
case "$T" in ''|*[!0-9]*) log "REFUSING TO ARM: seconds '$T' is not a positive integer"; exit 2 ;; esac
log "armed: credential $CRED (check http $HC), stop at $(date -u -d "@$(( $(date +%s) + T ))" +%FT%TZ 2>/dev/null || echo "+${T}s") (in ${T}s), retry ${RETRY}s"
# Wall-clock deadline: a killed or interrupted sleep must never stop the pod early (E39, 2026-10-26 05:10Z).
DEADLINE=$(( $(date +%s) + T ))
trap 'log "signal received; ignoring, deadline unchanged"' TERM INT HUP
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  left=$(( DEADLINE - $(date +%s) )); [ "$left" -gt 60 ] && left=60
  sleep "$left" || true
done
trap - TERM INT HUP
log "hard timeout reached (deadline $DEADLINE) → stopping"
attempt=0
while true; do
  attempt=$((attempt + 1))
  code=$(eval "$STOP" 2>/dev/null | tr -d "[:space:]"); code=${code: -3}
  case "$code" in 2[0-9][0-9]) log "stop attempt $attempt: http $code → stopped"; exit 0 ;; esac
  if eval "$STATUS" 2>/dev/null | grep -Eq "$EXITED_RE"; then log "stop attempt $attempt: http ${code:-none}, but pod reads EXITED → stopped"; exit 0; fi
  log "stop attempt $attempt FAILED (http ${code:-none}); retrying in ${RETRY}s"
  sleep "$RETRY"
done
