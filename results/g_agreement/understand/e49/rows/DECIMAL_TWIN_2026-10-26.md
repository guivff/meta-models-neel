# Row 16 consumes row 15 — 2026-10-26

`unit_system.generate()` supplies the exact 168 prefixes and read token for `decimal_separator.generate(source_items)`. Do not render new text. Its A/B values are metric/imperial and its literal final read-token suffix is `3`.

Every prefix contains both format notes, one requiring a comma and one a point between integer and fractional digits. The text explicitly says the final format note overrides the earlier one. The last note therefore defines the decimal label independently of the metric/imperial label. Recover it from text, never template metadata. Both conventions have 42 dev and 42 test items, crossed equally with metric/imperial. The last-note order varies across template families; both notes are always present.

Row 16 supplies only its SPEC (with `twin_of='unit_system'`), checker and fixed candidate suggestions. `relabel_twin` preserves the original text, template, filler and variant fields. The central validator also compares exact token arrays. No BOW gate has been fitted on these items.
