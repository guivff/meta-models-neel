import copy
import unittest
from .e107b_source import project, digest, QUESTION, OLD_QUESTION


class ForecastSourceTest(unittest.TestCase):
    def setUp(self):
        item = dict(id='original', bank='E82', row='row', item_id='private-item', cohort='belief_wrong')
        prompt = 'A public test prompt.'
        binding = dict(item, source_public_id='public', source_public_file='source',
            source_prompt_sha256=digest(prompt), instruction=OLD_QUESTION,
            generation_prompt_sha256=digest(prompt+'\n'+OLD_QUESTION))
        self.args = [[item], [binding], [dict(id='original', prompt=prompt+'\n'+OLD_QUESTION)],
            [dict(inventory_id='original', bank='E82', target=t, property='property', values={'A':['x'],'B':['y']})
             for t in ('belief','truth')], {'source':[dict(id='public',prompt=prompt)]}]

    def run_project(self):
        return project(*self.args, expected=1)

    def test_instruction_only_and_private_join_off_wire(self):
        calls, custody, plans = self.run_project()
        self.assertEqual(calls[0]['rendered'], dict(system=None,user='A public test prompt.\n'+QUESTION,schema=None))
        self.assertNotIn('private-item', str(calls))
        self.assertEqual(custody[0]['original_item_id'], 'private-item')
        self.assertEqual([p['target'] for p in plans], ['belief','truth'])
        self.assertEqual(plans[0]['values'],self.args[3][0]['values'])

    def test_original_classification_not_inferred(self):
        self.args[0][0]['cohort'] = 'no_canonical_truth'
        with self.assertRaises(Exception): self.run_project()

    def test_changed_public_prompt_rejected(self):
        self.args[4]['source'][0]['prompt'] += ' changed'
        with self.assertRaises(Exception): self.run_project()

    def test_rewritten_original_wrapper_rejected(self):
        self.args[2][0]['prompt'] = 'another wrapper'
        with self.assertRaises(Exception): self.run_project()

    def test_duplicate_source_and_missing_target_rejected(self):
        saved = copy.deepcopy(self.args)
        self.args[1].append(copy.deepcopy(self.args[1][0]))
        with self.assertRaises(Exception): self.run_project()
        self.args = saved
        self.args[3].pop()
        with self.assertRaises(Exception): self.run_project()


if __name__ == '__main__': unittest.main()
