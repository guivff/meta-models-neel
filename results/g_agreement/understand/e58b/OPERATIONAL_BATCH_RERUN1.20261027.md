# E58b — §149 OPERATIONAL batching rebuild, 2026-10-27

The user reports the first admission rejected 4,536 batch-8 forwards: approximately6,500s forecast against approximately2,000s available. Raw failure logs have not been delivered to this worker. The Integrator must verify no production occurred, stop the prior allocation and record its actual provider usage before this one authorized operational rerun. Original guards and outputs remain history.

The scorer now groups all rows by conditional-prefix length and tries batch32 and64. Each forward consumes only a conditional prefix and requests its final-position logits. Shared A/B prefixes are evaluated once per item; every token of every frozen candidate still contributes to the full summed conditional log probability. At block44, the original prompt positions are projected; padding and candidate-prefix positions are excluded. There is no generation, KV branching, item reduction, candidate truncation or change to labels, arms, subspaces, metrics, thresholds or rules.

The unchanged blind bank has37 rows,3108dev and3108test items,4452 item/pair units and18,648 candidate tokens per arm. It yields9492 unique conditional prefixes per arm,2376 scoring forwards at32 or1192 at64 across all8arms. These are CPU scheduling counts, not measured GPU speedups. The registered37-row/35616-record output grid and CPU-only label join remain unchanged.

On the H200 relaunch, BENCHMARK.json records up to3 real frozen batches per phase and batch size, a warmup plus3 timed repeats, median time, prefixes/s, unpadded tokens/s, peak allocated/reserved memory and free/total memory. Capture probes use scratch moments that are discarded; they never enter the shared PCA. Probe probabilities are discarded. Admission requires at least max(4GiB,5% total) free headroom, and rejects OOM layouts before production. The fastest safe32/64 layout supplies the full workload forecast. Exact no-edit/zero-projection parity remains mandatory; a parity or validity failure has no retry.

After the real shared dev-PCA capture, BUDGET.json tests the complete remaining forecast against1.5·F+360 plus the180s retrieval reserve. It selects the original aggregate2700s limit if it fits, and the user-approved aggregate5400s limit only if2700s fails. Prior provider time counts toward both. Actual allocation and programme stop remain upper bounds. The Integrator watches the selected budget and tightens the external provider stop; the worker also tightens its own signal deadline. A failure to fit5400s stops without production or scope reduction.

New guard: cache/g_agreement/understand/e58b/WORKER.rerun1.RUN_ONCE.json.
New output: cache/g_agreement/understand/e58b/out-rerun1-batched-20261027/.
New verified pull: cache/g_agreement/understand/e58b/verified-pull-rerun1/.
The existing once-only CPU analysis guard remains unconsumed. No real analysis or H200 measurement was run by the worker while making this rebuild.
