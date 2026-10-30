#!/usr/bin/env python3
"""A02 pod supervisor / local billed-time watchdog. Standard library only.

No create/resume operation is implemented. Supply the actual create/resume time,
not SSH arrival. bootstrap emits a first-SSH-command script with this source
embedded; no prior remote transfer is required. Credentials are read only from
RUNPOD_API_KEY and never included in logs, command arguments or generated code.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

MAX_BILLED_SECONDS = 9900
STOP_MARGIN_SECONDS = 60
SAMPLE_SECONDS = 30
IDLE_SECONDS = 900
STOPPED = {"STOPPED", "EXITED", "TERMINATED"}


class ApiError(RuntimeError):
    """Safe error text: never retain API response bodies or request headers."""


def log(event: str, **fields) -> None:
    print(json.dumps({"time": datetime.now(timezone.utc).isoformat(), "event": event, **fields}, sort_keys=True), flush=True)


def started_epoch(value: str) -> float:
    try:
        out = float(value)
    except ValueError:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("started-at must include a timezone") from None
        out = parsed.timestamp()
    if not 0 < out < float("inf"):
        raise ValueError("invalid started-at timestamp")
    return out


def compute_deadline(started: float, limit: int, margin: int) -> float:
    if not 1 <= limit <= MAX_BILLED_SECONDS:
        raise ValueError("limit-seconds must be between 1 and 9900")
    if not 0 < margin < limit:
        raise ValueError("stop-margin-seconds must be positive and below limit-seconds")
    return started + limit - margin


class Api:
    def __init__(self, key: str, opener=None):
        if not key:
            raise ApiError("RUNPOD_API_KEY is missing")
        self._key = key
        self._opener = opener or urllib.request.urlopen

    def request(self, url: str, method="GET", payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(url, data=body, method=method, headers={
            "Authorization": "Bearer " + self._key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 A02-PodGuard/1.0",
        })
        try:
            with self._opener(request, timeout=10) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as exc:
            raise ApiError("http_" + str(exc.code)) from None
        except Exception as exc:
            raise ApiError(type(exc).__name__) from None

    def graphql(self, query: str):
        result = self.request("https://api.runpod.io/graphql", "POST", {"query": query})
        if result.get("errors"):
            raise ApiError("graphql_error")
        return result.get("data") or {}

    def status(self, pod_id: str) -> str:
        try:
            result = self.request("https://rest.runpod.io/v1/pods/" + pod_id)
            if result.get("id") != pod_id or not result.get("desiredStatus"):
                raise ApiError("invalid_rest_identity")
        except ApiError:
            query = 'query { pod(input: {podId: %s}) { id desiredStatus } }' % json.dumps(pod_id)
            result = self.graphql(query).get("pod") or {}
            if result.get("id") != pod_id or not result.get("desiredStatus"):
                raise ApiError("invalid_graphql_identity")
        return str(result["desiredStatus"]).upper()

    def stop(self, pod_id: str) -> None:
        try:
            self.request("https://rest.runpod.io/v1/pods/" + pod_id + "/stop", "POST", {})
        except ApiError:
            query = 'mutation { podStop(input: {podId: %s}) { id desiredStatus } }' % json.dumps(pod_id)
            result = self.graphql(query).get("podStop") or {}
            if result.get("id") != pod_id:
                raise ApiError("invalid_stop_identity")


class IdleClock:
    """Track elapsed continuous idle time, not number of samples."""
    def __init__(self, threshold=IDLE_SECONDS):
        self.threshold = threshold
        self.since = None

    def observe(self, values, now: float) -> bool:
        if not values or any(value != 0 for value in values):
            self.since = None
            return False
        if self.since is None:
            self.since = now
        return now - self.since >= self.threshold


def gpu_utilization():
    result = subprocess.run(["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                            capture_output=True, text=True, timeout=5, check=True)
    values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    if not values or any(not 0 <= value <= 100 for value in values):
        raise ValueError("invalid_gpu_telemetry")
    return values


class Stopper:
    def __init__(self, api: Api, pod_id: str):
        self.api, self.pod_id = api, pod_id
        self.lock = threading.Lock()
        self.requested = threading.Event()
        self.confirmed = threading.Event()

    def stop(self, reason: str) -> None:
        self.requested.set()
        with self.lock:
            if self.confirmed.is_set():
                return
            log("stop_requested", pod_id=self.pod_id, reason=reason)
            attempt = 0
            # Continue until the API confirms the explicit pod is no longer running.
            # The independent local controller retries too if this process dies.
            while not self.confirmed.is_set():
                attempt += 1
                try:
                    self.api.stop(self.pod_id)
                    status = self.api.status(self.pod_id)
                    if status in STOPPED:
                        self.confirmed.set()
                        log("stop_confirmed", pod_id=self.pod_id, status=status)
                        return
                    log("stop_pending", pod_id=self.pod_id, status=status, attempt=attempt)
                except ApiError as exc:
                    log("stop_retry", pod_id=self.pod_id, error=str(exc), attempt=attempt)
                time.sleep(5)


def hard_watch(stopper: Stopper, deadline: float):
    # Absolute UTC deadline includes provisioning/startup, unlike job-only timeout.
    while not stopper.requested.is_set():
        remaining = deadline - time.time()
        if remaining <= 0:
            stopper.stop("absolute_billed_deadline")
            return
        stopper.requested.wait(min(1.0, remaining))


def boot_watch(stopper: Stopper, ack_path: Path, deadline: float):
    while not stopper.requested.is_set() and not ack_path.is_file():
        remaining = deadline - time.time()
        if remaining <= 0:
            stopper.stop("bootstrap_ack_timeout")
            return
        stopper.requested.wait(min(1.0, remaining))


def idle_watch(stopper: Stopper):
    tracker = IdleClock()
    errors = 0
    while not stopper.requested.is_set():
        tick = time.monotonic()
        try:
            values = gpu_utilization()
            errors = 0
            if tracker.observe(values, time.monotonic()):
                stopper.stop("gpu_zero_for_900_seconds")
                return
        except Exception:
            tracker.observe(None, time.monotonic())
            errors += 1
            if errors >= 3:
                stopper.stop("gpu_telemetry_unavailable")
                return
        # Sampling period includes nvidia-smi's bounded query duration.
        stopper.requested.wait(max(0, SAMPLE_SECONDS - (time.monotonic() - tick)))


def install_signals():
    def terminate(signum, _frame):
        raise SystemExit(128 + signum)
    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGHUP, terminate)


def terminate_job(job):
    if job is not None and job.poll() is None:
        try:
            os.killpg(job.pid, signal.SIGTERM)
            job.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(job.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def await_sync(stopper, run_dir: Path, deadline: float, grace: int):
    sync_until = min(deadline, time.time() + grace)
    while not stopper.requested.is_set() and not (run_dir / "SYNCED").is_file() and time.time() < sync_until:
        stopper.requested.wait(min(1, max(0, sync_until - time.time())))
    log("sync_window_end", acknowledged=(run_dir / "SYNCED").is_file())


def pod_run(args, api: Api, deadline: float) -> int:
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    # Durable logs must live on the network volume. No large pull window is added.
    log_file = (run_dir / "guard.jsonl").open("a", buffering=1)
    os.dup2(log_file.fileno(), 1)
    os.dup2(log_file.fileno(), 2)
    log_file.close()
    stopper = Stopper(api, args.pod_id)
    install_signals()
    job = None
    rc = 1
    try:
        threading.Thread(target=hard_watch, args=(stopper, deadline), daemon=True).start()
        threading.Thread(target=idle_watch, args=(stopper,), daemon=True).start()
        log("guards_armed", pod_id=args.pod_id, started_at=args.started_at,
            stop_deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat(),
            billed_cap_seconds=args.limit_seconds, stop_margin_seconds=args.stop_margin_seconds,
            idle_seconds=IDLE_SECONDS, sample_seconds=SAMPLE_SECONDS)
        if (run_dir / "READY").exists():
            raise RuntimeError("stale_READY_requires_new_run_directory")
        status = api.status(args.pod_id)
        if status != "RUNNING":
            raise ApiError("pod_not_running_" + status)
        # This file is published only after both watchdogs and authenticated identity
        # are established. READY must be installed last by an atomic rename.
        armed = {"pod_id": args.pod_id, "self_stop_armed": True, "idle_watchdog_armed": True,
                 "billed_start_epoch": float(started_epoch(args.started_at)),
                 "deadline": deadline, "hard_deadline_epoch": deadline,
                 "billed_cap_seconds": args.limit_seconds, "stop_margin_seconds": args.stop_margin_seconds,
                 "idle_seconds": IDLE_SECONDS, "sample_seconds": SAMPLE_SECONDS}
        (run_dir / ".ARMED.tmp").write_text(json.dumps(armed) + "\n")
        (run_dir / ".ARMED.tmp").replace(run_dir / "ARMED")
        while not stopper.requested.wait(1):
            if (run_dir / "READY").is_file():
                job_path = run_dir / "job.sh"
                if not job_path.is_file():
                    raise RuntimeError("READY_without_job")
                log("job_start", pod_id=args.pod_id)
                with (run_dir / "job.log").open("ab", buffering=0) as output:
                    job = subprocess.Popen(["bash", str(job_path)], cwd=str(run_dir),
                                           stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
                while job.poll() is None and not stopper.requested.wait(1):
                    pass
                rc = job.returncode if job.returncode is not None else 124
                log("job_exit", pod_id=args.pod_id, returncode=rc)
                (run_dir / "DONE").write_text(json.dumps({"pod_id": args.pod_id, "returncode": rc,
                    "finished_at": datetime.now(timezone.utc).isoformat()}) + "\n")
                # Small bounded opportunity for the Mac's streaming pull to finish.
                # Hard/idle watchdogs continue independently throughout this window.
                await_sync(stopper, run_dir, deadline, args.sync_grace_seconds)
                break
    except ApiError as exc:
        log("guard_error", pod_id=args.pod_id, error=str(exc))
    except Exception as exc:
        # Do not include exception text: it can contain credentials in downstream tools.
        log("guard_error", pod_id=args.pod_id, error=type(exc).__name__)
    finally:
        for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(signum, signal.SIG_IGN)
        try:
            terminate_job(job)
        except Exception:
            log("job_cleanup_failed", pod_id=args.pod_id)
        # Flush persistent-volume logs before stop. Bounded sync only, no pull sleep.
        try:
            subprocess.run(["sync"], timeout=5, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        stopper.stop("job_or_supervisor_exit")
    return int(rc)


def local_watch(args, api: Api, deadline: float) -> int:
    stopper = Stopper(api, args.pod_id)
    install_signals()
    # The deadline thread is independent of status calls and failed pod boots.
    threading.Thread(target=hard_watch, args=(stopper, deadline), daemon=True).start()
    ack_path = Path(args.boot_ack_path) if getattr(args, "boot_ack_path", None) else None
    boot_deadline = started_epoch(args.started_at) + getattr(args, "boot_timeout_seconds", 180)
    if ack_path is not None:
        threading.Thread(target=boot_watch, args=(stopper, ack_path, boot_deadline), daemon=True).start()
    log("local_watchdog_armed", pod_id=args.pod_id, deadline=deadline, started_at=args.started_at,
        boot_deadline=boot_deadline if ack_path is not None else None)
    try:
        while not stopper.requested.is_set():
            if ack_path is not None and not ack_path.is_file() and time.time() >= boot_deadline:
                stopper.stop("bootstrap_ack_timeout")
                break
            if time.time() >= deadline:
                stopper.stop("absolute_billed_deadline")
                break
            try:
                status = api.status(args.pod_id)
                if status in STOPPED:
                    stopper.confirmed.set()
                    stopper.requested.set()
                    log("already_stopped", pod_id=args.pod_id, status=status)
                    return 0
            except ApiError as exc:
                log("status_retry", pod_id=args.pod_id, error=str(exc))
            stopper.requested.wait(min(SAMPLE_SECONDS, max(0, deadline - time.time())))
    finally:
        if not stopper.confirmed.is_set():
            stopper.stop("local_controller_exit_or_deadline")
    return 0


def bootstrap(args) -> str:
    """Emit a self-contained first SSH command, sourcing env without output."""
    source = Path(__file__).read_text()
    command = ["python3", "-", "pod", "--pod-id", args.pod_id, "--started-at", args.started_at,
               "--run-dir", args.run_dir, "--limit-seconds", str(args.limit_seconds),
               "--stop-margin-seconds", str(args.stop_margin_seconds),
               "--sync-grace-seconds", str(args.sync_grace_seconds)]
    # Save explicit id as readonly before sourcing an env that may export a wrong id.
    # The independent local watchdog must already be running if env sourcing fails.
    return ("#!/usr/bin/env bash\nset -eo pipefail\n"
            + "readonly A02_EXPLICIT_POD_ID=" + shlex.quote(args.pod_id) + "\n"
            + "if [ -f /workspace/.env ]; then source /workspace/.env >/dev/null 2>&1; fi\n"
            + "export RUNPOD_POD_ID=\"$A02_EXPLICIT_POD_ID\"\n"
            + "exec " + shlex.join(command) + " <<'A02_SUPERVISOR_SOURCE'\n" + source
            + "\nA02_SUPERVISOR_SOURCE\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("bootstrap", "pod", "local-watchdog"))
    parser.add_argument("--pod-id", required=True)
    parser.add_argument("--started-at", required=True, help="actual API create/resume timestamp, UTC ISO8601 or Unix seconds")
    parser.add_argument("--run-dir", default="/workspace/a02", help="unique persistent-volume directory; use a new directory per pod run")
    parser.add_argument("--limit-seconds", type=int, default=MAX_BILLED_SECONDS)
    parser.add_argument("--stop-margin-seconds", type=int, default=STOP_MARGIN_SECONDS)
    parser.add_argument("--sync-grace-seconds", type=int, default=45, help="wait up to 0..60s after DONE for SYNCED; bounded by absolute deadline")
    parser.add_argument("--boot-ack-path", help="local-watchdog only: unique local marker written after remote ARMED; never reuse an old marker")
    parser.add_argument("--boot-timeout-seconds", type=int, default=180, help="local ack deadline from actual create/resume; 1..300 seconds")
    args = parser.parse_args(argv)
    if not 1 <= args.boot_timeout_seconds <= 300:
        parser.error("boot-timeout-seconds must be between 1 and 300")
    if not 0 <= args.sync_grace_seconds <= 60:
        parser.error("sync-grace-seconds must be between 0 and 60")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.pod_id):
        parser.error("invalid pod id")
    if args.mode in ("pod", "bootstrap") and (not Path(args.run_dir).is_absolute() or not args.run_dir.startswith("/workspace/") or ".." in Path(args.run_dir).parts):
        parser.error("run-dir must be an absolute path under /workspace/")
    try:
        start = started_epoch(args.started_at)
        deadline = compute_deadline(start, args.limit_seconds, args.stop_margin_seconds)
    except (ValueError, OverflowError):
        parser.error("invalid timezone-aware start time, billed limit or stop margin")
    if start > time.time() + 5:
        parser.error("started-at cannot be in the future")
    if args.mode == "bootstrap":
        print(bootstrap(args), end="")
        return 0
    try:
        api = Api(os.environ.get("RUNPOD_API_KEY", ""))
    except ApiError as exc:
        log("fatal", error=str(exc))
        return 2
    if args.mode == "pod":
        return pod_run(args, api, deadline)
    return local_watch(args, api, deadline)


if __name__ == "__main__":
    raise SystemExit(main())
