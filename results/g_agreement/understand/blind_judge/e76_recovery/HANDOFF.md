# E76 recovery — Integrator execution only

Guiv authorized zero settlement of d235c8e8 as “rejected, uncharged (HTTP 429)” using its saved response as evidence. No provider usage record is expected under this specific ruling. W-internals-B has not accessed credentials, settled the live ledger, or resumed judging.

Run from the shared checkout after pulling this commit. The existing E10 ledger code appends the settlement under its file lock; a hash-bound reconciliation receipt preserves the request and saved 429 response. The command is idempotent and rejects a generation ID, choices, a nonzero usage cost, or a non-429 response:

```sh
python -m projects.g_agreement.understand.blind_judge.e76_recovery --route /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/results/g_agreement/understand/blind_judge/ROUTE_SEAL.json --ledger-root /Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/cache/g_agreement/understand/blind_judge/e76_2usd --request-id d235c8e8592ec2d0b419599f84e7ac1e8b704824289dad6849551773147e54bf --cap-usd 18
```

Copy the existing E76 run spec to a NEW recovery spec, preserving all seals, packet, custody and budget fields. Add `"resume": true` and `"ledger_root": "/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-blindspot-internals/cache/g_agreement/understand/blind_judge/e76_2usd"`. Keep the original spec, ledger, results and requests. Then:

```sh
python -m projects.g_agreement.understand.blind_judge.e76_runner --spec RECOVERY_SPEC.json --preflight-only
python -m projects.g_agreement.understand.blind_judge.e76_runner --spec RECOVERY_SPEC.json
```

Recovery reuses the existing runner with an E76-only entry point, original packet/copy checks, and remaining-unsent budget admission. Existing successful requests are reused; a saved uncharged 429 retries after 5/10/20/40 seconds, at most four retries, each with a distinct reservation and cached result. Subsequent 429s are settled through Ledger.settle under the same explicit ruling, with saved evidence. No retry for an unresolved transport failure, non-429 error, credential failure, route mismatch or budget failure. Retrying the recovery command cannot reset the four-retry limit for a request. Scientific validation retries retain the existing rules. Route and USD18 E76 cap remain unchanged; all retries count in the existing ledger/global guard. No ledger rows, cached failures or completed results are deleted.

Six offline tests passed. Live settlement and resumed completion must be reported by the Integrator before describing E76 as resumed. Guiv relays this handoff to the Claude Integrator.
