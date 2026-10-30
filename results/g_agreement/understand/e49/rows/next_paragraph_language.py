"""E49 next_paragraph_language: definition-only W-text authoring."""
from .interface import length_match
from .text_common import SPECS,check,generate as build
SPEC=SPECS['next_paragraph_language']
def check_label(text):return check(SPEC.row_id,text)
def generate(source_items=None):return build(SPEC.row_id,source_items)
