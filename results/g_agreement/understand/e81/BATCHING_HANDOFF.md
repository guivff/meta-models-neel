# Batched E81/E90 and I-2 reader handoff

E81 was already configured batch64, but sorted by longest prompt before batch occupancy; the first bucket had2 items. The same exact-length buckets now run full batches first. No prompt padding, duplication, decoding change or item omission. Sparse tails remain smaller, preserving exact prompt token sequences.

Run rebind_batch.py with the previous REQUEST, a fresh destination and I-2 admitted cap, --profile-only. It preserves the PUBLIC_INPUTS byte hash and freezes the new source. The worker profiles3 batches >=32 in each128/32-token phase after synthetic warmup. Each phase compares the first8 batched outputs to serial greedy; any mismatch stops. The report separates warmup/parity/setup from measured real-batch means. MEASURED_PROFILE is timing-only, never a scientific result. Production rebind requires this report and cap >= ceil(forecast_seconds), which includes1.25 margin. Regenerate all11064 records in one production job, including the previous two A1 records and all probe records.

Text output token_ids now exclude only padding after the first EOS, matching serial output exactly; decoded text is unchanged. Parity compares the entire serialized output record. CPU fixtures pass; real Qwen parity is PENDING and mandatory on the pod, never claimed from fixtures.

late198 native Oracle/NLA acquisition uses batch32 for E82/E85/E86/E91/E92, retaining128/512 limits and native stop. Each reader compares its first8 production outputs with serial. No changes to historical E56 code or old source archives. New source/input seals are required; do not launch old archives expecting this change. E82 all-position and E86 complete-answer owner bindings still must be used, not the older generic final-position/argmax contract.

Production rebind also requires --phase-timings PHASE_TIMINGS.json and --profile-seal OUTPUT_SEAL.json from the same verified probe pull. It binds both report hashes, seeds BOTH base_text128/base_text32 from their three measured real batches, and removes --profile-only even when the input request was a profiling request. The already-running probe archive remains unchanged.
