# Shared staging for BRIEF_BLINDSPOT (§70–§84): proposal for Guiv

Integrator, 2026-10-23. Asked by Guiv: shared staging (a network volume with the pinned weights, or one warm pod shared by
W-core, W-mechanism and the lens chat), or else the per-pod staging cost so it can be booked apart from experiment caps.
No volume or pod has been created for this; both options below need Guiv's go.

## What every run downloads

All stage lists used so far pin the same public weights (from the integrator's §58, §60 and §66 stage lists):

| repo | revision | used by |
|---|---|---|
| `Qwen/Qwen3.6-27B` | `6a9e13bd6fc8f0983b9b99948120bc37f49c13e9` | every run |
| `agu18dec/olens_and_ar` (Oracle lens + AR) | `c95215d5d2f6250f20c305ae55c6e4d7569f92dc` | §58, §66, W6, W7 |
| `ceselder/qwen3.6-27b-nla-rl` (NLA) | `5a13b7ec21a69fcdd0fb24d5edbe96a92aef4b9f` | §66, W8, NLA arms |
| `neuronpedia/jacobian-lens` | `b25d72a96b79c8e309d6625955a98751da47e67a` | §60, J-lens arms |

P3's §66 manifest of the first three is 112.3 GB (50 files). One staged copy covers every BRIEF_BLINDSPOT owner, provided
each owner confirms its pins match this table before using it.

## Measured per-pod staging cost (cold H200, $5.29/h)

From provider creation to the first science step (dispatch or setup ready). This includes the owner's arm and handover time.

| pod | run | creation → science | GPU-h | $ |
|---|---|---|---|---|
| `b0gm9me46o1w47` | §66 dev (112.3 GB, EUR-IS-4) | 704 s | 0.196 | 1.04 |
| `kku01qhsnscudw` | §54-core | 825 s | 0.229 | 1.21 |
| `532rwv8ikn0ywe` | §65B | 1,165 s | 0.324 | 1.71 |
| `raemnqmlbvetma` | §54-core | 1,748 s | 0.486 | 2.57 |
| `8inga28o0q0z1r` | §65B R2 (stage passed; loading never did) | ≥ 2,038 s | ≥ 0.566 | ≥ 2.99 |
| `4zt59wlwu1eygm` | §64 (idle-stopped at ≈ 102 GiB, never staged) | > 1,430 s, no science | 0.397 | 2.10 |

**Median 1,165 s (0.32 GPU-h, $1.71) per pod; observed range 704 to over 2,038 s, and 2 of 6 pods never reached science.**
That is larger than the whole cap of W2, W3, W7 (0.3 GPU-h each) and W6 (0.2), and about two-thirds of W5 and W8 (0.5).
With roughly 6–9 fresh pods for §70–§84, cold staging would cost about 1.9–5.1 GPU-h ($10–$27) next to 9.6 GPU-h of science.

## Option A (recommended): a network volume in EUR-IS-5 with the pinned weights

- **Why EUR-IS-5:** of 115 successful H200 deploys since 2026-10-20 (`pod_deploys.jsonl`), EUR-IS-5 has the most (31 OK,
  7 failed), then AP-JP-1 (21/22) and EUR-IS-4 (20/5). Both existing project volumes (`mats-minis`, 600 GB; `mats-minis-b`,
  200 GB) are in EUR-IS-3, where **0 of 11** H200 deploys succeeded, so they are not usable for this.
- **How:** one fill pod in EUR-IS-5 downloads the table above once into the volume (about 0.2–0.6 GPU-h, booked once as
  "§70–§84 shared staging"), hash-checks every file against its pinned revision, measures read throughput, then stops.
  Each run then deploys a fresh pod on the volume, reads the weights in place (read-only), and writes outputs only to its own
  container disk. Owners keep their own guards and custody as now. Nothing idles between runs; only storage is billed.
- **Costs and limits:** the volume's storage charge, which I have not checked against RunPod's current price (it is small next
  to GPU time); every run is pinned to EUR-IS-5's H200 stock. When EUR-IS-5 has none within 15 min, the run falls back to a
  cold off-volume pod, with that staging booked under the shared-staging line. Read speed from a network volume is
  unmeasured; the fill pod measures it before anyone relies on it.
- **Work before first use:** a volume deploy path in the stock loop (`networkVolumeId`, EUR-IS-5 only) with decoy tests
  (rule 10), and owners' stagers pointing `HF_HOME` at the volume read-only. The watchdog's new `.incomplete` credit must
  watch the pod's own disk, never the shared volume (`WD_HF_DIR`, per 4a625566).

## Option B: one warm pod shared in sequence (W-core → W-mechanism → lens)

- The integrator stages once and holds; each owner takes custody in turn (arm, run, verified pull, release) and the next
  owner arms under a ≤ 30-min reservation.
- **Against it for this sprint:** owners are ready at different times (lens features freeze Friday 20:00, W1 targets
  Sunday 18:00, §84 Monday), so the pod would idle for hours at $5.29/h or be stopped, and a stop on a no-volume pod wipes
  the stage. W2–W4 depend on W1 outputs, so they cannot share W1's pod window. The two 27B-class models (target and NLA)
  leave no room for two owners on one H200 at once. It also needs Guiv to lift the 2026-10-20 "no warm handovers" rule
  for this wave.
- Worth it only for a batch of runs that are launch-ready at the same moment.

## If neither: book staging separately

Book a **staging allowance of 0.6 GPU-h (2,160 s, the registered staging stop) per cold pod**, outside the experiment caps,
under a "§70–§84 staging" line. Each run's cap then counts from its first science step. Expected 0.32 GPU-h per pod (median),
worst observed above 0.57.

## Decision needed from Guiv

1. Create the EUR-IS-5 volume and run the fill pod (Option A)? Or
2. Go cold with a separate 0.6 GPU-h staging allowance per pod (W-core and the lens chat first)?
