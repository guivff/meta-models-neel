"""Abort gate (Guiv, 2026-10-18): every dataset/items_r*.json under <tree root> must match manifest/frozen_config_r.json byte for byte.

Usage: python3 ws2_verify_banks.py <tree root>   (exit = number of mismatches).
The bank list is the manifest's own items_sha256 (never typed here). A bank the manifest names that is missing or differs,
and an items_r*.json on the tree that the manifest does not name (rule 10 decoy test, 2026-10-20: the docstring's "every"
was not checked), each count as a mismatch and are named."""
import glob, hashlib, json, os, sys
root = sys.argv[1]
man = json.load(open(f"{root}/projects/g_agreement/manifest/frozen_config_r.json"))["items_sha256"]
bad = 0
for name, sha in sorted(man.items()):
    try:
        h = hashlib.sha256(open(f"{root}/projects/g_agreement/dataset/{name}", "rb").read()).hexdigest()
    except FileNotFoundError:
        h = "MISSING"
    ok = h == sha
    bad += not ok
    print(f"{name:16s} {'OK  ' if ok else 'DIFF'} {h[:16]} manifest {sha[:16]}")
for path in sorted(glob.glob(f"{root}/projects/g_agreement/dataset/items_r*.json")):
    name = os.path.basename(path)
    if name not in man:
        bad += 1
        print(f"{name:16s} NOT IN MANIFEST (an unfrozen bank on the tree)")
print("ALL BANKS MATCH" if not bad else f"MISMATCH: {bad} -> do not run")
sys.exit(bad)
