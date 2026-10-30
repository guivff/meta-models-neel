# E37 dated operational reading — 2026-10-26

§134 clarification 3 (`be450eb9`) releases the original conditional build. No E37 forward or scientific score exists.

The manifest key is added in E37's own CHECKPOINT_MANIFEST_2026-10-26.json. The shared asset manifest is already bound to running experiments and remains unchanged. The selected staged directory is supplied to checkpoint_cpu.py, then byte-bound through CHECKPOINT_RECEIPT.json and the assignment.

PEFT name normalisation removes wrapper prefixes and the optional adapter name only. Comparison covers the union of tensor names, shape, dtype and exact equality. If original tensors differ, a name-normalised PEFT loading copy retains every original tensor exactly; the raw download and an exact CPU comparison of the loading copy are retained. The HF adapter config is pinned; incompatible tensors/configs stop at load verification. Corrupt tensors are not a download-unavailable fallback.

Anonymous access to the one pinned original file returned HTTP 401 locally. This is the registered NOT POSSIBLE branch; lora_hf is selected and the README identity claim is unverified. No credentials were used. The Integrator repeats the mandatory CPU gate against its bound staging input before any forward.

The existing E33 helper is copied byte-for-byte from E37's v1 source archive to e33_runtime_frozen.py (sha256 2fa88c71882e1603576e7c0b2568617fcf0a541109b6a61eb21e3f867a6f0acb), preserving the originally tested loader/scoring helper without changing E33. PLAN, smoke IDs, parity thresholds, input seal, channels, row population and rules remain byte-identical.

The RL three-row reproduction runs before smoke or SFT scoring. A scientific parity failure stops without retry. §154 moves the operational programme stop to 2026-10-29 22:59 UTC; the 5400-second cap and arrival deadline stay unchanged. The optional space-RL descriptive arm is omitted.
