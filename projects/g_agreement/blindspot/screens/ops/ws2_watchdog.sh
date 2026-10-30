#!/usr/bin/env bash
# Idle watchdog (PODS.md rule item 2, as amended 2026-10-19 17:31Z). Arm it BEFORE the job, detached:
#   nohup bash ws2_watchdog.sh <podId> <jobPidFile> <output file>... > /workspace/ws2_logs/watchdog_<podId>.log 2>&1 &
# <podId> is the pod's OWN id (never .env's $RUNPOD_POD_ID, which names another pod); the script refuses to arm (exit 2)
# unless it equals RUNPOD_POD_ID in /proc/1/environ (PODS.md item 4). The job writes its PID to <jobPidFile> at
# launch. <output file>... are the job's OWN declared output files: never a directory, a glob over a shared tree, or a file other
# pods also write (a shared-volume path keeps "idle but productive" alive forever while another pod writes there); directories
# are ignored with a warning.
# Rule: stop the pod by its id after IDLE consecutive minutes at 0% GPU, unless the job PID is alive AND a declared output grew
# (size up since the previous sample, or mtime within GROW s) — logged "idle but productive" — but never past CEIL consecutive
# minutes at 0%. Any sample > 0% resets the count. A failed GPU read counts as 0%.
# IDLE and CEIL are WALL-CLOCK minutes (2026-10-20, Neel-five's finding r/neel5 f593271; until then both were SAMPLE COUNTS,
# so a slow cycle stretched them: under the Mac guard, sleep 60 + one SSH per output made "15" ≈ 25.5 min). The run of zeros
# is timed from its first 0% sample; reserved samples still count as idle (the clock keeps running). WD_MINUTE_MS (default
# 60000, tests shrink it) is the length of one IDLE / CEIL minute.
# Stopping: retries every RETRY s, logging each attempt, until the API answers 2xx or the pod reads EXITED; only then exits.
# Warm handover (PODS.md rule 7): WD_RESERVE_FILE names a flag file holding two lines, `job=<name>` and
# `until=<YYYY-MM-DDTHH:MM:SSZ>` (absolute UTC). While it exists, is well formed and its deadline is in the future, the 0%-GPU
# idle stop is held, logged once per sample "reserved for <job> until <deadline>". Each version of the flag holds at most
# 30 min (RMAX, which WD_RESERVE_MAX may only lower) from the sample that first sees it; a later deadline is clamped and logged.
# Renewal (PODS.md rule 7c): an operator rewrites the flag with a new until= (<= 30 min ahead of the rewrite); the watchdog logs
# "reservation renewed for <job> until <t>" and holds from there. Rewriting the same content is not a renewal. Reserved samples
# still count as idle, so past the deadline the normal rule applies at once (no fresh IDLE minutes). The ceiling CEIL is checked
# first and stops any continuous 0% stretch whatever the renewals (tonight armed with WD_CEIL=90). A missing-field or malformed
# flag is ignored with a WARNING (fails toward stopping).
# No WD_RESERVE_FILE, or no file at that path: behaviour unchanged.
# Mac-side mode (PODS.md rule 8 default, 2026-10-20; ws2_macguard.sh): the same rule run on the Mac against a pod. WD_ALIVE_CMD
# (exit 0 = the job pid in <jobPidFile> is alive) and WD_STAT_CMD (called with an output path; prints "<size> <mtime_epoch>",
# nothing when the file is missing) replace the local kill -0 / stat, so <jobPidFile> and <output file>... are pod paths.
# WD_STAT_CMD is called ONCE per sample with every declared output path as arguments (one SSH per cycle, not one per output)
# and prints "<size> <mtime_epoch> <path>" for each output that exists. Unset: the local checks, as before.
# WD_CEIL_STOP_CMD (GUARDS.md rule 4, 2026-10-20): the stop used when the CEILING fires (a safety net: the Mac guard's pull,
# verify, then terminate / else stop and alert); the IDLE stop keeps WD_STOP_CMD. Unset: the ceiling uses WD_STOP_CMD, as before.
# Network-in progress (Guiv, 2026-10-21, after R-D's relaunch was idle-stopped mid-download): WD_NET_CMD prints the pod's
# cumulative received bytes (default: the non-loopback rx sum from /proc/net/dev; the Mac guard reads it over ssh). A sample
# whose counter rose by at least WD_NET_MIN bytes (default 1048576) since the previous one counts as productive, exactly like
# a growing declared output: only while the job pid is alive, logged "idle but productive (... network in +N bytes)", and never
# past the CEIL ceiling. A counter that is missing or not a number never counts (fails toward stopping).
# Weight-download progress (Guiv, 2026-10-23, after §64's lens pod was idle-stopped at ≈ 102 GiB of a cold stage with only
# +29 KB network in, since hf_xet can rebuild weights locally with the network quiet): WD_INC_CMD prints the total size in bytes
# of the HF `*.incomplete` files under WD_HF_DIR (default /workspace; the Mac guard reads it over ssh). It must be the pod's OWN
# HF cache, never a shared network-volume path (the same rule as the outputs). A sample whose total rose by at least WD_INC_MIN
# bytes (default 1048576) counts as productive, only while the job pid is alive, logged "idle but productive (... hf
# .incomplete +N bytes)". Time bound: this credit lasts only for the first WD_INC_CEIL wall-clock minutes of a run of zeros
# (default CEIL, never above it), and CEIL still stops everything. A total that falls (a file finished and was renamed),
# stays flat (a stalled download) or is not a number never counts. This is not a heartbeat: the bytes on disk must grow.
ID=$1; PIDF=$2; shift 2
INT=${WD_INTERVAL:-60}; IDLE=${WD_IDLE:-15}; CEIL=${WD_CEIL:-45}; GROW=${WD_GROW:-300}; RETRY=${WD_RETRY:-60}
RES=${WD_RESERVE_FILE:-}; RMAX=${WD_RESERVE_MAX:-1800}
MIN_MS=${WD_MINUTE_MS:-60000}; case "$MIN_MS" in ''|*[!0-9]*) MIN_MS=60000 ;; esac
case "$IDLE$CEIL" in *[!0-9]*) echo "watchdog: WD_IDLE and WD_CEIL must be whole minutes"; exit 2 ;; esac
IDLE_MS=$((IDLE * MIN_MS)); CEIL_MS=$((CEIL * MIN_MS))
case "$RMAX" in ''|*[!0-9]*) RMAX=1800 ;; esac; [ "$RMAX" -gt 1800 ] && RMAX=1800   # 30 min is a hard cap
GPU=${WD_GPU_CMD:-"nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits"}
NET=${WD_NET_CMD:-"awk -F'[: ]+' 'NR > 2 && \$2 != \"lo\" { s += \$3 } END { printf \"%.0f\\n\", s + 0 }' /proc/net/dev 2>/dev/null"}
NET_MIN=${WD_NET_MIN:-1048576}; case "$NET_MIN" in ''|*[!0-9]*) NET_MIN=1048576 ;; esac
HFD=${WD_HF_DIR:-/workspace}
INC=${WD_INC_CMD:-"find $(printf '%q' "$HFD") -type f -name '*.incomplete' -printf '%s\n' 2>/dev/null | awk '{ s += \$1 } END { printf \"%.0f\\n\", s + 0 }'"}
INC_MIN=${WD_INC_MIN:-1048576}; case "$INC_MIN" in ''|*[!0-9]*) INC_MIN=1048576 ;; esac
INC_CEIL=${WD_INC_CEIL:-$CEIL}; case "$INC_CEIL" in ''|*[!0-9]*) INC_CEIL=$CEIL ;; esac
[ "$INC_CEIL" -gt "$CEIL" ] && INC_CEIL=$CEIL   # never past the ceiling
INC_CEIL_MS=$((INC_CEIL * MIN_MS))
# STOP must print the HTTP status code; STATUS must print the pod's REST JSON body. Only the field "desiredStatus": "EXITED"
# counts as stopped: the body's lastStatusChange text ("Exited by user: ...") also contains the word while the pod runs again.
ENVFILE=${WD_ENVFILE:-/workspace/.env}
STOP=${WD_STOP_CMD:-"set -a; source $ENVFILE; set +a; curl -s -m 30 -X POST https://rest.runpod.io/v1/pods/$ID/stop -H \"Authorization: Bearer \$RUNPOD_API_KEY\" -o /dev/null -w '%{http_code}'"}
STATUS=${WD_STATUS_CMD:-"set -a; source $ENVFILE; set +a; curl -s -m 30 https://rest.runpod.io/v1/pods/$ID -H \"Authorization: Bearer \$RUNPOD_API_KEY\""}
EXITED_RE='"desiredStatus"[[:space:]]*:[[:space:]]*"EXITED"'
log() { echo "[$(date -u +%FT%TZ)] watchdog $ID: $*"; }
# PODS.md item 4: never arm a watchdog that would stop another pod. The id must equal the container's own RUNPOD_POD_ID
# (from /proc/1/environ; an ssh shell's $RUNPOD_POD_ID is empty, and .env's names another pod).
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
mtime() { stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0; }
fsize() { stat -c %s "$1" 2>/dev/null || stat -f %z "$1" 2>/dev/null || echo 0; }
now_ms() {  # wall clock in ms: bash 5's EPOCHREALTIME (pods), GNU-style date %N, else perl / python3 / whole seconds
  local t
  if [ -n "${EPOCHREALTIME:-}" ]; then t=${EPOCHREALTIME/[.,]/}; echo $((t / 1000)); return; fi
  t=$(date +%s%N 2>/dev/null); case "$t" in ''|*[!0-9]*) ;; *) echo $((t / 1000000)); return ;; esac
  perl -MTime::HiRes=time -e 'printf "%d\n", time() * 1000' 2>/dev/null && return
  python3 -c 'import time; print(int(time.time() * 1000))' 2>/dev/null && return
  echo $(( $(date +%s) * 1000 ))
}
secs() { printf '%d.%01ds' $(($1 / 1000)) $((($1 % 1000) / 100)); }
OUTS=()
for f in "$@"; do
  if [ -d "$f" ]; then log "WARNING: $f is a directory; ignored (declare the job's own output files)"; else OUTS+=("$f"); fi
done
sample_outputs() {  # CUR[i] = "<size> <mtime>" of output i, "" when missing; ONE WD_STAT_CMD call for all of them
  local i out line q=""
  CUR=()
  [ ${#OUTS[@]} -gt 0 ] || return 0
  if [ -n "${WD_STAT_CMD:-}" ]; then
    for i in "${!OUTS[@]}"; do q="$q $(printf '%q' "${OUTS[$i]}")"; done
    out=$(eval "$WD_STAT_CMD$q" 2>/dev/null)
    for i in "${!OUTS[@]}"; do
      line=$(printf '%s\n' "$out" | awk -v p="${OUTS[$i]}" '$1 ~ /^[0-9]+$/ && $2 ~ /^[0-9]+$/ { s = $1; m = $2; sub(/^[^ ]+ [^ ]+ /, ""); if ($0 == p) { print s " " m; exit } }')
      CUR[$i]=$line
    done
  else
    for i in "${!OUTS[@]}"; do
      if [ -e "${OUTS[$i]}" ]; then CUR[$i]="$(fsize "${OUTS[$i]}") $(mtime "${OUTS[$i]}")"; else CUR[$i]=""; fi
    done
  fi
}
net_rx() {  # the pod's cumulative received bytes, or nothing when unreadable
  local v; v=$(eval "$NET" 2>/dev/null | head -1 | tr -d '[:space:]')
  case "$v" in ''|*[!0-9]*) ;; *) echo "$v" ;; esac
}
inc_bytes() {  # total bytes of the HF *.incomplete files, or nothing when unreadable
  local v; v=$(eval "$INC" 2>/dev/null | head -1 | tr -d '[:space:]')
  case "$v" in ''|*[!0-9]*) ;; *) echo "$v" ;; esac
}
NET_PREV=$(net_rx)
INC_PREV=$(inc_bytes); INC_LATE=""
PREV=()
sample_outputs
for i in "${!OUTS[@]}"; do st=${CUR[$i]:-}; PREV[$i]=${st%% *}; [ -n "$st" ] || PREV[$i]=0; done   # indexed: bash 3.2 (Mac) and 5 (pods)
iso() { date -u -d "@$1" +%FT%TZ 2>/dev/null || date -u -r "$1" +%FT%TZ; }
to_epoch() {  # strict YYYY-MM-DDTHH:MM:SSZ → epoch seconds, or nothing
  echo "$1" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$' || return 1
  date -u -d "$1" +%s 2>/dev/null || date -u -j -f "%Y-%m-%dT%H:%M:%SZ" "$1" +%s 2>/dev/null
}
RES_FIRST=""; RES_SIG=""; RES_CLAMP=""; RES_EXP=""   # current flag version, first seen; last clamp / expiry logged
reserved() {  # 0 = hold the idle stop this sample (and log it); 1 = no valid, unexpired reservation
  [ -n "$RES" ] && [ -e "$RES" ] || return 1
  local job ustr dl now cap eff
  job=$(sed -n 's/^job=//p' "$RES" 2>/dev/null | head -1 | tr -d '\r')
  ustr=$(sed -n 's/^until=//p' "$RES" 2>/dev/null | head -1 | tr -d '\r')
  if ! echo "$job" | grep -Eq '^[A-Za-z0-9._:/-]{1,80}$' || ! dl=$(to_epoch "$ustr") || [ -z "$dl" ]; then
    log "WARNING: reservation flag $RES malformed (job='$job', until='$ustr'); ignored → normal idle rule"; return 1
  fi
  now=$(date +%s)
  if [ "$RES_SIG" != "$job|$ustr" ]; then                     # a new flag version: its own 30-min budget starts now
    local prev=$RES_SIG; RES_SIG="$job|$ustr"; RES_FIRST=$now
    eff=$dl; [ "$eff" -gt $((now + RMAX)) ] && eff=$((now + RMAX))
    [ -n "$prev" ] && log "reservation renewed for $job until $(iso "$eff")"
  fi
  cap=$((RES_FIRST + RMAX))
  if [ "$dl" -gt "$cap" ]; then
    [ "$RES_CLAMP" != "$job $ustr $RES_FIRST" ] && log "reservation for $job until $ustr exceeds ${RMAX}s from first seen $(iso "$RES_FIRST") → clamped to $(iso "$cap")"
    RES_CLAMP="$job $ustr $RES_FIRST"; dl=$cap
  fi
  if [ "$now" -lt "$dl" ]; then log "reserved for $job until $(iso "$dl") (0% for $n)"; return 0; fi
  [ "$RES_EXP" != "$job $dl" ] && log "reservation for $job expired at $(iso "$dl") → normal idle rule (0% for $n)"
  RES_EXP="$job $dl"; return 1
}
stop_pod() {  # stop_pod [command]: the stop command (default STOP), retried
  local attempt=0 code cmd=${1:-$STOP}
  while true; do
    attempt=$((attempt + 1))
    code=$(eval "$cmd" 2>/dev/null | tr -d "[:space:]"); code=${code: -3}   # last 3 chars after stripping whitespace
    case "$code" in 2[0-9][0-9]) log "stop attempt $attempt: http $code → stopped"; return 0 ;; esac
    if eval "$STATUS" 2>/dev/null | grep -Eq "$EXITED_RE"; then log "stop attempt $attempt: http ${code:-none}, but pod reads EXITED → stopped"; return 0; fi
    log "stop attempt $attempt FAILED (http ${code:-none}); retrying in ${RETRY}s"
    sleep "$RETRY"
  done
}
log "armed: credential $CRED (check http $HC), interval ${INT}s, idle ${IDLE}, ceiling ${CEIL} (wall-clock minutes of ${MIN_MS} ms), growth window ${GROW}s, retry ${RETRY}s, pidfile $PIDF, outputs ${OUTS[*]:-none}, reserve file ${RES:-none} (max ${RMAX}s), network-in min ${NET_MIN} bytes, hf .incomplete min ${INC_MIN} bytes for ≤ ${INC_CEIL} min under ${HFD}"
n=0; first=1; z0=""   # z0: wall time (ms) of the first 0% sample of the current run of zeros
while sleep "$INT"; do
  u=$(eval "$GPU" 2>/dev/null | head -1 | tr -d ' %'); raw=$u
  case "$u" in ''|*[!0-9]*) u=0 ;; esac
  [ $first = 1 ] && { log "first sample: gpu ${u}% (raw '${raw}')"; first=0; }
  grew=0
  sample_outputs; now=$(date +%s)
  for i in "${!OUTS[@]}"; do
    st=${CUR[$i]:-}; [ -n "$st" ] || continue
    s=${st% *}; m=${st#* }
    { [ "$s" -gt "${PREV[$i]:-0}" ] || [ $((now - m)) -le "$GROW" ]; } && grew=1
    PREV[$i]=$s
  done
  netin=0; rx=$(net_rx)
  if [ -n "$rx" ] && [ -n "$NET_PREV" ] && [ "$rx" -ge "$NET_PREV" ]; then netin=$((rx - NET_PREV)); fi
  [ -n "$rx" ] && NET_PREV=$rx
  incin=0; ib=$(inc_bytes)
  if [ -n "$ib" ] && [ -n "$INC_PREV" ] && [ "$ib" -ge "$INC_PREV" ]; then incin=$((ib - INC_PREV)); fi
  INC_PREV=$ib   # unreadable → empty, so the next sample cannot claim growth across the gap
  if [ "$u" -gt 0 ]; then [ $n -gt 0 ] && log "gpu ${u}% → reset (was $n)"; n=0; z0=""; INC_LATE=""; continue; fi
  n=$((n + 1)); t=$(now_ms); [ -n "$z0" ] || z0=$t; el=$((t - z0))
  if [ $el -ge "$CEIL_MS" ]; then log "0% for $n samples ($(secs $el)) ≥ ceiling $CEIL → stopping"; stop_pod "${WD_CEIL_STOP_CMD:-$STOP}"; exit 0; fi
  reserved && continue
  [ $el -lt "$IDLE_MS" ] && continue
  alive=0
  if [ -n "${WD_ALIVE_CMD:-}" ]; then pid="(pod) $PIDF"; eval "$WD_ALIVE_CMD" >/dev/null 2>&1 && alive=1
  else pid=$(cat "$PIDF" 2>/dev/null); [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null && alive=1; fi
  if [ $alive = 1 ] && [ $grew = 1 ]; then log "idle but productive (0% for $n, pid $pid alive, output grew)"; continue; fi
  if [ $alive = 1 ] && [ "$netin" -ge "$NET_MIN" ]; then log "idle but productive (0% for $n, pid $pid alive, network in +$netin bytes)"; continue; fi
  if [ $alive = 1 ] && [ "$incin" -ge "$INC_MIN" ]; then
    if [ $el -lt "$INC_CEIL_MS" ]; then log "idle but productive (0% for $n, pid $pid alive, hf .incomplete +$incin bytes)"; continue; fi
    [ -n "$INC_LATE" ] || log "hf .incomplete still growing (+$incin bytes) but past ${INC_CEIL} min of 0% → no longer counts"; INC_LATE=1
  fi
  log "0% for $n samples ($(secs $el)), pid alive=$alive, output grew=$grew, network in +$netin bytes, hf .incomplete +$incin bytes → stopping"; stop_pod; exit 0
done
