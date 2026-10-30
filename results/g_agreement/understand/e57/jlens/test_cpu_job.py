import unittest
import torch
from cpu_job import ranks_and_hits,validate_units

class CPUJobContracts(unittest.TestCase):
    def test_full_rank_item_specific_tokens_and_capacity_top50(self):
        logits=torch.arange(100,dtype=torch.float32).repeat(2,1)
        ids=[[[1],[2]],[[99],[98]]]
        groups=[{'list_nouns':[{'name':'one','token_ids':[90,91]},{'name':'two','token_ids':[70]},{'name':'three','token_ids':[5]}]},{}]
        ranks,top,desc=ranks_and_hits(logits,ids,groups)
        self.assertEqual(ranks,[[98,97],[0,1]])
        self.assertEqual(top.shape,(2,50));self.assertEqual(desc[0]['list_nouns']['distinct_entries_top50'],2)
        self.assertEqual(desc[0]['list_nouns']['distinct_entries_top10'],1)

    def test_empty_tokens_do_not_become_rank_zero(self):
        ranks,_,_=ranks_and_hits(torch.arange(100,dtype=torch.float32)[None,:],[[[],[99]]],[{}])
        self.assertEqual(ranks,[[None,0]])

    def test_units_cover_frozen_test_items_once(self):
        records=[{'id':str(i),'feature':'x','split':'test','label':i%2} for i in range(84)]+[{'id':'dev','feature':'x','split':'dev','label':1}]
        ids=[str(i) for i in range(84)]
        unit={'id':'x','source_row':'x','binary':True,'item_ids':ids,'value_token_ids':{i:[[1],[2]] for i in ids},'descriptive_token_sets':{i:{} for i in ids}}
        self.assertEqual(set(validate_units([unit],records,['dev']+ids[::-1])),set(ids))
        with self.assertRaises(ValueError):validate_units([unit,unit],records,ids)
        with self.assertRaises(ValueError):validate_units([unit],records,ids[:1])
        records[0]['label']=1
        with self.assertRaises(ValueError):validate_units([unit],records,ids)

if __name__=='__main__':unittest.main()
