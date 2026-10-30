"""E137 behaviour-only selection, Track Q's committed prospective freeze (§249; C runner packet 1408a8bd4, selection.py in C's sealed archive 539a25c0).
Calls W-mechanism-C's sealed projects.g_agreement.e137.selection.select UNCHANGED, run from a fresh extract of C's archive, with the one-hop MAIN rule frozen
here before any screen output: Guiv 2026-10-30 ~03:58Z, "First 16 one-hop (Recommended)" = first 16 qualifying one-hop pairs in source order, both members
correct, fewer if fewer qualify, no refill; with the first 42 D1 + first 42 D2 pairs this stays <= 600 registered readouts (2 members x Oracle 44/52/60).
Labels and the CPU pair map stay on the Mac; only the label-free main root is pushed to the pod.
Usage: select137.py <screen_root> <screen_sha> <out>"""
import json, sys
from projects.g_agreement.e137.selection import select
ONE_HOP_LIMIT = 16
AUTHORITY = 'Guiv 2026-10-30 ~03:58Z (Track Q question): First 16 one-hop (Recommended); frozen in Track Q select137.py before any E137 screen output'
PUBLIC_ROOT = '/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e137-inputs-v1/inputs'
INPUT_SHA = '0ea22830b2025dd63582317bb1da2101dd874e44f7a3c4eb646c17920dcb6a44'
PAIRS = '/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs/e137-bank-v1/PAIRS.PRIVATE.json'
PAIR_SHA = '92a5af53112e750be82336f0bdbfb996aa25cbe0d5b5e9102ba860f8b764e9dc'
if __name__ == '__main__':
    print(json.dumps(select(sys.argv[1], sys.argv[2], PUBLIC_ROOT, INPUT_SHA, PAIRS, PAIR_SHA, sys.argv[3], one_hop_limit=ONE_HOP_LIMIT, authority=AUTHORITY)))
