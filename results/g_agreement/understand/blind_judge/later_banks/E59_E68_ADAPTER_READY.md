# E59/E68 judgment adapter READY

Format-only CLI scope now includes E59 and E68 (alongside E56/E57/E62). No re-judging, scoring, resampling, category or threshold changes. Kept code objects, values order (including both values), evidence strings and UNPARSEABLE sentinels are preserved. Original packet/judgment files are never rewritten; all source seals are checked before output creation.

E59 uses the existing command:

```sh
python -m projects.g_agreement.understand.blind_judge.judgment_adapter402 adapt --blind ORIGINAL_BLIND_DIRECTORY --blind-sha ORIGINAL_BLIND_SEAL_SHA --terminal TERMINAL_DIRECTORY --terminal-sha TERMINAL_RESULT_SEAL_SHA --out NEW_ANALYSIS_INPUT_DIRECTORY
```

For E68, add `--converted CONVERTED_PACKET_DIRECTORY --converted-sha CONVERTED_PACKET_SEAL_SHA` when the terminal binds the channels66_68 converted packet. The adapter verifies the converted seal's original blind-seal hash, packet-file hash and unchanged record grid, then binds the terminal to that converted seal. Output JUDGMENT_SEAL.json retains blind_seal_sha256 for the original W-mechanism packet and additionally records converted_packet_seal_sha256. A direct-original E68 terminal is also accepted with the unchanged original binding.

Where present, both sealed JUDGE_COPY.json and PATH_REDACTION_AUDIT.json are required together. The authorized path-only judge copy and affected-ID audit are reproduced from originals and checked; evidence is validated against that copy. Both artifacts are copied byte-for-byte and bound in the output seal for downstream sensitivity reporting. No sensitivity analysis is performed by this converter.

Wire export scope also accepts E59/E68 through their existing admissions. Tests exercise actual adapt CLI for both banks, both-value preservation, UNPARSEABLE retention, source immutability, exact audit-copy bytes, and tamper rejection. Combined adapter/privacy tests: 16 passed. Privacy fixtures now construct synthetic path/address/token strings at runtime; no hook configuration or bypass was used.
