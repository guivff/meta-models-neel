"""CPU-only definition and independent-label tests; no reader/model outcomes."""
from collections import Counter
import unittest
from bank133 import generate,check,NAMES,PLACES,RELATIONS,render


class BankTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.public,cls.pairs=generate();cls.lookup={r['id']:r['prompt'] for r in cls.public}

    def test_exact_census_and_public_whitelist(self):
        self.assertEqual(len(self.public),900)
        self.assertEqual(Counter((p['family'],p['relation']) for p in self.pairs),
                         {(f,r):n for f,n in [('multi_hop',100),('one_hop',50)] for r in RELATIONS})
        self.assertTrue(all(set(r)=={'id','prompt'} for r in self.public))
        self.assertEqual(len({r['prompt'] for r in self.public}),900)

    def test_twins_only_final_recipient(self):
        for p in self.pairs:
            masked=[]
            for m in p['members']:
                text=self.lookup[m['id']];a,b=m['final_recipient_char_span']
                self.assertEqual(text[a:b],m['current_holder'])
                masked.append(text[:a]+'<RECIPIENT>'+text[b:])
            self.assertEqual(masked[0],masked[1])
            self.assertNotEqual(p['recipients'][0],p['recipients'][1])

    def test_independent_trackers_and_relation_pools(self):
        for p in self.pairs:
            for m in p['members']:
                actual=check(self.lookup[m['id']]);pool=PLACES if p['relation']=='object_location' else NAMES
                self.assertEqual(actual['chain'],m['chain'])
                self.assertEqual(actual['previous'],p['previous_holder'])
                self.assertTrue(set(actual['chain'])<=set(pool))
                self.assertEqual(actual['transfers'],3 if p['family']=='multi_hop' else 1)
                self.assertTrue(self.lookup[m['id']].endswith(' by'))

    def test_generation_deterministic_and_ordered(self):
        self.assertEqual((self.public,self.pairs),generate())
        self.assertEqual([p['generation_order'] for p in self.pairs[:300]],list(range(300)))
        self.assertEqual([p['generation_order'] for p in self.pairs[300:]],list(range(150)))
        self.assertTrue(all(p['family']=='multi_hop' for p in self.pairs[:300]))

    def test_checker_rejects_disconnected_transfer_or_bad_count(self):
        prompt,_=render('object_holder','brass key',['Alice','Bob','Dana','Erin'],0)
        with self.assertRaises(ValueError):check(prompt.replace('Bob hands','Carl hands'))
        with self.assertRaises(ValueError):check(prompt.replace('Bob hands the brass key to Dana. ',''))
        with self.assertRaises(ValueError):check(prompt.replace('held by','held near'))


if __name__=='__main__':unittest.main()
