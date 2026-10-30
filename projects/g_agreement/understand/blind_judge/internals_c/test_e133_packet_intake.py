import unittest
from .e133_packet_intake import native_units,templates

class NativeIntakeTest(unittest.TestCase):
    def fixture(self):
        t=[dict(item_id=str(i),pair_id='pair',member=i,family='multi_hop',arm='synthetic',property='holder of key',values={'A':['Ada'],'B':['Bea'],'C':['Cy']},value_map={'A':'Ada','B':'Bea','C':'Cy','OTHER':'__OTHER__'},current='Ada'if i==0 else'Bea',previous='Cy')for i in range(2)]
        index=[dict(id=str(i),kind='oracle',block=l,member='oracle/test.json',record=i)for i in range(2)for l in (44,52,60)]
        return t,index,lambda _:[dict(text='Ada holds it.'),dict(text='')]
    def test_exact_id_grid_empty_retained_private_roles_off_wire(self):
        t,ix,load=self.fixture();units,refs=native_units(t,ix,load,['0','1'])
        self.assertEqual(len(units),6);self.assertEqual(sum(u['data']['readout']==''for u in units),3)
        self.assertTrue(all(set(u['data'])=={'id','property','values','readout'}for u in units));self.assertEqual(refs[0]['native_keys'],[0,'text'])
    def test_duplicate_cell_rejected(self):
        t,ix,load=self.fixture();ix.append(ix[0])
        with self.assertRaises(ValueError):native_units(t,ix,load,['0','1'])
    def test_incomplete_grid_is_not_stitched(self):
        t,ix,load=self.fixture()
        with self.assertRaises(ValueError):native_units(t,ix[:-1],load,['0','1'])
    def test_single_member_selection_rejected(self):
        t,ix,load=self.fixture()
        with self.assertRaises(ValueError):native_units(t,ix[:3],load,['0'])
    def test_missing_text_is_not_empty_readout(self):
        t,ix,_=self.fixture()
        with self.assertRaises(ValueError):native_units(t,ix,lambda _:[{},dict(text='')],['0','1'])
    def test_changed_native_identity_rejected(self):
        t,ix,load=self.fixture();ix[0]=dict(ix[0],id='another')
        with self.assertRaises(ValueError):native_units(t,ix,load,['0','1'])

if __name__=='__main__':unittest.main()
