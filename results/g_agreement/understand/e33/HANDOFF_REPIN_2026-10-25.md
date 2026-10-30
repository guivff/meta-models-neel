# E33 operational re-pin — 2026-10-25

Status: prior custody audited to 927.1 seconds; reserve 928. Complete scientific
scope retained. New fixed envelopes: slot0 9,043 seconds, slot1 6,229 seconds.
Total including historical reserve: exactly 16,200 seconds (4.5 GPU-hours).

Use the newly pinned SLOT0/SLOT1 requests and one common finalized run plan.
Each envelope includes up to 600 seconds for future failed SSH/setup custody;
book stopped setup-only pod receipts and reduce the corresponding live-pod
allocation before finalizing that plan. Live-pod setup is already counted from
its creation epoch. The per-slot warmed forecast must still admit every owned
prompt-dose path. No scientific inputs, labels, rows, doses or rules changed.

Provision and stage both live pods first. Then freeze one common run plan with
both live IDs and all stopped-deploy loss receipts, copy its exact bytes and
bound assignments to both pods, and only then start either worker. Do not edit
the shared ledger after one shard starts: final analysis requires identical
run-plan hashes. Waiting custody still counts against each live allocation.

Integrator alone scans, publishes and launches. Global ceiling12 and180-second
launch spacing apply. The re-pin is the §136 operational rebuild; a parity or
validity failure stops with no retry. No GPU job was launched by W-lens.

E37's already committed conditional source archive contains its own pinned
copy of the earlier E33 helpers. Launch E37 from that exact source archive;
do not replace dependencies with this later E33 operational update.
