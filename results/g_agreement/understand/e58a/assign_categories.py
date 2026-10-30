"""Description-only taxonomy. Never imports an item generator or any outcome file.
W1's FEATURES constant is parsed solely to extract its descriptions argument.
"""
import ast,json,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CATEGORIES=('bookkeeping','delimiter','syntactic','format','content')
W1={
 'bookkeeping':'prose_sentence prose_words prose_budget prose_column python_line python_argument python_depth python_indent latex_section latex_item latex_brace latex_fraction json_field json_depth table_column table_row table_role list_index list_depth list_completed list_words'.split(),
 'delimiter':'prose_paren prose_quote python_string latex_math latex_environment json_type'.split(),
 'format':'python_comment list_ordered'.split(),
 'content':'prose_topic prose_sentiment python_effect python_error latex_subject latex_role json_status table_status list_task list_priority list_topic'.split()}
SPECIAL={
 'latex_fraction':'Numerator versus denominator is a position/role within the fraction, not whether a delimiter is open.',
 'table_role':'Header versus data cell is a positional role within the table.',
 'python_comment':'Comment versus executable code distinguishes representational modes; the description does not ask for a delimiter count.',
 'json_type':'String versus numeric at the read position is the presence versus absence of quoted string scope.',
 'latex_environment':'Equation versus quotation describes the currently enclosing environment, including maths scope.',
 'list_task':'Checked versus unchecked is completion status, not number or position.'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def w1_descriptions():
 tree=ast.parse((ROOT/'projects/g_agreement/blindspot/items.py').read_text())
 node=next(n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='FEATURES' for t in n.targets))
 # No values, token candidates, generators, labels or raw items are evaluated.
 return {ast.literal_eval(k):' / '.join(ast.literal_eval(v.args[3])) for k,v in zip(node.keys,node.values)}
def record(bank,row,description,category,rationale=None):
 assert category in CATEGORIES
 return {'bank':bank,'row':row,'description':description,'category':category,'rationale':rationale or {'bookkeeping':'Position, count, index, depth or numeric bookkeeping.','delimiter':'Enclosing/open lexical scope or delimiter-controlled mode.','syntactic':'Grammatical category, relation or clause state.','format':'Representational convention or language.','content':'Semantic entity, topic, value or status.'}[category]}
def main():
 rows=[];mapping={r:c for c,names in W1.items() for r in names};descriptions=w1_descriptions();assert set(mapping)==set(descriptions) and len(mapping)==40
 rows.extend(record('W1',r,d,mapping[r],SPECIAL.get(r)) for r,d in descriptions.items())
 packet=json.loads((ROOT/'results/g_agreement/understand/e36/ROW_DEFINITIONS.json').read_text())['rows']
 rows.extend(record('E36',r,d['definition'],mapping[r],SPECIAL.get(r)) for r,d in packet.items())
 w12=[('syntax_role','Current noun is subject versus object of its clause.','syntactic'),('sentence_type','Current sentence is a question versus statement.','syntactic'),('sentence_position','Within the first three words versus after word twelve of the sentence.','bookkeeping'),('paragraph_index','First paragraph versus third or later paragraph.','bookkeeping'),('paragraph_start','First sentence versus later sentence of a paragraph.','bookkeeping'),('clause_embedding','Main clause versus an unclosed relative clause.','syntactic')]
 rows.extend(record('W12',*x) for x in w12)
 e49=[('pronoun_referent','Whether a pronoun refers to the giver or receiver.','content'),('chased_role','Identity of the pursuer in a chase relation.','content'),('container_after_move','Current container of an object after a move.','content'),('holder_after_handovers','Current holder after several handovers.','content'),('arith_carry','Whether the units addition produces a carry.','bookkeeping'),('arith_compare','Whether an arithmetic product exceeds a threshold.','bookkeeping'),('branch_taken','Whether a program branch will execute.','content'),('var_type_at_use','Integer versus string type of a variable at use.','content'),('asserted_vs_hypothetical','Asserted versus counterfactual scope of the current clause.','syntactic'),('negation_scope','Whether the current predicate lies inside negation.','syntactic'),('instruction_provenance','Principal instruction versus quoted vendor source.','content'),('user_expertise','Expert versus novice register of the user.','content'),('topic_twin','Topic of the same asserted/counterfactual passages.','content'),('next_paragraph_language','Next paragraph language in an alternating bilingual document.','format'),('unit_system','Metric versus imperial measurement convention.','format'),('decimal_separator','Comma versus point decimal notation convention.','format')]
 rows.extend(record('E49',*x) for x in e49)
 family56=[('tense_implicit','Past versus present tense of the original passage.','syntactic'),('tense_asked','Asked report of the same original passage tense.','syntactic'),('linewrap_implicit','Characters since last newline at original read position.','bookkeeping'),('linewrap_asked','Asked report of the original character count.','bookkeeping'),('language_continuation','French versus German passage for continuation.','format'),('language_report','Asked report of the original passage language.','format'),('adjective_implicit','Next coordinated word is adjective versus noun.','syntactic'),('adjective_asked','Asked report of next-word part of speech.','syntactic'),('anomaly_state','An earlier foreign-language sentence versus none.','format'),('fact_recall','One-step recall of a capital city.','content'),('reasoning_bridge','Intermediate entity required by a two-hop question.','content'),('rhyme_plan','Intended lexical word completing a rhyme.','content'),('instructed_focus','Concept held in focus while copying unrelated text.','content')]
 rows.extend(record('E56',*x) for x in family56)
 e57=[('multi_token_entity','Identity of a multi-token entity with a shared first answer token.','content'),('focus_ignore_mention','Mention of a concept under think, mention, ignore or no instruction.','content'),('category_switch','Animal-category items retained after animal versus colour ending.','content'),('capacity_list','Identities of unrelated nouns retained from a fixed twelve-word list.','content'),('antonym_crosslingual','Meaning of an antonym across languages, with query language fixed.','content'),('count_gradient','Original line count under implicit, report and first-letter questions.','bookkeeping'),('subject_number','Singular versus plural subject pending its verb.','syntactic'),('clause_pending','Whether a subordinate clause still requires a main clause.','syntactic'),('nesting_depth','One versus three unclosed brackets.','bookkeeping'),('indent_level','Four versus twelve leading spaces.','bookkeeping')]
 rows.extend(record('E57',*x) for x in e57)
 for x in rows:
  if x['row']=='capacity_list':x['rationale']='The input property is the identities/membership of a fixed-size set; number named is an outcome and does not turn the category into bookkeeping.'
  if x['row']=='antonym_crosslingual':x['rationale']='The target varies semantic antonym identity, not the fixed Chinese query language.'
  if x['row']=='anomaly_state':x['rationale']='The manipulated property is an earlier language-mode change, classified with language under format.'
  if x['row'] in ['unit_system','decimal_separator']:x['rationale']='A representational convention for quantities, not the quantity itself.'
  if x['row'] in ['branch_taken','var_type_at_use']:x['rationale']='Program execution/type status rather than syntactic form or nesting/count.'
 assert len(rows)==110 and len({(x['bank'],x['row']) for x in rows})==110
 sources=['projects/g_agreement/blindspot/items.py','results/g_agreement/understand/e36/ROW_DEFINITIONS.json','projects/g_agreement/BRIEF_UNDERSTAND.md']
 result={'experiment':'E58a','registration':'§174 80033b37','status':'DESCRIPTION_ONLY_CATEGORY_ASSIGNMENT','categories':CATEGORIES,'rows':rows,'counts_by_bank':{b:sum(x['bank']==b for x in rows) for b in ['W1','E36','W12','E49','E56','E57']},'source_files':{s:sha(ROOT/s) for s in sources},'source_scope':{'W1':'FEATURES descriptions argument only; AST extraction, no generator execution','E36':'Definition-only packet','W12':'§100 row descriptions','E49':'§163 row descriptions','E56':'§172 row descriptions and clarification 1','E57':'§173 row descriptions'},'condition_policy':'E57 arm variants inherit the category of their listed canonical family; no outcome-based reassignment. Dropped/not-built rows remain listed and are excluded downstream by availability.','exclusions_deferred':'Probe <0.85 and all outcome-dependent gates are applied by W-lens, not read here.','blinding':'No label, probe, reader or J-lens files were opened for this assignment. Prior conversation contains historical results; this is a description-only assignment, not a claim of lifetime outcome blindness.'}
 with (HERE/'CATEGORIES.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
 with (HERE/'CATEGORY_SEAL.json').open('x') as f:json.dump({'files':{n:sha(HERE/n) for n in ['assign_categories.py','CATEGORIES.json']},'authority':'§174; assigned before W-lens join'},f,indent=2,sort_keys=True);f.write('\n')
 print('Category seal:',sha(HERE/'CATEGORY_SEAL.json'));print('Rows:',len(rows))
if __name__=='__main__':main()
