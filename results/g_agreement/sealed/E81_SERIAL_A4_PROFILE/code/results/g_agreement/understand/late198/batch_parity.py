"""Exact output parity; mismatches stop acquisition, never silently fall back."""
import hashlib
import json
from contract import require, write


def check_outputs(batched, serial, path, ids, batch_size):
    require(len(batched) == len(serial) == len(ids) and len(ids) > 0, 'parity coverage')
    encode = lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    rows = [dict(id=i, batched_sha256=hashlib.sha256(encode(a)).hexdigest(),
                 serial_sha256=hashlib.sha256(encode(b)).hexdigest(), equal=encode(a)==encode(b))
            for i, a, b in zip(ids, batched, serial)]
    passed = all(x['equal'] for x in rows)
    write(path, dict(status='PASS' if passed else 'FAIL', n=len(rows),
                     production_batch_size=batch_size, exact_serialized_output=True, records=rows))
    require(passed, 'batched greedy differs from serial greedy; no production continuation')


def trim_generated(tokens, eos_ids):
    """Remove only batch padding after the first terminal EOS; keep EOS itself."""
    for i, token in enumerate(tokens):
        if token in eos_ids:
            return tokens[:i+1]
    return tokens
