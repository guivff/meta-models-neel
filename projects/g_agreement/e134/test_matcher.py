import pytest
from .matcher import match_candidates,stated_value,coverage_gate

C={'Ann':['Annie'],'Bob':['Robert']}
def test_names_aliases_case_insensitive_and_no_truth():
 assert match_candidates('ANN and annie',C)==['Ann']
 assert match_candidates('roBERT',C)==['Bob']
 assert stated_value(match_candidates('unknown',C)) is None
 assert stated_value(match_candidates('Ann / Bob',C)) is None

def test_whole_word_unicode_and_punctuation():
 assert match_candidates('Joanne Ann2 _Ann Ann_ éAnn Anné',C)==[]
 assert match_candidates('(Ann), Bob!',C)==['Ann','Bob']
 assert match_candidates('ANN-Marie',C)==['Ann']

def test_literal_aliases_dedup_and_ambiguous_alias():
 c={'A+B':['x.y','shared'],'Other':['shared']}
 assert match_candidates('AAB xay',c)==[]
 assert match_candidates('A+B x.y',c)==['A+B']
 assert match_candidates('shared',c)==['A+B','Other']
 assert stated_value(match_candidates('shared',c)) is None

def test_exact_70_gate_any_block_fails_and_reports_dual():
 rows=[dict(readings={44:'Ann' if i<7 else None,52:'Ann' if i<6 else None},matcher_matches={44:['Ann'] if i<7 else [],52:['Ann'] if i<6 else ['Ann','Bob']}) for i in range(10)]
 gate=coverage_gate(rows)
 assert gate['blocks']['44']['passes'] and not gate['passes']
 assert gate['blocks']['52']['dual']==4
 assert gate['blocks']['44']['exact_one_coverage']==.7
 rows[6]['readings'][52]='Ann';rows[6]['matcher_matches'][52]=['Ann']
 assert coverage_gate(rows)['passes']

def test_invalid_inputs_and_scalar_mismatch():
 with pytest.raises(ValueError):match_candidates('x',{'A':['']})
 with pytest.raises(ValueError):coverage_gate([dict(readings={44:'Ann'},matcher_matches={44:[]})])
