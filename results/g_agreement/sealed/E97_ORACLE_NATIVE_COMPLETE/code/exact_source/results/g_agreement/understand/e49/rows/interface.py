"""Shared E49 generator contract, frozen before generators are authored.
No model, bank or outcome imports. Labels must be recoverable by check_label(text).
"""
from dataclasses import dataclass,replace
from typing import Callable,Sequence

@dataclass(frozen=True)
class RowSpec:
    row_id: str
    values: tuple[str,str]  # A, B; fixed before capture
    kind: str  # semantic_state, descriptor, or surface_state
    read_token_rule: str  # literal suffix whose final tokenizer token is read
    twin_of: str|None=None

@dataclass(frozen=True)
class Item:
    row_id: str
    template_index: int
    filler_index: int
    variant: int
    text: str
    value: str
    @property
    def split(self):return 'dev' if self.template_index<6 else 'test'
    @property
    def pair_key(self):return (self.template_index,self.filler_index)
    @property
    def source_key(self):return (self.template_index,self.filler_index,self.variant)

REGISTRY={
 1:('pronoun_referent','semantic_state'),2:('chased_role','semantic_state'),
 3:('container_after_move','semantic_state'),4:('holder_after_handovers','semantic_state'),
 5:('arith_carry','semantic_state'),6:('arith_compare','semantic_state'),
 7:('branch_taken','semantic_state'),8:('var_type_at_use','semantic_state'),
 9:('asserted_vs_hypothetical','semantic_state'),10:('negation_scope','semantic_state'),
 11:('instruction_provenance','semantic_state'),12:('user_expertise','descriptor'),
 13:('topic_twin','descriptor'),14:('next_paragraph_language','descriptor'),
 15:('unit_system','descriptor'),16:('decimal_separator','surface_state')}

def length_match(pair:Sequence[Item],encode:Callable[[str],list[int]])->tuple[Item,Item]:
    """Default construction hook: no silent padding/replacement, reject ratio >1.10.
    A module may implement its own deterministic PRE-FREEZE hook with this API.
    It may not depend on gate scores, model outputs or held-out feedback.
    """
    if len(pair)!=2:raise ValueError('two variants required')
    a,b=pair
    if a.pair_key!=b.pair_key or {a.variant,b.variant}!={0,1}:raise ValueError('bad paired variants')
    lengths=[len(encode(x.text)) for x in pair]
    if min(lengths)<1 or max(lengths)/min(lengths)>1.10:raise ValueError('length ratio exceeds 1.10')
    if encode(a.text)[-1]!=encode(b.text)[-1]:raise ValueError('read token differs across variants')
    return a,b

def relabel_twin(source:Sequence[Item],spec:RowSpec,check_label:Callable[[str],str])->list[Item]:
    """Twin modules may change ONLY row_id/value, never text, index or read token."""
    if not spec.twin_of or any(x.row_id!=spec.twin_of for x in source):raise ValueError('wrong twin source')
    result=[]
    for x in source:
        value=check_label(x.text)
        if value not in spec.values:raise ValueError('checker returned out-of-bin value')
        result.append(replace(x,row_id=spec.row_id,value=value))
    return result

def validate(items:Sequence[Item],spec:RowSpec,check_label:Callable[[str],str],encode):
    from collections import Counter
    expected={(t,f,v) for t in range(12) for f in range(7) for v in range(2)}
    if len(items)!=168 or {x.source_key for x in items}!=expected:raise ValueError('require exact 12x7x2 grid')
    if len({x.text for x in items})!=168:raise ValueError('duplicate prefixes within row')
    for x in items:
        if x.row_id!=spec.row_id or x.value not in spec.values or check_label(x.text)!=x.value:raise ValueError('label check failed')
        if not x.text.endswith(spec.read_token_rule):raise ValueError('read-token suffix rule failed')
    for split in ['dev','test']:
        if Counter(x.value for x in items if x.split==split)!=Counter({v:42 for v in spec.values}):raise ValueError('84 items, 42 A/42 B per split required')
    for t in range(12):
        for f in range(7):length_match([x for x in items if x.pair_key==(t,f)],encode)
