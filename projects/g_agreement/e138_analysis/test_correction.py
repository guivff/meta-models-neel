import copy
import unittest
from unittest.mock import patch
from . import correction as c

class CorrectionTests(unittest.TestCase):
    def packet(self):
        src={'seal':'terminal','sha256':'new'}
        return dict(experiment='E138R', correction_authority=c.AUTHORITY, defective_analysis_sha256=c.DEFECTIVE, corrected_input_sha256=c.INPUT,
            whole_values_verified=True,same168_native_readouts_verified=True,R5_actual_sample_pass=True,post_output_correction_disclosed=True,
            corrected_judgments=src,source_seals=[src],R5_sample_review_source={'path':'review','sha256':'reviewhash'})
    def admit(self,p):
        with patch.object(c.original,'admission'),patch.object(c.core,'verify',return_value={'input_seal_sha256':c.INPUT}),patch.object(c.core,'sha',return_value='reviewhash'):
            return c.admission(p)
    def test_corrected_bank(self): self.assertEqual(self.admit(self.packet()),0)
    def test_reject_old_bank(self):
        p=self.packet();p['experiment']='E138'
        with self.assertRaises(ValueError):self.admit(p)
    def test_reject_wrong_input(self):
        p=self.packet();p['corrected_input_sha256']='old'
        with self.assertRaises(ValueError):self.admit(p)
    def test_require_disclosure(self):
        p=self.packet();p['post_output_correction_disclosed']=False
        with self.assertRaises(ValueError):self.admit(p)
    def test_require_sample_pass(self):
        p=self.packet();p['R5_actual_sample_pass']=False
        with self.assertRaises(ValueError):self.admit(p)
    def test_terminal_input_mismatch(self):
        with patch.object(c.original,'admission'),patch.object(c.core,'verify',return_value={'input_seal_sha256':'old'}):
            with self.assertRaises(ValueError):c.admission(self.packet())
    def rows(self):
        cell={'e104_role_code':{k:{'ref':{'seal_index':1,'member':'JUDGMENTS.json','keys':[0,k]}} for k in ('code','status','judgment_id','value_roles')}}
        return [{'arms':{'donor':copy.deepcopy(cell),'random':copy.deepcopy(cell)}} for _ in range(84)]
    def test_all_new_pointers(self):self.assertEqual(len(c.check_pointers(self.rows(),1)),84)
    def test_mixed_old_status(self):
        r=self.rows();r[42]['arms']['random']['e104_role_code']['status']['ref']['seal_index']=0
        with self.assertRaises(ValueError):c.check_pointers(r,1)
    def test_literal_codes_rejected(self):
        r=self.rows();r[0]['arms']['donor']='none'
        with self.assertRaises(ValueError):c.check_pointers(r,1)
    def test_missing_grid(self):
        with self.assertRaises(ValueError):c.check_pointers(self.rows()[:-1],1)
    def test_separate_guard_science_identity(self):
        self.assertNotEqual(c.GUARD,c.original.GUARD)
        self.assertIs(c.analyze,c.original.analyze)
    def test_consumed_guard_never_opens_spec(self):
        with patch.object(c,'ROOT',c.Path('/tmp/wt-wmech2')),patch.object(c,'committed'),patch.object(c.Path,'exists',return_value=True),patch.object(c.core,'read') as read:
            with self.assertRaises(FileExistsError):c.main('not-read')
            read.assert_not_called()

if __name__=='__main__':unittest.main()
