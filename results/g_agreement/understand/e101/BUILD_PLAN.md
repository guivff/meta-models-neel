# E101 runner build plan

Authority: §209, 69f8c08e4; user prioritised E101 on 2026-10-28.

Existing components inspected before implementation: E79 worker.py patched-prefill hook and Clock; E56 worker56.py native_one (Oracle 128, NLA 512); late198/hardware204.py authorised loaders and hardware gate; E100 sealed dev direction/capture provenance. No E101 runner exists on the shared branch at this inventory.

Reuse the registered native adapters and sealed captures. Separate dev-only logits acquisition, CPU dose selection, and test-cell materialisation. Test input creation requires a committed dose receipt, and test runs bind its hash. Both layers 44 and 42 use their own dev mean differences. Labels, target orientation, and dose scoring remain CPU-side; pod input contains precomposed vectors, opaque IDs and frozen prompt/candidate tokens only. No u_tok is used.

Pending rulings before scientific materialisation: 84 versus approximately 40 dev items; independent block-42 dose versus block-44 dose; full continuation versus literal next-token scoring for frozen bookkeeping pairs with a shared first token. Build the reusable acquisition primitive while these are pending. No GPU calls or dose/test outputs are opened in this implementation task.

Synthetic verification will cover patch layer/position, base-model execution, hook cleanup on error, finite outputs, equal-length batching, exact dev dose grids, smallest passing dose, no passing dose, CPU target sign, and the committed-dose barrier. Source is committed before scientific inputs are materialised.
