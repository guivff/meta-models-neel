"""mac_guard's verified-pull check (rule-8 safety-net amendment; PODS.md rule 10 item 2): compare the pod's manifest with the Mac's.

A manifest is ``sha256sum``-style lines ``<hex>  <relative path>`` for every row file (*.jsonl) the runner wrote under its cache root
(the pod's own complete set, from ``find`` on the pod). Verified iff the two sets of paths are equal and every sha256 matches.
Prints one ``MISMATCH <reason> <path>`` line per failing file and exits 1, else prints ``VERIFIED <n> files`` and exits 0.

    python3 projects/r_panel/verify_manifest.py <pod_manifest> <mac_manifest>
"""

from __future__ import annotations

import sys


def parse(text: str) -> dict[str, str]:
    out = {}
    for line in text.splitlines():
        if line.strip():
            h, p = line.split(None, 1)
            out[p.strip().lstrip("*").removeprefix("./")] = h
    return out


def compare(pod: dict[str, str], mac: dict[str, str]) -> list[str]:
    bad = [f"MISMATCH missing_on_mac {p}" for p in sorted(set(pod) - set(mac))]
    bad += [f"MISMATCH extra_on_mac {p}" for p in sorted(set(mac) - set(pod))]
    bad += [f"MISMATCH sha256 {p}" for p in sorted(set(pod) & set(mac)) if pod[p] != mac[p]]
    if not pod:
        bad.append("MISMATCH empty_pod_manifest -")
    return bad


def main(argv: list[str]) -> int:
    pod, mac = (parse(open(f).read()) for f in argv[:2])
    bad = compare(pod, mac)
    for b in bad:
        print(b)
    if not bad:
        print(f"VERIFIED {len(pod)} files")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
