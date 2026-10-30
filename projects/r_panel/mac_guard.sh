#!/usr/bin/env bash
# Mac-side stop backstop for a BRIEF_RP pod. The RUNPOD_API_KEY that RunPod injects into the container gets HTTP 403 on the REST
# API, even GET /v1/pods/<own id> (found 2026-10-20 00:33Z, when P8's pod_guard stop failed). So no pod-side guard can stop its
# own pod. This loop carries out every stop decision with the account key (~/repl/tools/runpod_api.sh, never printed):
#   * the pod's hard cap (absolute UTC deadline);
#   * the pod's own watchdog deciding to stop ("→ stopping", "stop attempt", "hard timeout" in /root/watchdog_<id>*.log);
#   * the pod unreachable over SSH for 30 consecutive minutes while RUNNING (fail toward stopping).
# Exits when the pod reads EXITED.
#   bash projects/r_panel/mac_guard.sh <pod_id> <ip> <port> <hard_deadline YYYY-MM-DDTHH:MM:SSZ>
set -u
POD="$1"; IP="$2"; PORT="$3"; DEADLINE="$4"
SSH=(ssh -p "$PORT" -i "$HOME/.ssh/id_ed25519_runpod" -o StrictHostKeyChecking=no -o ConnectTimeout=20 "root@$IP")
dl=$(date -j -u -f "%Y-%m-%dT%H:%M:%SZ" "$DEADLINE" +%s 2>/dev/null || date -u -d "$DEADLINE" +%s)
log() { echo "[$(date -u +%FT%TZ)] mac_guard $POD: $*"; }
state() { bash ~/repl/tools/runpod_api.sh "query { pod(input: {podId: \"$POD\"}) { desiredStatus } }" | grep -o '"desiredStatus": "[A-Z]*"' | grep -o '[A-Z]*"$' | tr -d '"'; }
stop() {
  log "STOP ($1)"
  for i in 1 2 3 4 5; do
    bash ~/repl/tools/runpod_api.sh "mutation { podStop(input: {podId: \"$POD\"}) { id desiredStatus } }" >/dev/null
    sleep 10; [ "$(state)" = EXITED ] && { log "pod EXITED"; exit 0; }
  done
  log "stop not confirmed after 5 tries"; exit 1
}
# RP_CEIL_TERMINATE=1 (rule-8 safety-net amendment, Guiv; only after his go in this chat): when the pod's watchdog CEILING fires,
# pull, verify (reachable + sha256 of every pulled row file equal on pod and Mac), then terminate by id if verified, else stop.
verify_pull() {
  local dst=cache/g_agreement/rp/_final_pull_$POD; mkdir -p "$dst"
  rsync -a --no-owner --no-group --exclude 'states_pos/' --exclude 'unfrozen/' -e "ssh -p $PORT -i $HOME/.ssh/id_ed25519_runpod -o StrictHostKeyChecking=no" "root@$IP:/root/rp/" "$dst/" 2>/dev/null || return 1
  "${SSH[@]}" "cd /root/rp && find . -name '*.jsonl' -not -path './unfrozen/*' -type f -exec sha256sum {} + | sort -k2" > "$dst.pod.txt" 2>/dev/null || return 1
  (cd "$dst" && find . -name '*.jsonl' -not -path './unfrozen/*' -type f -exec shasum -a 256 {} + | sort -k2) > "$dst.mac.txt"
  python3 projects/r_panel/verify_manifest.py "$dst.pod.txt" "$dst.mac.txt" | sed "s/^/[verify] /"   # names every mismatching file
  return "${PIPESTATUS[0]}"
}
terminate_or_stop() {
  if verify_pull; then
    log "final pull VERIFIED (sha256 of every row file equal) → terminate by id"
    bash ~/repl/tools/runpod_api.sh "mutation { podTerminate(input: {podId: \"$POD\"}) }" >/dev/null
    sleep 15; chk=$(bash ~/repl/tools/runpod_api.sh "query { pod(input: {podId: \"$POD\"}) { id desiredStatus } }")
    if echo "$chk" | grep -q '"desiredStatus": "RUNNING"'; then log "terminate FAILED → stop"; stop "terminate fallback"; fi
    log "TERMINATED; provider check: $(echo "$chk" | tr -d '\n ' | head -c 160)"; exit 0
  fi
  log "ALERT: final pull NOT verified → STOP (disk kept for recovery); tell the integrator and Guiv at once"
  stop "ceiling, pull unverified"
}
log "armed: hard deadline $DEADLINE; backs the pod's own watchdog and hard timeout (their in-pod stops get HTTP 403)"
unreach=0
while true; do
  [ "$(state)" = EXITED ] && { log "pod reads EXITED; done"; exit 0; }
  [ "$(date +%s)" -ge "$dl" ] && stop "hard cap $DEADLINE"
  w=$("${SSH[@]}" "cat /root/watchdog_${POD}*.log 2>/dev/null" 2>/dev/null); rc=$?
  if [ $rc -ne 0 ]; then
    unreach=$((unreach + 1)); [ "$unreach" -ge 30 ] && stop "unreachable 30 min"
  else
    unreach=0
    if [ "${RP_CEIL_TERMINATE:-0}" = 1 ] && echo "$w" | grep -qE "ceiling [0-9]+ → stopping"; then terminate_or_stop; fi
    if echo "$w" | grep -qE "→ stopping|stop attempt [0-9]|timeout [0-9]+s -> stop"; then stop "pod watchdog decided: $(echo "$w" | grep -E '→ stopping|stop attempt [0-9]|timeout [0-9]+s -> stop' | head -1)"; fi
  fi
  sleep 60
done
