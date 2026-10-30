"""Prospective C4 explicit-property statement detector, never enactment scoring."""
import re

PATTERNS = {
 'json_type': (r'\bstring(?:[- ]valued| value)?\b',r'\b(?:numeric|number)(?:[- ]valued| value)?\b'),
 'latex_environment': (r'\bequation environment\b',r'\b(?:quote|quotation) environment\b'),
 'latex_fraction': (r'\b(?:fraction )?numerator\b',r'\b(?:fraction )?denominator\b'),
 'latex_item': (r'\bfirst (?:enumerated|enumeration|list) item\b',r'\b(?:later|subsequent|non[- ]first) (?:enumerated|enumeration|list) item\b'),
 'latex_math': (r'\b(?:inline )?math(?:ematical)? mode\b',r'\b(?:ordinary )?text mode\b'),
 'latex_section': (r'\b(?:early|first) (?:document )?section\b',r'\b(?:late|later) (?:document )?section\b'),
 'list_depth': (r'\b(?:top[- ]level|first[- ]level|shallow) (?:list|bullet)(?: item)?\b',r'\b(?:third[- ]level|deep(?:ly nested)?) (?:list|bullet)(?: item)?\b'),
 'list_index': (r'\bfirst (?:list|bullet) item\b',r'\b(?:later|subsequent|non[- ]first) (?:list|bullet) item\b'),
 'prose_paren': (r'\b(?:inside (?:a |an |the )?(?:open )?parenthes(?:is|es)|open parenthes(?:is|es))\b',r'\b(?:outside (?:any |a |the )?parenthes(?:is|es)|closed parenthes(?:is|es))\b'),
 'prose_quote': (r'\b(?:open quotation|inside (?:a |the )?(?:quotation|quoted text))\b',r'\b(?:closed quotation|outside (?:a |the )?(?:quotation|quoted text))\b'),
 'prose_sentence': (r'\b(?:early|first) sentence (?:in|of) (?:the |a )?paragraph\b',r'\b(?:late|later) sentence (?:in|of) (?:the |a )?paragraph\b'),
 'python_argument': (r'\bfirst (?:function |call )?argument\b',r'\b(?:later|subsequent|non[- ]first) (?:function |call )?argument\b'),
 'python_comment': (r'\b(?:python |code )?comment\b',r'\b(?:executable python code|executable code|python code outside (?:a |the )?comment)\b'),
 'python_depth': (r'\bshallow (?:bracket )?nesting\b',r'\bdeep (?:bracket )?nesting\b'),
 'python_indent': (r'\b(?:one|1|single) level of indentation\b',r'\b(?:three|3) levels? of indentation\b'),
 'python_string': (r'\b(?:open string literal|inside (?:a |the )?string literal)\b',r'\b(?:closed string literal|outside (?:a |the )?string literal)\b'),
 'table_column': (r'\bfirst (?:table )?column\b',r'\b(?:later|subsequent|non[- ]first) (?:table )?column\b'),
 'table_role': (r'\b(?:table )?header cell\b',r'\b(?:table )?data cell\b'),
 'table_row': (r'\b(?:early|first) (?:table )?data row\b',r'\b(?:late|later) (?:table )?data row\b'),
}
NEGATION = r"\b(?:not|never|cannot|isn.t|isn’t|doesn.t|doesn’t)\b"


def statement(row, text):
    """Return A/B/both/neither, with conservative sentence-local negation rejection."""
    if row not in PATTERNS: return 'not_structure'
    clauses = re.split(r'[.!?\n]+', text)
    hits = [any(re.search(pattern, s, re.I) and not re.search(NEGATION, s, re.I) for s in clauses)
            for pattern in PATTERNS[row]]
    return 'both' if all(hits) else 'A' if hits[0] else 'B' if hits[1] else 'neither'
