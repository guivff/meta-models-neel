"""Offline R-D phase assembly, provenance checks, reports and fixed examples.

This module never loads model weights, states, credentials, or provider tools.
Pulled source files are read-only. Aggregate rows receive a deterministic new
analysis identity while preserving each phase file's original provenance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from projects.g_agreement.r_bench import rd_pretext as P
from projects.g_agreement.r_bench import rd_pretext_items as I
from projects.g_agreement.r_bench import rd_pretext_report as R

FINAL_PATHS = dict(R.REPORT_PATHS) | {'aggregate': 'scores_aggregate.jsonl',
                                    'examples': 'examples.json', 'receipt': 'finalize_receipt.json'}
PROVENANCE_FIELDS = ('run_id', 'run_kind', 'code_sha256')


def paths(out):
    return {key: Path(out)/name for key, name in FINAL_PATHS.items()}


def sha(path):
    import hashlib
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def json_file(path):
    return json.loads(Path(path).read_text())


def json_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def _registered(source, basename):
    """A manifest may reference only registered basenames within this source."""
    if not isinstance(basename, str) or Path(basename).name != basename:
        raise ValueError('unregistered phase path '+str(basename))
    allowed = set(P.paths(source).values())
    path = Path(source)/basename
    if path not in allowed or path.resolve().parent != Path(source).resolve():
        raise ValueError('unregistered phase path '+basename)
    return path


def _check_sha(path, expected, label):
    if not isinstance(expected, str) or len(expected) != 64 or sha(path) != expected:
        raise ValueError(label+' SHA256 mismatch: '+Path(path).name)


def _source_hashes(manifest, code_root):
    values = manifest.get('source_hashes')
    if not isinstance(values, dict) or not values:
        raise ValueError('missing frozen source hashes')
    root = Path(code_root).resolve()
    for relative, expected in values.items():
        path = root/relative
        if Path(relative).is_absolute() or not path.resolve().is_relative_to(root):
            raise ValueError('source path outside frozen code root: '+relative)
        _check_sha(path, expected, 'frozen source')
    return values


def validate_windows(bank, windows):
    """Exact frozen a/c prefixes; available b must extend that same prefill."""
    captures = {(row['id'], row['prefilled']): row for row in bank['captures']}
    expected = {(ident, option, position) for ident, option in captures for position in P.POSITIONS}
    by_item = {item['id']: item for item in bank['items']}
    got = {}
    for window in windows:
        key = (window.get('id'), window.get('prefilled'), window.get('position'))
        if key not in expected or key in got:
            raise ValueError('unexpected/duplicate window '+str(key))
        if type(window.get('available')) is not bool:
            raise ValueError('invalid window availability '+str(key))
        capture = captures[key[:2]]
        original = capture['prefix_ids']
        if not window['available']:
            if key[2] != 'b' or not isinstance(window.get('reason'), str) or not window['reason']:
                raise ValueError('only documented b boundary failure is allowed '+str(key))
            if window.get('prefix_ids') is not None or window.get('visible_trace') is not None:
                raise ValueError('missing b window contains invented prefix/text '+str(key))
        else:
            prefix = window.get('prefix_ids')
            if not isinstance(prefix, list) or not prefix or any(type(token) is not int or token < 0 for token in prefix):
                raise ValueError('invalid window prefix '+str(key))
            if window.get('prefix_sha256') != P.digest(prefix):
                raise ValueError('window prefix SHA256 mismatch '+str(key))
            if window.get('read_token_index') != len(prefix)-1 or window.get('read_token_id') != prefix[-1]:
                raise ValueError('window read token/index mismatch '+str(key))
            if not isinstance(window.get('visible_trace'), str):
                raise ValueError('missing window text '+str(key))
            if key[2] == 'a':
                if prefix != original[:-1] or window['visible_trace'] != key[1] or window.get('generated_tokens_used') != 0:
                    raise ValueError('a contains altered prefix or future text '+str(key))
            elif key[2] == 'c':
                if prefix != original or window['visible_trace'] != capture['visible_trace'] or window.get('generated_tokens_used') != 1:
                    raise ValueError('c contains altered prefix or future text '+str(key))
            else:
                forced = original[:-1]
                used = window.get('generated_tokens_used')
                if type(used) is not int or not 1 < used <= P.MAX_GENERATED_TOKENS or len(prefix) != len(forced)+used or prefix[:len(forced)] != forced:
                    raise ValueError('b prefix/cap does not extend frozen forced letter '+str(key))
                common = min(used, len(capture['continuation_ids']))
                if prefix[len(forced):len(forced)+common] != capture['continuation_ids'][:common]:
                    raise ValueError('b changed cached X3 continuation '+str(key))
                if not window['visible_trace'].startswith(key[1]):
                    raise ValueError('b visible trace omitted forced option '+str(key))
        for field in ('split', 'family'):
            if field in window and window[field] != by_item[key[0]][field]:
                raise ValueError('window metadata mismatch '+str(key)+' '+field)
        got[key] = window
    if set(got) != expected:
        raise ValueError('missing windows '+str(sorted(expected-set(got))[:1]))
    failures = [{'id': key[0], 'prefilled': key[1], 'position': 'b',
                 'reason': window['reason'], 'split': by_item[key[0]]['split']}
                for key, window in sorted(got.items()) if not window['available']]
    return got, failures


def phase_rows(source, entries, source_hashes, *, run_kind, windows, bank_sha256, capture_sha256):
    """Verify each phase separately before canonical aggregate stamping."""
    if run_kind not in ('real', 'smoke', 'test'):
        raise ValueError('invalid requested run kind')
    expected_phases = {name[len('scores_'):-len('.jsonl')] for name in P.OUTPUT_PATHS if name.startswith('scores_') and name.endswith('.jsonl')}
    seen_paths, seen_phases, result = set(), set(), []
    for entry in entries:
        phase, basename = entry.get('phase'), entry.get('path')
        if not isinstance(phase, str) or not phase or phase in seen_phases or basename in seen_paths:
            raise ValueError('duplicate/invalid phase manifest entry '+str((phase, basename)))
        if phase not in expected_phases or basename != P.output_path(source, 'scores_'+phase+'.jsonl').name:
            raise ValueError('unknown phase or mismatched score path '+str((phase, basename)))
        seen_phases.add(phase); seen_paths.add(basename)
        path = _registered(source, basename)
        _check_sha(path, entry.get('sha256'), 'phase output')
        rows = json_rows(path)
        if not rows:
            raise ValueError('empty phase output '+basename)
        P.audit_provenance(rows, run_kind=run_kind)
        expected_provenance = tuple(entry.get(field) for field in PROVENANCE_FIELDS)
        if expected_provenance[1] != run_kind or expected_provenance[2] not in source_hashes.values():
            raise ValueError('phase kind/code not in frozen manifest '+phase)
        for row in rows:
            key = (row.get('id'), row.get('prefilled'), row.get('position'))
            if tuple(row.get(field) for field in PROVENANCE_FIELDS) != expected_provenance:
                raise ValueError('phase provenance mismatch '+phase+' '+str(key))
            if key not in windows or not windows[key]['available']:
                raise ValueError('score references absent window '+phase+' '+str(key))
            for field in ('window_prefix_sha256', 'prefix_sha256'):
                if field in row and row[field] != windows[key]['prefix_sha256']:
                    raise ValueError('score/window SHA mismatch '+phase+' '+str(key))
            if 'bank_sha256' in row and row['bank_sha256'] != bank_sha256:
                raise ValueError('score bank SHA mismatch '+phase+' '+str(key))
            if 'capture_manifest_sha256' in row and row['capture_manifest_sha256'] != capture_sha256:
                raise ValueError('score capture SHA mismatch '+phase+' '+str(key))
            result.append(dict(row, source_provenance={**{field: row[field] for field in PROVENANCE_FIELDS},
                          'phase': phase, 'path': basename, 'sha256': entry['sha256']}))
        if 'rows' in entry and entry['rows'] != len(rows):
            raise ValueError('phase row count mismatch '+phase)
    if seen_phases != expected_phases:
        raise ValueError('missing phase outputs '+str(sorted(expected_phases-seen_phases)))
    if not result:
        raise ValueError('no phase outputs to assemble')
    return result


def assemble(bank, bank_file, source, *, run_kind='real', code_root=None):
    """Read and validate complete source; return metadata, rows and windows."""
    source = Path(source)
    code_root = Path(code_root) if code_root is not None else Path(__file__).resolve().parents[3]
    P.audit_paths(source)
    manifest_path = P.output_path(source, 'run_manifest.json')
    manifest = json_file(manifest_path)
    if manifest.get('bank_sha256') != bank['bank_sha256']:
        raise ValueError('run manifest bank SHA256 mismatch')
    _check_sha(bank_file, manifest.get('bank_file_sha256'), 'bank file')
    source_hashes = _source_hashes(manifest, code_root)
    if manifest.get('status') != 'COMPLETE':
        raise ValueError('run manifest is not COMPLETE: '+str(manifest.get('status')))
    capture_path = P.output_path(source, 'capture_manifest.json')
    _check_sha(capture_path, manifest.get('capture_manifest_sha256'), 'capture manifest')
    capture = json_file(capture_path)
    windows_path = P.output_path(source, 'windows.jsonl')
    _check_sha(windows_path, manifest.get('windows_sha256'), 'windows')
    if capture.get('bank_sha256') != bank['bank_sha256'] or capture.get('windows_sha256') != manifest['windows_sha256']:
        raise ValueError('capture/window/bank identity mismatch')
    _check_sha(P.output_path(source, 'states.pt'), capture.get('states_sha256'), 'states')
    raw_windows = json_rows(windows_path)
    P.audit_provenance(raw_windows, run_kind=run_kind)
    if any(window['code_sha256'] not in source_hashes.values() for window in raw_windows):
        raise ValueError('window code not in frozen source manifest')
    if 'generation_sha256' in capture:
        _check_sha(P.output_path(source, 'generation.jsonl'), capture['generation_sha256'], 'generation')
    windows, failures = validate_windows(bank, raw_windows)
    gathered = phase_rows(source, manifest.get('phase_outputs', []), source_hashes,
                          run_kind=run_kind, windows=windows, bank_sha256=bank['bank_sha256'],
                          capture_sha256=manifest['capture_manifest_sha256'])
    by_id = {item['id']: item for item in bank['items']}
    for row in gathered:
        if row['id'] not in by_id or by_id[row['id']]['split'] != 'test' or row['split'] != 'test':
            raise ValueError('full assembly accepts test rows only: '+str(row.get('id')))
    if failures and any(row['position'] == 'b' for row in gathered):
        raise ValueError('globally disabled b position has score rows')
    active = tuple(position for position in P.POSITIONS if not (position == 'b' and failures))
    P.assert_score_coverage(gathered, [item for item in bank['items'] if item['split']=='test'], positions=active)
    aggregate_id = 'rd-aggregate-' + sha(manifest_path)[:24]
    aggregate_code = sha(__file__)
    gathered = [P.stamp_row(row, run_id=aggregate_id, run_kind=run_kind, code_sha256=aggregate_code)
                for row in sorted(gathered, key=lambda row: (row['id'],row['prefilled'],row['position'],row['arm']))]
    P.audit_provenance(gathered, run_kind=run_kind)
    metadata = {'brief_section': P.BRIEF_SECTION, 'run_id': aggregate_id, 'run_kind': run_kind,
                'code_sha256': aggregate_code, 'bank_sha256': bank['bank_sha256'],
                'bank_file_sha256': manifest['bank_file_sha256'], 'run_manifest_sha256': sha(manifest_path),
                'capture_manifest_sha256': manifest['capture_manifest_sha256'],
                'windows_sha256': manifest['windows_sha256'], 'states_sha256': capture['states_sha256'],
                'phase_outputs': manifest['phase_outputs'], 'source_hashes': source_hashes,
                'active_positions': list(active), 'position_failures': failures}
    return {'rows': gathered, 'windows': windows, 'failures': failures, 'metadata': metadata}


def examples(bank, windows, rows, item_ids):
    """Whitelist visible context through each window; never copy full captures."""
    items = {item['id']: item for item in bank['items']}
    score_map = {(row['id'],row['prefilled'],row['position'],row['arm']):row for row in rows}
    result = []
    for ident in item_ids:
        item = items[ident]
        prefills = {}
        for option in ('A','B'):
            positions = {}
            for position in P.POSITIONS:
                window = windows[(ident, option, position)]
                value = {'available': window['available'], 'reason': window.get('reason'),
                         'visible_trace': window.get('visible_trace') if window['available'] else None}
                if window['available']:
                    value.update(visible_context=P.visible_text(item, window),
                                 prefix_sha256=window['prefix_sha256'], read_token_index=window['read_token_index'],
                                 read_token_id=window['read_token_id'])
                available_rows = {arm: score_map[(ident,option,position,arm)]
                                  for arm in P.ARMS_BY_POSITION[position]
                                  if (ident,option,position,arm) in score_map}
                value['reader_outputs'] = {arm: {'score': row['score'], 'outputs': row['outputs'],
                                                'source_provenance': row['source_provenance']}
                                           for arm,row in available_rows.items()}
                if not available_rows:
                    value['evaluation_status'] = 'MISSING_POSITION' if position == 'b' else 'UNAVAILABLE'
                positions[position] = value
            prefills[option] = {'dispreferred': option != item['preferred'], 'positions': positions}
        result.append({'id': ident, 'family': item['family'], 'prompt': item['prompt'],
                       'options': item['options'], 'preferred': item['preferred'], 'prefills': prefills})
    return result


def _write_extra(path, value, *, jsonl=False):
    with Path(path).open('x') as handle:
        if jsonl:
            for row in value:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n')
        else:
            json.dump(value, handle, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False);handle.write('\n')


def finalize(bank_file, source, destination, *, run_kind='real', draws=R.DRAWS, code_root=None):
    """Validate, analyze and report a pulled full run; smoke cannot be promoted."""
    if run_kind not in ('real', 'test'):
        raise ValueError('smoke outputs cannot become a full scientific report')
    source, destination = Path(source), Path(destination)
    if destination.resolve().is_relative_to(source.resolve()):
        raise ValueError('report destination must not modify the pulled source tree')
    out_paths = paths(destination)
    if any(path.exists() for path in out_paths.values()):
        raise FileExistsError('finalized artifact already exists')
    bank = I.load_bank(bank_file)
    manifest = json_file(P.output_path(source,'run_manifest.json'))
    if manifest.get('status') == 'FAILED':
        return finalize_failed(bank, bank_file, source, destination, manifest, run_kind=run_kind, code_root=code_root)
    assembled = assemble(bank, bank_file, source, run_kind=run_kind, code_root=code_root)
    analysis = R.analyze(assembled['rows'], bank, draws=draws, position_failures=assembled['failures'])
    selected_examples = examples(bank, assembled['windows'], assembled['rows'], analysis['example_ids'])
    R.write_report(destination, analysis, assembled['metadata'])
    _write_extra(out_paths['aggregate'], assembled['rows'], jsonl=True)
    _write_extra(out_paths['examples'], selected_examples)
    receipt = {'status': analysis['status'], **assembled['metadata'], 'rows': len(assembled['rows']),
               'example_ids': analysis['example_ids'], 'files': {key: sha(path) for key,path in out_paths.items() if key != 'receipt'}}
    _write_extra(out_paths['receipt'], receipt)
    return receipt


def finalize_failed(bank, bank_file, source, destination, manifest, *, run_kind, code_root=None):
    """Technical/budget stop: verified available evidence and counts, no CIs."""
    if not isinstance(manifest.get('reason'), str) or not manifest['reason'].strip():
        raise ValueError('FAILED manifest needs an explicit reason')
    if manifest.get('bank_sha256') != bank['bank_sha256']:
        raise ValueError('failed manifest bank mismatch')
    _check_sha(bank_file, manifest.get('bank_file_sha256'), 'bank file')
    root = code_root if code_root is not None else Path(__file__).resolve().parents[3]
    source_hashes = _source_hashes(manifest, root)
    P.audit_paths(source)
    available = manifest.get('available_files', {})
    for basename, expected in available.items():
        _check_sha(_registered(source, basename), expected, 'available failed-run output')
    counts = {'frozen_pool_pairs': sum(item['split']=='pool' for item in bank['items']),
              'frozen_test_pairs': sum(item['split']=='test' for item in bank['items']),
              'verified_available_files': len(available)}
    for logical in ('generation.jsonl','windows.jsonl'):
        name = P.output_path(source,logical).name
        if name in available:
            saved = json_rows(P.output_path(source,logical))
            if saved:
                P.audit_provenance(saved, run_kind=run_kind)
            counts[logical+'_saved_rows'] = len(saved)
    analysis = {'status': 'NOT RUN', 'reason': manifest['reason'], 'counts': counts,
                'arms': {}, 'positions': {}, 'scientific_claims': []}
    metadata = {'brief_section': P.BRIEF_SECTION, 'run_kind': run_kind,
                'bank_sha256': bank['bank_sha256'], 'source_hashes': source_hashes,
                'available_files': available, 'run_manifest_sha256': sha(P.output_path(source,'run_manifest.json'))}
    destination = Path(destination); destination.mkdir(parents=True, exist_ok=True)
    out = paths(destination)
    _write_extra(out['analysis'], analysis); _write_extra(out['metadata'], metadata)
    with out['report'].open('x') as handle:
        handle.write('# R-D (§42): NOT RUN\n\n'+manifest['reason']+'\n\n'+
                     '\n'.join(f'- {key}: {value}' for key,value in counts.items())+
                     '\n\nNo reader AUROCs or confidence intervals are reported. Available outputs are preserved and hash-verified.\n')
    _write_extra(out['aggregate'], [], jsonl=True); _write_extra(out['examples'], [])
    receipt = {'status':'NOT RUN', 'reason':manifest['reason'], **metadata,
               'files': {key:sha(path) for key,path in out.items() if key!='receipt'}}
    _write_extra(out['receipt'], receipt)
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bank', type=Path, required=True)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--destination', type=Path, required=True)
    p.add_argument('--draws', type=int, default=R.DRAWS)
    a = p.parse_args()
    receipt = finalize(a.bank,a.source,a.destination,draws=a.draws)
    print(json.dumps({'status':receipt['status'],'destination':str(a.destination)},sort_keys=True))


if __name__ == '__main__':
    main()
