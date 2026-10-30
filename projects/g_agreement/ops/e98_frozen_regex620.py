"""CPU-only adapter to E76's frozen catalog; absent hits remain unresolved.

Resolve stated A/B values only from a catalog family whose two patterns map
unambiguously to the item's frozen value strings. Never infer silence from a
miss, and never use the true label. Frozen family negation policy is retained.
"""
import re


def aliases(value):return [value] if isinstance(value,str) else value


def apply(text,values,catalog_row):
    if catalog_row is None or catalog_row['status']!='AVAILABLE':return None
    # §202 ambiguity is unresolved and goes to the blind judge, never credited
    # merely because a literal value occurs inside a prohibition/option token.
    if re.search(r"\b(?:not|never|avoid|prohibit(?:ed|s)?|don.t|isn.t|mustn.t)\b",text,re.I):return None
    if re.fullmatch(r"\W*(?:(?:option|answer)\s*)?[a-z]\W*",text.strip(),re.I):return None
    if re.search(r"[\"'].*?\b(?:think|reply|choose|answer|say)\b.*?[\"']",text,re.I):return None
    found=[]
    for family in catalog_row['families']:
        if len(family['patterns'])!=2:continue
        flags=re.I if family['ignore_case'] else 0
        mapped=[]
        for pattern in family['patterns']:
            matches=[v for v in ('A','B') if any(re.search(pattern,a,flags) for a in aliases(values[v]))]
            if len(matches)!=1:break
            mapped.append(matches[0])
        if len(mapped)!=2 or len(set(mapped))!=2:
            # E49's original detector declares A/B by pattern position; its
            # phrase patterns need not match the short value alias alone.
            # This preserves that frozen source order, without adding aliases.
            if catalog_row.get('bank')=='E49' and family.get('derivation')=='Exact frozen E49 extension of E24':mapped=['A','B']
            else:continue
        if family['policy']=='sentence_negation':
            clauses=re.split(r'[.!?\n]+',text)
            hits=[any(re.search(p,c,flags) and not re.search(family['negation'],c,flags) for c in clauses) for p in family['patterns']]
        elif family['policy']=='whole_word_or_frozen_regex':hits=[bool(re.search(p,text,flags)) for p in family['patterns']]
        else:raise ValueError('unknown frozen catalog policy')
        stated=tuple(v for v,h in zip(mapped,hits) if h)
        if stated:found.append(set(stated))
    if not found:return None
    if any(x!=found[0] for x in found):return None  # conflicting mappings need judging
    return [v for v in ('A','B') if v in found[0]]
