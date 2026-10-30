# E61 D5 blind coding rubric

Classify what this native readout explicitly says, not whether it is correct. Do not infer the source text, repair truncated text, or use knowledge of the experimental result. Assign exactly one category:

- `topic_content`: describes subject matter, entities, events, facts or semantic content.
- `register_genre`: identifies style, register, expertise, tone, genre or communicative purpose.
- `format_without_value`: names formatting, syntax, layout, bookkeeping or a structural property without asserting its state/value.
- `structural_value`: explicitly asserts a structural, syntactic, delimiter, position, count or bookkeeping state/value. It may be wrong; correctness is not judged here. A value merely occurring inside an example is insufficient.
- `generic_other`: none of the above, including empty/incomprehensible output, generic boilerplate, or refusals with no substantive classification.

When several categories apply, use structural_value > format_without_value > register_genre > topic_content > generic_other. This deterministic tie-break is frozen before D5 coding and does not turn a topical/semantic value into a structural one. A response that merely enacts a format without describing it does not qualify as format_without_value or structural_value.

Return {"id": opaque_id, "category": category, "evidence": "exact supporting substring"}. Require a nonempty verbatim substring except for generic_other, where the evidence may be empty. Classify each record independently; do not compare repetitions or guess the true class.
