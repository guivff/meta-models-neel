## §144 Accelerating E24, E32 and E34 (26 Oct, 01:10 CET; operations; no E24/E32/E34 science exists)

1. **Conditional requests now.** W-core prepares relaunch requests for E24 and E32 now, one per candidate capture mode
   (G, E, and C/D batch-size-1), each complete and CPU-tested. When E24-E certifies a mode, the integrator launches
   the matching pair without a further build. Requests for uncertified modes are never launched.
2. **E24 sharding.** The relaunch may use up to **8 pods** (ceiling 20), splitting the same grid within the
   unchanged remaining cap of 32,738 s total.
   - Every shard runs the every-item h44 parity gate on its own items before its own science. A shard that fails
     parity stops; its cells are INCOMPLETE and it is reported.
   - R0 and every analysis rule are unchanged; the analysis runs once, on all sealed shards.
3. **E34 decoupled from E24's relaunch.** E34 uses W1's stored h44 and the reconstructor on text; it captures nothing
   new. Its hold was about whether W1's stored vectors are right. E34 is therefore released as soon as **E24-E shows
   W1's stored h44 agree with arm C** (batch size 1, no padding; every item cos ≥ 0.999). It does not wait for E24's
   relaunch. If arm C disagrees with W1, E34 stays held with everything capture-dependent (§137 item 1).
