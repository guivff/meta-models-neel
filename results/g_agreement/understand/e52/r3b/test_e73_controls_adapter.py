"""Synthetic-only coverage/orientation checks for E73's operational adapter."""
import copy
import unittest
from e73_controls_adapter import validate_units


def fixture():
    records, units, order = [], [], []
    for state in ['W7','W8']:
        ids = [state+'_'+str(i) for i in range({'W7':400,'W8':316}[state])]
        records.extend({'id':uid,'feature':state,'split':'test','original_label':i%2,'label':1-i%2} for i,uid in enumerate(ids))
        order.extend(ids)
        units.append({'id':state,'source_row':state,'binary':True,'item_ids':ids,
                      'value_token_ids':{i:[[],[7]] for i in ids},'descriptive_token_sets':{i:{} for i in ids}})
    return units, records, order


class AdapterTests(unittest.TestCase):
    def test_full_control_split_and_empty_g3_set_preserved(self):
        u,r,o=fixture();self.assertEqual(len(validate_units(u,r,o)),716)

    def test_native200_subsample_rejected(self):
        u,r,o=fixture();u[0]['item_ids']=u[0]['item_ids'][:200]
        with self.assertRaises(ValueError):validate_units(u,r,o)

    def test_supplemental_state_cannot_be_omitted(self):
        u,r,o=fixture();u.pop(1)
        with self.assertRaises(ValueError):validate_units(u,r,o)

    def test_original_label_orientation_cannot_pass_through(self):
        u,r,o=fixture()
        for row in r:row['label']=row['original_label']
        with self.assertRaises(ValueError):validate_units(u,r,o)

    def test_cross_state_identity_rejected(self):
        u,r,o=fixture();r[0]['feature']='W1'
        with self.assertRaises(ValueError):validate_units(u,r,o)

    def test_duplicate_capture_id_rejected(self):
        u,r,o=fixture();o[0]=o[1]
        with self.assertRaises(ValueError):validate_units(u,r,o)

    def test_token_omission_rejected(self):
        u,r,o=fixture();del u[0]['value_token_ids'][o[0]]
        with self.assertRaises(ValueError):validate_units(u,r,o)


if __name__=='__main__':unittest.main()
