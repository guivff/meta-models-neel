"""Verified pull (PODS.md rule 8 / GUARDS.md rule 4, WS2 2026-10-20): the Mac's pulled copy must equal the pod's outputs, file by file.

Usage: python3 ws2_verify_pull.py <pod_manifest.txt> <dest_dir> <podId> <suffix>   (exit 0 = verified, 1 = not)

<pod_manifest.txt> is `sha256sum` output taken ON THE POD from the job tree, paths relative to it: cache/g_agreement/r/<x> (pulled
to <dest>/cache/<x>) and results/g_agreement/<y> (pulled to <dest>/results/<y>). Not verified, each named: an empty manifest
(nothing to verify is not a verified pull), a file missing on the Mac, a sha that differs, a manifest path outside those two
trees, and a *.<suffix>* file on the Mac that the pod's manifest does not list. Verified: <dest>/PULL_VERIFIED.json (pod, files,
manifest sha256, time); a failed check removes any earlier marker, so a stale one never stands.
"""
import datetime, hashlib, json, os, sys

man_path, dest, pod, sfx = sys.argv[1:5]
ROOTS = {"cache/g_agreement/r/": "cache/", "results/g_agreement/": "results/"}
raw = open(man_path, "rb").read()
bad, seen = [], set()
lines = [ln for ln in raw.decode().splitlines() if ln.strip()]
if not lines:
    bad.append("empty pod manifest (no *.%s* outputs on the pod)" % sfx)
for ln in lines:
    sha, _, rel = ln.partition("  ")
    rel = rel.strip().lstrip("./")
    mac = next((v + rel[len(k):] for k, v in ROOTS.items() if rel.startswith(k)), None)
    if mac is None:
        bad.append(f"{rel}: outside the pulled trees")
        continue
    seen.add(mac)
    try:
        h = hashlib.sha256(open(os.path.join(dest, mac), "rb").read()).hexdigest()
    except FileNotFoundError:
        bad.append(f"{rel}: MISSING on the Mac")
        continue
    if h != sha.strip():
        bad.append(f"{rel}: sha differs (pod {sha.strip()[:12]}, Mac {h[:12]})")
for top in ROOTS.values():
    for d, _, files in os.walk(os.path.join(dest, top)):
        for f in files:
            rel = os.path.relpath(os.path.join(d, f), dest)
            if f".{sfx}" in f and rel not in seen:
                bad.append(f"{rel}: on the Mac but not in the pod's manifest")
marker = os.path.join(dest, "PULL_VERIFIED.json")
if bad:
    if os.path.exists(marker):
        os.remove(marker)
    print(f"pull NOT VERIFIED for {pod}: " + "; ".join(bad))
    sys.exit(1)
json.dump({"pod": pod, "suffix": sfx, "files": len(lines), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
           "verified_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, open(marker, "w"), indent=1)
print(f"pull VERIFIED for {pod}: {len(lines)} files, manifest sha256 {hashlib.sha256(raw).hexdigest()[:16]}")
