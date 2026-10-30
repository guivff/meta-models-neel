"""CPU custody/schema audit of the existing Arm-B document; never scores or generates."""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]

def read(p):
    return json.loads(Path(p).read_text())

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def require(ok, message):
    if not ok:
        raise ValueError(message)

def validate(document, contract, frozen_ids):
    require(document['schema'] == contract['schema'], 'schema')
    require(document['candidate_token_ids'] == contract['candidate_token_ids'], 'candidate A/B token order')
    require(all(s == s.lstrip() for pairs in contract['candidate_strings'].values()
                for pair in pairs for s in pair), 'no leading spaces')
    rows = document['records']
    require(len(rows) == 672, 'exactly 672 records')
    expected = {(row, i, c) for row, ids in frozen_ids.items() for i in ids
                for c in contract['conditions']}
    require(len(expected) == 672 and all(len(ids) == 84 for ids in frozen_ids.values()), 'frozen 2x84x4 grid')
    actual = [(r['feature'], r['id'], r['condition']) for r in rows]
    require(len(set(actual)) == len(actual) and set(actual) == expected, 'exact frozen IDs and conditions')
    for r in rows:
        require(set(r) == {'id', 'feature', 'condition', 'pair_logits'}, 'record schema')
        require(len(r['pair_logits']) == len(contract['candidate_token_ids'][r['feature']]), 'frozen pairs')
        require(all(len(p) == 2 and all(type(v) in (int, float) and math.isfinite(v) for v in p)
                    for p in r['pair_logits']), 'finite raw paired logits')
    return Counter((r['feature'], r['condition']) for r in rows)

def run(out):
    spec = read(HERE/'BEHAVIOUR_SPEC.json')
    receipt = read(spec['receipt']); acquisition = Path(receipt['output'])
    require(receipt['verified'] is True and receipt['issuer'] == 'integrator', 'verified integrator custody')
    require(sha(acquisition/'OUTPUT_SEAL.json') == receipt['output_seal_sha256'], 'acquisition seal')
    seal = read(acquisition/'OUTPUT_SEAL.json'); request = read(HERE/'REQUEST.json')
    require(seal['status'] == 'COMPLETE' and seal['pod_id'] == receipt['pod_id'], 'completed main run')
    for name in ('source_seal_sha256', 'input_seal_sha256'):
        require(seal[name] == request[name], 'executed source/input')
    def sealed(name):
        require(sha(acquisition/name) == seal['files'][name], 'acquisition file '+name)
        return read(acquisition/name)
    assignment = sealed('ASSIGNMENT.json'); timing = sealed('TIMING.json')
    phases = sealed('PHASE_TIMINGS.json')
    require(assignment['pod_id'] == receipt['pod_id'] and timing['completed_epoch'] <= assignment['absolute_deadline_epoch'], 'fixed patch custody')
    contract_path = HERE/'cpu_scorer/INPUT_CONTRACT.json'; contract = read(contract_path)
    require(sha(spec['private_items']) == contract['E59_private_items_sha256'], 'frozen CPU item set')
    private = read(spec['private_items'])
    ids = {row: {x['id'] for x in private if x['feature'] == row and x['split'] == 'test'}
           for row in contract['candidate_token_ids']}
    document_path = Path(spec['out'])/'NEXT_TOKEN_LOGITS.json'
    behaviour_seal = read(Path(spec['out'])/'BEHAVIOUR_SEAL.json')
    require(behaviour_seal['output_seal_sha256'] == receipt['output_seal_sha256'] and
            sha(document_path) == behaviour_seal['files']['NEXT_TOKEN_LOGITS.json'], 'existing sealed document')
    document = read(document_path); counts = validate(document, contract, ids)
    binding = read(HERE/'INPUT_BINDING.json')
    require(sha(spec['private_join']) == binding['private_join_sha256'], 'CPU private join pin')
    key = {x['id']: x for x in read(spec['private_join'])}
    grid = sealed('JOB_GRID.json'); completed = sealed('COMPLETED.json')
    require(completed == list(range(len(grid))), 'complete job grid')
    expected = []
    for i, job in enumerate(grid):
        if job['kind'] != 'continuation':
            continue  # Never open native readouts.
        for x in sealed(f'jobs/{i:06d}.json'):
            k = key[x['id']]
            expected.append(dict(id=k['source_item_id'], feature=k['row'],
                condition={'J':'d_J','nonJ':'d_perp','random':'random','none':'none'}[k['condition']],
                pair_logits=x['pair_logits']))
    require(document['records'] == expected, 'unaltered raw acquisition logits in A/B order')
    result = dict(status='PASS_EXISTING_DOCUMENT_NO_RESCORING', document=str(document_path),
        document_sha256=sha(document_path), records=672, contract_sha256=sha(contract_path),
        acquisition_receipt=receipt, acquisition_receipt_sha256=sha(spec['receipt']),
        source_seal_sha256=seal['source_seal_sha256'], input_seal_sha256=seal['input_seal_sha256'],
        patch_custody=dict(block=44, position='frozen read_index; last prompt token',
            forward='base model, adapter disabled, exactly one prefill patch, no generation',
            candidate_order='A/B; exact contract token IDs; no leading spaces',
            assignment_sha256=sha(acquisition/'ASSIGNMENT.json'),
            timing_sha256=sha(acquisition/'TIMING.json'), completed_epoch=timing['completed_epoch']),
        cell_counts={f'{row}/{condition}': n for (row,condition),n in sorted(counts.items())},
        CPU_only_labels=True, new_scores=0, GPU_seconds=0)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('x') as f:
        json.dump(result, f, indent=2); f.write('\n')
    return result

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); run(a.out)
    print('PASS: 672 unchanged paired-logit records; no scoring, native access or GPU')
