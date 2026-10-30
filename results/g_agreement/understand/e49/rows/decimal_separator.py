"""E49 row 16: relabel W-text row 15 verbatim; never author new prefixes."""
import re
from .interface import RowSpec, length_match, relabel_twin
SPEC = RowSpec('decimal_separator', ('comma', 'point'), 'surface_state', '3', twin_of='unit_system')
PHRASINGS = (("- a decimal comma", "- a decimal point"),
             ("- The decimal separator is a comma.", "- The decimal separator is a point."))
CONTINUATIONS = ((",", "."),)

def check_label(text):
    suffix = ' The final format note overrides the earlier note. The next measurement is a length of 3'
    if not text.endswith(suffix):
        raise ValueError('missing precedence rule or row-15 read position')
    notes = re.findall(r'Format note: use a (comma|point) between the integer and fractional digits\.', text)
    if len(notes) != 2 or set(notes) != {'comma', 'point'} or text.count('Format note:') != 2:
        raise ValueError('expected the two unambiguous row-15 format notes')
    # Both conventions occur; the explicit precedence statement selects the last one.
    return notes[-1]

def generate(source_items):
    return relabel_twin(source_items, SPEC, check_label)
