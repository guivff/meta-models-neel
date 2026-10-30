"""Frozen E122 continuation arithmetic; no model loading or outcome selection.

Input JSONL: id, contrast_id, positive_token_logprobs, negative_token_logprobs.
Each list contains *conditional* log-probabilities in the frozen token order.
Run: python score122.py INPUT.jsonl OUTPUT.jsonl (output must not already exist).
"""
import argparse
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_contract():
    return json.loads((HERE / 'CONTRASTS.json').read_text())


def score(contrast_id, positive_token_logprobs, negative_token_logprobs):
    pairs = {c['id']: c for c in load_contract()['contrasts']}
    if contrast_id not in pairs:
        raise ValueError('unknown frozen contrast')
    pair = pairs[contrast_id]
    totals = []
    for side, values in (('positive', positive_token_logprobs),
                         ('negative', negative_token_logprobs)):
        if not isinstance(values, list) or len(values) != len(pair[side]['token_ids']):
            raise ValueError('conditional log-probability count differs from frozen tokens')
        if any(isinstance(v, bool) or not isinstance(v, (int, float))
               or not math.isfinite(v) or v > 0 for v in values):
            raise ValueError('expected finite nonpositive conditional log-probabilities')
        totals.append(math.fsum(values))
    return totals[0] - totals[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    # Validate the full input before creating an exclusive output; no partial report.
    results, seen = [], set()
    for line in args.input.read_text().splitlines():
        record = json.loads(line)
        item_id = record['id']
        if not isinstance(item_id, str) or not item_id:
            raise ValueError('expected nonempty string item id')
        key = (item_id, record['contrast_id'])
        if key in seen:
            raise ValueError('duplicate item/contrast')
        seen.add(key)
        value = score(record['contrast_id'], record['positive_token_logprobs'],
                      record['negative_token_logprobs'])
        results.append({'id': item_id, 'contrast_id': record['contrast_id'],
                        'log_probability_difference': value})
    with args.output.open('x') as handle:
        for record in results:
            handle.write(json.dumps(record, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
