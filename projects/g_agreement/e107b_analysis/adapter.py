"""§240: sealed original Oracle versus a forecast baseline, CPU only."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e107_analysis.adapter import evaluate
from projects.g_agreement.e107_analysis.rules import compare

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRIMARY = 'f2da69a4f0e7acb560552cb9bee8c56ea8012a926a9508303113a2d3ccdd93b8'
GUARD = ROOT.parent / 'wt-wmech/cache/g_agreement/understand/e107/part_b/ANALYSIS_ONCE.json'
require = core.require


def reading(d):
    p, ci = d['estimate'], d['CI95']
    if p is None or ci is None:
        return 'NOT EVALUABLE'
    return 'MET' if round(p, 12) >= .20 and ci[0] > 0 else 'NOT MET'


def analyze(items):
    pooled = compare(items, 'oracle', 'outside', 'belief', True)
    return dict(experiment='E107b', authority='§240', status='DESCRIPTIVE',
                baseline='forecast Qwen answer; outside denotes forecast throughout this result',
                bootstrap=dict(draws=5000, seed=0, unit='source item', paired=True,
                               denominators='each output independently conditional on naming a value'),
                pooled=pooled, forecast_survival=reading(pooled['difference']),
                interpretation='MET: claim survives forecast; NOT MET: narrows to beyond a describer; NOT EVALUABLE: unknown',
                caveat='Baseline and judge share a model family; confounding direction unknown. Original E107 result and verdict remain sealed.')


def resolver(sources):
    seals = [core.verify(x['seal'], x['sha256']) for x in sources]
    cache = {}
    def ref(r):
        i = r['seal_index']
        require(type(i) is int and 0 <= i < len(seals), 'source seal index')
        require(r['member'] in seals[i]['files'], 'sealed source member')
        k = (i, r['member'])
        if k not in cache:
            cache[k] = core.read(Path(sources[i]['seal']).parent / r['member'])
        value = cache[k]
        for key in r['keys']:
            value = value[key]
        return value
    return ref


def targets(entry, ref):
    require(set(entry) == {'belief', 'truth'}, 'both original target judgments required')
    out = {}
    for target, fields in entry.items():
        require(set(fields) == {'text', 'code', 'target_letter'}, 'exact source fields')
        out[target] = {k: ref(v) for k, v in fields.items()}
    return out


def cohort(metadata):
    rows = [x for x in metadata if x['bank'] == 'E82' and x['cohort'] == 'belief_wrong']
    require(len(rows) == 199, 'exact original 199 belief-wrong items')
    require(len({(x['row'], x['item_id']) for x in rows}) == 199, 'unique original source items')
    return core.unique(rows)


def inputs(s):
    primary = Path(s['primary_seal'])
    ps = core.verify(primary, PRIMARY)
    require('BINDING.json' in ps['files'] and 'RESULTS.json' in ps['files'], 'original private primary binding')
    old = core.read(primary.parent / 'BINDING.json')
    ip = Path(old['inventory_seal'])
    inv = core.verify(ip, old['inventory_sha256'])
    require('INVENTORY.json' in inv['files'], 'original inventory')
    original = cohort(core.read(ip.parent / 'INVENTORY.json'))
    op = Path(old['output_seal'])
    oldseal = core.verify(op, old['output_sha256'])
    require('MEASUREMENTS.json' in oldseal['files'], 'original Oracle index')
    oldvalues = core.unique(core.read(op.parent / 'MEASUREMENTS.json'))
    oldref = resolver(oldseal['source_seals'])
    fp = Path(s['output_seal'])
    fs = core.verify(fp, s['output_sha256'])
    require(fs['experiment'] == 'E107b' and fs['status'] == 'COMPLETE', 'terminal E107b bank')
    require(fs['primary_sha256'] == PRIMARY and fs['inventory_sha256'] == old['inventory_sha256'], 'original cohort binding')
    for flag in ('route_verified', 'privacy_verified', 'same_route_and_judge', 'redaction_audit_complete', 'full_original_cohort', 'source_mapping_verified'):
        require(fs.get(flag) is True, 'owner verification: ' + flag)
    require(fs['redacted_records'] == 0, 'nonzero redaction needs prospective source-bound companion before opening')
    require(fs['unknown_cost_requests'] == 0 and 0 <= fs['booked_usd'] <= fs['cap_usd'] == 2, 'terminal lifetime USD2 cap')
    require(fs['prompt'] == "What will this model answer? Give the value.", 'registered forecast instruction')
    require(fs['outside_generation'] == oldseal['outside_generation'], 'same original generation route/settings')
    require('MEASUREMENTS.json' in fs['files'], 'forecast index')
    forecast = core.unique(core.read(fp.parent / 'MEASUREMENTS.json'))
    require(set(forecast) == set(original), 'no skipped/added forecast items')
    newref = resolver(fs['source_seals'])
    items = []
    for ident, meta in original.items():
        oracle = targets(oldvalues[ident]['systems']['oracle'], oldref)
        entry = forecast[ident]
        require((entry['row'], entry['item_id']) == (meta['row'], meta['item_id']), 'exact original identity')
        outside = targets(entry['targets'], newref)
        letters = meta.get('target_letters_by_system', {}).get('oracle', meta.get('target_letters'))
        m = dict(meta, systems=['oracle', 'outside'], target_letters_by_system={
            'oracle': letters, 'outside': entry['target_letters']})
        items.append(evaluate(m, dict(oracle=oracle, outside=outside)))
    return items


def committed():
    receipt = core.read(HERE / 'SOURCE_RECEIPT.json')
    for name, digest in receipt['source_files'].items():
        p = ROOT / name
        require(core.sha(p) == digest, 'source receipt mismatch: ' + name)
        blob = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=ROOT)
        require(hashlib.sha256(blob).hexdigest() == digest, 'source not committed: ' + name)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    s = core.read(parser.parse_args().spec)
    commit = committed()
    require(ROOT.name == 'wt-wmech2', 'production only from canonical worktree')
    require(not GUARD.exists(), 'E107b once guard consumed')
    result = analyze(inputs(s))
    json.dumps(result, allow_nan=False)  # validate result BEFORE sole guard
    out = core.claim(dict(analysis=s['analysis'], guard=str(GUARD), output_sha256=s['output_sha256']), commit)
    core.write(out / 'RESULTS.json', result)
    core.write(out / 'BINDING.json', s)
    core.seal(out, 'ANALYSIS_SEAL.json', experiment='E107b', status='COMPLETE_ONCE',
              code_commit=commit, primary_sha256=PRIMARY, output_sha256=s['output_sha256'])


if __name__ == '__main__':
    main()
