"""CPU evidence checks only. Never allocates compute, reserves funds, or issues GO."""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile
from zoneinfo import ZoneInfo

ZONE = ZoneInfo("Europe/Zurich")
FREEZE = datetime.fromisoformat("2026-10-28T18:00:00+01:00")
OMEGA_GATE = datetime.fromisoformat("2026-10-28T12:00:00+01:00")
CEILING = Decimal("300")
OCT27_CEILING = Decimal("500")
OCT27_BUDGET_AUTHORITY = "BRIEF_UNDERSTAND §190 budget note 2026-10-27 (86ba523d1044e4a26767a750259736fc2a616609)"
E74_CEILING = Decimal("100")
E74_PHASES = ("weight_staging", "archive_staging", "boot", "smoke", "capture",
              "forecast_wait", "readouts", "closeout")
MAX_ARCHIVE_BYTES = 20_000_000
ABSENT_J_RECORD = "R-G2 NOT EVALUABLE; J-lens unavailable"


class Hold(ValueError):
    pass


class NoFit(Hold):
    pass


def require(condition, message):
    if not condition:
        raise Hold(message)


def amount(value, name):
    require(type(value) in (int, float, str), name + " must be a number")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise Hold(name + " must be finite and nonnegative") from exc
    require(result.is_finite() and result >= 0, name + " must be finite and nonnegative")
    return result


def timestamp(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "timestamps require an explicit timezone")
    return result


def digest(data):
    return hashlib.sha256(data).hexdigest()


def daily_budget_authority(now):
    if now.astimezone(ZONE).date().isoformat() == "2026-10-27":
        return OCT27_CEILING, OCT27_BUDGET_AUTHORITY
    return CEILING, "original USD 300 daily ceiling; no dated increase registered for this Zurich date"


def file_bytes(ref):
    data = Path(ref["path"]).read_bytes()
    require(digest(data) == ref["sha256"], "file hash differs: " + Path(ref["path"]).name)
    return data


def document(ref):
    return json.loads(file_bytes(ref))


def git_bytes(ref, now):
    """Resolve real immutable Git objects; never trust a SHA-shaped string alone."""
    commit = ref["commit"]
    require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "full Git commit required")
    path = PurePosixPath(ref["path"])
    require(not path.is_absolute() and ".." not in path.parts and "\\" not in str(path), "unsafe Git path")

    def git(*args):
        return subprocess.check_output(["git", "-C", ref["repo"], *args], stderr=subprocess.DEVNULL)

    resolved = git("rev-parse", "--verify", commit + "^{commit}").decode().strip()
    require(resolved == commit, "reference is not the requested commit")
    committed_at = timestamp(git("show", "-s", "--format=%cI", commit).decode().strip())
    require(committed_at <= now, "commit is in the future")
    data = git("show", commit + ":" + str(path))
    require(digest(data) == ref["sha256"], "committed file hash differs")
    return data, committed_at


def private_json(value):
    forbidden = {"label", "labels", "ground_truth", "answer_key", "correct_value", "private", "key"}
    if isinstance(value, dict):
        return any(str(k).lower() in forbidden or private_json(v) for k, v in value.items())
    return isinstance(value, list) and any(private_json(v) for v in value)


def archive(ref):
    path = Path(ref["path"])
    require(path.stat().st_size <= MAX_ARCHIVE_BYTES, "archive exceeds 20,000,000 bytes")
    raw = file_bytes(ref)
    names = set()
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as tar:
        for member in tar:
            name = PurePosixPath(member.name)
            require(not name.is_absolute() and ".." not in name.parts and "\\" not in member.name,
                    "unsafe archive path")
            require(str(name) not in names, "duplicate archive member")
            names.add(str(name))
            require(member.isdir() or member.isfile(), "archive links and special files are forbidden")
            require(not re.search(r"(?i)(label|private|do_not_stage|(^|[/_.-])key([/_.-]|$))", member.name),
                    "private or labelled archive member")
            require(not re.search(r"(?i)(readouts|generations|pilot_results)", member.name),
                    "reader payloads must not be included in staging archives")
            if member.isfile() and name.suffix.lower() in (".json", ".jsonl"):
                content = tar.extractfile(member).read().decode("utf-8")
                values = [json.loads(line) for line in content.splitlines() if line.strip()] if name.suffix.lower() == ".jsonl" else [json.loads(content)]
                require(not any(private_json(value) for value in values), "private labels in archive JSON")
    return digest(raw)


def validate_e74_forecast(request, now):
    """One whole-replication forecast, including phases outside this launch."""
    raw, _ = git_bytes(request["e74_full_forecast"], now)
    full = json.loads(raw)
    require(full["scope"] == "FULL_E74", "E74 forecast must cover FULL_E74, not a stage fragment")
    git_bytes(full["source_forecast"], now)
    card = json.loads(git_bytes(request["asset_card"], now)[0])
    require(full["asset_card_sha256"] == card["source_card"]["sha256"]
            and full["input_seal_sha256"] == request["input_seal"]["sha256"],
            "E74 full forecast asset/input binding differs")
    cost = request["compute"]
    require(full["gpu_count"] == cost["gpu_count"] and full["gpu_type"] == cost["gpu_type"],
            "E74 full forecast hardware differs")
    rate = amount(full["usd_per_gpu_hour"], "E74 forecast per-GPU hourly rate")
    require(rate == amount(cost["usd_per_gpu_hour"], "per-GPU hourly rate"),
            "E74 full forecast rate differs from current launch rate")
    phases = full["phase_seconds"]
    require(set(phases) == set(E74_PHASES), "E74 full forecast requires every phase: " + ", ".join(E74_PHASES))
    seconds = {name: amount(phases[name], "E74 " + name) for name in E74_PHASES}
    require(seconds["weight_staging"] <= 3600, "E74 full forecast weight_staging exceeds 3600 seconds")
    require(seconds["archive_staging"] <= 900, "E74 full forecast archive_staging exceeds 900 seconds")
    if request["stage"] == "smoke" and "boot_smoke_cap_seconds" in full:
        cap = amount(full["boot_smoke_cap_seconds"], "package boot/smoke cap")
        require(cap > 0 and amount(cost["science_cap_seconds"], "science cap") <= cap,
                "GLM smoke exceeds the committed package boot/smoke cap")
    forecast = (Decimal(cost["gpu_count"]) * sum(seconds.values()) * rate / 3600
                + amount(full["additional_provider_usd"], "E74 full provider costs"))
    buffered = forecast * Decimal("1.25")
    if buffered > E74_CEILING:
        raise NoFit("full E74 forecast times 1.25 exceeds USD 100")
    return forecast, buffered


def validate_budget(request, now):
    snapshot = document(request["budget_snapshot"])
    require(snapshot["status"] == "RECONCILED" and snapshot["scope"] == "ALL_TRACKS", "combined reconciled snapshot required")
    as_of = timestamp(snapshot["as_of"])
    require(as_of <= now and as_of.astimezone(ZONE).date() == now.astimezone(ZONE).date(), "budget snapshot is not for the current local day")
    # Hash the CURRENT ledger. Any modification invalidates the prior reconciliation.
    file_bytes(snapshot["current_ledger"])
    if snapshot.get("provider_evidence") is not None:
        evidence = document(snapshot["provider_evidence"])
        require(evidence["authenticated"] is True and evidence["scope"] == "ALL_TRACKS", "authenticated combined provider evidence required")
        require(timestamp(evidence["retrieved_at"]) <= as_of and bool(evidence["provider"]), "provider evidence timing/source missing")
    else:
        acknowledgment = document(snapshot["q_acknowledgment"])
        require(acknowledgment["issuer"] == "Track Q integrator" and acknowledgment["status"] == "RECONCILED",
                "recorded Track Q reconciliation acknowledgment required")
        require(acknowledgment["ledger_sha256"] == snapshot["current_ledger"]["sha256"]
                and timestamp(acknowledgment["as_of"]) <= as_of, "Track Q acknowledgment is for a different ledger")
    authorised, authority = daily_budget_authority(now)
    declared = amount(snapshot["ceiling_usd"], "ceiling")
    require(declared <= authorised,
            f"declared ceiling USD {declared} exceeds authorised USD {authorised} for "
            f"{now.astimezone(ZONE).date()}: {authority}")
    billed = amount(snapshot["billed_usd"], "billed spend")
    reservations = snapshot["outstanding_reservations"]
    ids = [row["id"] for row in reservations]
    require(len(ids) == len(set(ids)) and request["run_id"] not in ids, "duplicate or already-reserved candidate")
    outstanding = sum((amount(row["usd"], "reservation") for row in reservations), Decimal(0))
    cost = request["compute"]
    count = cost["gpu_count"]
    require(type(count) is int and count > 0, "positive integer GPU count required")
    seconds = {key: amount(cost[key], key) for key in
               ("staging_seconds", "forecast_wait_seconds", "closeout_seconds", "science_cap_seconds", "forecast_seconds")}
    require(seconds["staging_seconds"] <= 900, "staging exceeds 900 seconds")
    require(seconds["science_cap_seconds"] > 0, "positive science cap required")
    duration = sum((seconds[key] for key in ("staging_seconds", "forecast_wait_seconds", "closeout_seconds", "science_cap_seconds")), Decimal(0))
    weight_staging = amount(cost.get("weight_staging_seconds", 0), "weight_staging_seconds")
    if request["track"] == "G":
        require("weight_staging_seconds" in cost, "G requires separate weight_staging_seconds, zero if already cached")
        require(weight_staging <= 3600, "weight_staging_seconds exceeds 3600 seconds")
        require(count <= 8, "GLM replica GPU count exceeds eight")
        duration += weight_staging
    else:
        require(weight_staging == 0, "separate weight staging applies only to G")
    candidate = (Decimal(count) * duration * amount(cost["usd_per_gpu_hour"], "per-GPU hourly rate") / 3600
                 + amount(cost["additional_provider_usd"], "additional provider costs"))
    detail = {}
    if request["track"] == "G":
        forecast, buffered = validate_e74_forecast(request, now)
        # Reconciled G costs already in billed/reserved totals are not charged twice.
        covered = amount(snapshot.get("e74_already_accounted_usd", 0), "already accounted E74 spend")
        require(covered <= billed + outstanding, "already accounted E74 spend exceeds the reconciled total")
        candidate = max(candidate, buffered - covered)
        detail = {"full_e74_forecast_usd": str(forecast), "full_e74_buffered_usd": str(buffered),
                  "e74_already_accounted_usd": str(covered)}
    combined = billed + outstanding + candidate
    require(combined <= declared,
            f"combined worst-case spend exceeds USD {declared} declared ceiling; "
            f"authorised daily maximum USD {authorised}: {authority}. "
            "Reconcile before launch; exceeding the authorised maximum requires Guiv's new ruling.")
    if request["track"] == "C":
        prior = amount(cost["prior_track_c_gpu_seconds"], "prior consumed/reserved Track C GPU-seconds")
        require(prior + Decimal(count) * duration <= 6 * 3600,
                "Track C prior plus candidate aggregate allocation exceeds six GPU-hours")
    if seconds["forecast_seconds"] * Decimal("1.25") > seconds["science_cap_seconds"]:
        raise NoFit("forecast times 1.25 exceeds the science cap")
    return {"billed_usd": str(billed), "outstanding_reserved_usd": str(outstanding),
            "candidate_worstcase_usd": str(candidate), "projected_combined_usd": str(combined),
            "declared_ceiling_usd": str(declared), "authorised_daily_ceiling_usd": str(authorised),
            "budget_authority": authority,
            "aggregate_gpu_seconds": str(Decimal(count) * duration), **detail}


def validate_track(request, now):
    track = request["track"]
    if track == "C":
        sampler, sampler_at = git_bytes(request["sampler"], now)
        raw, bow_at = git_bytes(request["bow_gate"], now)
        gate = json.loads(raw)
        require(gate["sampler_sha256"] == digest(sampler) and gate["input_seal_sha256"] == request["input_seal"]["sha256"], "BOW gate is bound to different sampler or inputs")
        rows = gate["rows"]
        require(len({row["state"] for row in rows}) == len(rows), "duplicate BOW state")
        by_state = {row["state"]: row for row in rows}
        states = request["states"]
        require(bool(states) and len(states) == len(set(states)), "nonempty unique census states required")
        for state in states:
            row = by_state[state]
            require(row["status"] == "PASS" and amount(row["test_auroc"], "BOW AUROC") <= Decimal("0.65"), "requested state failed the committed BOW gate")
        if request["stage"] == "readers":
            require(max(sampler_at, bow_at) <= timestamp(document(request["capture_seal"])["sealed_at"]),
                    "sampler and BOW gate must be committed before capture")
    elif track == "G":
        raw, asset_at = git_bytes(request["asset_card"], now)
        card = json.loads(raw)
        git_bytes(card["source_card"], now)
        require(card["verdict"] == "FEASIBLE" and card["anonymous_weights"] is True and card["anonymous_licence"] is True
                and card["substitutions"] is False, "GLM asset card does not pass the registered stop rule")
        count = card["gpus_per_replica"]
        require(type(count) is int and 1 <= count <= 8 and request["compute"]["gpu_count"] == count, "GLM replica GPU count differs or exceeds eight")
        hardware = request["compute"]["gpu_type"]
        require(hardware == card["hardware"], "GLM hardware differs from the asset card")
        if hardware == "B200":
            require(count in (4, 8), "GLM B200 path requires four or eight GPUs")
        else:
            require(card.get("runtime_path") == "NVFP4/W4A16" and "author_runtime_support" in card,
                    "other GLM hardware requires the author's documented NVFP4/W4A16 runtime support")
            support, _ = git_bytes(card["author_runtime_support"], now)
            require(bool(support.strip()), "author runtime support document is empty")
        require(bool(card["assets"]), "pinned GLM asset inventory missing")
        for asset in card["assets"]:
            require(bool(asset["repo_id"]) and bool(re.fullmatch(r"[0-9a-f]{40}", asset["revision"])), "exact GLM repo/revision required")
        if request["stage"] == "readers":
            require(asset_at <= timestamp(document(request["capture_seal"])["sealed_at"]),
                    "GLM asset card must be committed before capture")
    elif track == "Ω":
        require(now >= OMEGA_GATE, "Track Ω is closed before the Wednesday noon gate")
        gate = document(request["omega_gate"])
        require(gate["status"] == "PASS" and timestamp(gate["as_of"]) == OMEGA_GATE,
                "passing Wednesday noon gate required")
        require(OMEGA_GATE <= timestamp(gate["recorded_at"]) <= now, "invalid gate record time")
        capture = document(gate["c_capture_seal"])
        running = document(gate["g_capture_status"])
        require(timestamp(capture["sealed_at"]) <= OMEGA_GATE and capture["track"] == "C", "C captures were not sealed by the gate")
        require(running["track"] == "G" and running["stage"] == "capture" and running["status"] == "RUNNING"
                and timestamp(running["as_of"]) == OMEGA_GATE, "G did not have a running capture at the gate")


def validate_readers(request, now):
    capture = document(request["capture_seal"])
    require(capture["track"] == request["track"], "capture belongs to a different track")
    require(capture["input_seal_sha256"] == request["input_seal"]["sha256"], "capture/input binding differs")
    raw, committed_at = git_bytes(request["forecast"], now)
    forecast = json.loads(raw)
    require(forecast["worker"] == "W-lens", "W-lens forecast required")
    require(forecast["capture_seal_sha256"] == request["capture_seal"]["sha256"]
            and forecast["input_seal_sha256"] == request["input_seal"]["sha256"], "forecast capture/input binding differs")
    require(timestamp(capture["sealed_at"]) <= timestamp(forecast["created_at"]) <= committed_at <= now,
            "capture must precede forecast creation and actual commit")
    require(forecast["reader_outputs_accessed"] is False, "forecast custody was broken")
    if request["track"] == "G":
        card = json.loads(git_bytes(request["asset_card"], now)[0])
        if card.get("j_lens_available") is False:
            require(forecast.get("record") == ABSENT_J_RECORD, "absent-J custody record required")
        if forecast.get("record") == ABSENT_J_RECORD:
            require(forecast["asset_card_sha256"] == card["source_card"]["sha256"], "absent-J record is bound to a different asset card")
            require(forecast["rg2_not_evaluable_permanent"] is True, "R-G2 must remain permanently not evaluable")
            expected = request["rows"]
            actual = forecast["category_forecast"]
            require(bool(expected) and len({r["row"] for r in expected}) == len(expected), "unique requested GLM rows required")
            require(len({r["row"] for r in actual}) == len(actual) == len(expected), "category forecast duplicates or missing rows")
            by_row = {r["row"]: r for r in actual}
            require(set(by_row) == {r["row"] for r in expected}, "category forecast row coverage differs")
            for row in expected:
                value = by_row[row["row"]]
                require(bool(row["category"]) and value["category"] == row["category"], "category forecast changed a frozen category")
                prediction = "REPORTED" if row["category"] in ("content", "plan") else "MISSED"
                require(value["prediction"] == prediction, "category-only forecast mapping differs")


def validate(request, now=None):
    now = now or datetime.now(ZONE)
    try:
        require(now.tzinfo is not None, "current time must be timezone-aware")
        require(now < FREEZE, "new-launch freeze has begun")
        require(request["track"] in ("C", "G", "Ω"), "unknown track")
        require(request["stage"] in {"C": ("capture", "readers"), "G": ("smoke", "capture", "readers"), "Ω": ("omega",)}[request["track"]], "stage is not permitted for this track")
        require(bool(request["run_id"]), "run identity required")
        file_bytes(request["input_seal"])
        budget = validate_budget(request, now)
        refs = request["archives"]
        require(bool(refs), "exact staging archives required")
        hashes = [archive(ref) for ref in refs]
        require(len(hashes) == len(set(hashes)), "duplicate staging archive")
        preflight = document(request["cpu_preflight"])
        require(preflight["status"] == "PASS" and type(preflight["gpu_calls"]) is int and preflight["gpu_calls"] == 0,
                "passing CPU-only preflight required")
        require(sorted(preflight["archive_sha256s"]) == sorted(hashes)
                and preflight["input_seal_sha256"] == request["input_seal"]["sha256"], "CPU preflight does not bind the exact staging archives/inputs")
        validate_track(request, now)
        if request["stage"] == "readers":
            validate_readers(request, now)
        return {"status": "VALIDATED_FOR_OPERATOR_REVIEW", "track": request["track"], "run_id": request["run_id"],
                **budget, "authorises_launch": False, "issues_go": False,
                "limitation": "Evidence attestations require operator verification; funds are not reserved. Reconcile again immediately before launch."}
    except NoFit as exc:
        return {"status": "NO_FIT", "reason": str(exc), "authorises_launch": False}
    except (Hold, KeyError, TypeError, ValueError, AttributeError, OSError, subprocess.SubprocessError, tarfile.TarError) as exc:
        return {"status": "HOLD", "reason": str(exc), "authorises_launch": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request", type=Path)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.request.read_text()))
    except (OSError, ValueError) as exc:
        result = {"status": "HOLD", "reason": str(exc), "authorises_launch": False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "VALIDATED_FOR_OPERATOR_REVIEW" else 2


if __name__ == "__main__":
    raise SystemExit(main())
