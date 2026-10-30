## §146 Ruling on E24-E (26 Oct, 01:15 CET; before any E24/E32/E34 science)

**Facts reported.** W-core certified arm G (W1 code extended to the grid, `/weights/venv`, W1 batching; every item cos
≥ 0.999 against W1). Arm C (batch size 1, no padding) matches W1 on 482/500 items. §137 item 1 sends that case to the
coordinator.

**Ruling.**
1. **Proceed in mode G.** Every sealed result in the project used W1's stored vectors, and mode G reproduces them
   exactly. Consistency with those results is what E24, E32 and E34 need. The 18-item disagreement concerns how
   faithful W1's batched capture is, which affects all W1-based results equally. It is an audit item, not a reason to
   block.
   - **E24 and E32** relaunch in mode G (§144 sharding and per-shard parity).
   - **E34** is released on W1's stored vectors once its request is committed.
2. **Audit of the 18 items (W-core, CPU, now).**
   - **Report:** for each of the 18, its id, row, length, padding in W1's batch, and cos(W1, C), cos(W1, D) and
     cos(C, D); plus the C-vs-D agreement count over all 500 items.
   - **Sensitivity analysis:** if any of the 18 has cos(W1, C) < 0.99, the §137 item 3 audit identifies the condition
     (padding, length or row). Each headline result is then reported with and without items in that condition, as
     a sensitivity analysis; sealed verdicts do not change.
   - **No action needed:** if all 18 are ≥ 0.99, they are recorded as bf16 batching numerics.
3. **E36 and E38 continue.** E38 injects no activation. E36 runs under its own score-level W1 parity gate and records
   padding and length per item for the same audit.
