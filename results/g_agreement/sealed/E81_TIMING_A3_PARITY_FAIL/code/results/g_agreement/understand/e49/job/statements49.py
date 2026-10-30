"""Frozen E49 extension of E24 explicit-value regex, same clause/negation policy."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'vendor'))
import e24_statements as E24
PATTERNS={
 'pronoun_referent':(r'\b(?:pronoun (?:refers to|denotes) (?:the )?giver|giver (?:as|is) (?:the )?(?:pronoun )?referent)\b',r'\b(?:pronoun (?:refers to|denotes) (?:the )?receiver|receiver (?:as|is) (?:the )?(?:pronoun )?referent)\b'),
 'chased_role':(r'\b(?:thief (?:is (?:the )?(?:chaser|pursuer)|chases|chased)|(?:chaser|pursuer) is (?:the )?thief)\b',r'\b(?:policeman (?:is (?:the )?(?:chaser|pursuer)|chases|chased)|(?:chaser|pursuer) is (?:the )?policeman)\b'),
 'container_after_move':(r'\b(?:currently |now )?(?:in|inside) (?:the |a )?cup\b',r'\b(?:currently |now )?(?:in|inside) (?:the |a )?bowl\b'),
 'holder_after_handovers':(r'\b(?:Alex (?:holds|has|is (?:the )?(?:current )?holder)|(?:current holder|holder) is Alex)\b',r'\b(?:Robin (?:holds|has|is (?:the )?(?:current )?holder)|(?:current holder|holder) is Robin)\b'),
 'arith_carry':(r'\b(?:units (?:sum |column )?carries|a carry from the units|(?<!no )carry into (?:the )?tens)\b',r'\b(?:no carry(?: from the units)?|carry[- ]free addition)\b'),
 'arith_compare':(r'\b(?:product (?:is |exceeds )?(?:greater than|above|the threshold)|(?:comparison|answer) is yes)\b',r'\b(?:product (?:is )?(?:less than|below|at most)|(?:comparison|answer) is no)\b'),
 'branch_taken':(r'\b(?:branch (?:is |will be )?taken|condition (?:is|evaluates to) true|branch will run)\b',r'\b(?:branch (?:is |will be )?skipped|condition (?:is|evaluates to) false|branch is untaken)\b'),
 'var_type_at_use':(r'\b(?:x (?:holds|is) an? (?:integer|int)|(?:runtime )?type of x is int)\b',r'\b(?:x (?:holds|is) a (?:string|str)|(?:runtime )?type of x is str)\b'),
 'asserted_vs_hypothetical':(r'\b(?:asserted (?:claim|statement|proposition)|claim is asserted|factual assertion)\b',r'\b(?:hypothetical (?:claim|statement|proposition)|counterfactual (?:claim|statement)|claim is hypothetical)\b'),
 'negation_scope':(r'\b(?:negated predicate|predicate is negated|inside (?:a |the )?negation)\b',r'\b(?:unnegated predicate|predicate is unnegated|outside (?:a |the )?negation)\b'),
 'instruction_provenance':(r"\b(?:principal.s (?:own )?instruction|instruction (?:comes |is )?from (?:the )?principal)\b",r'\b(?:quoted vendor text|vendor.s instruction|instruction (?:comes |is )?from (?:the )?vendor)\b'),
 'user_expertise':(r'\b(?:expert user|experienced user|user is (?:an )?expert|expert register)\b',r'\b(?:novice user|beginner user|user is (?:a )?(?:novice|beginner)|novice register)\b'),
 'topic_twin':(r'\b(?:engineering (?:topic|subject)|(?:topic|subject) is engineering|safety interlock)\b',r'\b(?:gardening (?:topic|subject)|(?:topic|subject) is gardening|irrigation system)\b'),
 'next_paragraph_language':(r'\b(?:next paragraph (?:is |will be )?(?:in )?French|French (?:as the )?next paragraph language)\b',r'\b(?:next paragraph (?:is |will be )?(?:in )?English|English (?:as the )?next paragraph language)\b'),
 'unit_system':(r'\b(?:metric units|metric unit system|units are metric)\b',r'\b(?:imperial units|imperial unit system|units are imperial)\b'),
 'decimal_separator':(r'\b(?:decimal comma|decimal separator is (?:a )?comma|comma as (?:the )?decimal separator)\b',r'\b(?:decimal point|decimal separator is (?:a )?point|point as (?:the )?decimal separator)\b')}
E24.PATTERNS.update(PATTERNS)
def statement(row,text):return E24.statement(row,text)

def categorize(row,text,label):
 s=statement(row,text)
 if s in ('both','neither'):return s
 return 'correct_only' if s==('A' if label==1 else 'B') else 'wrong_only'
