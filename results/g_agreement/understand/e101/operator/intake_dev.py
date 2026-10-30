"""One-shot CPU intake. Delegate dose decisions to the frozen selector only."""
import argparse
from pathlib import Path
from projects.g_agreement.e101.contract import read, sha, verify, write, ROWS, validate, select
from projects.g_agreement.e101.select_doses import run
import numpy as np


def select_row(shard, key):
    """Reuse the frozen policy for an independently completed row, without test access."""
    inputs, outputs = Path(shard['input_root']), Path(shard['output_root'])
    verify(inputs, 'INPUT_SEAL.json', shard['input_sha256'])
    seal = verify(outputs, 'OUTPUT_SEAL.json', shard['output_sha256'])
    manifest = read(inputs / 'MANIFEST.json')
    if (seal['status'] != 'COMPLETE' or seal['stage'] != 'dev'
            or seal['input_sha256'] != shard['input_sha256'] or manifest['stage'] != 'dev'
            or manifest['dev_count'] != 84 or manifest['dose_policy'] != 'independent_blocks'
            or manifest['scoring_mode'] != 'continuation' or not manifest['ruling_commit']):
        raise ValueError('registered complete dev row')
    items = read(inputs / 'items.json')
    validate(items, np.load(inputs / 'vectors.npy', allow_pickle=False), 'dev', 84)
    rows = {x['row'] for x in items}
    if len(rows) != 1:
        raise ValueError('one dev row per intake')
    grid = read(outputs / 'JOB_GRID.json')
    if sorted(read(outputs / 'COMPLETED.json')) != list(range(len(grid))):
        raise ValueError('all row jobs complete')
    records = []
    for n, job in enumerate(grid):
        if job['kind'] != 'logits':
            raise ValueError('dev logits only')
        batch = read(outputs / f'jobs/{n:06d}.json')
        if [x['id'] for x in batch] != [items[i]['id'] for i in job['indices']]:
            raise ValueError('exact frozen job order')
        records.extend(batch)
    doses = select(items, records, key, 'continuation', 84)
    row = rows.pop()
    if set(doses) != {f'{row}:42', f'{row}:44'}:
        raise ValueError('both independent blocks')
    return dict(experiment='E101', row=row, stage='DEV_ONLY', selected_doses=doses,
                source_shard=shard, test_outputs_opened=False)


def inspect(binding_path, outputs, source_sha, replacements=None):
    binding = read(binding_path)
    replacements = replacements or {}
    if not set(replacements) <= ROWS:
        raise ValueError('known replacement row')
    if binding['stage'] != 'dev' or {x['row'] for x in binding['packages']} != ROWS:
        raise ValueError('all seven frozen dev input packages')
    complete, pending = [], []
    for package in binding['packages']:
        root = outputs / package['row'] / 'out'
        if package['row'] in replacements:
            original_seal = root / 'OUTPUT_SEAL.json'
            if original_seal.exists() and read(original_seal)['status'] == 'COMPLETE':
                raise ValueError('cannot replace a completed scientific row')
            root = Path(replacements[package['row']])
        seal_path = root / 'OUTPUT_SEAL.json'
        if not seal_path.exists():
            pending.append(dict(row=package['row'], status='AWAITING_VERIFIED_PULL'))
            continue
        digest = sha(seal_path)
        seal = verify(root, seal_path.name, digest)
        if (seal['experiment'] != 'E101' or seal['stage'] != 'dev'
                or seal['input_sha256'] != package['input_sha256']
                or seal['source_sha256'] != source_sha):
            raise ValueError('dev output source/input/stage binding')
        if seal['status'] != 'COMPLETE':
            pending.append(dict(row=package['row'], status=seal['status']))
            continue
        complete.append(dict(input_root=package['input_root'], input_sha256=package['input_sha256'],
                             output_root=str(root.resolve()), output_sha256=digest))
    return binding, dict(shards=complete), pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binding', type=Path, required=True)
    parser.add_argument('--outputs', type=Path, required=True)
    parser.add_argument('--source-sha', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--select-out', type=Path)
    parser.add_argument('--row-out', type=Path)
    parser.add_argument('--row-output', action='append', default=[], metavar='ROW=PATH',
                        help='Explicit Integrator-authorized replacement after incomplete first attempt')
    args = parser.parse_args()
    replacements = dict(x.split('=', 1) for x in args.row_output)
    if len(replacements) != len(args.row_output):
        raise ValueError('one replacement per row')
    source, binding, pending = inspect(args.binding, args.outputs, args.source_sha, replacements)
    receipt = dict(experiment='E101', complete_rows=len(binding['shards']), pending=pending,
                   input_binding_sha256=sha(args.binding), source_sha256=args.source_sha,
                   GPU_calls=0, binding=binding, replacement_output_roots=replacements)
    write(args.receipt, receipt)
    if args.row_out:
        key_path = Path(source['cpu_key_path'])
        if sha(key_path) != source['cpu_key_sha256']:
            raise ValueError('CPU key identity')
        key = read(key_path)
        args.row_out.mkdir(parents=True, exist_ok=True)
        for shard in binding['shards']:
            result = select_row(shard, key)
            path = args.row_out / (result['row'] + '.json')
            if path.exists():
                if read(path) != result:
                    raise ValueError('sealed row selection changed')
            else:
                write(path, result)
    if args.select_out:
        if pending or len(binding['shards']) != 7:
            raise ValueError('all seven COMPLETE rows required before dose selection')
        run(binding, Path(source['cpu_key_path']), source['cpu_key_sha256'], args.select_out)
    print(f"E101 dev intake: {len(binding['shards'])}/7 COMPLETE; {len(pending)} pending")


if __name__ == '__main__':
    main()
