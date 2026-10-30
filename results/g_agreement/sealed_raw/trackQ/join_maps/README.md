# Track Q post-analysis join maps (Guiv 2026-10-28)

These are published only for banks whose once-only analysis has sealed: E56, E57, E59, E62, E66, E68, E67 wave 1 and E67 wave 2. Each map joins an opaque judge ID to its row, reader, condition, arm and packet:
- E56, E57, E59, E62 and E68: `source_id` = row:item:…:reader:repeat.
- E66: stratum.
- E67: bank, row, arm and condition per packet record.

**No truth labels or values are included.** Item truth stays in the owners' private item files, because several of these banks' items are reused by banks not yet analysed (E78, E79, E81–E88). DROPPED_FIELDS.json lists every field removed. Local paths were removed.

E54 and D5 have no separate join map: their export binding holds only the question definitions.
