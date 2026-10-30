"""Conservative primary value regex; unresolved records go to the registered judge.
No labels or reader identity are accepted. Bare alpha/beta is never a value report.
"""
import re
from rows97 import specifications
SPECS={s['row']:s for s in specifications()}
def classify(row,text):
    # Scope, attribution, and bare-option clauses require semantic judging. Do not
    # treat a forbidden, negated, quoted, or merely conditional value as reported.
    if re.search(r"\b(not|no|never|without|avoid|ignore|don't|cannot|if|otherwise|either|instead|rather|instruction|instructed|asked|told|says|said|quote|quoted|mentions)\b|[\"'“”‘’]",text,re.I):
        return None
    hits=[label for label,p in SPECS[row]['value_regex'].items() if re.search(p,text)]
    return hits[0] if len(hits)==1 else None
