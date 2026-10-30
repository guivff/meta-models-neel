# E116 exploratory note 1

Post hoc exploratory appendix, authorized57f72f804. R-CH3 remains NOT MET; primary unchanged.

## Immediate modal split

Original E108 mode baseline: category-wide leave-one-out across both arms with canonical-ID lexical tie break. All329 immediate items partition into218 modal and111 non-modal.

| Subset | Block | Hits / observed | Missing | Hit rate | Wilson95 CI |
|---|---:|---:|---:|---:|---|
| modal | 52 | 133/218 | 0 | 0.6101 | [0.5440, 0.6724] |
| modal | 60 | 141/218 | 0 | 0.6468 | [0.5813, 0.7072] |
| non_modal | 52 | 29/111 | 0 | 0.2613 | [0.1885, 0.3500] |
| non_modal | 60 | 59/110 | 1 | 0.5364 | [0.4435, 0.6268] |

Always-mode reader baseline on non-modal subset:0. Non-modal block60 lower bound .4435 exceeds .25: **tracks specific choices**, exploratory criterion only. This does not establish causal access or alter R-CH3.

## Paired per-item gains

Original observed pairs only;5000 item bootstrap draws, seed0. Missing pairs excluded and counted, never filled with zero.

| Arm | Contrast | Paired / planned | Gain | 95% CI |
|---|---|---:|---:|---|
| all | 60_minus_44 | 375/376 | 0.3893 | [0.3307, 0.4507] |
| all | 60_minus_52 | 375/376 | 0.1147 | [0.0533, 0.1760] |
| delayed | 60_minus_44 | 47/47 | 0.2128 | [0.1064, 0.3404] |
| delayed | 60_minus_52 | 47/47 | 0.1064 | [-0.0213, 0.2340] |
| immediate | 60_minus_44 | 328/329 | 0.4146 | [0.3506, 0.4817] |
| immediate | 60_minus_52 | 328/329 | 0.1159 | [0.0488, 0.1799] |

## Distinct named members per family

**NOT AVAILABLE from the sealed judgments.** The original channel judges only whether the supplied chosen member is named. A false hit does not identify which other members, if any, were named. Counting distinct picked members on hits would only provide a lower bound, not the requested diversity. No guessed lexical parser, new extraction or judging was performed. RESULTS.json preserves each family/block44/52/60 with null count and its observed-judgment coverage. I2/C are asked to identify any existing sealed member-extraction records; this part remains an input gap.

Source3d50023cb committed before sole invocation; six synthetic tests PASS. Separate exploratory guard consumed. Primary E116/E108 seals and guards unchanged. Private binding stays local.
Exploratory seal: `4533330ea8a2f90cede483b60941e3867aaf61466247a7a1c1111afc5ca16cfb`.
