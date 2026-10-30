"""P restart timing/memory contract and complete-grid preservation, CPU only."""
import json,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
from .p_retime import steady_forecast,memory_headroom,arm_p_retime
from .worker import Clock


class Retime(unittest.TestCase):
    def test_unknown_work_not_admitted_and_setup_deficit_charged(self):
        a={'created_epoch':0};setups={'oracle':[300],'nla':[250]};current={'oracle':200,'nla':250}
        f=steady_forecast(a,1366,450,setups,current,{'oracle':[],'nla':[8]},{'oracle':19,'nla':19},{'fits':True})
        self.assertEqual(f['status'],'TIMING_REQUIRED')
        work={'oracle':[8,9],'nla':[10]}
        f=steady_forecast(a,1366,450,setups,current,work,{'oracle':19,'nla':19},{'fits':True})
        self.assertEqual(f['own_setup_deficit_seconds'],100)
        self.assertEqual(f['complete_custody_upper_seconds'],1121.25)
        self.assertTrue(f['fits'])
        f=steady_forecast(a,1000,450,setups,current,work,{'oracle':19,'nla':19},{'fits':True})
        self.assertFalse(f['fits'])
        f=steady_forecast(a,1366,450,setups,current,work,{'oracle':19,'nla':19},{'fits':False})
        self.assertFalse(f['fits'])

    def test_memory_requires_measured_transient_plus_reserve(self):
        g=1024**3
        self.assertFalse(memory_headroom(3*g,5*g,3*g)['fits'])
        self.assertTrue(memory_headroom(4*g,5*g,3*g)['fits'])

    def test_retained_pilots_plus_production_cover_each_item_once_both_readers(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);out=root/'out';out.mkdir()
            items=[dict(key=str(i),id=i,row='synthetic',source_row='synthetic',bank='CPU_SYNTHETIC',split='test') for i in range(672)]
            (root/'ITEMS.json').write_text(json.dumps(items));(root/'PROMPT.json').write_text(json.dumps({'prefix':'frozen'}))
            for b in (42,44):np.save(root/f'acts{b}.npy',np.zeros((672,5120),dtype=np.float32))
            lens=types.SimpleNamespace(prompt='native',_slots={},carrier=lambda b:([1],1),prompt_ids=[1],marker=1)
            seen=[]
            def generate(reader,lens,h):seen.append((reader,len(h)));return [dict(raw='SYNTHETIC',text='SYNTHETIC',malformed=False,truncated=False) for _ in h]
            a={'created_epoch':time.time(),'measured_e106_staging_seconds':[1]}
            with patch('projects.g_agreement.e106.runtime.verify_assets'),patch('projects.g_agreement.e106.runtime.load',return_value=lens),patch('projects.g_agreement.e106.runtime.prefix_nla'),patch('projects.g_agreement.e106.runtime.generate',side_effect=generate),patch('torch.cuda.synchronize'),patch('torch.cuda.reset_peak_memory_stats'),patch('torch.cuda.memory_allocated',return_value=1),patch('torch.cuda.max_memory_allocated',return_value=2),patch('torch.cuda.mem_get_info',return_value=(16*1024**3,140*1024**3)):
                arm_p_retime(a,root,{},Clock(out,time.time()+1366))
            self.assertEqual(len(seen),42)
            for r in ('oracle','nla'):
                rows=[x for f in sorted(out.glob(r+'_????.json')) for x in json.loads(f.read_text())]
                self.assertEqual([x['id'] for x in rows],list(range(672)))
                self.assertTrue(all(x['reader']==r for x in rows))
            self.assertEqual(json.loads((out/'REPORT.json').read_text())['outputs'],1344)

if __name__=='__main__':unittest.main()
