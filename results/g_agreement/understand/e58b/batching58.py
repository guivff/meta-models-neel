"""Label-free conditional-prefix scheduling and operational admission."""
import math
from common58 import ARMS, CAP, MAX_CAP, PROGRAMME_STOP, RESERVE, require


def prefix_plan(rows):
    nodes, candidates = [], {}
    for row in rows:
        for item in row['test']:
            prefixes = {}
            for j, pair in enumerate(item['pairs']):
                for side in ('A', 'B'):
                    tokens = pair[side + '_ids']
                    key = (row['key'], item['id'], j, side)
                    candidates[key] = len(tokens)
                    for position, token in enumerate(tokens):
                        prefix = tuple(tokens[:position])
                        node = prefixes.setdefault(prefix, {'row': row['key'], 'id': item['id'],
                            'ids': item['ids'] + list(prefix), 'prompt_length': len(item['ids']), 'uses': []})
                        node['uses'].append((key, position, token))
            for node in prefixes.values():
                node['targets'] = sorted({token for key, position, token in node['uses']})
                nodes.append(node)
    nodes.sort(key=lambda n: (len(n['ids']), n['row'], n['id'], n['ids']))
    return nodes, candidates


def batches(values, size):
    return [values[i:i + size] for i in range(0, len(values), size)]


def probe_batches(values, size):
    chunks = batches(values, size)
    require(chunks, 'Nonempty frozen work plan required')
    # Real input batches: longest sequence, largest padded work, median location.
    indices = [len(chunks) - 1, max(range(len(chunks)), key=lambda i: len(chunks[i]) * len(chunks[i][-1]['ids'])),
               len(chunks) // 2]
    return [chunks[i] for i in dict.fromkeys(indices)]


def estimate_batches(chunks, measurements):
    """Nearest measured upper-shape estimate, quadratic in sequence growth."""
    require(measurements, 'Real measured batches required')
    estimate = 0.
    for chunk in chunks:
        n, length = len(chunk), max(len(x['ids']) for x in chunk)
        estimate += min(m['median_seconds'] * max(1., n / m['sequences'])
                        * max(1., length / m['max_tokens']) ** 2 for m in measurements)
    return estimate


def accumulate(terms, nodes, values):
    require(len(nodes) == len(values), 'Prefix batch count mismatch')
    for node, probabilities in zip(nodes, values):
        for key, position, token in node['uses']:
            value = probabilities[token]
            require(math.isfinite(value) and value <= 0 and terms[key][position] is None, 'Invalid/duplicate token likelihood')
            terms[key][position] = value


def finish(terms):
    import torch
    result = {}
    for key, values in terms.items():
        require(all(v is not None for v in values), 'Missing candidate token probability')
        result[key] = float(torch.tensor(values, dtype=torch.float32).sum())
    return result


def choose_budget(assignment, remaining_seconds, now):
    require(math.isfinite(remaining_seconds) and remaining_seconds >= 0, 'Finite full-run forecast required')
    required_end = now + 1.5 * remaining_seconds + 360
    options = []
    for cap in (CAP, MAX_CAP):
        end = min(assignment['deadline_epoch'], PROGRAMME_STOP,
                  assignment['provider_created_epoch'] + cap - assignment['previous_gpu_seconds'])
        options.append((cap, end, required_end < end - RESERVE))
    for cap, end, fits in options:
        if fits:
            return {'status': 'FIT', 'selected_total_gpu_seconds': cap,
                    'admitted_epoch': now,
                    'preferred_total_gpu_seconds': CAP, 'extension_used': cap > CAP,
                    'preferred_fit': options[0][2], 'effective_provider_deadline_epoch': end,
                    'production_deadline_epoch': end - RESERVE, 'remaining_forecast_seconds': remaining_seconds}
    return {'status': 'NO_FIT', 'admitted_epoch': now, 'preferred_fit': False, 'selected_total_gpu_seconds': None,
            'remaining_forecast_seconds': remaining_seconds, 'maximum_total_gpu_seconds': MAX_CAP}
