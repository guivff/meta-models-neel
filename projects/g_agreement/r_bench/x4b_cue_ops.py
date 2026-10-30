"""X4b integrator operations; CPU preparation never creates or resumes a pod.

The X3 two-stage freeze/pull protocol is reused. Shared scaffold ws2 guards are
used byte-for-byte with a stricter status check (HTTP 200 and matching body ID).
Every deadline includes setup, selection, freeze, evaluation, and retrieval.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
import urllib.error
import urllib.request

OPS_RUN_ID = str(time.time_ns()) + "-" + uuid.uuid4().hex


def ops_provenance():
    return {"run_id": OPS_RUN_ID, "run_kind": "test" if "pytest" in sys.modules else "real",
            "code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


BRIEF_SECTION = 33  # Integrator-assigned dated follow-up X4b.
MAX_SECONDS = 7200
RETRIEVAL_RESERVE = 180
REMOTE_OPS = "/workspace/x4b_ops"
REMOTE_REPO = "/workspace/x4b_repo"
DATA_REL = "cache/g_agreement/r/x4b_cue"
CANDIDATE_REL = "projects/g_agreement/dataset/items_r_x4b_cue_candidates.json"
SELECTED_REL = "projects/g_agreement/dataset/items_r_x4b_cue_selected.json"
GUARD_REL = "results/g_agreement/r/pod_tools"
MODULE = "projects.g_agreement.r_bench.x4b_cue_run"
GUARDS = ("ws2_hardstop.sh", "ws2_watchdog.sh", "ws2_selfstop.sh", "ws2_macguard.sh", "ws2_offvolume.sh")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, sort_keys=True, indent=2)
        stream.write("\n")


def validate_assignment(a, now=None):
    """Reject placeholders, recycled allocations, and any clock reset."""
    now = time.time() if now is None else now
    if not re.fullmatch(r"[a-zA-Z0-9-]{6,80}", a.get("pod_id", "")):
        raise ValueError("an explicit assigned pod ID is required")
    if type(a.get("brief_section")) is not int or a["brief_section"] != BRIEF_SECTION:
        raise ValueError("integrator-assigned BRIEF_R section number required")
    if a.get("fresh_pod") is not True and not (a.get("fresh_pod") is False and
            a.get("handover_confirmed") is True and a.get("handover_evidence", "").strip()):
        raise ValueError("X4b requires a fresh assignment or explicit integrator handover evidence")
    gpu = a.get("gpu", "")
    if not ("H100" in gpu or "H200" in gpu or ("A100" in gpu and "80" in gpu) or ("RTX PRO 6000" in gpu and "96" in gpu)):
        raise ValueError("only H100/H200/A100 80GB or integrator-cleared RTX PRO 6000 96GB is allowed")
    if not isinstance(a.get("off_volume"), bool):
        raise ValueError("storage disposition must be explicit")
    if not a.get("integrator_clearance", "").strip():
        raise ValueError("dated no-collision clearance from integrator required")
    for field in ("source_commit", "candidate_commit"):
        if not re.fullmatch(r"[a-f0-9]{40}", a.get(field, "")):
            raise ValueError("full frozen Git commits are required")
    for field in ("candidate_file_sha256", "candidate_sha"):
        if not re.fullmatch(r"[a-f0-9]{64}", a.get(field, "")):
            raise ValueError("frozen candidate file and items SHAs are required")
    start, end = a.get("assigned_at"), a.get("hard_deadline")
    if not all(isinstance(t, (int, float)) and not isinstance(t, bool) for t in (start, end)):
        raise ValueError("assigned_at and hard_deadline must be Unix seconds")
    if not 0 < end - start <= MAX_SECONDS or start > now or end <= now:
        raise ValueError("expired, future, or >7200-second assignment")
    return a


def remaining(a, now=None, science=False):
    now = time.time() if now is None else now
    validate_assignment(a, now)
    seconds = int(a["hard_deadline"] - now) - (RETRIEVAL_RESERVE if science else 0)
    if seconds <= 0:
        raise ValueError("immutable deadline leaves no permitted time")
    return seconds


def same_assignment(a, receipt):
    if receipt.get("assignment_sha256") != digest(canonical(a)):
        raise ValueError("receipt does not match immutable assignment")


def validate_guard_receipt(a, receipt, now=None):
    remaining(a, now, science=True)
    same_assignment(a, receipt)
    if receipt.get("status_http") != 200 or receipt.get("status_id") != a["pod_id"]:
        raise ValueError("guard status must be HTTP 200 with own body ID")
    if receipt.get("credential_source") != "/workspace/.env" and not (receipt.get("credential_source") == "mac_account_env" and receipt.get("guard_location") == "mac" and receipt.get("guards_verified_at")):
        raise ValueError("guard credential/location receipt missing")
    if len(receipt.get("guard_pids", [])) != 2 or len(set(receipt["guard_pids"])) != 2 or set(receipt.get("guard_logs", {})) != {"hardstop", "watchdog"}:
        raise ValueError("both guard receipts required")
    if not all(type(pid) is int and pid > 1 for pid in receipt["guard_pids"]):
        raise ValueError("invalid guard PID")
    if receipt.get("hard_deadline") != a["hard_deadline"]:
        raise ValueError("hard deadline changed")


def private_env(path):
    values = {}
    for line in Path(path).read_text().splitlines():
        line = line.removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw = line.split("=", 1)
        if key.strip() in {"RUNPOD_API_KEY", "HF_TOKEN"}:
            parts = shlex.split(raw, comments=True)
            if len(parts) != 1:
                raise ValueError("malformed credential file entry")
            values[key.strip()] = parts[0]
    if not values.get("RUNPOD_API_KEY"):
        raise ValueError("account credential missing from supplied .env file")
    return values


def provider(pod, key, method="GET"):
    """Never propagate response bodies/headers containing provider secrets."""
    if method not in {"GET", "POST", "DELETE"}:
        raise ValueError("unsupported provider method")
    if method == "GET":
        query = 'query { pod(input: {podId: ' + json.dumps(pod) + '}) { id desiredStatus } }'
        request = urllib.request.Request("https://api.runpod.io/graphql", data=canonical({"query": query}),
            headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "curl/8.7.1"})
    else:
        url = "https://rest.runpod.io/v1/pods/" + pod + ("/stop" if method == "POST" else "")
        request = urllib.request.Request(url, method=method, headers={"Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read()
            body = json.loads(raw) if raw else {}
            if method == "GET":
                if body.get("errors") or "data" not in body or "pod" not in body["data"]:
                    return 502, {}
                pod_body = body["data"]["pod"]
                return (404, {}) if pod_body is None else (response.status, pod_body)
            return response.status, body
    except urllib.error.HTTPError as exc:
        return exc.code, {}
    except Exception:
        raise RuntimeError("provider transport failed; details redacted") from None


def checked_status(pod, envfile, call=provider):
    code, body = call(pod, private_env(envfile)["RUNPOD_API_KEY"])
    if code != 200 or body.get("id") != pod:
        raise RuntimeError("rule-9 refused: status is not 200 with own ID")
    return {"status_http": code, "status_id": pod, "credential_source": str(envfile)}


def own_id(pod, environ=Path("/proc/1/environ")):
    ids = [p.split(b"=", 1)[1].decode() for p in Path(environ).read_bytes().split(b"\0")
           if p.startswith(b"RUNPOD_POD_ID=")]
    if ids != [pod]:
        raise RuntimeError("native container ID mismatch; nothing staged")


def endpoint(pod, key):
    """Only the assigned pod's own query; never a shared pods listing."""
    query = 'query { pod(input: {podId: ' + json.dumps(pod) + '}) { id runtime { ports { ip isIpPublic privatePort publicPort } } } }'
    request = urllib.request.Request("https://api.runpod.io/graphql", data=canonical({"query": query}),
                                     headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": "curl/8.7.1"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            value = json.loads(response.read())
        p = value["data"]["pod"]
        if p["id"] != pod:
            raise ValueError()
        ports = [r for r in p["runtime"]["ports"] if r["privatePort"] == 22 and r["isIpPublic"]]
        if len(ports) != 1:
            raise ValueError()
        return {"ip": ports[0]["ip"], "port": int(ports[0]["publicPort"])}
    except Exception:
        raise RuntimeError("assigned pod's own API entry has no verified SSH endpoint") from None


def ssh_cmd(state):
    cfg = read_json(Path(state) / "connection.json")
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20", "-p", str(cfg["port"]),
            "-i", cfg["ssh_key"], "root@" + cfg["ip"]]


def remote(state, command, data=None, capture=True):
    result = subprocess.run(ssh_cmd(state) + [command], input=data,
                            stdout=subprocess.PIPE if capture else None, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError("remote operation failed; inspect sanitized remote logs")
    return result.stdout


def git(*args):
    return subprocess.check_output(["git", *args])


def verify_frozen_git(a):
    if git("status", "--porcelain").strip():
        raise ValueError("prepare only from a clean committed worktree")
    if git("rev-parse", "HEAD").decode().strip() != a["source_commit"]:
        raise ValueError("HEAD does not match frozen source commit")
    pushed = git("ls-remote", "origin", "refs/heads/r/x4").decode().split()
    if not pushed or pushed[0] != a["source_commit"]:
        raise ValueError("exact source must be pushed on r/x4 before launch")
    subprocess.run(["git", "merge-base", "--is-ancestor", a["candidate_commit"], a["source_commit"]], check=True)
    for commit in (a["candidate_commit"], a["source_commit"]):
        raw = git("show", commit + ":" + CANDIDATE_REL)
        if digest(raw) != a["candidate_file_sha256"]:
            raise ValueError("frozen candidate bytes changed")
        if json.loads(raw).get("sha256_items") != a["candidate_sha"]:
            raise ValueError("candidate semantic SHA mismatch")


def prepare(a, state):
    validate_assignment(a)
    verify_frozen_git(a)
    from projects.g_agreement.r_bench import x4b_cue_run as runner
    a = dict(a, source_hashes={path: digest(git("show", a["source_commit"] + ":" + path)) for path in runner.SOURCE_FILES})
    state = Path(state).resolve()
    state.mkdir(parents=True, exist_ok=False)
    write_new(state / "assignment.json", a)
    (state / "source.tar").write_bytes(git("archive", "--format=tar", a["source_commit"]))
    guards = {name: git("show", a["source_commit"] + ":" + GUARD_REL + "/" + name).decode() for name in GUARDS}
    write_new(state / "guards.json", guards)
    (state / "ops_source.py").write_bytes(git("show", a["source_commit"] + ":projects/g_agreement/r_bench/x4b_cue_ops.py"))
    write_new(state / "bundle.json", {"assignment_sha256": digest(canonical(a)),
                                      "archive_sha256": digest((state / "source.tar").read_bytes()),
                                      "ops_source_sha256": digest((state / "ops_source.py").read_bytes()),
                                      "guards_sha256": {k: digest(v.encode()) for k, v in guards.items()}})
    return state



def verified_bundle(state):
    state = Path(state)
    bundle = read_json(state / "bundle.json")
    assignment = read_json(state / "assignment.json")
    same_assignment(assignment, bundle)
    archive = (state / "source.tar").read_bytes()
    code = (state / "ops_source.py").read_text()
    guards = read_json(state / "guards.json")
    if digest(archive) != bundle["archive_sha256"] or digest(code.encode()) != bundle["ops_source_sha256"]:
        raise ValueError("frozen source payload changed after prepare")
    if set(guards) != set(GUARDS) or {k: digest(v.encode()) for k, v in guards.items()} != bundle["guards_sha256"]:
        raise ValueError("frozen guard scripts changed after prepare")
    return assignment, archive, code, guards


def bootstrap(payload):
    """First remote command. Only native-ID check precedes guard bootstrap."""
    a = payload["assignment"]
    own_id(a["pod_id"])
    remaining(a)
    root = Path(REMOTE_OPS)
    root.mkdir(parents=True, exist_ok=False)
    envfile = Path("/workspace/.env")
    old_lines = envfile.read_text().splitlines() if envfile.exists() and not a["off_volume"] else []
    preserved = [line for line in old_lines if not re.match(r"^(?:export )?(RUNPOD_API_KEY|HF_TOKEN)=", line)]
    with envfile.open("w") as stream:
        stream.write("\n".join(preserved) + ("\n" if preserved else ""))
        for key, value in payload["private"].items():
            if key not in {"RUNPOD_API_KEY", "HF_TOKEN"}:
                raise ValueError("unsupported secret field")
            stream.write(key + "=" + shlex.quote(value) + "\n")
        if not any(re.match(r"^(?:export )?HF_HOME=", line) for line in preserved):
            stream.write("HF_HOME=/workspace/hf_cache\n")
    envfile.chmod(0o600)
    status = checked_status(a["pod_id"], envfile)
    (root / "x4b_cue_ops.py").write_text(payload["code"])
    write_new(root / "assignment.json", a)
    for name, content in payload["guards"].items():
        if name not in GUARDS:
            raise ValueError("unexpected guard script")
        (root / name).write_text(content)
    env = {k: v for k, v in os.environ.items() if not k.startswith("WD_") and k != "RUNPOD_API_KEY"}
    env.update(WD_INTERVAL="60", WD_CEIL="45", WD_IDLE="15", WD_GROW="300", WD_ENVFILE=str(envfile))
    env["WD_CHECK_CMD"] = shlex.join([sys.executable, str(root / "x4b_cue_ops.py"), "check-status",
                                      "--pod", a["pod_id"], "--env-file", str(envfile)])
    pids = {}
    for name, args in (("hardstop", [str(max(0, remaining(a) - 60))]),
                       ("watchdog", [str(root / "job.pid"), str(root / "runner.log")])):
        with (root / (name + ".log")).open("w") as log:
            process = subprocess.Popen(["bash", str(root / ("ws2_" + name + ".sh")), a["pod_id"], *args],
                                       stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                       start_new_session=True, env=env)
        pids[name] = process.pid
    for _ in range(30):
        if all("armed: credential" in (root / (name + ".log")).read_text() for name in pids):
            break
        time.sleep(1)
    else:
        raise RuntimeError("both guards did not log armed; no staging authorized")
    for pid in pids.values():
        os.kill(pid, 0)
    receipt = {**status, "assignment_sha256": digest(canonical(a)), "guard_pids": [pids["hardstop"], pids["watchdog"]],
               "guard_logs": {name: str(root / (name + ".log")) for name in pids}, "status_id_matched": True,
               "hard_deadline": a["hard_deadline"], "armed_at": time.time()}
    write_new(root / "guard_receipt.json", receipt)
    print(json.dumps(receipt))


def expire(state, envfile):
    state = Path(state)
    a = read_json(state / "assignment.json")
    while time.time() < a["hard_deadline"] - 30:
        if (state / "closed.json").exists():
            return
        time.sleep(min(10, max(0, a["hard_deadline"] - 30 - time.time())))
    if (state / "closed.json").exists():
        return
    # Deadline/idle safety guards stop; off-volume deletion waits for verified pull.
    key = private_env(envfile)["RUNPOD_API_KEY"]
    while True:
        try:
            code, _ = provider(a["pod_id"], key, "POST")
        except RuntimeError:
            code = 0
        with (state / "deadline_events.jsonl").open("a") as stream:
            stream.write(json.dumps({**ops_provenance(), "at": time.time(), "pod_id": a["pod_id"], "http": code}) + "\n")
        if 200 <= code < 300:
            return
        try:
            code, body = provider(a["pod_id"], key)
        except RuntimeError:
            code, body = 0, {}
        if code == 404 or (code == 200 and body.get("id") == a["pod_id"] and body.get("desiredStatus") == "EXITED"):
            return
        time.sleep(30)


def arm(state, envfile, ssh_key):
    state = Path(state).resolve()
    a, archive, code, guards = verified_bundle(state)
    remaining(a, science=True)
    if (state / "connection.json").exists():
        raise ValueError("already attempted; reconcile durable state, never re-arm/reset")
    checked_status(a["pod_id"], envfile)
    private = private_env(envfile)
    connection = endpoint(a["pod_id"], private["RUNPOD_API_KEY"])
    write_new(state / "connection.json", {**connection, "ssh_key": str(Path(ssh_key).resolve())})
    with (state / "deadline.log").open("w") as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "expire", "--state", str(state),
                                    "--env-file", str(Path(envfile).resolve())], stdout=log, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, start_new_session=True)
    write_new(state / "local_guard.json", {"pid": process.pid, "hard_deadline": a["hard_deadline"]})
    payload = {"assignment": a, "private": private, "code": code, "guards": guards}
    # Source and private payload travel via stdin, never argv, environment, or logs.
    program = "import json,sys; p=json.load(sys.stdin); ns={'__name__':'x4b_bootstrap'}; exec(p['code'],ns); ns['bootstrap'](p)"
    try:
        output = remote(state, "python3 -c " + shlex.quote(program), canonical(payload))
        receipt = json.loads(output)
        validate_guard_receipt(a, receipt)
    except Exception:
        try:
            code, _ = provider(a["pod_id"], private["RUNPOD_API_KEY"], "POST")
        except RuntimeError:
            code = 0
        write_new(state / "arm_failed.json", {"pod_id": a["pod_id"], "at": time.time(), "stop_http": code, "reconcile_required": True})
        raise RuntimeError("guard startup failed; explicit-ID stop attempted; reconcile receipts") from None
    write_new(state / "guard_receipt.json", receipt)
    remote(state, "cat > " + REMOTE_OPS + "/source.tar", archive)
    remote(state, "echo " + shlex.quote(digest(archive) + "  " + REMOTE_OPS + "/source.tar") + " | sha256sum --check --status && mkdir " + REMOTE_REPO + " && tar -xf " + REMOTE_OPS + "/source.tar -C " + REMOTE_REPO)
    remote(state, "printf '%s\\n' " + shlex.quote(a["source_commit"]) + " > " + REMOTE_REPO + "/GIT_SHA")
    cache_target = "/workspace/x4b_data/cache" if a["off_volume"] else "/workspace/mats-minis/cache"
    remote(state, "mkdir -p " + cache_target + " && ln -s " + cache_target + " " + REMOTE_REPO + "/cache")
    remote(state, "ls -la " + REMOTE_REPO + "/cache", capture=False)
    return receipt


def phase_receipt(a, guard, phase, selection=None):
    validate_guard_receipt(a, guard)
    receipt = {**a, **guard, "phase": phase, "expected_candidate_sha": a["candidate_sha"],
               "integrator_confirmation": a["integrator_clearance"]}
    if phase != "select":
        if selection is None:
            raise ValueError("selection freeze required before reader or probe work")
        same_assignment(a, selection)
        if selection.get("selection_pull_verified") is not True or selection.get("selection_push_verified") is not True:
            raise ValueError("selection must be pulled, hash verified, committed and pushed")
        if selection.get("gate_passed") is not True:
            raise ValueError("selection gate failed: NOT RUN")
        if not re.fullmatch(r"[a-f0-9]{40}", selection.get("selected_commit", "")):
            raise ValueError("retained commit missing")
        if not re.fullmatch(r"[a-f0-9]{64}", selection.get("selected_sha", "")):
            raise ValueError("retained SHA missing")
        receipt.update(selection)
    return receipt


def stage_phases(stage):
    if stage not in {"select", "evaluate"}:
        raise ValueError("unknown stage: " + str(stage))
    return ["select"] if stage == "select" else ["capture", "smoke", "run"]


def chain_text(stage):
    if stage not in {"select", "evaluate"}:
        raise ValueError("unknown stage")
    phases = stage_phases(stage)
    lines = ["#!/usr/bin/env bash", "set -euo pipefail", "cd " + REMOTE_REPO,
             'echo "$$" > ' + REMOTE_OPS + "/job.pid", "set -a", "source /workspace/x4b_ops/model.env", "set +a",
             "unset RUNPOD_API_KEY", "export PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_DISABLE_XET=1 OMP_NUM_THREADS=4"]
    if stage == "select":
        lines += ["python3 -m venv --system-site-packages /workspace/x4b_venv",
                  "/workspace/x4b_venv/bin/python -m pip install --disable-pip-version-check transformers==5.18.0 peft==0.21.2 accelerate==1.15.0 huggingface_hub==1.33.0 safetensors==0.8.0 tokenizers==0.23.2 numpy==2.5.3 scipy==1.18.1 scikit-learn==1.9.1 PyYAML==6.0.3",
                  "/workspace/x4b_venv/bin/python " + REMOTE_OPS + "/x4b_cue_ops.py runtime-check --state " + REMOTE_OPS,
                  "/workspace/x4b_venv/bin/python -m pip freeze > " + REMOTE_OPS + "/venv_freeze.txt"]
    for phase in phases:
        bank = CANDIDATE_REL
        lines += [shlex.join(["/workspace/x4b_venv/bin/python", "-m", MODULE, phase,
                             "--bank", bank, "--out", DATA_REL, "--receipt", REMOTE_OPS + "/" + phase + ".json"])]
    lines += ["touch " + REMOTE_OPS + "/" + stage + ".DONE",
              "# Explicit retrieval/finalization is a separate integrator step; never an EXIT stop."]
    return "\n".join(lines) + "\n"


def launch(state, stage):
    state = Path(state)
    a, guard = read_json(state / "assignment.json"), read_json(state / "guard_receipt.json")
    remaining(a, science=True)
    phases = stage_phases(stage)
    selection = None if stage == "select" else read_json(state / "selection_freeze.json")
    for phase in phases:
        receipt = phase_receipt(a, guard, phase, selection)
        remote(state, "test ! -e " + REMOTE_OPS + "/" + phase + ".json && cat > " + REMOTE_OPS + "/" + phase + ".json", canonical(receipt))
    script = chain_text(stage).encode()
    remote(state, "test ! -e " + REMOTE_OPS + "/" + stage + ".sh && cat > " + REMOTE_OPS + "/" + stage + ".sh", script)
    live = " && ".join("kill -0 " + str(pid) for pid in guard["guard_pids"])
    remote(state, live + " && (setsid nohup bash " + REMOTE_OPS + "/" + stage + ".sh >> " + REMOTE_OPS + "/runner.log 2>&1 < /dev/null &)", capture=False)
    write_new(state / (stage + "_launch.json"), {"at": time.time(), "hard_deadline": a["hard_deadline"], "chain_sha256": digest(script)})


def tree_manifest(root):
    root = Path(root)
    manifest = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("snapshot cannot contain symlinks: " + str(path))
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            if path.name == ".env" or path.suffix == ".pem":
                raise ValueError("secret file excluded from snapshots: " + str(path))
            manifest[rel] = digest(path.read_bytes())
    return manifest


def verify_pull(before, after, local):
    if not before or before != after or before != local:
        raise ValueError("pull hash mismatch or files changed during retrieval: " + repr(sorted(k for k in set(before) | set(after) | set(local) if before.get(k) != after.get(k) or before.get(k) != local.get(k))))
    return {"verified": True, "file_count": len(local), "manifest_sha256": digest(canonical(local))}



def require_quiescent(state):
    # Check the recorded chain PID, never an ambiguous process-name search.
    program = ("import pathlib,os; p=pathlib.Path(" + repr(REMOTE_OPS + "/job.pid") + "); "
               "pid=int(p.read_text()) if p.exists() else 0; "
               "live=pid>1 and pathlib.Path('/proc/'+str(pid)).exists(); "
               "assert not live, 'X4b chain still alive: wait for exit before pull/closure'")
    remote(state, "python3 -c " + shlex.quote(program))


def snapshot_manifest_command(stage, snapshot=None):
    snap = snapshot or REMOTE_OPS + "/snapshot-" + stage
    rawroot = REMOTE_REPO + "/" + DATA_REL
    program = "import sys,json;sys.path.insert(0," + repr(REMOTE_OPS) + ");import x4b_cue_ops as o; print(json.dumps({'data/'+k:v for k,v in o.tree_manifest(" + repr(rawroot) + ").items()} | {'ops/'+k:v for k,v in o.tree_manifest(" + repr(snap) + ").items()},sort_keys=True))"
    return "python3 -c " + shlex.quote(program)


def verify_closure_snapshot(state, a, receipt, stage, envfile):
    saved = read_json(Path(receipt["destination"]) / "verified_manifest.json")
    if digest(canonical(saved)) != receipt.get("manifest_sha256"):
        raise ValueError("local verified manifest changed after pull")
    if not receipt.get("quiescent"):
        raise ValueError("pull did not certify a quiescent chain")
    code, body = provider(a["pod_id"], private_env(envfile)["RUNPOD_API_KEY"])
    if code == 200 and body.get("id") == a["pod_id"] and body.get("desiredStatus") == "EXITED":
        if stage == "failed" or not receipt.get("complete_stage"):
            raise ValueError("stopped pod requires a previously verified completed-stage pull")
        return
    if code != 200 or body.get("id") != a["pod_id"]:
        raise ValueError("own-ID status unavailable before closure")
    require_quiescent(state)
    current = json.loads(remote(state, snapshot_manifest_command(stage, receipt["remote_snapshot"])))
    if current != saved:
        raise ValueError("new or changed output since pull; retrieve again before closure")


def pull(state, stage, destination):
    state, destination = Path(state), Path(destination).resolve()
    a = read_json(state / "assignment.json")
    if stage not in {"select", "evaluate", "failed"}:
        raise ValueError("unknown pull stage")
    if stage != "failed":
        remote(state, "test -f " + REMOTE_OPS + "/" + stage + ".DONE")
    require_quiescent(state)
    # Snapshot metadata once. Guard logs may continue growing; their copied bytes do not.
    pull_id = str(time.time_ns())
    snap = REMOTE_OPS + "/snapshot-" + stage + "-" + pull_id
    code = "import pathlib,shutil; p=pathlib.Path(" + repr(snap) + "); p.mkdir(); "
    code += "[(shutil.copy2(f,p/f.name)) for f in pathlib.Path(" + repr(REMOTE_OPS) + ").iterdir() if f.is_file() and f.suffix in {'.json','.jsonl','.log','.sh','.py','.txt'}]"
    remote(state, "python3 -c " + shlex.quote(code))
    rawroot = REMOTE_REPO + "/" + DATA_REL
    command = snapshot_manifest_command(stage, snap)
    before = json.loads(remote(state, command))
    destination.mkdir(parents=True, exist_ok=False)
    for name, path in (("data", rawroot), ("ops", snap)):
        target = destination / name
        target.mkdir()
        archive = remote(state, "tar -cf - -C " + path + " .")
        subprocess.run(["tar", "-xf", "-", "-C", str(target)], input=archive, check=True)
    after = json.loads(remote(state, command))
    result = verify_pull(before, after, tree_manifest(destination))
    result.update(stage=stage, assignment_sha256=digest(canonical(a)), destination=str(destination), verified_at=time.time(),
                  quiescent=True, complete_stage=stage in {"select", "evaluate"}, remote_snapshot=snap, pull_id=pull_id)
    write_new(state / (stage + "_pull." + pull_id + ".json"), result)
    latest = state / (stage + "_pull.latest.tmp")
    write_new(latest, result)
    os.replace(latest, state / (stage + "_pull.json"))
    write_new(destination / "verified_manifest.json", before)
    return result


def freeze_receipt(state, selected, commit):
    state, selected = Path(state), Path(selected)
    a = read_json(state / "assignment.json")
    remaining(a, science=True)
    pulled = read_json(state / "select_pull.json")
    same_assignment(a, pulled)
    if pulled.get("verified") is not True:
        raise ValueError("selection pull unverified")
    bank = read_json(selected)
    raw = selected.read_bytes()
    snapshot = Path(pulled["destination"])
    selection_bytes = (snapshot / "data/selection.jsonl").read_bytes()
    if bank.get("selection_rows_sha") != digest(selection_bytes) or bank.get("candidate_sha") != a["candidate_sha"]:
        raise ValueError("retained bank does not derive from the verified selection pull")
    if git("show", commit + ":" + SELECTED_REL) != raw:
        raise ValueError("selected bytes differ from retained commit")
    pushed = git("ls-remote", "origin", "refs/heads/r/x4").decode().split()
    if not pushed or pushed[0] != commit:
        raise ValueError("retained commit must be pushed before readers")
    subprocess.run(["git", "merge-base", "--is-ancestor", a["source_commit"], commit], check=True)
    receipt = {"assignment_sha256": digest(canonical(a)), "selected_commit": commit,
               "selected_sha": bank["sha256_items"], "selected_file_sha256": digest(raw),
               "gate_passed": bank.get("passed") is True,
               "selection_pull_verified": True, "selection_push_verified": True,
               "selection_manifest_sha256": pulled["manifest_sha256"], "frozen_at": time.time()}
    phase_receipt(a, read_json(state / "guard_receipt.json"), "capture", receipt)
    write_new(state / "selection_freeze.json", receipt)
    remote(state, "test ! -e " + REMOTE_REPO + "/" + SELECTED_REL + " && cat > " + REMOTE_REPO + "/" + SELECTED_REL, raw)
    remote(state, "test ! -e " + REMOTE_REPO + "/" + DATA_REL + "/selected.json && cat > " + REMOTE_REPO + "/" + DATA_REL + "/selected.json", raw)
    return receipt


def final_action(a, pull_receipt, disposition):
    same_assignment(a, pull_receipt)
    if pull_receipt.get("verified") is not True:
        raise ValueError("cannot stop or terminate before verified pull")
    if disposition not in {"queue-empty", "cheaper-idle", "hard-cap", "handover"}:
        raise ValueError("dated integrator queue disposition required (PODS 7b)")
    if disposition == "handover":
        raise ValueError("handover is integrator-managed; retain both guards until new owner armed")
    return "DELETE" if a["off_volume"] else "POST"



def record_billing(state, event):
    """One writer (integrator) appends the measured assignment span once."""
    state = Path(state)
    if (state / "pod_billed.json").exists():
        return
    a = read_json(state / "assignment.json")
    seconds = max(0, event["at"] - a["assigned_at"])
    row = {**ops_provenance(), "type": "pod_billed", "experiment": "X4b", "brief_section": a["brief_section"],
           "pod_id": a["pod_id"], "gpu": a["gpu"], "off_volume": a["off_volume"],
           "assigned_at": a["assigned_at"], "ended_at": event["at"], "wall_s": seconds,
           "pod_hours": seconds / 3600, "source_commit": a["source_commit"], "seed": 0,
           "action": event["action"], "command": event.get("command", "python -m projects.g_agreement.r_bench.x4b_cue_ops " + ("failed-pull-stop" if event["action"] == "stop-after-failed-pull" else "finish") + " --state " + str(state)),
           "cap_seconds": a["hard_deadline"] - a["assigned_at"], "cap_overrun_s": max(0, event["at"] - a["hard_deadline"])}
    if "cost_per_hour" in a:
        row["cost_usd"] = seconds / 3600 * float(a["cost_per_hour"])
    write_new(state / "pod_billed.json", row)
    results = Path("results/g_agreement")
    results.mkdir(parents=True, exist_ok=True)
    with (results / "compute.jsonl").open("a") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(event["at"]))
    with (results / "log.md").open("a") as stream:
        stream.write(f"\n- {stamp} X4b BRIEF_R §{a['brief_section']}: pod {a['pod_id']} {event['action']}; "
                     f"assignment-to-closure {seconds:.3f}s ({seconds/3600:.6f} pod-h), seed 0, "
                     f"source {a['source_commit']}; command `{row['command']}`; durable receipts `{state}`.\n")


def failed_pull_stop(state, envfile):
    """PODS rule-8 failure addendum: stop, retain disk, tell Guiv; never delete."""
    state = Path(state)
    a = read_json(state / "assignment.json")
    key = private_env(envfile)["RUNPOD_API_KEY"]
    for _ in range(10):
        code, _ = provider(a["pod_id"], key, "POST")
        status, body = provider(a["pod_id"], key)
        if status == 200 and body.get("id") == a["pod_id"] and body.get("desiredStatus") == "EXITED":
            event = {"pod_id": a["pod_id"], "action": "stop-after-failed-pull", "at": time.time(),
                     "http": code, "status_http": status, "notify_guiv_required": True,
                     "outputs_verified": False, "termination_forbidden_until_verified_pull": True}
            write_new(state / "stopped_after_failed_pull.json", event)
            record_billing(state, event)
            return event
        time.sleep(10)
    raise RuntimeError("failed-pull stop not confirmed; tell Guiv now; guards remain active")


def finish(state, envfile, stage, disposition, queue_evidence):
    state = Path(state)
    a = read_json(state / "assignment.json")
    receipt = read_json(state / (stage + "_pull.json"))
    if (state / "evaluate_launch.json").exists() and stage == "select":
        raise ValueError("selection-only pull is stale after evaluation launch")
    if not queue_evidence.strip():
        raise ValueError("dated integrator queue evidence required")
    method = final_action(a, receipt, disposition)
    verify_closure_snapshot(state, a, receipt, stage, envfile)
    key = private_env(envfile)["RUNPOD_API_KEY"]
    for _ in range(10):
        code, _ = provider(a["pod_id"], key, method)
        status, body = provider(a["pod_id"], key)
        confirmed = status == 404 if method == "DELETE" else status == 200 and body.get("id") == a["pod_id"] and body.get("desiredStatus") == "EXITED"
        if confirmed:
            result = {"pod_id": a["pod_id"], "action": "terminate" if method == "DELETE" else "stop", "at": time.time(),
                      "queue_disposition": disposition, "queue_evidence": queue_evidence, "http": code,
                      "confirmed_http": status, "assignment_sha256": digest(canonical(a)), "pull_manifest_sha256": receipt["manifest_sha256"]}
            write_new(state / "closed.json", result)
            record_billing(state, result)
            return result
        time.sleep(10)
    raise RuntimeError("provider closure not confirmed; guards remain armed, reconcile exact ID")



def runtime_check(state):
    import torch
    state = Path(state)
    a, guard = read_json(state / "assignment.json"), read_json(state / "guard_receipt.json")
    validate_guard_receipt(a, guard)
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise ValueError("exactly one CUDA GPU required")
    info = torch.cuda.get_device_properties(0)
    gpu = info.name
    if not ("H100" in gpu or "H200" in gpu or "A100" in gpu or "RTX PRO 6000" in gpu) or info.total_memory < 78_000 * 1024**2:
        raise ValueError("actual GPU is not supported 80GB class or larger")
    value = torch.ones((128, 128), device="cuda", dtype=torch.bfloat16)
    out = value @ value
    torch.cuda.synchronize()
    if not bool(torch.isfinite(out).all()) or float(out[0, 0]) != 128:
        raise ValueError("CUDA smoke arithmetic failed")
    write_new(state / "runtime.json", {"gpu": gpu, "memory_bytes": info.total_memory,
              "torch": torch.__version__, "cuda": torch.version.cuda, "passed": True, "at": time.time()})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "arm", "select", "evaluate", "pull", "freeze", "finish", "expire", "check-status", "render-chain", "runtime-check", "failed-pull-stop"))
    parser.add_argument("--state", type=Path)
    parser.add_argument("--assignment", type=Path)
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--ssh-key", type=Path)
    parser.add_argument("--pod")
    parser.add_argument("--stage", choices=("select", "evaluate", "failed"))
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--selected", type=Path, default=Path(SELECTED_REL))
    parser.add_argument("--commit")
    parser.add_argument("--queue-disposition")
    parser.add_argument("--queue-evidence", default="")
    parser.add_argument("--receiver-job")
    args = parser.parse_args(argv)
    if args.mode == "prepare":
        print(prepare(read_json(args.assignment), args.state))
    elif args.mode == "arm":
        from projects.g_agreement.r_bench import x4b_cue_mac
        print(json.dumps(x4b_cue_mac.arm(args.state, args.env_file, args.ssh_key)))
    elif args.mode in {"select", "evaluate"}:
        from projects.g_agreement.r_bench import x4b_cue_mac
        x4b_cue_mac.launch(args.state, args.mode)
    elif args.mode == "pull":
        print(json.dumps(pull(args.state, args.stage, args.destination)))
    elif args.mode == "freeze":
        print(json.dumps(freeze_receipt(args.state, args.selected, args.commit)))
    elif args.mode == "failed-pull-stop":
        print(json.dumps(failed_pull_stop(args.state, args.env_file)))
    elif args.mode == "finish":
        from projects.g_agreement.r_bench import x4b_cue_mac
        print(json.dumps(x4b_cue_mac.finish(args.state, args.env_file, args.stage, args.queue_disposition, args.queue_evidence, args.receiver_job)))
    elif args.mode == "expire":
        expire(args.state, args.env_file)
    elif args.mode == "check-status":
        checked_status(args.pod, args.env_file)
        print("200")
    elif args.mode == "runtime-check":
        runtime_check(args.state)
    elif args.mode == "render-chain":
        print(chain_text(args.stage))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # No HTTP bodies, private payloads, or subprocess output printed here.
        print("X4b OPS FAILED: " + type(exc).__name__ + ": " + str(exc), file=sys.stderr)
        raise SystemExit(2) from None
