"""Synthetic checks only; no real readouts or judgments."""
import copy
from collections import Counter
import unittest
from packet67 import *


def pool(bank='E49',reader='oracle',n=120):
    return [{'bank':bank,'reader':reader,'row':'row'+str(i%2),'item_id':f'item{i:04d}',
        'prompt_text':f'Input {i}: α\noriginal prompt.','readout':f'Exact readout {i}\n',
        'arm':('think','ignore','none')[i%3] if bank=='D4' else None,
        'source':{'path':'synthetic','record_index_zero_based':i},'truncation_cohort':'synthetic','native_max_new_tokens':512}
        for i in range(n)]


class PacketTests(unittest.TestCase):
    def test_uniform_seed_sample_and_cap(self):
        x=pool();a=sample(x)
        expected=sorted(x[int(i)]['item_id'] for i in np.random.default_rng(20261027).choice(120,100,replace=False))
        self.assertEqual([y['item_id'] for y in a],expected)
        self.assertEqual(sample(list(reversed(x))),a)
        self.assertEqual(len(sample(pool(n=20))),20)
        with self.assertRaises(ValueError):sample(x+x[:1])

    def test_D4_exact_balance_99(self):
        a=sample(pool('D4',n=252),balanced=True)
        self.assertEqual(len(a),99)
        self.assertEqual(Counter(x['arm'] for x in a),{'ignore':33,'none':33,'think':33})
        self.assertEqual(len({x['item_id'] for x in a}),99)

    def test_separate_packets_same_readout_different_prompt_item(self):
        x=pool(n=20);packets,mapping,inv=build_packets({('E49','oracle'):x})
        self.assertEqual(list(map(len,packets)),[20,20]);validate_packets(packets,mapping)
        self.assertTrue(all(set(y)=={'id','prompt_text','readout'} for p in packets for y in p))
        for pair in mapping:
            self.assertEqual({x['packet'] for x in pair['records']},{1,2})
            matched,other=pair['records']
            self.assertEqual(matched['condition'],'matched');self.assertEqual(other['condition'],'mismatched')
            self.assertNotEqual(other['prompt_item_id'],pair['item_id'])
            self.assertEqual(other['prompt_row'],pair['row'])
        self.assertEqual(build_packets({('E49','oracle'):list(reversed(x))}),(packets,mapping,inv))

    def test_selection_assignment_ids_and_donors_ignore_readout_content(self):
        a=pool();b=copy.deepcopy(a)
        for item in b:item['readout']='Entirely changed, even empty for one item.'
        pa,ma,_=build_packets({('E49','oracle'):a});pb,mb,_=build_packets({('E49','oracle'):b})
        self.assertEqual([[x['id'] for x in p] for p in pa],[[x['id'] for x in p] for p in pb])
        self.assertEqual([[x['prompt_text'] for x in p] for p in pa],[[x['prompt_text'] for x in p] for p in pb])
        self.assertEqual([x['item_id'] for x in ma],[x['item_id'] for x in mb])
        self.assertEqual([[y['prompt_item_id'] for y in x['records']] for x in ma],[[y['prompt_item_id'] for y in x['records']] for x in mb])

    def test_same_text_different_id_allowed_and_reported(self):
        x=pool(n=20)
        for item in x:item['prompt_text']='identical prompt'
        _,mapping,inv=build_packets({('E49','oracle'):x})
        self.assertEqual(inv[0]['mismatched_equal_prompt_text_count'],20)
        self.assertTrue(all(pair['records'][1]['prompt_item_id']!=pair['item_id'] for pair in mapping))

    def test_no_donor_stops_and_metadata_tampering_rejected(self):
        with self.assertRaises(ValueError):build_packets({('E49','oracle'):pool(n=1)})
        packets,mapping,_=build_packets({('E49','oracle'):pool(n=20)})
        bad=copy.deepcopy(packets);bad[0][0]['condition']='matched'
        with self.assertRaises(ValueError):validate_packets(bad,mapping)
        bad=copy.deepcopy(mapping);bad[0]['records'][1]['prompt_item_id']=bad[0]['item_id']
        with self.assertRaises(ValueError):validate_packets(packets,bad)

    def test_claim_schema_generic_and_status_constraints(self):
        schema=read(Path(__file__).parent/'judge_wave1/CLAIMS_OUTPUT_SCHEMA.json')
        self.assertEqual(schema['properties']['claims']['maxItems'],5)
        validate_claims({'id':'a'*32,'claims':[],'GENERIC':True},'a'*32)
        validate_claims({'id':'a'*32,'claims':[{'claim':'A specific claim','status':'UNVERIFIABLE'}],'GENERIC':False},'a'*32)
        for x in ({'id':'a'*32,'claims':[],'GENERIC':False},
                  {'id':'a'*32,'claims':[{'claim':'Claim','status':'FABRICATED'}],'GENERIC':False},
                  {'id':'a'*32,'claims':[{'claim':'Claim','status':'SUPPORTED'}]*6,'GENERIC':False},
                  {'id':'a'*32,'claims':[{'claim':'Claim','status':'SUPPORTED'}],'GENERIC':True}):
            with self.assertRaises(ValueError):validate_claims(x,'a'*32)


if __name__=='__main__':unittest.main()
