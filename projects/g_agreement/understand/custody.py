"""Narrow E3 missing-array exception authorized by §91 amendment 4af1004b."""
from pathlib import Path
import json
from projects.g_agreement.blindspot import protocol as P

E3_LOST_ARRAYS = (
    "olens/table_row.residuals.npy",
    "olens/table_status.input_stage.npy",
    "olens/table_status.residuals.npy",
)


def verify_available(directory, seal_name="SCORE_SEAL.json", *, allowed_missing=()):
    directory = Path(directory)
    seal = json.loads((directory / seal_name).read_text())
    allowed_missing = set(allowed_missing)
    if not allowed_missing <= set(seal["files"]):
        raise ValueError("missing-array exception includes an unsealed file")
    missing = []
    for name, digest in seal["files"].items():
        path = directory / name
        if not path.is_file():
            if name not in allowed_missing or not name.endswith(".npy"):
                raise ValueError("unapproved missing sealed file: " + name)
            missing.append(name)
        elif P.sha(path) != digest:
            raise ValueError("seal mismatch: " + name)
    return seal, sorted(missing)
