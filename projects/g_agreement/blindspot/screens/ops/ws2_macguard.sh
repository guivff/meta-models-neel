#!/usr/bin/env bash
# Mac-side guards for an off-volume pod (PODS.md rule 8 default, Guiv 2026-10-20 05:17Z): the hard stop and the idle watchdog
# run ON THE MAC and stop the pod by its id with the Mac's account key (runpod_api.sh reads it; never printed, never staged on
# the pod). They are ws2_hardstop.sh and ws2_watchdog.sh themselves, unchanged in rule, with their commands pointed at the pod:
# status and stop by GraphQL from the Mac, GPU / job pid / output sizes by SSH. Each runs under `caffeinate -i` (rule 8a) and
# its PID goes into the state file and the printed line, for HANDOFF.md.
#   ws2_macguard.sh arm   <podId> <ip:port> <hard_s> [WD_CEIL] [pod_pidfile] [pod_output...]   → both guards armed, or none
#   ws2_macguard.sh rearm <podId> <pod_pidfile> <pod_output>...    → a new watchdog on the job's pid / outputs; the old one is
#                                                                     killed only after the new one prints "armed:"
#   ws2_macguard.sh hold  <podId> <job> [minutes<=30]              → warm hold (GUARDS.md rule 4): the watchdog's reservation flag
#   ws2_macguard.sh terminate <podId> --confirm '<HANDOFF line>'   → END OF JOB, only with the integrator's HANDOFF line naming the pod
#   ws2_macguard.sh stop      <podId> --confirm '<HANDOFF line>'     (exact line of HANDOFF.md) and, to terminate, a verified pull
#   ws2_macguard.sh state <podId>                                  → the state file (PIDs, deadline)
# Safety nets (GUARDS.md rule 4 / PODS.md rule 8): the hard cap and the idle CEILING call _safety: pull the job's outputs
# (pull_tree / pull_suffix, recorded by ws2_offvolume.sh job) and verify them. Then (Guiv 2026-10-20) the action depends on
# whether a key is on the pod (keys_staged in the state, set by `WS2_KEYS_STAGED=1 … arm`, i.e. ws2_offvolume.sh --stage-keys):
# no key (the default) → STOP by id (recoverable, nothing sensitive on the disk); a staged key → TERMINATE by id. An unverified
# pull (or no recorded job) always STOPS and writes ALERT. The idle stop (WD_IDLE) only stops. Nothing else terminates.
# Internal, as the guards' WD_*_CMD: _check <podId> (prints 200 only when the GraphQL pod query made with the account key returns
# this pod's id: rule 9's own-id status check), _stop <podId>, _status <podId>, _safety <podId> <why>, _terminate <podId>,
# _gpu, _alive <ip:port> <pidfile>, _stat <ip:port> <path>... (one ssh), _net, _inc <ip:port> <hf dir> (WD_IDLE / WD_CEIL wall-clock).
# The guards and this script are COPIED into the state directory and run from there (a worktree may be removed while they run).
# State: ${WS2_MAC_GUARD_DIR:-<main checkout>/cache/g_agreement/r/offvolume/<podId>/mac_guard}. Overrides for tests: WS2_API,
# WS2_SSH, WS2_SSH_KEY, WS2_CAFFEINATE (default "caffeinate -i"), WS2_ARM_WAIT (s, default 30).
set -uo pipefail
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
HERE=$(dirname "$SELF")
MAIN=${WS2_MAIN_CHECKOUT:-/Users/guivff/Documents/Neel_Exploration/activation-readers}
API=${WS2_API:-$HOME/repl/tools/runpod_api.sh}
SSHB=${WS2_SSH:-ssh}
KEYF=${WS2_SSH_KEY:-$HOME/.ssh/id_ed25519_runpod}
CAFF=${WS2_CAFFEINATE-caffeinate -i}
GUARD_SCRIPTS="ws2_hardstop.sh ws2_watchdog.sh"   # what arm starts; "both armed" below is derived from this list
COPIED="ws2_offvolume.sh ws2_verify_pull.py"      # what the safety net's pull needs, copied beside the guards
MACCACHE=${WS2_MAC_CACHE:-/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement/r}   # = ws2_offvolume.sh's pull root
RMAX_MIN=30                                       # a hold is at most 30 min ahead (the watchdog clamps to the same 1800 s)
ts() { date -u +%FT%TZ; }
die() { echo "[$(ts)] macguard: $*" >&2; exit 1; }
hp() { H=${1%:*}; P=${1##*:}; [ -n "$H" ] && [ -n "$P" ] && [ "$H" != "$1" ] || die "bad ip:port '$1'"; }
rsh() { $SSHB -o StrictHostKeyChecking=no -o ConnectTimeout=20 -o BatchMode=yes -p "$P" -i "$KEYF" "root@$H" "$@"; }
api() { bash "$API" "$1"; }
iso() { date -u -r "$1" +%FT%TZ 2>/dev/null || date -u -d "@$1" +%FT%TZ; }
id_re() { echo "\"id\"[[:space:]]*:[[:space:]]*\"$1\""; }
dir_of() { echo "${WS2_MAC_GUARD_DIR:-$MAIN/cache/g_agreement/r/offvolume/$1/mac_guard}"; }
sval() { sed -n "s/^$2=//p" "$1/state" 2>/dev/null | tail -1; }
guard_alive() {  # guard_alive <pid> <script> <podId>: the pid is alive AND is the bash running <script> for <podId>, so a
  # recorded pid that has exited, been reused, or is the guard's caffeinate fails (GUARDS.md, integrator 15:41Z)
  local a; [ -n "$1" ] || return 1
  a=$(ps -o args= -p "$1" 2>/dev/null) || return 1
  case "$a" in caffeinate*|*/caffeinate\ *) return 1 ;; *"$2 $3"*) return 0 ;; esac; return 1
}
running() {  # any guard of this state dir still alive (the arm-time "already running" check)
  local id; id=$(sval "$1" pod)
  guard_alive "$(sval "$1" hardstop_pid)" ws2_hardstop.sh "$id" || guard_alive "$(sval "$1" watchdog_pid)" ws2_watchdog.sh "$id"
}
both_live() {  # both_live <dir>: dies naming the guard whose recorded pid is not its live guard loop
  local id p g; id=$(sval "$1" pod)
  for g in hardstop watchdog; do
    p=$(sval "$1" ${g}_pid)
    guard_alive "$p" "ws2_$g.sh" "$id" || die "the Mac guards of $id are not running: $g pid ${p:-none} is $(ps -o args= -p "${p:-0}" >/dev/null 2>&1 && echo "not ws2_$g.sh $id" || echo exited); a warm hold needs them live (re-arm)"
  done
}
is_guard() { case "$1" in caffeinate*|*/caffeinate\ *) return 1 ;; bash\ *ws2_hardstop.sh*|bash\ *ws2_watchdog.sh*|*/bash\ *ws2_hardstop.sh*|*/bash\ *ws2_watchdog.sh*) return 0 ;; esac; return 1; }
is_caf() { case "$1" in caffeinate*|*/caffeinate\ *) return 0 ;; esac; return 1; }
pids_of() {  # pids_of <$!> → "<caffeinate pid or none> <guard pid>": the PERSISTENT guard loop, never one of its transient
  # $(…) subshells, which share its argv (the bug the integrator found 15:41Z: those were recorded and had exited by `hold`).
  # macOS caffeinate keeps the launched pid ($!) for the utility and forks itself off as its child: then $! IS the guard. A
  # launcher that does it the other way round leaves caffeinate at $! with the guard as its DIRECT child. Only those two.
  local p caf=none g="" i
  for i in 1 2 3 4 5 6 7 8 9 10; do
    if is_guard "$(ps -o args= -p "$1" 2>/dev/null)"; then
      g=$1
      for p in $(pgrep -P "$1" 2>/dev/null); do is_caf "$(ps -o args= -p "$p" 2>/dev/null)" && caf=$p; done
    elif is_caf "$(ps -o args= -p "$1" 2>/dev/null)"; then
      caf=$1
      for p in $(pgrep -P "$1" 2>/dev/null); do is_guard "$(ps -o args= -p "$p" 2>/dev/null)" && { g=$p; break; }; done
    fi
    [ -n "$g" ] && [ "$caf" != none ] && break
    sleep 0.3
  done
  echo "$caf ${g:-$1}"
}
guard_env() {  # the WD_* commands for this pod, all pointing back at this (copied) script
  local D=$1 ID=$2 ADDR=$3
  export WD_ENVIRON="$D/environ" WD_ENVFILE="$D/no_env_on_the_mac" WD_RETRY=${WD_RETRY:-60}
  export WD_CHECK_CMD="bash '$D/ws2_macguard.sh' _check $ID" WD_STOP_CMD="bash '$D/ws2_macguard.sh' _stop $ID"
  export WD_STATUS_CMD="bash '$D/ws2_macguard.sh' _status $ID" WD_GPU_CMD="bash '$D/ws2_macguard.sh' _gpu $ADDR"
  export WS2_API="$API" WS2_SSH="$SSHB" WS2_SSH_KEY="$KEYF" WS2_MAC_CACHE="$MACCACHE"
  export WD_RESERVE_FILE="$D/reserve.flag" WD_CEIL_STOP_CMD="bash '$D/ws2_macguard.sh' _safety $ID idle_ceiling"
}
SAFETY_STOP() { echo "bash '$1/ws2_macguard.sh' _safety $2 hard_cap"; }
handoff_src() {  # the HANDOFF.md the confirmation must be a line of: $WS2_HANDOFF, else the integration branch's current copy
  if [ -n "${WS2_HANDOFF:-}" ]; then cat "$WS2_HANDOFF"; return; fi
  git -C "$MAIN" fetch -q origin r/phase-r-scaffold 2>/dev/null
  git -C "$MAIN" show origin/r/phase-r-scaffold:results/g_agreement/r/HANDOFF.md
}
confirmed() {  # confirmed <verb> <podId> <line>: dies, naming what is missing, unless <line> is an exact HANDOFF line naming the pod
  [ -n "$3" ] || die "refusing to $1 $2: no confirmation. GUARDS.md rule 4: only after the integrator's HANDOFF.md line saying no queued job fits $2; pass it as --confirm '<that line>'"
  case "$3" in *"$2"*) ;; *) die "refusing to $1 $2: the --confirm line does not name $2" ;; esac
  handoff_src | grep -Fxq -- "$3" || die "refusing to $1 $2: the --confirm line is not a line of ${WS2_HANDOFF:-origin/r/phase-r-scaffold:results/g_agreement/r/HANDOFF.md}"
}
end_guards() { local k p; for k in hardstop_pid hardstop_caffeinate_pid watchdog_pid watchdog_caffeinate_pid; do
  for p in $(sed -n "s/^$k=//p" "$1/state"); do kill "$p" 2>/dev/null; done; done; }
launch() {  # launch <log> <script> <args...> → prints "<caffeinate pid> <guard pid>"
  local log=$1; shift
  nohup $CAFF bash "$@" > "$log" 2>&1 < /dev/null &
  pids_of $!
}
wait_armed() {  # wait_armed <log>... → 0 when every log has "armed:", 1 on REFUSING, a dead guard or the timeout
  local t0 l n; t0=$(date +%s)
  while [ $(( $(date +%s) - t0 )) -lt "${WS2_ARM_WAIT:-30}" ]; do
    n=0
    for l in "$@"; do grep -q "REFUSING" "$l" 2>/dev/null && return 1; grep -q "armed: credential" "$l" 2>/dev/null && n=$((n + 1)); done
    [ "$n" -eq $# ] && return 0
    sleep 0.5
  done
  return 1
}

cmd=${1:-}; shift || true
case "$cmd" in
arm)
  [ $# -ge 3 ] || die "usage: arm <podId> <ip:port> <hard_s> [WD_CEIL] [pod_pidfile] [pod_output...]"
  ID=$1; ADDR=$2; hp "$2"; T=$3; CEIL=${4:-45}; PIDF=${5:-/workspace/ws2_logs/job.pid}; shift $(( $# < 5 ? $# : 5 ))
  case "$T$CEIL" in *[!0-9]*) die "hard_s and WD_CEIL must be integers" ;; esac
  [ -n "$CAFF" ] && command -v "${CAFF%% *}" >/dev/null 2>&1 \
    || die "no '${CAFF%% *}' to keep the Mac awake (rule 8a: the guards run under caffeinate -i); refusing to arm"
  [ -n "$ID" ] || die "empty pod id"
  own=$(rsh 'tr "\0" "\n" < /proc/1/environ | sed -n "s/^RUNPOD_POD_ID=//p"' 2>/dev/null | head -1)
  [ "$own" = "$ID" ] || die "id check FAILED: the pod at $ADDR says '${own:-unreadable}', expected '$ID' (rule 4); nothing armed"
  D=$(dir_of "$ID"); mkdir -p "$D"
  if [ -f "$D/state" ] && [ -z "$(sval "$D" stopped)$(sval "$D" terminated)" ] && running "$D"; then
    die "guards for $ID already running ($(grep _pid= "$D/state" | tr '\n' ' ')); use rearm, or stop them first"
  fi
  cp "$SELF" "$D/ws2_macguard.sh"; for s in $GUARD_SCRIPTS $COPIED; do cp "$HERE/$s" "$D/$s"; done
  printf 'RUNPOD_POD_ID=%s\0' "$own" > "$D/environ"   # the pod's own id, read from the pod (rule 4), for the guards' own-id check
  guard_env "$D" "$ID" "$ADDR"
  export WD_ALIVE_CMD="bash '$D/ws2_macguard.sh' _alive $ADDR '$PIDF'" WD_STAT_CMD="bash '$D/ws2_macguard.sh' _stat $ADDR" WD_NET_CMD="bash '$D/ws2_macguard.sh' _net $ADDR"
  export WD_INC_CMD="bash '$D/ws2_macguard.sh' _inc $ADDR '${WD_HF_DIR:-/workspace}'"
  now=$(date +%s)
  WD_STOP_CMD=$(SAFETY_STOP "$D" "$ID")   # the hard cap is a safety net: verified pull → terminate, else stop + ALERT
  read -r hc hs < <(launch "$D/hardstop.log" "$D/ws2_hardstop.sh" "$ID" "$T")
  WD_STOP_CMD="bash '$D/ws2_macguard.sh' _stop $ID"   # the watchdog's idle stop only stops (its ceiling: WD_CEIL_STOP_CMD)
  export WD_CEIL=$CEIL
  read -r wc wd < <(launch "$D/watchdog.log" "$D/ws2_watchdog.sh" "$ID" "$PIDF" "$@")
  if ! wait_armed "$D/hardstop.log" "$D/watchdog.log"; then
    kill "$hs" "$wd" "$hc" "$wc" 2>/dev/null
    grep -h "armed:\|REFUSING" "$D/hardstop.log" "$D/watchdog.log"
    die "the Mac guards did not both arm for $ID (above); both killed: nothing may run on the pod — stop it by id from the Mac"
  fi
  { echo "pod=$ID"; echo "addr=$ADDR"; echo "armed_at=$now"; echo "deadline=$((now + T))"; echo "ceil=$CEIL"; echo "pidfile=$PIDF"
    echo "caffeinate=$CAFF"; echo "keys_staged=${WS2_KEYS_STAGED:-0}"; echo "hardstop_pid=$hs"; echo "hardstop_caffeinate_pid=$hc"; echo "watchdog_pid=$wd"
    echo "watchdog_caffeinate_pid=$wc"; } > "$D/state"
  grep -h "armed:" "$D/hardstop.log" "$D/watchdog.log"
  echo "mac guards armed for $ID under '$CAFF': hardstop pid $hs (caffeinate $hc), watchdog pid $wd (caffeinate $wc); hard stop at $(iso $((now + T))); state $D/state — log these PIDs in HANDOFF.md" ;;
rearm)
  [ $# -ge 3 ] || die "usage: rearm <podId> <pod_pidfile> <pod_output>..."
  ID=$1; PIDF=$2; shift 2
  D=$(dir_of "$ID"); [ -f "$D/state" ] || die "no Mac guard state for $ID ($D/state): arm first"
  ADDR=$(sval "$D" addr); hp "$ADDR"; old=$(sval "$D" watchdog_pid); oldc=$(sval "$D" watchdog_caffeinate_pid)
  guard_env "$D" "$ID" "$ADDR"
  export WD_ALIVE_CMD="bash '$D/ws2_macguard.sh' _alive $ADDR '$PIDF'" WD_STAT_CMD="bash '$D/ws2_macguard.sh' _stat $ADDR" WD_NET_CMD="bash '$D/ws2_macguard.sh' _net $ADDR"
  export WD_INC_CMD="bash '$D/ws2_macguard.sh' _inc $ADDR '${WD_HF_DIR:-/workspace}'"
  n=$(ls "$D"/watchdog*.log 2>/dev/null | wc -l | tr -d ' ')
  log="$D/watchdog.$n.log"
  export WD_CEIL; WD_CEIL=$(sval "$D" ceil)
  read -r wc wd < <(launch "$log" "$D/ws2_watchdog.sh" "$ID" "$PIDF" "$@")
  if ! wait_armed "$log"; then kill "$wd" "$wc" 2>/dev/null; grep -h "armed:\|REFUSING" "$log"; die "new watchdog did not arm; the old one (pid $old) keeps running"; fi
  kill "$old" "$oldc" 2>/dev/null
  { echo "pidfile=$PIDF"; echo "watchdog_pid=$wd"; echo "watchdog_caffeinate_pid=$wc"; } >> "$D/state"
  grep -h "armed:" "$log"
  echo "watchdog re-armed for $ID on $PIDF ($*): pid $wd (caffeinate $wc); old watchdog pid $old killed — log the new PID in HANDOFF.md" ;;
stop|terminate)
  [ $# -ge 1 ] || die "usage: $cmd <podId> --confirm '<the integrator's HANDOFF line naming this pod>'"
  ID=$1; shift; CONF=""
  while [ $# -gt 0 ]; do case "$1" in --confirm) CONF=${2:-}; shift 2 || shift ;; *) die "unknown argument '$1'" ;; esac; done
  confirmed "$cmd" "$ID" "$CONF"
  D=$(dir_of "$ID"); [ -f "$D/state" ] || die "no Mac guard state for $ID ($D/state)"
  ADDR=$(sval "$D" addr); guard_env "$D" "$ID" "$ADDR"
  if [ "$cmd" = terminate ]; then
    V=$MACCACHE/offvolume/$ID/PULL_VERIFIED.json
    [ -f "$V" ] || die "refusing to terminate $ID: no verified pull ($V); run release / pull first (rule 8)"
    code=000
    for i in 1 2 3 4 5; do code=$(bash "$D/ws2_macguard.sh" _terminate "$ID"); [ "$code" = 200 ] && break; sleep "${WD_RETRY:-10}"; done
    [ "$code" = 200 ] || die "terminate of $ID not confirmed by the API after 5 tries; guards left running"
    { echo "terminated=$(date +%s)"; echo "terminate_confirmed_by=$CONF"; } >> "$D/state"
  else
    bash "$D/ws2_hardstop.sh" "$ID" 0 >> "$D/final_stop.log" 2>&1; rc=$?
    tail -3 "$D/final_stop.log"
    [ $rc -eq 0 ] || die "final stop of $ID failed (exit $rc, $D/final_stop.log)"
    { echo "stopped=$(date +%s)"; echo "stop_confirmed_by=$CONF"; } >> "$D/state"
  fi
  end_guards "$D"; rm -f "$D/reserve.flag"
  done_word=terminated; [ "$cmd" = stop ] && done_word=stopped
  echo "pod $ID $done_word by id from the Mac (confirmed by HANDOFF: $CONF); its Mac guards ended" ;;
hold)
  [ $# -ge 2 ] || die "usage: hold <podId> <job> [minutes<=$RMAX_MIN]"
  ID=$1; JOB=$2; MIN=${3:-$RMAX_MIN}
  case "$MIN" in ''|*[!0-9]*) die "minutes must be an integer" ;; esac
  [ "$MIN" -le $RMAX_MIN ] || die "a hold is at most $RMAX_MIN min ahead (asked $MIN); renew it instead"
  echo "$JOB" | grep -Eq '^[A-Za-z0-9._:/-]{1,80}$' || die "bad job name '$JOB'"
  D=$(dir_of "$ID"); [ -f "$D/state" ] || die "no Mac guard state for $ID: a warm hold needs its guards live"
  both_live "$D"
  u=$(( $(date +%s) + MIN * 60 )); want=$(printf 'job=%s\nuntil=%s' "$JOB" "$(iso "$u")")
  printf '%s\n' "$want" > "$D/reserve.flag.tmp" && mv "$D/reserve.flag.tmp" "$D/reserve.flag"
  [ -f "$D/reserve.flag" ] && [ "$(cat "$D/reserve.flag" 2>/dev/null)" = "$want" ] \
    || die "hold of $ID: $D/reserve.flag does not read back as written (job=$JOB until=$(iso "$u")); NOT held — the watchdog will idle-stop"
  echo "held=$(date +%s) job=$JOB until=$u" >> "$D/state"
  echo "$ID held warm for $JOB until $(iso "$u") (watchdog reservation $D/reserve.flag; the idle ceiling and the hard cap still apply)" ;;
_safety)
  ID=$1; WHY=${2:-safety}; D=$(dir_of "$ID"); L=$D/safety.log
  if [ -n "$(sval "$D" terminated)$(sval "$D" safety_stopped)" ]; then printf 200; exit 0; fi
  mkdir "$D/safety.lock" 2>/dev/null || { printf 000; exit 0; }   # the other safety net is acting; this one retries
  code=000
  {
    KS=$(sval "$D" keys_staged)
    echo "[$(ts)] safety net ($WHY) for $ID: pull, verify, then $([ "$KS" = 1 ] && echo "terminate (a key is staged on the pod)" || echo "stop (no key on the pod)")"
    TR=$(sval "$D" pull_tree); SFX=$(sval "$D" pull_suffix); ADDR=$(sval "$D" addr)
    if [ -n "$TR" ] && [ -n "$SFX" ] && bash "$D/ws2_offvolume.sh" pull "$ID" "$ADDR" "$TR" "$SFX"; then
      if [ "$KS" = 1 ]; then
        code=$(bash "$D/ws2_macguard.sh" _terminate "$ID")
        if [ "$code" = 200 ]; then echo "terminated=$(date +%s)" >> "$D/state"; echo "[$(ts)] verified pull → TERMINATED $ID by id ($WHY; key was staged)"
        else echo "[$(ts)] ALERT: terminate of $ID (key staged) failed after a verified pull → STOP instead; tell Guiv at once" | tee -a "$D/ALERT"; fi
      else
        code=$(bash "$D/ws2_macguard.sh" _stop "$ID")
        [ "$code" = 200 ] && { echo "safety_stopped=$(date +%s)" >> "$D/state"; echo "[$(ts)] verified pull → STOPPED $ID by id ($WHY; no key on the pod, recoverable)"; }
      fi
    else
      echo "[$(ts)] ALERT: pull of $ID NOT verified (${TR:+tree $TR }${SFX:+suffix $SFX}${TR:-no job recorded}) → STOP, disk kept; tell Guiv at once" | tee -a "$D/ALERT"
    fi
    if [ "$code" != 200 ]; then
      code=$(bash "$D/ws2_macguard.sh" _stop "$ID"); [ "$code" = 200 ] && echo "safety_stopped=$(date +%s)" >> "$D/state"
    fi
  } >> "$L" 2>&1
  rmdir "$D/safety.lock"
  printf '%s' "$code" ;;
_terminate)
  r=$(api "mutation { podTerminate(input: {podId: \"$1\"}) }" 2>/dev/null)
  if echo "$r" | grep -q '"errors"'; then printf 000; exit 0; fi
  st=$(api "query { pod(input: {podId: \"$1\"}) { id desiredStatus } }" 2>/dev/null)
  if echo "$st" | grep -Eq '"pod"[[:space:]]*:[[:space:]]*null|"desiredStatus"[[:space:]]*:[[:space:]]*"TERMINATED"'; then printf 200; else printf 000; fi ;;
state)
  [ $# -eq 1 ] || die "usage: state <podId>"
  cat "$(dir_of "$1")/state" ;;
_check)
  r=$(api "query { pod(input: {podId: \"$1\"}) { id desiredStatus } }" 2>/dev/null)
  if echo "$r" | grep -Eq "$(id_re "$1")"; then printf 200; else printf 000; fi ;;
_stop)
  r=$(api "mutation { podStop(input: {podId: \"$1\"}) { id desiredStatus } }" 2>/dev/null)
  if echo "$r" | grep -Eq "$(id_re "$1")"; then printf 200; else printf 000; fi ;;
_status)
  api "query { pod(input: {podId: \"$1\"}) { id desiredStatus } }" 2>/dev/null ;;
_gpu)
  hp "$1"; rsh "nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits" 2>/dev/null | head -1 ;;
_alive)
  hp "$1"; rsh "p=\$(cat '$2' 2>/dev/null) && [ -n \"\$p\" ] && kill -0 \"\$p\"" ;;
_net)    # the pod's cumulative received bytes (non-loopback rx sum from /proc/net/dev): download progress counts as productive
  hp "$1"; rsh "awk -F'[: ]+' 'NR > 2 && \$2 != \"lo\" { s += \$3 } END { printf \"%.0f\\n\", s + 0 }' /proc/net/dev" 2>/dev/null | head -1 ;;
_inc)    # total bytes of the pod's HF *.incomplete files under <hf dir>: a growing weight download counts as productive
  hp "$1"; rsh "find '$2' -type f -name '*.incomplete' -printf '%s\\n' 2>/dev/null | awk '{ s += \$1 } END { printf \"%.0f\\n\", s + 0 }'" 2>/dev/null | head -1 ;;
_stat)   # ONE ssh for every declared output (the watchdog calls this once per sample): "<size> <mtime> <path>" per existing file
  hp "$1"; shift; q=""; for f in "$@"; do q="$q '$f'"; done
  [ -n "$q" ] && rsh "stat -c '%s %Y %n'$q 2>/dev/null" 2>/dev/null; exit 0 ;;
*)
  sed -n '2,22p' "$0"; exit 2 ;;
esac
