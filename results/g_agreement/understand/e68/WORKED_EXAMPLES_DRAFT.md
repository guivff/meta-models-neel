# E68 worked examples — draft for ratification

No position seal. No capture authorised by this draft.

| Row | Test | Kept | Dropped | Token-gap distribution |
|---|---:|---:|---:|---|
| container_after_move | 84 | 84 | 0 | {14: 84} |
| holder_after_handovers | 84 | 84 | 0 | {26: 84} |
| arith_compare | 84 | 0 | 84 | {2: 84} |
| topic_twin | 84 | 0 | 84 | {5: 84} |

## container_after_move

### container_after_move:6:0:0 — KEEP, gap 14

Final state clause context: ` object. The coin starts in the cup, and the bead starts in the bowl. The coin is put in the bowl by Sam. The coin is put in the cup by Sam.`

Text after P_far's clause boundary: `" The light remains steady throughout the activity. Now the coin is in the"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 51 | 13 | `"."` |
| P_mid | 58 | 5524 | `" activity"` |
| P_pre | 65 | 279 | `" the"` |

### container_after_move:6:0:1 — KEEP, gap 14

Final state clause context: ` object. The coin starts in the cup, and the bead starts in the bowl. The coin is put in the cup by Sam. The coin is put in the bowl by Sam.`

Text after P_far's clause boundary: `" The light remains steady throughout the activity. Now the coin is in the"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 51 | 13 | `"."` |
| P_mid | 58 | 5524 | `" activity"` |
| P_pre | 65 | 279 | `" the"` |

### container_after_move:6:1:0 — KEEP, gap 14

Final state clause context: `ked object. The key starts in the cup, and the ring starts in the bowl. The key is put in the bowl by Sam. The key is put in the cup by Sam.`

Text after P_far's clause boundary: `" The light remains steady throughout the activity. Now the key is in the"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 51 | 13 | `"."` |
| P_mid | 58 | 5524 | `" activity"` |
| P_pre | 65 | 279 | `" the"` |

## holder_after_handovers

### holder_after_handovers:6:0:0 — KEEP, gap 26

Final state clause context: `ile Alex holds the key. The coin is passed from Robin to Alex. The coin is passed from Alex to Robin. The coin is passed from Robin to Alex.`

Text after P_far's clause boundary: `" The room stays quiet for a moment. The clock ticks by the door.\nQ: Who has it now?\nA:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 54 | 13 | `"."` |
| P_mid | 67 | 279 | `" the"` |
| P_pre | 80 | 25 | `":"` |

### holder_after_handovers:6:0:1 — KEEP, gap 26

Final state clause context: `le Robin holds the key. The coin is passed from Alex to Robin. The coin is passed from Robin to Alex. The coin is passed from Alex to Robin.`

Text after P_far's clause boundary: `" The room stays quiet for a moment. The clock ticks by the door.\nQ: Who has it now?\nA:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 54 | 13 | `"."` |
| P_mid | 67 | 279 | `" the"` |
| P_pre | 80 | 25 | `":"` |

### holder_after_handovers:6:1:0 — KEEP, gap 26

Final state clause context: `sed from Alex to Robin. The ring is passed from Robin to Alex. The ring is passed from Alex to Robin. The ring is passed from Robin to Alex.`

Text after P_far's clause boundary: `" The room stays quiet for a moment. The clock ticks by the door.\nQ: Who has it now?\nA:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 63 | 13 | `"."` |
| P_mid | 76 | 279 | `" the"` |
| P_pre | 89 | 25 | `":"` |

## arith_compare

### arith_compare:6:0:0 — DROP, gap 2

Final state clause context: `Determine whether the inequality holds.
Is 21 × 43 more than 655?`

Text after P_far's clause boundary: `" Answer:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 22 | 30 | `"?"` |
| P_mid | 23 | 21134 | `" Answer"` |
| P_pre | 24 | 25 | `":"` |

### arith_compare:6:0:1 — DROP, gap 2

Final state clause context: `Determine whether the inequality holds.
Is 12 × 34 more than 655?`

Text after P_far's clause boundary: `" Answer:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 22 | 30 | `"?"` |
| P_mid | 23 | 21134 | `" Answer"` |
| P_pre | 24 | 25 | `":"` |

### arith_compare:6:1:0 — DROP, gap 2

Final state clause context: `Determine whether the inequality holds.
Is 31 × 42 more than 807?`

Text after P_far's clause boundary: `" Answer:"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 22 | 30 | `"?"` |
| P_mid | 23 | 21134 | `" Answer"` |
| P_pre | 24 | 25 | `":"` |

## topic_twin

### topic_twin:6:0:0 — DROP, gap 5

Final state clause context: `is the case that after the clerk reviewed the dated notes and checked every entry in the report, the engineer inspected the safety interlock`

Text after P_far's clause boundary: `" and adjusted the protection system"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 79 | 988 | `"lock"` |
| P_mid | 81 | 22643 | `" adjusted"` |
| P_pre | 84 | 1785 | `" system"` |

### topic_twin:6:0:1 — DROP, gap 5

Final state clause context: `rfactually, that after the clerk reviewed the dated notes and checked every entry in the report, the engineer inspected the safety interlock`

Text after P_far's clause boundary: `" and adjusted the protection system"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 79 | 988 | `"lock"` |
| P_mid | 81 | 22643 | `" adjusted"` |
| P_pre | 84 | 1785 | `" system"` |

### topic_twin:6:1:0 — DROP, gap 5

Final state clause context: `is the case that after the clerk reviewed the dated notes and checked every entry in the report, the engineer inspected the safety interlock`

Text after P_far's clause boundary: `" and adjusted the protection system"`

| Position | Index | Token ID | Decoded token |
|---|---:|---:|---|
| P_far | 79 | 988 | `"lock"` |
| P_mid | 81 | 22643 | `" adjusted"` |
| P_pre | 84 | 1785 | `" system"` |
