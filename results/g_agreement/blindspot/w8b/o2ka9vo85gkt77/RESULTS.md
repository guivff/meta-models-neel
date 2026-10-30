# W8b (§85)

{'H1': 'NOT EVALUABLE', 'H2': 'NOT EVALUABLE'}

n=600, clusters=32. Signed AUROCs; no sign flip.

| Reader | TRUE | RANDOM donor | OPPOSITE donor | Probe | Evaluable |
|---|---:|---:|---:|---:|---|
| nla42 | 0.2752 | 0.3284 | 0.4363 | 0.9917111111111111 | False |
| oracle44 | 0.5545 | 0.4392 | 0.1394 | 0.9951 | True |
| oracle52 | 0.6824 | 0.6530 | 0.6734 | None | None |

Oracle44−NLA gap=0.2793; paired cluster-bootstrap95%CI=[0.12685417463546056, 0.5307241455131119].
See public JSON for signed confidence intervals, per-phrasing, length-adjusted and secondary results.

Both registered hypotheses are **NOT EVALUABLE**: the NLA RANDOM-DONOR AUROC 0.3284 fails the registered [0.40, 0.60] gate. The inversion and reader gap are descriptive only; no sign was flipped. Oracle44 passes its own gates.

All 15 package files independently hash-verified; matching Mac receipt and VERIFIED_READY_TO_STOP release; independent account EXITED confirmed. Provider creation-to-exit 1738.082177 seconds: setup 1079.354423 seconds outside science, science plus final pull 658.727754 seconds (actual science 624.840374 seconds). Operational logs retained locally.
