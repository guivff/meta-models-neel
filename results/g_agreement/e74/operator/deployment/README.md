# E74 author-runtime deployment recipe

This directory follows the author's **pip path**: vLLM0.31.0 followed by the exact bundled `glm53` fork, installed without dependency resolution. It adds explicit dependency locks, a reproducible fork-wheel build and CPU verification. It does not change resident-v5, its scientific inputs, hardware implementation, budgets or gates.

The author publishes package families and a fork tarball, but the pinned HF inventory contains no complete environment freeze or container image digest. This is our reproducible realization of that published path, not a claim that ceselder supplied this image or used every transitive version below. The Linux/amd64 image has now passed the CPU installation checks and all six offline import checks. Consult `BUILD_RECEIPT.json` for the image identity, separate import-check outcomes, size and local archive availability. `RECIPE.json` retains its pre-build candidate status because it is an input embedded in the image; the external build receipt is the subsequent status record.

## Pins and provenance

| Component | Pin | Basis |
|---|---|---|
| Python | CPython3.12.14, Linux x86-64 | Build target selected within the fork's published Python≥3.12 requirement |
| Linux ABI | glibc≥2.35; pinned base has2.36 | All209 resolved packages have compatible wheels for this target |
| Base image | `python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a` | Official Python3.12.14-slim-bookworm **build substrate**, not an author GPU image |
| vLLM | 0.31.0 | Exact author requirement |
| torch | 2.13.0 | Author2.13 family; exact requirement of vLLM0.31.0 |
| transformers | 5.17.0 | Patch pin within author5.17 family |
| PEFT | 0.21.0 | Patch pin within author0.21 family |
| vllm-lens | 1.1.0.post7 | Metadata inside the exact author fork; never use the PyPI/upstream distribution as a substitute |
| Fork tar SHA256 | `8d9ca706651a1325c7ad9db78b19989a0f0082944577b310dc5aa0cf95046c82` | Author `vllm_metamodels_glm53_b26f02d.tar.gz` |
| Built fork wheel SHA256 | `d9922eed27d2191e641c00fa7a360c0f2d4c285828fe7eb632b1127cde0c8f30` | Two identical host CPU builds, also checked by the Linux/amd64 builder |

`runtime.lock` pins209 distributions and their permitted distribution hashes. `build.lock` pins the fork's six-package Hatchling build closure. `fork.lock` permits only the wheel built from the pinned author tar. The fork's declared runtime dependencies (`datasets`, `pydantic`, `vllm`, `zstandard`) are included. No dev/benchmark groups or reconstructor path are installed.

An offline, fully constrained re-resolution reproduced all209 versions and hash sets. The initial glibc2.28 target had no compatible allowed `llguidance` wheel; moving the **OS ABI target**, without changing the author's four core library versions, resolved the closure. This recipe requires its declared target rather than assuming every Linux distribution works.

The fork's `tool.uv.sources` table points torch at CUDA12.6. That is not the author card's CUDA13 pip path. The build uses `--no-config --no-sources`, exact source hashes and locked build dependencies; it does not run `uv sync` in the fork workspace or resolve a mutable Git branch.

## CUDA and hardware limits

The torch2.13.0 Linux dependency requires CUDA toolkit13.0.3 (normalized PyPI package version13.0.3.0), and the CPU installation check requires `torch.version.cuda == "13.0"`. The resolved closure also includes CUDA bindings13.4.4 and NVCC/NVVM/nvJitLink13.4.92. These are concrete pins allowed by the published dependency graph, **not** evidence that the author used this exact compiler closure.

NVIDIA lists driver family580 or later as the CUDA13 minor-compatibility floor, but explicitly limits that guarantee for features and PTX compilation. Therefore a driver meeting that floor alone does not prove this lock's JIT/compiler path works. I-2 must verify the actual host driver against the resolved13.4 compiler/PTX components and run the admitted author smoke. No older CUDA stack, different torch version or alternative quantization kernel is silently substituted.

Resident-v5 implements **4×B200 TP4**, with B200 compute capability10.0. The author's separate wild README documents8×B300 W4A16 support (B300 compute capability10.3); that does not add B300 or TP8 support to this resident package.

## Reproduce the build

From the repository root, prepare a new context containing only these recipe files and the two existing, hash-verified author source artifacts:

```sh
python3 results/g_agreement/e74/operator/deployment/prepare_context.py \
  --e74 results/g_agreement/e74 --out /absolute/new/e74-build-context
docker build --platform linux/amd64 --target fork-builder \
  --tag codex/e74-runtime-builder:20261027 /absolute/new/e74-build-context
docker build --platform linux/amd64 --target runtime \
  --tag codex/e74-author-runtime:20261027 \
  --metadata-file /absolute/new/e74-build-metadata.json /absolute/new/e74-build-context
```

The first target downloads only the small Python/build dependencies and builds the exact fork source. The second downloads and installs the locked software runtime; it does not download GLM weights. Every pip install uses `--require-hashes --no-deps`, with a subsequent `pip check`. The fork is installed from the locally built wheel with `--no-index`; no upstream plugin can replace it. `SOURCE_DATE_EPOCH=1704067200` fixes wheel packaging timestamps only.

The final build runs `verify_deployment.py --installed` with CUDA visibility disabled. It checks the target platform, every locked installed version, `pip check`, the exact installed fork Python sources, plugin entrypoint and torch's compiled CUDA version. It does not construct a vLLM engine, initialize CUDA, load weights or claim GPU verification. The resulting image defaults to `python --version`, so it cannot implicitly launch E74.

The base is digest-pinned. A locally built image ID is a content-addressed **local image identity**, not automatically a registry pull digest. Before use on a provider, I-2 must arrange the distribution route, verify the final manifest/digest and measure image pull/setup within the original900 s archive/environment allowance. Image transfer and provider release controls remain external to this recipe. No image has been pushed to an external registry by this task.

For a fresh lock audit, uv0.13.6 was used with Python3.12.14, `--python-platform x86_64-manylinux_2_35 --only-binary :all: --generate-hashes`, the public PyPI index, no local configuration and no Python downloads. Install from the committed locks; do not silently regenerate them from the floating transitive requirements in `runtime.in`. The resolver's verified executable/wheel hashes and all source references are recorded in `RECIPE.json` and `AUDIT.json`.

## Still required before scientific execution

I-2 must verify the actual provider quote, Linux/driver/device inventory, CUDA13/JIT compatibility, four B200s, NVMe/free space, runtime image identity and retrieval route, process/provider hard stops and the remaining whole-E74 cost forecast. The actual engine must then satisfy the author's plugin/capture/injection counters, adapter merge/unmerge behavior and frozen50-fixture agreement rule. These checks are unresolved until admitted GPU execution; a CPU build cannot establish them. The original fixture, read layer51, prompt/marker/norm, greedy grammar and downstream forecast/GO custody remain unchanged. The ordinal-estimator question is still with Guiv.

Sources: [author lens card at the frozen revision](https://huggingface.co/ceselder/glm-5.3-olens-lens/blob/689c5dbae3d2f83dbf969e234a023958f1612185/README.md), [vLLM0.31.0 metadata](https://pypi.org/pypi/vllm/0.31.0/json), [torch2.13.0 metadata](https://pypi.org/pypi/torch/2.13.0/json), [CUDA13.0 Update3 release notes](https://docs.nvidia.com/cuda/archive/13.0.3/cuda-toolkit-release-notes/index.html), [NVIDIA minor-version compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html), [GPU compute capabilities](https://developer.nvidia.com/cuda/gpus), [uv command reference](https://docs.astral.sh/uv/reference/cli/).

## CPU import checks and local handoff

After building, run the committed `cpu_imports.py` in the image with no network, a read-only root filesystem, an unprivileged user and only a temporary writable `/tmp`:

```sh
docker run --rm -i --platform linux/amd64 --network none --read-only \
  --user 65534:65534 --tmpfs /tmp:rw,nosuid,nodev,size=512m \
  -e CUDA_VISIBLE_DEVICES= -e PYTHONDONTWRITEBYTECODE=1 -e HOME=/tmp \
  --entrypoint python codex/e74-author-runtime:20261027 - \
  < results/g_agreement/e74/operator/deployment/cpu_imports.py
```

This separately imports torch, transformers, PEFT, vLLM, the exact plugin entrypoint callable, and the author's module. It never calls the plugin registration function or constructs an engine. A failed import is retained in `CPU_IMPORTS.json`; no package substitution or exception suppression turns it into a pass.

`BUILD_RECEIPT.json` records the local Docker archive when export finishes. A recipient can use `docker image load --input <verified-local-archive>` and compare the resulting config/image ID to that receipt. This is a local handoff artifact, not a provider upload or registry image. The Docker exporter returns the same config ID as both `containerimage.digest` and `containerimage.config.digest`; neither is claimed as a verified registry pull manifest. I-2 must still establish provider retrieval, validate its final artifact identity and charge transfer/setup against the existing allowance.

See `DEPLOYMENT_ROUTE.md` for the Runpod registry/control requirements and the conditional host-Docker archive route. `verify_archive.py` reproduces the archive SHA256, gzip CRC, image config identity and OCI manifest/member-size checks. It records that large layer digests were not independently recomputed.
