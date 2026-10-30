"""Bind E107 targets to retained dispatch records and I-2's sealed inventory."""
import argparse
from pathlib import Path
from .runner import CACHE, funded
from .transport import ROOT, HERE, frozen_wire
from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require


def indexed(rows, key):
    result = {r[key]: (i, r) for i, r in enumerate(rows)}
    require(len(result) == len(rows), 'no duplicate dispatch identities')
    return result


def join_dispatch(mapping, validations, calls, attempts, judgments):
    """Join explicit original IDs only. Indices are output pointers, not joins."""
    ms = indexed(mapping, 'judgment_id')
    vs = {r['unit']['id']: (i, r) for i, r in enumerate(validations)}
    cs, ats, js = indexed(calls, 'id'), indexed(attempts, 'unit_id'), indexed(judgments, 'id')
    require(len(vs) == len(validations) and set(ms) == set(vs) == set(ats) == set(js), 'full exact unit census')
    out = []
    seen_calls = set()
    for ident, (_, m) in ms.items():
        vi, v = vs[ident]
        ai, a = ats[ident]
        ji, j = js[ident]
        require(v['unit']['kind'] == a['kind'] == j['kind'] == m['kind'] and
                v['unit']['data']['id'] == ident and len(v['calls']) == 1 and
                a['attempt'] == j['attempts'] == 0 and a['id'] == v['calls'][0],
                'original single-attempt unit/call identity')
        ci, call = cs[a['id']]
        expected_phase = 'original' if m['kind'] == 'old_value' else 'judging'
        require(call['phase'] == a['phase'] == expected_phase and
                a['request_id'] == j['request_id'] and a['response_sha256'] == j['response_sha256'] and
                a['status'] == j['status'], 'retained terminal/request/response identity')
        seen_calls.add(call['id'])
        out.append(dict(m, physical_call_id=call['id'], request_id=j['request_id'],
            response_sha256=j['response_sha256'], validation_index=vi, call_index=ci,
            attempt_index=ai, judgment_index=ji, actual_call_phase=call['phase']))
    require(seen_calls == set(cs), 'no unmatched calls')
    return out


def build():
    source = HERE/'E107_DISPATCH_BINDING_SOURCE_SEAL.json'
    for name, digest in read(source)['files'].items():
        require(sha(ROOT/name) == digest, 'published dispatch-binding source')
    home = CACHE/'E107'
    old = home/'explicit_target_binding/BINDING_SEAL.json'
    verify(old, '1318bd971a47d5b5d0c23c8aa345729939620a43cc4ed30bacfb1c3a1c90c14f')
    target_map = read(old.parent/'TARGET_BINDINGS.PRIVATE.json')
    i2 = ROOT.parent/'wt-i2/cache/g_agreement/i2/e107_original_judge_pointers232_v1/SEAL.json'
    verify(i2, 'f1e6f276d2d2f00ba8962253bc8eaa35207ce6f4d0810a6c8522d25df811c95c')
    inventory = indexed(read(i2.parent/'POINTERS.PRIVATE.json'), 'id')
    _, (_, _, protocol, _) = funded.route_api()  # Source modules only; no network call.
    combined, phase_sources = [], []
    for kind, name, n in [('value', 'outside_judge_copy_judging', 4496), ('old_value', 'outside_judge_copy_original', 1124)]:
        root = home/name
        inputs = root/'INPUT_SEAL.json'
        outputs = root/'outputs/JUDGMENT_SEAL.json'
        s = verify(outputs, sha(outputs))
        verify(inputs, s['input_sha256'])
        require(s['status'] == 'COMPLETE' and s['experiment'] == 'E107', 'complete original dispatch phase')
        calls = read(root/'CALLS.json')
        rows = join_dispatch([m for m in target_map if m['kind'] == kind], read(root/'VALIDATION.json'),
            calls, read(outputs.parent/'ATTEMPTS.json'), read(outputs.parent/'JUDGMENTS.json'))
        require(len(rows) == n, 'complete primary/original dispatch census')
        raw_refs = {x['path']: x['sha256'] for x in read(outputs.parent/'RAW_RESPONSE_BINDINGS.json')}
        for r in rows:
            call = calls[r.pop('call_index')]
            physical = ROOT.parent/'wt-internals-b/cache/g_agreement/understand/funded_queue/E107/ledger'/('E107_'+r['actual_call_phase'])
            response = physical/(r['request_id']+'.response.json')
            request = physical/(r['request_id']+'.request.json')
            require(str(response) in raw_refs and sha(response) == raw_refs[str(response)] == r['response_sha256'], 'sealed original response')
            require(read(request)['wire'] == frozen_wire(call, protocol), 'retained original request wire equals exact sealed dispatch call')
            ii, original_item = inventory[r['inventory_id']]
            require(original_item['bank'] == r['bank'], 'I-2 original inventory bank identity')
            r['validation_ref'] = dict(seal=str(inputs), sha256=sha(inputs), member='VALIDATION.json', keys=[r.pop('validation_index')])
            r['attempt_ref'] = dict(seal=str(outputs), sha256=sha(outputs), member='ATTEMPTS.json', keys=[r.pop('attempt_index')])
            r['inventory_ref'] = dict(seal=str(i2), sha256=sha(i2), member='POINTERS.PRIVATE.json', keys=[ii])
            r['request_sha256'] = sha(request)
            r['row'] = original_item['row']
        combined += rows
        phase_sources.append(dict(input_seal=str(inputs), input_sha256=sha(inputs), output_seal=str(outputs), output_sha256=sha(outputs)))
    dest = home/'original_dispatch_target_binding'
    dest.mkdir(exist_ok=True)
    final = dest/'BINDING_SEAL.json'
    if final.exists():
        verify(final, sha(final))
        require(read(dest/'DISPATCH_BINDINGS.PRIVATE.json') == combined, 'immutable original dispatch map')
        return final
    write(dest/'DISPATCH_BINDINGS.PRIVATE.json', combined)
    write(dest/'RECEIPT.json', dict(experiment='E107', n_primary=4496, n_original=1124,
        target_binding_seal=str(old), target_binding_sha256=sha(old), original_dispatch_sources=phase_sources,
        I2_inventory_seal=str(i2), I2_inventory_sha256=sha(i2), source_seal_sha256=sha(source),
        join_keys='explicit unit.id, call.id, attempt.unit_id/request_id and judgment.id; never list order',
        original_comparison='same outside text/property/candidates and inventory/target as amended primary; original E56 rubric, exact seeded25% target subset; not native readouts or an old-candidate-only target',
        original_saved_requests_verified=5620, new_calls=0, analysis_run=False, labels_cpu_only=True))
    write(final, dict(experiment='E107', status='COMPLETE_ORIGINAL_DISPATCH_AND_I2_BINDING',
        files={n: sha(dest/n) for n in ('DISPATCH_BINDINGS.PRIVATE.json', 'RECEIPT.json')}))
    return final


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__).parse_args()
    print('E107 original dispatch binding '+sha(build()))
