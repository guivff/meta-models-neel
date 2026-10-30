#!/usr/bin/env bash
set -euo pipefail
# No package or cache writes under the shared /weights tree.
chosen=$(python3 -B - <<'PYSELECT'
import json
from pathlib import Path
from projects.g_agreement.blindspot.screens.protocol import runtime_choice
print(runtime_choice(json.loads(Path('/workspace/s79/assignment.s79.json').read_text())))
PYSELECT
)
if [ "$chosen" != /workspace/s79-venv ]; then
  test -x "$chosen/bin/python"
  test ! -w "$chosen"
  test ! -e /workspace/s79-venv
  ln -s "$chosen" /workspace/s79-venv
else
  test -d /workspace/s79/kernel_wheels || { echo "Shared-runtime-only payload requires verified shared environment assignment" >&2; exit 2; }
python3 -m venv --system-site-packages /workspace/s79-venv
/workspace/s79-venv/bin/python -m pip install --no-index --find-links /weights/wheels -r /weights/wheels/requirements.lock
python3 -B - <<'PY'
from pathlib import Path
from projects.g_agreement.blindspot.screens import bundle as B,corpus as C
B.verify_wheels(Path('/workspace/s79/kernel_wheels'),C.OUT/'KERNEL_WHEEL_MANIFEST.json')
PY
/workspace/s79-venv/bin/python -m pip install --no-index --no-deps /workspace/s79/kernel_wheels/*.whl
fi
/workspace/s79-venv/bin/python - <<'PY'
import json,importlib.metadata
p=json.load(open('results/g_agreement/blindspot/s79/RUNTIME_PINS.json'))
a={k:importlib.metadata.version(k) for k in p}
assert a==p,repr(a)
PY
