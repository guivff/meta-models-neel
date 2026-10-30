import importlib,sys
import pytest
from projects.g_agreement.blindspot.screens import features as F

def test_frozen_registry():
 assert len(F.FEATURES)>=100
 assert len(F.BY_ID)==len(F.FEATURES)
 assert {f.kind for f in F.FEATURES}==set(F.CLASSES)
 for f in F.FEATURES:
  assert f.definition and f.positive and f.negative
  assert len(f.phrasing_pair)==2 and f.phrasing_pair[0]!=f.phrasing_pair[1]
  assert all('{statement}' not in x for x in f.phrasing_pair)
  assert set(f.domains)<=set(F.DOMAINS)
 assert not any('modal' in k for k in sys.modules if k.startswith('mats.'))

@pytest.mark.parametrize('text,key,value',[
 ('((word','paren_depth_ge_2',True),('(word','paren_depth_ge_2',False),
 ('([word','bracket_depth_ge_2',True),('(word)','inside_paren',False),
 ('(]word','unmatched_close',True),('line\nnext','line_index_ge_2',True),
 ('    foo','indent_spaces_ge_4',True),('\tfoo','indent_spaces_ge_4',True),
 ('abc','column_chars_ge_8',False),('First sentence. Another','paragraph_sentences_ge_2',True),
 ('He said "(word','inside_paren',False),('He said “word','inside_string',True),
 ("don't stop",'inside_single_quote',False),('WORD','word_allcaps',True),
 ('Word','word_titlecase',True),('word','word_lowercase',True),('café','word_nonascii',True),
 ('123','number_magnitude_ge_100',True),('-1.5e3','number_magnitude_ge_1000',True),
 ('x123','current_number',False),('123 ','current_number',False),
 ('because it was good','lexicon_causal',True),('not excellent','lexicon_positive',True),
 ('excellentish','lexicon_positive',False),('the','wordlist_determiner',True),
 ('the ','wordlist_determiner',None),('word','number_magnitude_ge_1',None),
])
def test_operational_examples(text,key,value):
 assert F.extract(text,'prose')[key] is value

@pytest.mark.parametrize('prefix,inside',[
 ("x = '(ignored)',",False),("x = '(ignored",True),("x = f'(value",True),
 ("x = '''many\n( lines",True),("x = '''many\n( lines'''",False),
 ('x = "escaped\\\" still',True),('x = "done"',False)])
def test_python_quotes(prefix,inside):
 out=F.extract(prefix,'python');assert out['inside_string'] is inside;assert out['inside_paren'] is False

def test_python_comments_and_empty_domain():
 out=F.extract('x = 1 # ((( comment','python');assert out['inside_comment'] and not out['inside_paren']
 assert not F.extract('x = 1 # comment\nnext','python')['inside_comment']
 assert F.extract('ordinary','prose')['inside_comment'] is None
 with pytest.raises(ValueError,match='unknown domain'):F.extract('x','not-a-domain')
 with pytest.raises(TypeError):F.extract(None,'python')

@pytest.mark.parametrize('prefix,math,display',[
 ('text $x',True,False),('text $x$ done',False,False),('text $$x',True,True),
 (r'text \(x',True,False),(r'text \[x',True,True),(r'text \[x\] done',False,False),
 (r'cost \$5',False,False),(r'\begin{align} x',True,True),
 (r'\begin{align} x \end{align}',False,False)])
def test_latex_math(prefix,math,display):
 out=F.extract(prefix,'latex');assert out['inside_math'] is math;assert out['inside_display_math'] is display

def test_latex_comments_escapes_and_environment():
 assert F.extract(r'\{ escaped','latex')['inside_brace'] is False
 out=F.extract('text % \\begin{align} $ {','latex');assert not out['inside_math'] and not out['inside_brace']
 assert F.extract(r'\begin{itemize}\item x','latex')['inside_latex_itemize']
 assert F.extract(r'\section{A}\subsection{B}','latex')['latex_sections_ge_2']
 assert not F.extract(r'\sectional{A}','latex')['latex_sections_ge_1']
 assert F.extract(r'\item x \item y','latex')['latex_items_ge_2']

@pytest.mark.parametrize('prefix,flag',[
 ('```python\nx = 1','inside_fence'),('~~~\ncode','inside_fence'),
 ('text `code','inside_inline_code'),('- item','line_bullet'),('2. item','line_ordered'),
 ('  - nested','list_depth_ge_2'),('- [x] done','line_task_checked'),('## Heading','line_heading')])
def test_markdown(prefix,flag):assert F.extract(prefix,'markdown')[flag]

def test_markdown_closures_and_pipes():
 assert not F.extract('```\ncode\n```\ntext','markdown')['inside_fence']
 assert not F.extract('text `code` done','markdown')['inside_inline_code']
 assert F.extract('| first | second','markdown')['table_column_ge_2']
 assert not F.extract(r'| first \| literal','markdown')['table_column_ge_2']
 assert not F.extract('| `a|b` end','markdown')['table_column_ge_2']
 assert not F.extract('```\n| code | value','markdown')['line_table']
 assert F.extract('plain','markdown')['table_column_ge_2'] is None

def test_no_suffix_access():
 prefix='word (quoted text'
 expected=F.extract(prefix,'prose')
 for suffix in [')','! Good negative','\n# end','" literal','\n```']:
  full=prefix+suffix
  assert F.extract(full[:len(prefix)],'prose')==expected

def test_all_boolean_or_missing():
 import random,string
 r=random.Random(79)
 for domain in F.DOMAINS:
  for _ in range(20):
   prefix=''.join(r.choices(string.printable,k=80));out=F.extract(prefix,domain)
   assert set(out)==set(F.BY_ID)
   assert all(v is None or type(v) is bool for v in out.values())
