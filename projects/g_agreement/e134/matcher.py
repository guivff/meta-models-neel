"""Frozen §242 clarification 2 literal T4 value matcher; never uses truth."""
import re
from collections.abc import Mapping


def match_candidates(text, candidates):
    """Return canonical identities matched by any original name or alias.

    Unicode whole-word means neither adjacent character is a Unicode word
    character (letter, digit or underscore), using Python re.IGNORECASE.
    Multiple aliases of one identity count once; overlapping aliases belonging
    to different identities remain dual. Strings are escaped, never regexes.
    """
    if not isinstance(text, str) or not isinstance(candidates, Mapping) or not candidates:
        raise ValueError('text and original nonempty candidate mapping required')
    matched=[]
    for name, aliases in candidates.items():
        if not isinstance(name,str) or not name or not isinstance(aliases,(list,tuple)):
            raise ValueError('canonical name and original aliases required')
        terms=[name,*aliases]
        if any(not isinstance(term,str) or not term or term!=term.strip() for term in terms):
            raise ValueError('nonempty unmodified original names and aliases required')
        if any(re.search(r'(?<!\w)'+re.escape(term)+r'(?!\w)',text,re.IGNORECASE) for term in terms):
            matched.append(name)
    return sorted(matched)


def stated_value(matches):
    return matches[0] if len(matches)==1 else None


def coverage_gate(rows):
    """All compared blocks must reach exact-one coverage >=70%."""
    report={}
    for block in (44,52,60):
        available=[r for r in rows if block in r['readings']]
        if not available:continue
        counts={'no_value':0,'single':0,'dual':0}
        for row in available:
            matches=row['matcher_matches'][block]
            if len(set(matches))!=len(matches) or any(not isinstance(v,str) for v in matches):
                raise ValueError('unique canonical matcher identities required')
            if row['readings'][block]!=stated_value(matches):raise ValueError('matcher/scalar mismatch')
            counts['no_value' if not matches else 'single' if len(matches)==1 else 'dual']+=1
        n=len(available)
        report[str(block)]=dict(total=n,unavailable=len(rows)-n,**counts,exact_one_coverage=counts['single']/n,passes=10*counts['single']>=7*n)
    return dict(blocks=report,passes=bool(report) and all(x['passes'] for x in report.values()),threshold=.70)
