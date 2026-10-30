"""Standalone CPU-only E118b report; never dispatch or replay original E118."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from .analysis import summarize
from projects.g_agreement.e118_analysis.adapter import SYSTEM
from projects.g_agreement.e82_analysis.analyze import mention
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
GUARD = ROOT.parent/'wt-wmech/cache/g_agreement/understand/e118/part_b/ANALYSIS_ONCE.json'
UNIT_SHA = 'eacf843a30acec062587209452823546b6ffad48d3683f5fe6e75f3aebab352e'


def report(spec):
    receipt = read(HERE/'SOURCE_RECEIPT.json')
    for n, h in receipt['files'].items():
        require(sha(ROOT/n) == h, 'frozen report source')
        require(subprocess.check_output(['git', 'show', 'HEAD:'+n], cwd=ROOT) == (ROOT/n).read_bytes(), 'committed report source')
    s = read(spec)
    unit_path = Path(s['unit_seal'])
    unit = verify(unit_path, UNIT_SHA)
    require(unit['n'] == 6790 and unit['n_items'] == 209 and unit['unit_definition_frozen'] is True and unit['frozen_before_judging'] is True, 'original all-position frozen census')
    source_map = {}
    for ref in unit['source_seals']:
        source_map[(ref['seal'], ref['sha256'])] = verify(ref['seal'], ref['sha256'])
    custody = read(unit_path.parent/'CUSTODY.PRIVATE.json')
    public = read(unit_path.parent/'UNITS.json')
    public_by = {x['id']: x for x in public}
    require(len(public_by) == len(public) == len(custody['units']) == 6790, 'all original units')
    files = {x['path']: x['sha256'] for x in custody['original_source_files']}
    for p, h in files.items():
        require(sha(p) == h, 'original public source hash')
    objects = {}

    def resolve(ref):
        if 'seal' in ref:
            sealed = source_map.get((ref['seal'], ref['sha256']))
            require(sealed is not None and ref['member'] in sealed['files'], 'original sealed member')
            path = str(Path(ref['seal']).parent/ref['member'])
        else:
            path = ref['path']
            require(files.get(path) == ref['sha256'], 'original context source')
        if path not in objects:
            objects[path] = read(path)
        value = objects[path]
        for key in ref['keys']:
            value = value[key]
        return value

    joins = []
    for u in custody['units']:
        require(u['id'] in public_by, 'exact opaque join')
        p = public_by[u['id']]
        require(p['context'] == resolve(u['context_ref']) and p['readout'] == resolve(u['readout_ref']), 'unchanged literal context and readout')
        labels = u['original_label_refs']
        require('belief' in labels and set(labels) <= {'belief', 'truth'}, 'original group labels')
        states = {k: mention(resolve(v), v['target_letter']) for k, v in labels.items() if v is not None}
        joins.append(dict(id=u['id'], family=u['family'], item_id=u['item_id'], position=u['position'],
                          belief=states['belief'], truth=states.get('truth'), has_truth=labels.get('truth') is not None))
    require(len({(x['family'], x['item_id']) for x in joins}) == 209, 'original209 items')
    inp = verify(s['input_seal'], s['input_sha256'])
    # C pins this full report closure in its prospective source seal before calls.
    require(sha(s['report_source_seal']) == s['report_source_sha256'], 'report closure seal hash')
    closure = read(s['report_source_seal'])
    require(all(closure['files'].get(n) == h for n, h in receipt['files'].items()), 'pre-call report dependency closure')
    judge = verify(s['judgment_seal'], s['judgment_sha256'])
    require(judge['experiment'] == 'E118' and judge['phase'] == 'belief_wrong_consistency_judging' and judge['status'] == 'COMPLETE', 'complete distinct part-b bank')
    require(judge['input_seal_sha256'] == s['input_sha256'] and judge['E118b_source_seal_sha256'] == s['report_source_sha256'], 'actual input and pre-call source binding')
    require(read(Path(s['input_seal']).parent/'PROVENANCE.json')['owner_seal_sha256'] == UNIT_SHA, 'transport binds exact original roster')
    calls = read(Path(s['input_seal']).parent/'CALLS.json')
    require(len(calls) == len(public_by) and {c['id'] for c in calls} == set(public_by), 'exact frozen calls')
    for c in calls:
        require(c['rendered']['system'] == SYSTEM and json.loads(c['rendered']['user']) == public_by[c['id']], 'original frozen prompt and literal payload')
    require(all(judge[k] is True for k in ('route_verified', 'labels_cpu_only', 'redaction_audit_complete')) and judge['redacted_records'] == 0, 'exact unchanged judged source and privacy')
    cap = verify(s['cap_seal'], s['cap_sha256'])
    cost = read(Path(s['cap_seal']).parent/'CAP_SETTLEMENT.json')
    require('CAP_SETTLEMENT.json' in cap['files'] and cost['bank'] == 'E118' and cost['lifetime_USD'] == 1 and cost['prior_actual_USD'] == .027057 and cost['unknown_USD'] == 0 and .027057 <= cost['total_actual_USD'] <= 1 and cost['judgment_sha256'] == s['judgment_sha256'], 'same lifetime cap includes prior spend and settled part-b bank')
    terminals = read(Path(s['judgment_seal']).parent/'RESPONSES.json')
    result = summarize(terminals, joins)
    out = GUARD.parent/'analysis_once'
    require(not out.exists(), 'fresh output; no replay')
    GUARD.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(GUARD, os.O_WRONLY|os.O_CREAT|os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('{"experiment":"E118","part":"b","status":"CLAIMED_ONCE"}\n')
    out.mkdir()
    write(out/'RESULTS.json', result)
    write(out/'BINDING.json', s)
    write(out/'ANALYSIS_SEAL.json', dict(experiment='E118', part='b', status='COMPLETE_ONCE', files={n: sha(out/n) for n in ('RESULTS.json', 'BINDING.json')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    report(parser.parse_args().spec)
