# E67 wave 2 READY — 0a3f3691

Integrator: use e67.py with `wave: 2` in both the run spec and its verified custody receipt. Convert the two wave-2 packets separately with the existing e67_packet_adapter command plus `--wave 2`; each new PACKET_SEAL.json must carry wave=2. Packet IDs remain packet_0/packet_1. Old wave-1 specs/seals without a wave field remain wave 1, with unchanged paths. No wave-1 packet, output, request cache or ledger is rewritten.

Wave 2 root: `cache/g_agreement/understand/blind_judge/e67_5usd/wave_2/`. Its own ledger.jsonl, route cache, per-attempt request/response caches and E67_wave_2_packet_0_judgments / E67_wave_2_packet_1_judgments are separate from wave 1. The wave prefix enters request digests and stages as well as output paths; reused opaque IDs cannot reuse old responses. Receipt and packet-seal wave mismatches fail closed.

Both waves retain the single USD5 authorization. Under their common parent DISPATCH.lock, the runner sets the active wave's cap to USD5 minus the other wave's ledger commitments (actual charges plus unresolved reservations). Thus USD0.42 committed by wave 1 leaves USD4.58, not a fresh USD5, for wave 2. Existing reserve-before-send checks also count the active wave's previous commitments. Both packets in wave 2 use its one ledger. No manual ledger reset or launch outside e67.py.

Lock handling: all observed judging DISPATCH.lock files, including E67's, were unheld on the read-only kernel-lock check. They remain in place. A leftover filename is not a lock: flock acquires the existing inode and releases on exit/exception. Never unlink DISPATCH.lock; a competing process could otherwise lock a different inode. The shared helper now emits an explicit active-dispatcher error and leaves any active holder untouched. It is also used by later_runner.

33 synthetic/offline tests passed: stale-file reuse, live contention, exception release, wave seal tagging, both mock wire/output namespaces, remaining-budget accounting, and E66/E68 regression. Live readouts unopened, no conversion/judging/scientific analysis performed. Source seals refreshed; integrator executes and pushes.
