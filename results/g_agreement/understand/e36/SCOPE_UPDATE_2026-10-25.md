# E36 expansion and supplied definitions — 2026-10-25

Authority: §135, commit `b1aca4c5`, and §132 dated clarification 1, commit
`d4bb903d`. These notes supersede the earlier missing-definition hold once the
specified coordinator packet has been hash-verified; earlier notes are retained
as the record of that hold.

The primary target is all 25 rows from `ROW_DEFINITIONS.json`: 16 structure rows
(seven state-like and nine count-like) and nine semantic rows. The same twelve
families × seven fillers × two values produce 4,200 prefixes: 2,100 dev and
2,100 test. Families 0–5 and 6–11 remain disjoint dev/test partitions, each row
having 42 A and 42 B items in each split. Token-length matching is checked per
same-family, same-filler A/B pair, with longer/shorter no greater than 1.10.

The expanded freeze deadline is **Monday 26 October 2026 at 12:00 CET**
(`2026-10-26T11:00:00Z`). If the 25-row bank cannot be frozen by then, the original
eight rows run alone with §132's original counts and three-GPU-hour cap. The
expanded cap is eight GPU hours, inclusive of all setup, warm measurements and
charged attempts. A scope is explicit in the bank and plan; the worker cannot
silently mix the expanded population with the original budget or hypothesis
denominators. This deadline is a fallback criterion, not a reason to delay a bank
that is ready earlier.

Channels remain those in §132. The automatic bank check, source/asset binding,
label-free acquisition and integrator-only launch constraints remain in force.
H1/H5's widened required counts, H2's widened count and H4's population/count have
been requested from the coordinator because §135 does not restate them. Original
eight-row rules are retained verbatim; expanded adjudication requires an explicit
rule binding. In particular, `python_indent` was in the original H4 population
but is count-like in the supplied taxonomy, so class alone cannot define H4.

After the bank freeze, bind the exact frozen `e30/CANDIDATES.json` to E30's
second-bank value-word scoring and its R1/R2 replication. This companion has its
own aggregate cap of 0.5 GPU hours. Its candidate source is not shown to authors
and is not opened during authoring. The E30 handoff identifies the same frozen
bank and preserves candidate variants; it does not silently expand E36's budget.

The integrator retains launch and push ownership. §135 permits an alternate GPU
after 15 minutes without an H200, subject to the specified memory check; the
assignment must record the GPU type and supporting receipts. No GPU is started
by this worker chat.

## Dated clarification 2 received from the coordinator, 2026-10-25

Authority: §132 dated clarification 2, commit `0cc77a85`, supplied directly in
chat before any E36 score or bank freeze. The expanded counts are now fixed:

- H1: Oracle ≤0.65 and probe ≥0.90 in the same ≥11 of 16 structure rows.
- H2: Oracle ≥0.85 on ≥7 of 9 semantic rows.
- H3: unchanged, using the rows where E30 finds R1, conditional on E30's R2.
- H4: continuation ≥0.70 on ≥5 of these seven rows: prose_paren, prose_quote,
  python_string, python_indent, python_depth, list_depth, table_role.
- H5: NLA minus Oracle ≥0.10 on ≥11 of 16 structure rows.

These explicit numbers and the explicit H4 population replace the pending-count
state described above. They are not derived from packet class labels or rounded
again by the worker. The original eight-row fallback retains §132's old rules.

## Dated implementation correction before freeze, 2026-10-25

The preliminary scaffold copied E15's original base-dev pair eligibility step.
That step is removed from E36: §132 requests E15's frozen pairs, and clarification
2 fixes the seven valid-row population. E36 therefore averages all supplied
frozen continuation pairs on the new test items. It does not score an extra base
dev arm, select new pairs, or drop pairs according to v2 outcomes. This supersedes
the continuation-pair selection paragraph in the initial plan. The original
native Oracle continuation prefix and log-odds scoring recipe are unchanged.

## Dated post-freeze candidate binding, 2026-10-25

The bank passed its full checks before any candidate artifact was opened. The
three frozen candidate sources are now bound by file hash, Git blob and source
commit in `CANDIDATE_PROVENANCE_2026-10-25.json`.

§125 specifies that E30's two bullet-register pairs are two phrasings of one
channel, averaged before AUROC. They are therefore bound together as
`e30_bullet`, preserving both original pairs in order. They are not split into
additional experimental arms. The original strings already contain their bullet,
so the native extra prefix is empty. E15 retains its frozen `- ` prefix and all
eight rows with candidate pairs, including table_column; H4 still uses exactly
the seven rows fixed by clarification 2.
