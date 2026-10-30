"""CPU-only regression tests for the 16:35 W10 timing gate."""
import ast
from collections import Counter, defaultdict
from contextlib import nullcontext
from pathlib import Path
import subprocess
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[4]
WORKER = ROOT/'projects/g_agreement/blindspot/w10_run.py'


@pytest.fixture
def gate():
    # Exercise exact gate definitions without importing unrelated reader assets.
    tree = ast.parse(WORKER.read_text())
    tree.body = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                 and n.name in ('warmup', 'timed_median', 'smoke')]
    namespace = {'defaultdict': defaultdict}
    exec(compile(tree, str(WORKER), 'exec'), namespace)
    return namespace


def test_median_uses_three_timed_units_and_not_first_or_mean(gate):
    elapsed = iter([100., 2., 3.])
    calls = []
    def timed(fn):
        value = fn()
        return value, next(elapsed)
    gate['timed'] = timed
    value, median, units = gate['timed_median'](lambda: calls.append(len(calls)) or calls[-1])
    assert len(calls) == 3
    assert (value, median, units) == (2, 3., [100., 2., 3.])


def test_generation_normalizes_each_real_unit_before_median(gate):
    values = iter([({'generated_tokens': 48}, 9.),
                   ({'generated_tokens': 24}, 4.),
                   ({'generated_tokens': 12}, 3.)])
    gate['timed'] = lambda fn: next(values)
    value, median, units = gate['timed_median'](
        lambda: None, lambda value, seconds: seconds*48/value['generated_tokens'])
    assert median == 9. and units == [9., 8., 12.]
    assert value['generated_tokens'] == 48


def test_setup_warms_capture_all_three_readers_and_generation_without_timing(gate):
    import torch
    events = []
    ol = SimpleNamespace(model=object(), tok=lambda *a, **kw: {'input_ids': [1, 2, 3]}, base=nullcontext)
    def capture(model, tok, items, checkpoint, batch):
        assert len(items) == batch == 8
        checkpoint()
        events.append('capture')
        return {42: torch.zeros(8, 2), 44: torch.zeros(8, 2)}, []
    def reader(name, obj, vectors, spec):
        assert vectors.shape == (16, 2)
        events.append(name)
    def generate(model, tok, item, checkpoint):
        checkpoint()
        events.append('generation')
    gate.update(capture_with_surprisal=capture, reader_values=reader,
                generate_one=generate, synchronize=lambda: events.append('sync'))
    # No timed/timed_median or score writer is available to this setup function.
    gate['warmup'](ol, object(), object(), lambda: events.append('setup-check'))
    assert [x for x in events if x != 'setup-check'] == ['capture', 'olens', 'jlens', 'nla', 'generation', 'sync']


def test_smoke_forecasts_every_path_from_three_units(gate):
    import torch
    counts = Counter()
    def capture(*args, **kwargs):
        counts['capture'] += 1
        return {42: torch.zeros(16, 2), 44: torch.zeros(16, 2)}, []
    def reader(name, *args):
        counts[name] += 1
    def generate(*args):
        counts['generation'] += 1
        return {'generated_tokens': 48}
    # Five paths: capture, three readers, generation; each has a first-call outlier.
    elapsed = iter([90., 2., 4.]*5)
    def timed(fn):
        return fn(), next(elapsed)
    gate.update(capture_with_surprisal=capture, reader_values=reader,
                generate_one=generate, timed=timed)
    items = [{'id': str(i), 'ids': [1, 2], 'feature': 'row'} for i in range(16)]
    checks = [{'feature': 'row', 'prompt_ids': [1, 2]}]*2
    ol = SimpleNamespace(model=None, tok=None, base=nullcontext)
    forecast, diagnostics = gate['smoke'](items, {'row': {}}, checks, ol, None, None, lambda: None)
    assert counts == dict.fromkeys(['capture', 'olens', 'jlens', 'nla', 'generation'], 3)
    assert forecast == 24.  # capture4 + readers12 + two generations8
    assert diagnostics['capture_units_s'] == [90., 2., 4.]
    assert all(row['sixteen_vectors_s'] == 4. for row in diagnostics['reader_rows'])
    assert all(row['units_s'] == [90., 2., 4.] for row in diagnostics['reader_rows'])
    assert diagnostics['mode_generation_smoke_s'] == [4.]


def test_setup_warmup_precedes_first_science_marker_and_gate():
    source = WORKER.read_text()
    assert source.index('        warmup(ol, jl, nla,') < source.index('        P.science_checkpoint(assignment)')
    assert source.index('        P.science_checkpoint(assignment)') < source.index('        F_remaining, diagnostics = smoke(')
    assert 'warmup(ol, jl, nla, lambda: P.science_deadline(assignment))' in source


def test_science_items_scoring_rules_and_collection_tail_are_unchanged():
    before = subprocess.check_output(['git', 'show', '90a576e4:projects/g_agreement/blindspot/w10_run.py'], cwd=ROOT, text=True)
    after = WORKER.read_text()
    def stable_functions(source):
        return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
                if isinstance(n, ast.FunctionDef) and n.name not in ('warmup', 'timed_median', 'smoke', 'main')}
    assert stable_functions(before) == stable_functions(after)
    marker = '        check()\n        with ol.base():\n            h, surprisal = capture_with_surprisal'
    assert before[before.index(marker):] == after[after.index(marker):]
