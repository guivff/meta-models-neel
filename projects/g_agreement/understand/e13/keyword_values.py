"""Post-seal descriptive value split; no new patterns, inference or API calls."""
import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from common.stats import wilson
from . import io as I
from . import protocol as P

LEDGER = I.CACHE / 'keyword_value_followup' / 'hits.sealed.jsonl'
SEAL = I.OUT / 'KEYWORD_HIT_RECORD_SEAL.json'


def verify_files(base, entries):
    for name, sha in entries.items():
        if I.sha(base / name) != sha:
            raise ValueError('sealed artifact changed: ' + name)


def make_hits():
    if SEAL.exists() or LEDGER.exists():
        raise ValueError('refuse overwrite of sealed hit records')
    verify_files(I.OUT, I.read(I.OUT / 'S84_KEYWORD_SEAL.json')['files'])
    counts = I.read(I.OUT / 'S84_KEYWORD_COUNTS.json')
    refs = counts['source_refs']
    for r in refs:
        if I.sha(Path(r['path'])) != r['sha256']:
            raise ValueError('source changed')
    def source(suffix):
        return Path(next(r['path'] for r in refs if r['path'].endswith(suffix)))
    items = {r['id']: r for r in I.rows(source('/items.input.jsonl'))}
    patterns = I.read(I.OUT / 'KEYWORDS_S84.json')['patterns']
    hits = []
    for reader, suffix, native in [('oracle', '/unasked.target.jsonl', 'olens'), ('nla', '/unasked.nla.jsonl', 'nla')]:
        for r in I.rows(source(suffix)):
            if r['reader'] != native:
                continue
            feature = items[r['id']]['feature']
            valid = isinstance(r['raw'], str) and bool(r['raw'].strip())
            hits.append(dict(scope='s84', item=r['id'], sample=r['sample'], reader=reader,
                             feature=feature, layer=r['layer'], valid=valid,
                             hit=bool(re.search(patterns[feature], r['raw'], re.I)) if valid else False))
    for r in counts['rows']:
        cells = [x for x in hits if x['reader'] == r['reader'] and x['feature'] == r['feature']]
        if (len(cells), sum(x['valid'] for x in cells), sum(x['hit'] for x in cells)) != (r['expected'], r['valid_raw'], r['keyword_hits']):
            raise ValueError('prior sealed count not recovered')
    w1 = I.read(I.OUT / 'POOL_MANIFEST.json')
    verify_files(I.CACHE, w1['files'])
    for r in I.rows(I.CACHE / 'pool.private.jsonl'):
        hits.append(dict(scope='w1', item=r['item_id'], sample=r['sample'], reader=r['reader'],
                         feature=r['feature'], layer=r['layer'], valid=bool(r['raw'].strip()),
                         hit=P.keyword(r['feature'], r['raw'])))
    if len(hits) != 7020:
        raise ValueError('hit-ledger coverage')
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    I.jsonl(LEDGER, hits)
    I.save(SEAL, dict(at=datetime.now(timezone.utc).isoformat(), status='HITS_SEALED_BEFORE_TRUE_VALUE_TABULATION',
                     ledger_cache_only=str(LEDGER), ledger_sha256=I.sha(LEDGER), records=len(hits),
                     source_count_seal_sha256=I.sha(I.OUT / 'S84_KEYWORD_SEAL.json'),
                     w1_pool_manifest_sha256=I.sha(I.OUT / 'POOL_MANIFEST.json'),
                     s84_map_sha256=I.sha(I.OUT / 'KEYWORDS_S84.json'),
                     w1_protocol_sha256=I.sha(Path(P.__file__)),
                     code_sha256=I.sha(Path(__file__)),
                     note='No true-value field is present in the ledger. Prior labels were used for original stratified sampling and dev/test selection; this is not a claim they were historically unseen. New true-value cross-tabulation follows this seal.'))
    print('7020 exact hit records sealed, no true values joined')


def value_rows(hits, labels):
    rows = []
    for scope in ['w1', 's84']:
        for feature in dict.fromkeys(x['feature'] for x in hits if x['scope'] == scope):
            values = P.QUESTIONS[feature]['values'] if scope == 'w1' else ['present', 'absent']
            for reader in ['oracle', 'nla']:
                for arm, value in zip(['A', 'B'], values):
                    cells = [x for x in hits if x['scope'] == scope and x['feature'] == feature and x['reader'] == reader
                             and labels[scope][x['item']]['split'] == 'test' and labels[scope][x['item']]['value'] == value]
                    n = sum(x['valid'] for x in cells)
                    k = sum(x['hit'] for x in cells)
                    p, lo, hi = wilson(k, n)
                    rows.append(dict(scope=scope, feature=feature, reader=reader, layer=cells[0]['layer'] if cells else None,
                                     arm=arm, true_value=value, hits=k, valid_test_records=n, missing_raw=len(cells)-n,
                                     rate=float(p), wilson95=[float(lo), float(hi)],
                                     regex_value_recoverable_hits=0, regex_value_unresolved_hits=k,
                                     correct_stated_value=None, incorrect_stated_value=None))
    return rows


def join_values():
    seal = I.read(SEAL)
    if I.sha(LEDGER) != seal['ledger_sha256'] or I.sha(Path(__file__)) != seal['code_sha256']:
        raise ValueError('hit ledger/code changed')
    if I.sha(I.OUT / 'KEYWORDS_S84.json') != seal['s84_map_sha256'] or I.sha(Path(P.__file__)) != seal['w1_protocol_sha256']:
        raise ValueError('frozen patterns changed')
    hits = I.rows(LEDGER)
    old = I.read(I.OUT / 'POOL_MANIFEST.json')
    refs = I.read(I.OUT / 'S84_KEYWORD_COUNTS.json')['source_refs']
    label_refs = {}
    labels = {}
    for scope, sources in [('w1', old['sources']), ('s84', refs)]:
        ref = next(x for x in sources if x['path'].endswith('/labels.DO_NOT_STAGE.jsonl'))
        if I.sha(Path(ref['path'])) != ref['sha256']:
            raise ValueError('labels changed')
        labels[scope] = {x['id']: x for x in I.rows(Path(ref['path']))}
        label_refs[scope] = ref
    rows = value_rows(hits, labels)
    if len(rows) != 48 or any(r['valid_test_records'] != (84 if r['scope'] == 's84' else (38 if (r['feature'], r['true_value']) in [('prose_paren','inside'), ('table_column','later')] else 37)) for r in rows):
        raise ValueError('value partition coverage')
    data = dict(status='DESCRIPTIVE_POST_SEAL_TRUE_VALUE_SPLIT', at=datetime.now(timezone.utc).isoformat(), rows=rows,
                hit_record_seal_sha256=I.sha(SEAL), label_sources=label_refs,
                value_correctness='NOT IDENTIFIABLE from the frozen expressions. They match property/family names only, with no assertion, negation, ordinal, threshold or relation parser. No additional terms or semantic coder introduced.',
                uncertainty='95% Wilson per readout; two generations per state in section84 are correlated, so these are descriptive record-level intervals, not cluster-adjusted inferential intervals.',
                api_calls=0, gpu_hours=0)
    I.save(I.OUT / 'KEYWORD_BY_TRUE_VALUE.json', data)
    lines = ['# E13(b): literal hits by true value', '',
             'DESCRIPTIVE; same frozen expressions, no new terms. Hits are sealed before this true-value cross-tabulation. W1 uses the original 150 matched test states (one generation/state); §84 uses all sealed test records (two generations/state). A/B are truth labels, not regex-predicted answers. Rates have record-level Wilson 95% intervals; repeated generations are correlated.', '',
             '| Scope / row | Reader / native block | A: hits/n; % [95% CI] | B: hits/n; % [95% CI] |',
             '|---|---|---:|---:|']
    def cell(r):
        return f"{r['hits']}/{r['valid_test_records']}; {100*r['rate']:.1f}% [{100*r['wilson95'][0]:.1f}, {100*r['wilson95'][1]:.1f}]"
    for scope, feature, reader in dict.fromkeys((r['scope'],r['feature'],r['reader']) for r in rows):
        a,b = [r for r in rows if (r['scope'],r['feature'],r['reader']) == (scope,feature,reader)]
        lines.append(f"| {scope} / {feature} | {reader} / {a['layer']} | {cell(a)} | {cell(b)} |")
    lines += ['', 'A/B mapping: W1 prose_paren = inside/outside; W1 table_column = first/later; all §84 rows = present/absent. All raw outputs are nonempty; no missing records.', '',
              '## Whether the stated value is correct', '',
              'NOT DETERMINABLE with the frozen regexes for any row. They flag property names, not a stated A/B value. A colon match also occurs in a negated or hypothetical colon statement; the map has no comma term or assertion/negation parser. The W1 column pattern has no first/later parser. Uppercase, preposition and auxiliary names likewise do not establish an affirmative assertion; digit and magnitude families deliberately share patterns across thresholds. Therefore correct/incorrect stated-value counts are unavailable, and every literal hit remains value-unresolved. This does not mean zero correct values, or that the readouts cannot contain recoverable values; a separately specified value coder would be required. No such coder, extra terms or reinterpretation of prior failed API codes is introduced here.', '',
              'The earlier sealed counts already used labels for stratified W1 sampling and §84 dev/test reporting. Here the exact per-record hits were reconstructed from unchanged source hashes, reconciled with sealed totals, and sealed before this new truth-value join. This sequence does not claim historical label blindness.', '',
              'Blind Claude files remain unchanged; no API/GPU use or Claude-code key join.']
    (I.OUT / 'KEYWORD_BY_TRUE_VALUE.md').write_text('\n'.join(lines)+'\n')
    I.save(I.OUT / 'KEYWORD_VALUE_ANALYSIS_SEAL.json', dict(files={n:I.sha(I.OUT/n) for n in ['KEYWORD_BY_TRUE_VALUE.json','KEYWORD_BY_TRUE_VALUE.md','KEYWORD_HIT_RECORD_SEAL.json']}))
    print('48 true-value cells written with Wilson intervals')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['seal_hits','join_values'])
    args = parser.parse_args()
    {'seal_hits':make_hits, 'join_values':join_values}[args.action]()
