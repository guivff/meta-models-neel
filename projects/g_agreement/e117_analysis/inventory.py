"""Accept the original acquisition roster without backdating its normalization."""
import hashlib
import json
import subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core as c

INPUT_SHA = '22532aef629d89603d0280df1f68f38d385b856a7f58628cc15c342b3545c78a'
DELIVERY_COMMIT = '40dcb4d28d3ae8352837993d8eae4dbc68510a76'
DELIVERY_PATH = 'results/g_agreement/understand/e117/PROBE_DELIVERY.json'
STATUS = 'POST_ACQUISITION_SOURCE_NORMALIZATION_NOT_NEW_SELECTION'


def load_inventory(s, root, rows):
    ip = Path(s['inventory_seal']).resolve()
    mode = s.get('inventory_mode', 'committed_inventory')
    if mode == 'committed_inventory':
        original = subprocess.check_output(['git', 'show', s['inventory_commit'] + ':' + str(ip.relative_to(root))], cwd=root)
        c.require(hashlib.sha256(original).hexdigest() == s['inventory_sha256'], 'committed original inventory')
    else:
        c.require(mode == 'original_sealed_input', 'inventory mode')
        c.require(s.get('inventory_commit') is None, 'normalization is not a pre-output commit')
    inv = c.verify(ip, s['inventory_sha256'])
    c.require(inv['experiment'] == 'E117' and inv['directions_committed_before_output'] is True, 'frozen source/directions')
    normalized = c.read(ip.parent / 'INVENTORY.json')
    meta = c.unique(normalized)
    c.require(len(meta) == 336 and all(x['row'] in rows and x['split'] == 'test' for x in meta.values()), 'full fixed test census')
    c.require(all(sum(x['row'] == row for x in meta.values()) == 84 for row in rows), '84 per original row')
    if mode == 'original_sealed_input':
        c.require(inv['status'] == STATUS and bool(inv['created_utc']), 'honest normalization provenance')
        pointer = inv['original_input_seal']
        c.require(pointer['sha256'] == INPUT_SHA, 'exact original acquisition input')
        delivery = json.loads(subprocess.check_output(['git', 'show', DELIVERY_COMMIT + ':' + DELIVERY_PATH], cwd=root))
        c.require(delivery['input_seal_sha256'] == INPUT_SHA, 'pre-output committed acquisition pin')
        original_path = Path(pointer['seal'])
        original = c.verify(original_path, INPUT_SHA)
        c.require(original['experiment'] == 'E117' and original['labels_on_pod'] is False, 'original input custody')
        c.require(set(original['files']) == {'MANIFEST.json', 'items.json', 'H44.npy', 'DELTAS.npy'}, 'whole original input inventory')
        roster = c.read(original_path.parent / 'items.json')
        c.unique(roster)
        c.require(len(roster) == 336, 'original roster count')
        expected = [dict(id=x['id'], row=x['row'], split='test') for x in roster]
        c.require(normalized == expected, 'exact original roster order and identity; no new selection')
        manifest = c.read(original_path.parent / 'MANIFEST.json')
        c.require(manifest['experiment'] == 'E117' and manifest['alphas'] == [1, 2, 4] and manifest['arms'] == ['T', 'W', 'R'], 'original direction grid')
        c.require(manifest['rows'] == delivery['rows'], 'committed original direction lineage')
    return meta
