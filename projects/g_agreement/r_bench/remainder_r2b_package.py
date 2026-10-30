"""Immutable compact pull inventory; fp16 state arrays stay on the volume."""
from pathlib import Path
import shutil
from projects.g_agreement.r_bench import remainder_r2b_runner as R


def package(run,destination):
    run=Path(run).resolve();destination=Path(destination).resolve()
    if destination==run or destination.is_relative_to(run/'outputs'):
        raise ValueError(f'Unsafe compact destination: {destination}')
    destination.mkdir(parents=True,exist_ok=False)
    # Enumerate the actual completed or partial scientific tree, including all states.
    files={str(p.relative_to(run)):R.sha(p) for p in (run/'outputs').rglob('*') if p.is_file()}
    if not files:raise ValueError('Empty output inventory')
    # Operational inputs are public; credential files are never part of this tree.
    for name in ('booking.json','registration.json','manifest.json','volume.json'):
        p=run/name
        if not p.is_file():raise ValueError(f'Missing compact input: {name}')
        files[name]=R.sha(p)
    compact={name:sha for name,sha in files.items() if '/states/' not in name}
    for name in compact:
        src=(run/name).resolve()
        if not src.is_relative_to(run):raise ValueError(f'Escaped source: {name}')
        target=destination/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
        if R.sha(target)!=compact[name]:raise ValueError(f'Changed compact copy: {name}')
    return dict(files=files,compact_files=compact)
