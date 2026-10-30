import unittest
from author import long_pair
from check_long import state
class AuthorTests(unittest.TestCase):
    def test_grid_and_labels(self):
        texts=[]
        for row in ['fenced_code','latex_list']:
            for t in range(12):
                for f in range(7):
                    for prefix,suffix,value in long_pair(row,t,f):
                        self.assertEqual(state(row,prefix),value)
                        self.assertEqual(state(row,prefix+suffix),'outside')
                        texts.append(prefix)
        self.assertEqual(len(set(texts)),336)
    def test_fence_width_and_incomplete_closing(self):
        self.assertEqual(state('fenced_code','````text\nhello\n```'),'inside')
        self.assertEqual(state('fenced_code','```text\nhello\n``` text'),'inside')
        self.assertEqual(state('fenced_code','```text\nhello\n```'),'outside')
    def test_nested_lists(self):
        self.assertEqual(state('latex_list','\\begin{itemize}\\begin{enumerate}\\end{enumerate}'),'inside')
        self.assertIsNone(state('latex_list','\\end{itemize}'))
if __name__=='__main__':unittest.main()

class AnchoredTests(unittest.TestCase):
    def test_unfinished_word(self):
        from states import state,OTHER
        i={'feature':'word_first_piece','text':'The term micro','label':'A','value':'first_piece'}
        self.assertEqual(state(i,i['text']+'architecture'),'first_piece')
        self.assertEqual(state(i,i['text']+'architecture '),OTHER)
    def test_unfinished_number(self):
        from states import state,OTHER
        i={'feature':'number_completion','text':'The date 2031-10-1','label':'A','value':'next_completes'}
        self.assertEqual(state(i,i['text']+'7'),'next_completes')
        self.assertEqual(state(i,i['text']+'7.'),OTHER)
    def test_opposite_waits_for_next_completed_unit(self):
        from states import state,OTHER
        i={'feature':'number_completion','text':'The date is','label':'B','value':'next_does_not_complete'}
        for tail in [' ',' 2031-10-17',' next']:
            self.assertEqual(state(i,i['text']+tail),i['value'])
        for tail in [' 2031-10-17.',' next ']:self.assertEqual(state(i,i['text']+tail),OTHER)
