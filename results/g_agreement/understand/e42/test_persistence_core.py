import unittest
from persistence_core import persistence
from states import state, OTHER, python_state, latex_state, table_state, unit_end

class PersistenceTests(unittest.TestCase):
    def test_full_and_first_loss(self):
        self.assertEqual(persistence([0],list(range(32)),'a',lambda x:x,lambda _: 'a'),32)
        self.assertEqual(persistence([0],list(range(32)),'a',lambda x:x,lambda x: 'b' if len(x)==5 else 'a'),3)
    def test_carry_and_exclusion(self):
        self.assertEqual(persistence([0],list(range(32)),'a',lambda x:x,lambda x: 'a' if len(x)==1 else None),32)
        self.assertIsNone(persistence([0],list(range(32)),'a',lambda x:x,lambda x:None))
    def test_short_or_mismatch_stops(self):
        with self.assertRaises(ValueError):persistence([0],[1]*16,'a',str,lambda _: 'a')
        with self.assertRaises(ValueError):persistence([0],[1]*32,'a',str,lambda _: 'b')
    def test_python_lexical(self):
        self.assertEqual(python_state('python_depth','call([name', ['shallow','deep']),OTHER)
        self.assertEqual(python_state('python_depth','[[[name', ['shallow','deep']),'deep')
        self.assertEqual(python_state('python_string','x="abc',['inside','outside']),'inside')
        self.assertEqual(python_state('python_string','x="abc"',['inside','outside']),'outside')
        self.assertEqual(python_state('python_argument','call(a,b,c,d,e',['first','later']),'later')
        self.assertEqual(python_state('python_indent','def f():\n    x = (',['shallow','deep']),'shallow')
    def test_latex(self):
        self.assertEqual(latex_state('latex_fraction',r'Let $\frac{x}{y',['numerator','denominator']),'denominator')
        self.assertEqual(latex_state('latex_math','Let $x',['math','text']),'math')
        self.assertEqual(latex_state('latex_math','Let $x$',['math','text']),'text')
    def test_units(self):
        self.assertTrue(unit_end('sentence_type',' there.'))
        self.assertFalse(unit_end('paragraph_index',' there.'))
        self.assertTrue(unit_end('paragraph_index','\n \n'))
        self.assertTrue(unit_end('syntax_role',' and next'))
        self.assertFalse(unit_end('syntax_role',' android'))
    def test_table(self):
        t='| a | b | c | d | e |\n|---|---|---|---|---|\n| x | y | z | q | n'
        self.assertEqual(table_state('table_column',t,['first','later']),'later')
    def test_all_shared_dispatchers(self):
        examples={'prose_paren':('inside','outside','a (b'),'prose_quote':('inside','outside','a "b'),
          'prose_sentence':('early','late','A sentence here'),'latex_environment':('equation','quote',r'\begin{equation} x'),
          'latex_section':('early','late',r'\section{One} x'),'latex_item':('first','later',r'\begin{enumerate}\item x'),
          'json_type':('string','number','{"a":"x'),'list_depth':('shallow','deep','- a'),
          'list_index':('first','later','- a'),'table_role':('header','data','| a | b'),
          'table_row':('early','late','| a |\n|---|\n| x')}
        for f,(a,b,text) in examples.items():
            self.assertEqual(state({'bank':'W1','feature':f,'body_offset':0,'values':[a,b]},text),a,f)

class Clarification2Tests(unittest.TestCase):
    def test_nested_section_titles(self):
        text=r'\section{A \emph{nested} title} x'
        self.assertEqual(latex_state('latex_section',text,['early','late']),'early')
        self.assertEqual(latex_state('latex_section',text*6,['early','late']),'late')
        self.assertIsNone(latex_state('latex_section',text+r'\section{Unfinished',['early','late']))
    def test_first_cell_without_pipe(self):
        text='a | b | c | d | e\n---|---|---|---|---\ncurrent cell'
        self.assertEqual(table_state('table_column',text,['first','later']),'first')
        self.assertEqual(table_state('table_row',text,['early','late']),'early')
        late='a | b\n---|---\n'+'x | y\n'*5+'current cell'
        self.assertEqual(table_state('table_row',late,['early','late']),'late')
        self.assertEqual(table_state('table_role',text,['header','data']),OTHER)
if __name__=='__main__':unittest.main()
