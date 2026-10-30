"""E49 topic_twin: definition-only W-text authoring."""
from .interface import length_match
from .text_common import SPECS,check,generate as build
SPEC=SPECS['topic_twin']
def check_label(text):return check(SPEC.row_id,text)
def generate(source_items=None):return build(SPEC.row_id,source_items)
