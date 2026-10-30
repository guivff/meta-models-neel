E23 step0: training span resolved before GPU work.

The input follows the target token: if the target is position p, the input is tokens p+1 through p+N. N is variable in1..32. The target is the single residual at p, separately for each layer; there is no position average. `SPAN.json` supplies pinned file:line evidence and hashes.

F16 is in-contract for this span/target convention. P32 and Pfull are off-contract. Mis remains a mismatched donor control. These labels do not claim that synthetic items match the training domain.

The config is the actual ar_ptag_pooled checkpoint metadata at HF revision c95215d5; the data/capture/training code is from the official extracted source at a3259008, with its extraction manifest retained. Only pinned individual files were fetched/read; no clone and no model work.
