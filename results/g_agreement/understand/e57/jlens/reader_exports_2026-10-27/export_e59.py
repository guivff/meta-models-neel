"""Package E59 saved J outputs; no forward, pursuit, statistics or analysis calls."""
from pathlib import Path
import ast
import hashlib
import importlib.util
import json
import shutil
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
FORECAST_COMMIT = 'c2dbe1773f44cf838b800a3cd9148e874fe95edf'
ADAPTER_COMMIT = '65297a2e98a200a5a7dcfcf1885cb527a2108020'
SPEC_PATH = 'results/g_agreement/understand/analysis5968/E59_SPEC.json'
EXPECTED_FORECAST = 'c21a4bef366f725a3f8df99f39045053040e43076aa1eb8289b34e88e201fef8'

def git_bytes(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT)

def main():
    modspec = importlib.util.spec_from_file_location('saved_export_helpers', HERE/'export_reader.py')
    h = importlib.util.module_from_spec(modspec)
    modspec.loader.exec_module(h)
    h.verify(HERE, 'EXPORT_CODE_SEAL.json')
    def original(path):
        assert path.read_bytes() == git_bytes(FORECAST_COMMIT, str(path.relative_to(ROOT)))
        return h.read(path)
    forecast_path = ROOT/'results/g_agreement/understand/e52/r3b/E59_JFORECAST.json'
    forecast = original(forecast_path)
    assert h.sha(forecast_path) == EXPECTED_FORECAST
    planpath = HERE.parent/'E59_INPUT_PLAN.json'
    plan = original(planpath)
    ld = HERE.parent/'E59_results'
    labels = original(ld/'ROW_LABELS.json')
    original(ld/'LABEL_SEAL.json')
    h.verify(ld, 'LABEL_SEAL.json', forecast['label_seal_sha256'])
    assert labels['plan_sha256'] == forecast['plan_sha256'] == h.sha(planpath)
    assert not labels['reader_outcomes_accessed'] and not forecast['reader_outcomes_accessed']
    raw = Path(labels['raw_directory'])
    h.verify(raw, 'RAW_SEAL.json', labels['raw_seal_sha256'])
    specbytes = git_bytes(ADAPTER_COMMIT, SPEC_PATH)
    spec = json.loads(specbytes)
    assert (ROOT.parent/'wt-wmech'/SPEC_PATH).read_bytes() == specbytes
    inp = Path(spec['inputs'])
    ins = h.verify(inp, 'INPUT_SEAL.json', spec['input_seal_sha256'])
    assert ins['experiment'] == 'E59' and ins['label_free'] is True
    assert plan['bank_seal']['sha256'] == forecast['bank_seal_sha256']
    assert any(x['path'] == str(inp/'INPUT_SEAL.json') and x['sha256'] == spec['input_seal_sha256'] for x in plan['value_sources'])
    assert h.sha(Path(plan['bank_seal']['path'])) == plan['bank_seal']['sha256']
    assert h.sha(Path(plan['records']['path'])) == plan['records']['sha256']
    records = h.read(plan['records']['path'])
    public = h.read(inp/'items.json')
    assert [x['id'] for x in records] == [x['id'] for x in public]
    expected = {x['feature'] for x in public if x['split'] == 'test'}
    assert len(expected) == 6 and not plan['exclusions'] and not forecast['exclusions']
    delivery = ROOT/'cache/g_agreement/understand/e59/capture_delivery'
    receipt = h.read(delivery/'DELIVERY.json')
    assert receipt['experiment'] == 'E59' and receipt['issuer'] == 'integrator'
    cap = h.verify(delivery, 'CAPTURE_SEAL.json', receipt['capture_seal_sha256'])
    assert cap['input_seal_sha256'] == spec['input_seal_sha256']
    bound = Path(plan['capture_seal']['path'])
    assert h.sha(bound) == forecast['capture_seal_sha256'] == plan['capture_seal']['sha256']
    h.verify(bound.parent, bound.name, plan['capture_seal']['sha256'])
    byid = {x['row']: x for x in labels['rows']}
    fr = {x['row']: x for x in forecast['rows']}
    assert set(byid) == set(fr) == expected == {u['id'] for u in plan['units']}
    rows, reader = {}, {}
    for unit in plan['units']:
        key = unit['id']
        items = h.read(raw/(key+'.readout.json'))['items']
        assert len(items) == 84
        assert set(unit['item_ids']) == {x['id'] for x in public if x['feature'] == key and x['split'] == 'test'}
        rows[key] = h.row_view(unit, byid[key], items)
        assert rows[key]['J_label'] == fr[key]['label']
        assert rows[key]['J_fraction'] == fr[key]['J_fraction']
        reader[key] = items
    out = ROOT/'cache/g_agreement/understand/j_reader_exports_2026-10-27/E59'
    target = Path(spec['j_input'])
    dest = HERE/'E59'
    assert not out.exists() and not target.exists() and not dest.exists()
    out.mkdir(parents=True)
    h.dump(out/'reader/READOUTS.json', reader)
    h.dump(out/'reader/INPUT_SEAL.json', {'files': {'READOUTS.json': h.sha(out/'reader/READOUTS.json')}, 'source_raw_seal_sha256': labels['raw_seal_sha256'], 'source_raw_directory': str(raw), 'method': 'Exact saved readouts; no forward or statistical rerun'})
    h.dump(out/'labels/ROW_LABELS.json', labels)
    h.dump(out/'labels/INPUT_SEAL.json', {'files': {'ROW_LABELS.json': h.sha(out/'labels/ROW_LABELS.json')}, 'source_label_seal_sha256': h.sha(ld/'LABEL_SEAL.json')})
    h.dump(out/'J_ROWS.json', rows)
    h.dump(out/'PROVENANCE.json', {'experiment': 'E59', 'forecast_commit': FORECAST_COMMIT, 'forecast_sha256': EXPECTED_FORECAST, 'adapter_commit': ADAPTER_COMMIT, 'adapter_spec_path': SPEC_PATH, 'adapter_spec_sha256': hashlib.sha256(specbytes).hexdigest(), 'plan_sha256': h.sha(planpath), 'source_delivery_sha256': h.sha(delivery/'DELIVERY.json'), 'original_bound_capture_seal_sha256': h.sha(bound), 'source_raw_seal_sha256': labels['raw_seal_sha256'], 'source_label_seal_sha256': h.sha(ld/'LABEL_SEAL.json'), 'delivery_target': str(target), 'reader_outcomes_accessed': False, 'G3_method': 'Copied sealed J_readability full-vocabulary A/B rank AUROC; no recomputation', 'row_grid': 'All six registered binary rows, 84 saved test readouts each, zero exclusions'})
    caps = {'E59': receipt['capture_seal_sha256']}
    seal = {'experiment': 'E59', 'bank_seal_sha256': plan['bank_seal']['sha256'], 'input_seal_sha256': spec['input_seal_sha256'], 'capture_seal_sha256': caps['E59'], 'capture_seals': caps, 'source_seals': {n: h.sha(out/n/'INPUT_SEAL.json') for n in ('reader','labels')}, 'export_code_sha256': h.sha(Path(__file__)), 'helper_code_seal_sha256': h.sha(HERE/'EXPORT_CODE_SEAL.json'), 'reader_outcomes_accessed': False, 'files': {str(p.relative_to(out)): h.sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
    h.dump(out/'J_SEAL.json', seal)
    # Run only the pinned J-input validator, never an outcome collector/analyzer.
    source = git_bytes(ADAPTER_COMMIT, 'results/g_agreement/understand/e56/job/analysis_io.py').decode()
    fun = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'j_inputs')
    def require(ok, message):
        if not ok:
            raise ValueError(message)
    env = {'Path': Path, 'verify': h.verify, 'read': h.read, 'require': require}
    exec(compile(ast.Module(body=[fun], type_ignores=[]), 'pinned_j_inputs', 'exec'), env)
    test_spec = dict(spec, j_input=str(out), bank_seal_sha256=plan['bank_seal']['sha256'])
    assert env['j_inputs'](test_spec, {'capture_seals': caps}) == rows
    # Exact E59-specific seal/row checks from analysis5968, using capture/input data only.
    js = h.verify(out, 'J_SEAL.json')
    assert js['capture_seal_sha256'] == h.sha(delivery/'CAPTURE_SEAL.json')
    assert js['input_seal_sha256'] in (spec['input_seal_sha256'], spec['parent_input_seal_sha256'])
    assert set(h.read(out/'J_ROWS.json')) == expected
    shutil.copytree(out, target)
    h.verify(target, 'J_SEAL.json', h.sha(out/'J_SEAL.json'))
    dest.mkdir()
    for name in ('J_ROWS.json', 'J_SEAL.json', 'PROVENANCE.json', 'reader/INPUT_SEAL.json', 'labels/INPUT_SEAL.json'):
        p = dest/name
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(out/name, p)
    h.dump(dest/'DELIVERY.json', {'experiment': 'E59', 'target': str(target), 'complete_bundle': str(out), 'forecast_commit': FORECAST_COMMIT, 'forecast_sha256': EXPECTED_FORECAST, 'J_SEAL_sha256': h.sha(out/'J_SEAL.json'), 'J_ROWS_sha256': h.sha(out/'J_ROWS.json'), 'rows': len(rows), 'saved_test_readouts': sum(len(x) for x in reader.values()), 'raw_reader_payload_in_cache': True, 'pinned_J_input_validation': 'PASS', 'E59_adapter_capture_input_row_checks': 'PASS', 'reader_outcomes_accessed': False, 'analysis_claim_consumed': False})
    print('E59: six rows / 504 saved test readouts delivered; J-only validation PASS')

if __name__ == '__main__':
    main()
