## §135 Second budget increase (25 Oct, 14:20 CET): parallelism and a wider replication

**Dated note (Guiv, recorded by the coordinator), operations and budget only, before any score of the affected runs.**
Guiv has added a further USD 500 (total additional USD 1,000 today). Rulings:
- **Pod ceiling 8 → 12.** Minimum spacing between deploys drops from 5 to 3 minutes, enforced through the integrator's
  global deploy lock. An operator that cannot obtain an H200 within 15 minutes may use an H100 80 GB only where the
  request's memory check passes, or a B200, recording the GPU type in its receipt.
- **Wider shards, same budgets.** Any run may split across more pods than its request names (E24 up to 8, E33 up to 4,
  E28 up to 4), provided each shard has its own warmed forecast and the run's total GPU-h cap is unchanged. Splitting
  changes wall-clock, not science.
- **E36 widened** (§132) to all 25 W1 rows instead of 8, with the same channels and rules H1–H5 applied to the 16
  structure and 9 content rows; cap raised from 3 to **≤ 8 GPU-h**. W-text writes the extra templates under the same
  blindness rule. If the 25-row bank cannot be frozen by Monday 12:00 CET, the 8-row bank runs alone as registered.
- **E30 on the second bank:** once E36's bank is frozen, E30's value-word scoring (frozen `CANDIDATES.json`) is applied
  to it as well, ≤ 0.5 GPU-h, as a replication of E30's R1/R2.
- Remaining reserve after these rulings ≈ USD 640, held for reruns and Monday's results.


---
