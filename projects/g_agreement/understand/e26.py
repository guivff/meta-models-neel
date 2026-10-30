"""E26 CPU freeze/package operations; no reconstructor imports or calls."""
import argparse
from collections import Counter
from pathlib import Path
import shutil
from .cpu import ROOT, read, rows, dump, sha, verify
from .e26_bank import FEATURES, BRIEF, expected_counts
from .followup_packed import jsonl

PLAN = 'results/g_agreement/understand/e26/PLAN.json'
PATHS = ('E15', 'continuation', 'description', 'noise')
BATCH = 8


def unit_plan(records):
    result = {}
    for path in PATHS:
        ix = [i for i, r in enumerate(records) if r['category'] == path]
        result[path] = [ix[j:j+BATCH] for j in range(0, len(ix), BATCH)]
    return result


def freeze_existing(draft, destination):
    """Preserve every previously hashed payload; only sentiment's admissibility changes."""
    draft, destination = Path(draft), Path(destination)
    old = read(draft/'PREPARATION.json')
    if old['authority_commit'] != '97cfc5dd' or old['reconstructor_calls'] != 0:
        raise ValueError('original pre-AR draft required')
    for r in old['rows']:
        verify(draft/r['feature'], 'BANK_SEAL.json')
        if sha(draft/r['feature']/'BANK_SEAL.json') != r['bank_seal_sha256']:
            raise ValueError('draft bank seal mismatch')
    shutil.copytree(draft, destination)
    receipts = []
    for feature in FEATURES:
        folder = destination/feature
        candidates = rows(folder/'candidates.input.jsonl')
        if dict(Counter(r['category'] for r in candidates)) != expected_counts(feature):
            raise ValueError('clarified category grid mismatch')
        if feature == 'prose_sentiment':
            s = read(folder/'BANK_SEAL.json')
            s.update(status='FROZEN_COMPLETE_ROW_BANK', clarification_commit='4384b1ad',
                     omitted_category='E15', own_value_continuations='category (b)',
                     prior_draft_seal_sha256=sha(draft/feature/'BANK_SEAL.json'))
            dump(folder/'BANK_SEAL.json', s)
        # No resampling, text editing, new candidate, or altered item/activation is permitted.
        for name in read(folder/'BANK_SEAL.json')['files']:
            if sha(folder/name) != sha(draft/feature/name):
                raise ValueError('frozen payload changed')
        receipts.append({'feature': feature, 'items': 80, 'candidates': len(candidates),
                         'counts': expected_counts(feature), 'status': 'FROZEN_COMPLETE_ROW_BANK',
                         'bank_seal_sha256': sha(folder/'BANK_SEAL.json'),
                         'candidate_sha256': sha(folder/'candidates.input.jsonl')})
    old.update(status='READY_BANKS', authority_commit='4384b1ad', launch_allowed=True,
               missing=[], rows=receipts, prior_preparation_sha256=sha(draft/'PREPARATION.json'))
    old['source_pins']['brief'] = sha(ROOT/BRIEF)
    dump(destination/'PREPARATION.json', old)
    return old


def package(banks, out, tokenizer):
    """Stage texts and public hash receipts only; private values/activations stay on CPU."""
    banks, out = Path(banks), Path(out)
    prep = read(banks/'PREPARATION.json')
    if prep['status'] != 'READY_BANKS' or prep['authority_commit'] != '4384b1ad':
        raise ValueError('all clarified banks must be frozen before packaging')
    out.mkdir(parents=True, exist_ok=False)
    records = []
    for receipt in prep['rows']:
        feature = receipt['feature']; folder = banks/feature
        verify(folder, 'BANK_SEAL.json')
        if sha(folder/'BANK_SEAL.json') != receipt['bank_seal_sha256']:
            raise ValueError('bank receipt mismatch')
        dst = out/'banks'/feature; dst.mkdir(parents=True)
        shutil.copyfile(folder/'candidates.input.jsonl', dst/'candidates.input.jsonl')
        records.extend({**r, 'feature':feature} for r in rows(dst/'candidates.input.jsonl'))
    jsonl(out/'texts.input.jsonl', records)
    dump(out/'units.json', unit_plan(records))
    # Unscored timing uses frozen candidates. Repeat the longest path text to fill batch8;
    # no authored filler, labels, activation scoring, or production reuse of timing outputs.
    lengths = [len(tokenizer.encode(r['text'], add_special_tokens=False)) for r in records]
    pilot = []; pilot_units = {}; length_report = {}
    for path in PATHS:
        ix = [i for i,r in enumerate(records) if r['category'] == path]
        longest = max(ix, key=lambda i: (lengths[i], -i))
        start = len(pilot)
        pilot.extend({'id':f'pilot-{path}-{i}', 'text':records[longest]['text'],
                      'source_candidate_id': records[longest]['id'], 'category':path} for i in range(24))
        pilot_units[path] = [list(range(start+j, start+j+8)) for j in (0,8,16)]
        length_report[path] = {'max_tokens':lengths[longest], 'pilot_batch_tokens':8*lengths[longest],
                               'min_tokens':min(lengths[i] for i in ix)}
    jsonl(out/'pilot.input.jsonl', pilot); dump(out/'pilot_units.json', pilot_units)
    dump(out/'BANKS.json', prep)
    dump(out/'PILOT.json', {'source':'frozen candidate copies; unscored', 'paths':length_report,
                           'one_setup_warmup_plus_three_timed_units_each':True})
    dump(out/'INPUT_SEAL.json', {'status':'E26_FROZEN_BEFORE_ANY_AR',
        'files':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}})
    validate_inputs(out)
    return {'input_seal_sha256':sha(out/'INPUT_SEAL.json'), 'records':len(records),
            'units':{k:len(v) for k,v in unit_plan(records).items()}, 'pilot':read(out/'PILOT.json')}


def validate_inputs(inputs, expected_sha=None):
    inputs = Path(inputs)
    if expected_sha is not None and sha(inputs/'INPUT_SEAL.json') != expected_sha:
        raise ValueError('input seal changed')
    verify(inputs, 'INPUT_SEAL.json')
    prep = read(inputs/'BANKS.json')
    if prep['authority_commit'] != '4384b1ad' or not prep['launch_allowed']:
        raise ValueError('clarified frozen banks required')
    if [r['feature'] for r in prep['rows']] != list(FEATURES):
        raise ValueError('exact six rows required')
    records = []
    for r in prep['rows']:
        path = inputs/'banks'/r['feature']/'candidates.input.jsonl'
        candidates = rows(path)
        if sha(path) != r['candidate_sha256'] or r['status'] != 'FROZEN_COMPLETE_ROW_BANK':
            raise ValueError('frozen bank mismatch')
        if Counter(c['category'] for c in candidates) != expected_counts(r['feature']):
            raise ValueError('registered candidate categories mismatch')
        records.extend({**c,'feature':r['feature']} for c in candidates)
    if len(records) != 836 or len({r['id'] for r in records}) != 836:
        raise ValueError('836 distinct candidate instances required')
    if records != rows(inputs/'texts.input.jsonl') or unit_plan(records) != read(inputs/'units.json'):
        raise ValueError('production grid differs from frozen banks')
    forbidden = {'value','source_item','source_split','source_row','label'}
    if any(forbidden & r.keys() for r in records) or any(inputs.rglob('*.DO_NOT_STAGE.*')):
        raise ValueError('private labels cannot be staged')
    pilot=rows(inputs/'pilot.input.jsonl'); units=read(inputs/'pilot_units.json')
    byid={r['id']:r for r in records}
    if len(pilot)!=96 or set(units)!=set(PATHS): raise ValueError('full four-path pilot required')
    for j,path in enumerate(PATHS):
        expected=[list(range(j*24+k,j*24+k+8)) for k in (0,8,16)]
        if units[path]!=expected: raise ValueError('frozen pilot unit grid required')
        for unit in expected:
            for i in unit:
                r=pilot[i];source=byid[r['source_candidate_id']]
                if r['category']!=path or source['category']!=path or r['text']!=source['text']:
                    raise ValueError('pilot must copy frozen candidates unchanged')
    return records


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('draft','banks','out','tokenizer'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    freeze_existing(a.draft,a.banks)
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(a.tokenizer,local_files_only=True)
    print(package(a.banks,a.out,tok))
