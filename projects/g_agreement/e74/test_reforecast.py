"""Synthetic CPU running-mean regression tests, against exact operational archive."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from . import resident as r, ops, hardware as h
from .test_operator import Engine, admission, go
from .test_hardware import hopper, NOW
from .test_smoke import runtime

class ReforecastTests(unittest.TestCase):
    def test_outlier_decays_and_prior_is_not_a_floor(self):
        t=r.RealBatchMean(99)
        t.observe(.91,512)
        for _ in range(45):t.observe(.08,512)
        self.assertAlmostEqual(t.rate,(.91+45*.08)/(46*512))
        self.assertLess(t.rate,.91/512)
        self.assertEqual(t.batches,46)
        self.assertFalse(t.evidence()['padding_applied_here'])
    def test_partial_batch_uses_real_items_and_bad_observations_fail(self):
        t=r.RealBatchMean(99);t.observe(10,512);t.observe(1,10)
        self.assertAlmostEqual(t.rate,11/522)
        for seconds,items in [(float('nan'),1),(-1,1),(1,0),(1,True)]:
            with self.assertRaises(ValueError):t.observe(seconds,items)
    def test_padding_once_warmup_charged_and_provider_deadline_unchanged(self):
        a=dict(admission(1000),allocation_start_epoch=1000,replica_hourly_usd=36,provider_stop_epoch=2000)
        t=r.RealBatchMean(99);t.observe(4,2);t.observe(2,2)
        # 20s already elapsed may include warm-up: charged, never an observation.
        x=ops.budget(a,10*t.rate,1020)
        self.assertAlmostEqual(x['forecast_times_1_25_usd'],((20+15)*.01+2)*1.25)
        self.assertEqual(t.seconds,6)
        with self.assertRaisesRegex(ValueError,'provider deadline'):
            ops.budget(dict(a,provider_stop_epoch=1034),15,1020)
    def test_exact_hopper_overlay_survives(self):
        self.assertEqual(h.limits(hopper())['cap_usd'],160)
        a=hopper();gate=a['hopper_fallback'];gate.update(no_b200_claim_by_deadline=False,
            failed_pre_ssh_b200_claim_exception_authorised=True,failed_run_id='e74-public-20261027-a2',
            failed_claim_ruling_sha256='9bbb6e60ba1a60417a456cc8aa9055bf5a1cdc74388fdc556c25cab967ab9f55')
        self.assertEqual(h.profile(a,NOW)['gpu_count'],8)
        gate['failed_claim_ruling_sha256']='0'*64
        with self.assertRaises(ValueError):h.profile(a,NOW)
    def test_both_real_loops_use_running_mean_exclude_smoke_and_keep_once_claim(self):
        with tempfile.TemporaryDirectory() as td,patch('time.time',return_value=NOW):
            out=Path(td);e=Engine();a=admission(NOW)
            items=[{'id':hashlib.sha256(str(i).encode()).hexdigest(),'ids':[10+i,20],'read_position':1} for i in range(6)]
            ids=[x['id'] for x in items]
            req={'adapter_dir':'adapter','admission_obj':a,'deadline_epoch':NOW+1200,'boot_seconds':500,
                 'source_seal_sha256':'d'*64,'reader_plan_sha256':'c'*64,'go_file':str(out/'GO.json')}
            wait=r.await_go
            def external(req,out,digest,epoch):
                ops.write(Path(req['go_file']),go(req,digest,epoch));wait(req,out,digest,epoch)
            # Simulated smoke/warm-up overhead is absent from real-batch samples.
            ticks=[0,.91,1,1.08,2,2.08,3,3.6,4,4.2,5,5.2]
            with patch.object(r,'BATCH',2),patch.object(r,'await_go',external),patch.object(r.smoke50,'run50',return_value={'passed':True}),patch.object(r.time,'monotonic',side_effect=ticks):
                r.run_resident(req,out,e,runtime(),[],items,ids)
            cap=json.loads((out/'capture/0001.json').read_text())['reforecast']
            reader=json.loads((out/'readers/0001.json').read_text())['reforecast']
            self.assertAlmostEqual(cap['seconds_per_item'],.99/4)
            self.assertAlmostEqual(reader['seconds_per_item'],.8/4)
            # The third batch claim must use the updated mean, not slowest/prior.
            c=json.loads((out/'capture/0002.CLAIM.json').read_text())['gate']
            d=json.loads((out/'readers/0002.CLAIM.json').read_text())['gate']
            self.assertAlmostEqual(c['remaining_seconds'],2*(.99/4)+600+840+120)
            self.assertAlmostEqual(d['remaining_seconds'],2*(.8/4)+120)
            with self.assertRaises(FileExistsError):r.run_resident(req,out,e,runtime(),[],items,ids)
    def test_hard_alarm_kills_live_child_even_when_mean_forecast_fits(self):
        import subprocess,time
        real=subprocess.Popen;children=[]
        with tempfile.TemporaryDirectory() as td:
            now=time.time();a=admission(now);a['replica_hourly_usd']=.01
            req={'admission':'synthetic','admission_sha256':'a'*64,'deadline_epoch':now+.15}
            def start(*args,**kwargs):
                child=real([r.sys.executable,'-c','import time;time.sleep(60)'],**kwargs);children.append(child);return child
            with patch.object(ops,'admission',return_value=a),patch.object(r.smoke50,'validate_clocks'),patch.object(r.subprocess,'Popen',side_effect=start):
                self.assertEqual(r.supervise(req,Path(td)/'run'),124)
            children[0].wait(timeout=5)
            self.assertIsNotNone(children[0].returncode)
            seal=ops.verify_seal(Path(td)/'run/SEAL.json')
            self.assertEqual(seal['status'],'STOP_INCOMPLETE')
            self.assertEqual(req['deadline_epoch'],now+.15)

if __name__=='__main__':unittest.main()
