# Build substrate, NOT a ceselder-published image. See external BUILD_RECEIPT.json.
FROM python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a AS fork-builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 SOURCE_DATE_EPOCH=1704067200 CUDA_VISIBLE_DEVICES=""
WORKDIR /recipe
COPY build.lock runtime.lock fork.lock RECIPE.json verify_deployment.py ./
COPY vendor/ ./vendor/
RUN python -m pip install --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-deps -r build.lock
RUN python -m pip wheel --no-build-isolation --no-deps --no-index --wheel-dir /wheels vendor/vllm_metamodels_glm53_b26f02d.tar.gz
RUN python verify_deployment.py --root /recipe --wheel /wheels/vllm_lens-1.1.0.post7-py3-none-any.whl --out /CPU_FORK_BUILD.json

FROM python@sha256:1aaa65a85fda306ffb8b910824d4e93bdce61e212c7e87168123ea3073b41a1a AS runtime
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
WORKDIR /recipe
COPY runtime.lock build.lock fork.lock RECIPE.json verify_deployment.py ./
COPY vendor/ ./vendor/
COPY --from=fork-builder /wheels/ /wheels/
RUN python -m pip install --index-url https://pypi.org/simple --only-binary=:all: --require-hashes --no-deps -r runtime.lock
RUN python -m pip install --no-index --find-links /wheels --require-hashes --no-deps -r fork.lock
RUN CUDA_VISIBLE_DEVICES="" python verify_deployment.py --root /recipe --installed --out /CPU_INSTALL_RECEIPT.json
# No model load, weight transfer, GPU tests or allocation is part of this build.
CMD ["python", "--version"]
