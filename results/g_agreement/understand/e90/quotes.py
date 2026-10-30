"""Section205 literal-buffer extractor, frozen before E81/E90 outputs.

CPU only. Count quoted occurrences (not unique strings), >=3 Unicode characters,
case-folded literal substring in the paired read prefix. No whitespace cleanup,
semantic matches or escape decoding. Straight/curly double quotes, straight/curly
single quotes and backticks are supported; intra-word apostrophes are excluded.
Unclosed or nested quote delimiters are not inferred. Random-vector records must
be supplied separately with their pre-fixed random-item pairing.
"""
import re

_PATTERNS = (
    re.compile(r'"([^"\n]+)"'),
    re.compile(r'“([^“”\n]+)”'),
    re.compile(r"(?<!\w)'([^'\n]+)'(?!\w)"),
    re.compile(r'(?<!\w)‘([^‘’\n]+)’(?!\w)'),
    re.compile(r'`([^`\n]+)`'),
)

def extract(text):
    candidates = sorted((m.start(), m.end(), m.group(1))
                        for pattern in _PATTERNS for m in pattern.finditer(text))
    accepted, end = [], -1
    for start, stop, span in candidates:
        if start < end:
            continue
        end = stop
        if len(span) >= 3:
            accepted.append(span)
    return accepted

def literal_counts(text, prefix):
    spans = extract(text)
    prefix = prefix.casefold()
    return {'quoted_spans': len(spans),
            'literal_spans': sum(span.casefold() in prefix for span in spans)}

def report(records):
    """Records: reader, text, prefix, random_vector (explicit boolean).

    Returns per-reader/control occurrence-weighted rates; zero denominator is
    None, never zero. Caller fixes and seals random-vector/item pairing first.
    """
    groups = {}
    for row in records:
        assert type(row['random_vector']) is bool
        key = (row['reader'], row['random_vector'])
        counts = groups.setdefault(key, dict(records=0, quoted_spans=0, literal_spans=0))
        counts['records'] += 1
        for name, value in literal_counts(row['text'], row['prefix']).items():
            counts[name] += value
    return [dict(reader=reader, random_vector=control, **counts,
                 literal_fraction=(counts['literal_spans']/counts['quoted_spans']
                                   if counts['quoted_spans'] else None))
            for (reader, control), counts in sorted(groups.items())]
