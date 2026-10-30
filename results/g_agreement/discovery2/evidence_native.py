"""Read-only access to allowlisted, already-sealed native outputs.

No experiments, analysis entrypoints, APIs, writes, or imports of project runtime.
Private joining information stays in memory. Never serialize whole returned rows:
only aggregate counts, opaque_id, public readout excerpts and public row definitions.
Run with PYTHONDONTWRITEBYTECODE=1 to avoid creating bytecode outside this folder.
"""
import hashlib
import ast
import json
from pathlib import Path

BASE = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech')
RESULTS = BASE / 'results/g_agreement/understand'


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_files(folder, name='ANALYSIS_SEAL.json'):
    folder = Path(folder)
    seal = read(folder / name)
    assert seal.get('status', 'COMPLETE') in ('COMPLETE', 'COMPLETE_ONCE', 'SEALED')
    for fn, digest in seal['files'].items():
        p = (folder / fn).resolve()
        assert p.is_relative_to(folder.resolve())
        assert sha(p) == digest, str(p)
    return seal


def load_native(bank, include_private=False):
    """E49/E56/E57/E59/E62. _truth/_prompt only when explicitly requested.

    Raw private item IDs are deliberately omitted. Same-item pairing uses an
    independently hashed opaque pair_id. E56 injection rows have no truth unless
    the sealed item bank supplies it, and are marked kind='injection'.
    """
    assert bank in ('E49', 'E56', 'E57', 'E59', 'E62')
    if bank == 'E49':
        return _e49(include_private)
    analysis_name = 'analysis5968_once_2026-10-27' if bank == 'E59' else 'analysis402_once_2026-10-27'
    analysis_dir = RESULTS / bank.lower() / analysis_name
    analysis_seal = verify_files(analysis_dir)
    spec_dir = 'analysis5968' if bank == 'E59' else 'analysis402'
    spec = read(RESULTS / spec_dir / (bank + '_SPEC.json'))
    assert sha(spec['receipt']) == analysis_seal.get('manifest_sha256', analysis_seal.get('receipt_sha256'))
    blind_dir = Path(spec['blind_out'])
    blind = verify_files(blind_dir, 'BLIND_SEAL.json')
    assert sha(spec['private_key']) == blind['private_key_sha256']
    assert sha(spec['private_items']) == spec['private_items_sha256']
    judges = {x['id']: x for x in read(spec['judgments'])}
    judge_seal_path = Path(spec['judgments']).parent / 'JUDGMENT_SEAL.json'
    judge_seal = verify_files(judge_seal_path.parent, judge_seal_path.name)
    if bank == 'E59':
        assert sha(judge_seal_path) == analysis_seal['judgment_seal_sha256']
    else:
        assert sha(judge_seal_path) == sha(analysis_dir / 'JUDGMENT_SEAL.copy.json')
    assert judge_seal.get('blind_seal_sha256', sha(blind_dir / 'BLIND_SEAL.json')) == sha(blind_dir / 'BLIND_SEAL.json')
    keys = {x['opaque_id']: x for x in read(spec['private_key'])}
    items = {x['id']: x for x in read(spec['private_items'])}
    probe_path = analysis_dir / 'PROBE.json'
    probes = read(probe_path) if probe_path.exists() else read(analysis_dir / 'RESULTS.json').get('probe', {})
    packets = read(blind_dir / 'JUDGE_PACKET.json')
    if bank == 'E62':
        packets += read(blind_dir / 'EVAL_PACKET.json')
    out = []
    for p in packets:
        k = keys[p['id']]
        parts = k['source_id'].split(':')
        unit_id = k.get('unit_id', ':'.join(parts[:-2]))
        item = items.get(unit_id)
        reader = parts[-2]
        assert reader in ('oracle', 'nla')
        feature = item['feature'] if item else p['property']
        r = dict(bank=bank, opaque_id=p['id'],
                 pair_id=hashlib.sha256((bank + '|' + unit_id).encode()).hexdigest()[:24],
                 reader=reader, feature=feature, property=p.get('property'),
                 values=p.get('values'), text=p.get('readout', p.get('text')),
                 judge=judges.get(p['id']), probe=probes.get(feature),
                 kind='text' if item else 'injection')
        if include_private and item:
            r['_truth'] = {0: 'A', 1: 'B'}.get(item.get('variant'), item.get('variant'))
            r['_prompt'] = item.get('text')
        out.append(r)
    return out


def _e49(include_private):
    analysis_dir = RESULTS / 'e49/job/analysis'
    a = verify_files(analysis_dir)
    spec = read(RESULTS / 'e49/job/ANALYSIS_SPEC.json')
    root = Path(spec['verified_output'])
    assert sha(root/'OUTPUT_SEAL.json') == a['output_seal_sha256']
    reader_dir = root/'readers'
    seal = verify_files(reader_dir, 'READER_OUTPUT_SEAL.json')
    gates = read(analysis_dir/'GATES.json')['rows']
    items = {}
    if include_private:
        bind = read(RESULTS/'e49/job/INPUT_BINDING.json')
        assert sha(bind['private_items_path']) == bind['private_items_sha256']
        items = {x['id']:x for x in read(bind['private_items_path'])}
    row_dir = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wtext/results/g_agreement/understand/e49/rows')
    public_values = {}
    for source in row_dir.glob('*.py'):
        for node in ast.walk(ast.parse(source.read_text())):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'RowSpec':
                try:
                    row_name = ast.literal_eval(node.args[0]); values = ast.literal_eval(node.args[1])
                except (ValueError, TypeError):
                    continue
                public_values[row_name] = dict(zip(('A','B'), values))
    out=[]
    for fn in sorted(seal['files']):
        if not fn.endswith(('/oracle_native.jsonl','/nla_native.jsonl')):
            continue
        reader=Path(fn).name.split('_')[0]
        for line in (reader_dir/fn).read_text().splitlines():
            x=json.loads(line)
            item=items.get(x['id'])
            r=dict(bank='E49', opaque_id=hashlib.sha256(('E49|'+reader+'|'+x['id']).encode()).hexdigest()[:24],
                   pair_id=hashlib.sha256(('E49|'+x['id']).encode()).hexdigest()[:24],reader=reader,
                   feature=x['feature'],property=x['feature'],values=public_values.get(x['feature']),text=x['text'],judge=None,
                   probe=gates[x['feature']]['probe'],kind='text',malformed=x['malformed'])
            if item:
                r['_truth']={1:'A',0:'B'}.get(item.get('label'));r['_prompt']=item.get('text')
            out.append(r)
    return out
