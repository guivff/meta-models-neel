"""Descriptive aggregate recount only; reads existing sealed data, writes nothing."""
import re
from collections import Counter
from evidence_positions import load_d4_records, load_e73_records

d4 = load_d4_records()
nla = [x for x in d4 if x['reader'] == 'nla']
quoted = [(x, re.search(r'final token\s+["“`]([^"”`]+)["”`]', x['text'], re.I)[1]) for x in nla]
print('D4 final-token quotes', len(quoted))
print('D4 exact anywhere', sum(s in x['prompt_text'] for x, s in quoted))
print('D4 casefold anywhere', sum(s.casefold() in x['prompt_text'].casefold() for x, s in quoted))
print('D4 exact suffix', sum(x['prompt_text'].endswith(s) for x, s in quoted))
print('D4 single-word quotes', sum(len(s.split()) == 1 for _, s in quoted))
print('D4 completion language', sum(bool(re.search(r'complet(?:e|es|ed|ing)|closes', x['text'], re.I)) for x in nla))
print('D4 distinct prefixes', len({x['prompt_text'] for x in nla}))
print('D4 distinct copied sentences', len({x['prompt_text'].split('\nCopy: ')[-1] for x in nla}))
future = r'(?:new|another) (?:section|example|prompt)|next (?:section|example)'
for reader in ['nla', 'oracle']:
    for arm in ['none', 'think', 'ignore']:
        rows = [x for x in d4 if x['reader'] == reader and x['arm'] == arm]
        print('D4 future', reader, arm, sum(bool(re.search(future, x['text'], re.I)) for x in rows), len(rows))
        for pos in sorted({x['position'] for x in rows}):
            group = [x for x in rows if x['position'] == pos]
            print('D4 future-position', reader, arm, pos, sum(bool(re.search(future, x['text'], re.I)) for x in group), len(group))

e73 = load_e73_records()
for reader in ['nla', 'oracle']:
    for state in ['W1', 'W2', 'W3', 'W4', 'W5', 'W7', 'W8']:
        rows = [x for x in e73 if x['reader'] == reader and x['row'] == state]
        nxt = [x for x in rows if re.search(r'next token|next word|continu(?:e|ation|ing)|expect', x['text'], re.I)]
        silent = sum(bool(x['judge']['code'] and x['judge']['code']['category'] == 'silent') for x in nxt)
        print('E73 next/silent', reader, state, len(nxt), len(rows), silent)
