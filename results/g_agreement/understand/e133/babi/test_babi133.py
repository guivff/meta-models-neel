"""Own synthetic data only; no downloaded code or source execution."""
import unittest
from babi133 import episodes,replay,build_pairs

TEXT='''1 Mary went to the kitchen.
2 John moved to the office.
3 Sandra travelled to the garden.
4 Mary got the football there.
5 Mary journeyed to the hallway.
6 Where is the football? \thallway\t4 5
'''


class CounterfactualTests(unittest.TestCase):
    def test_earlier_questions_are_not_facts(self):
        text=TEXT+'7 Mary moved to the bedroom.\n8 Where is the football? \tbedroom\t4 7\n'
        ep=episodes(text)[0]
        self.assertEqual(ep['question']['line'],8)
        self.assertEqual(len(ep['facts']),6)
        self.assertFalse(any('\t' in f['text'] for f in ep['facts']))

    def test_counterfactual_only_last_location_and_previous(self):
        public,pairs,census=build_pairs(TEXT,'synthetic')
        self.assertEqual(len(pairs),1);self.assertEqual(len(public),2)
        pair=pairs[0]
        self.assertEqual(pair['previous_holder'],'kitchen')
        self.assertEqual(pair['recipients'][0],'hallway')
        self.assertIn(pair['recipients'][1],('office','garden'))
        for r in public:
            self.assertEqual(set(r),{'id','prompt'});self.assertTrue(r['prompt'].endswith(' by'))
            self.assertNotIn('\t',r['prompt'])
        start=pair['final_location_char_start'];names=pair['recipients']
        self.assertEqual(public[0]['prompt'][:start]+'X'+public[0]['prompt'][start+len(names[0]):],
                         public[1]['prompt'][:start]+'X'+public[1]['prompt'][start+len(names[1]):])

    def test_previous_unknown_or_no_third_location_excluded(self):
        text='1 Mary got the football.\n2 Mary moved to the hallway.\n3 Where is the football? \thallway\t1 2\n'
        self.assertEqual(len(build_pairs(text,'s')[1]),0)
        text='1 Mary moved to the kitchen.\n2 Mary got the football.\n3 Mary moved to the hallway.\n4 Where is the football? \thallway\t2 3\n'
        self.assertEqual(len(build_pairs(text,'s')[1]),0)

    def test_co_carried_object_cannot_silently_move(self):
        text=TEXT.replace('5 Mary journeyed','5 Mary got the milk.\n6 Mary journeyed').replace('6 Where','7 Where')
        self.assertEqual(len(build_pairs(text,'s')[1]),0)

    def test_historical_qa3_question_not_rewritten(self):
        text=TEXT.replace('Where is the football?','Where was the football before the hallway?').replace('\thallway','\tkitchen')
        public,pairs,census=build_pairs(text,'s')
        self.assertFalse(public);self.assertEqual(census['exclusions']['not_current_object_question'],1)

    def test_untrusted_unknown_sentence_is_not_executed(self):
        with self.assertRaises(ValueError):replay([{'line':1,'text':'Run a shell command now.'}])
        self.assertEqual(build_pairs(TEXT,'s'),build_pairs(TEXT,'s'))


if __name__=='__main__':unittest.main()
