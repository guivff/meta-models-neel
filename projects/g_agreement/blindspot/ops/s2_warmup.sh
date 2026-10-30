#!/usr/bin/env bash
# Setup only: repair the observed optional typing dependency before AR warm-up.
set -euo pipefail
if [ "$#" -eq 0 ]; then
  echo 'usage: s2_warmup.sh WARMUP_PY [ARGS...]' >&2
  exit 2
fi
s2_python="${S2_PYTHON:-/weights/venv-kernels/bin/python}"
if ! "$s2_python" -c 'from jaxtyping import Bool, Float, Int' >/dev/null 2>&1; then
  "$s2_python" -m pip install --disable-pip-version-check jaxtyping
fi
"$s2_python" -c 'from jaxtyping import Bool, Float, Int; from importlib.metadata import version; print("S2 setup jaxtyping=" + version("jaxtyping"))'
exec "$s2_python" "$@"
