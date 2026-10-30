"""Synthetic-only warm-up isolation, running-mean real-batch forecast and stage-clock regressions."""
import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import worker76 as W
import parity76 as P
from common76 import DIM,read


class Tests(unittest.TestCase):
    def clock(self,folder,now,end=7000):
        return W.Clock({'absolute_deadline_epoch':end,'phase_forecasts_seconds':{x:10. for x in W.PHASES}},folder,clock=lambda:now[0])

    def test_dummy_batch_per_reader_discarded_and_deterministic(self):
        seen=[];calls=[]
        class Backend:
            def native(self,reader,h,batch):
                seen.append((reader,h.copy(),batch));return 'MUST_NOT_RETURN_OR_WRITE'
        class Clock:
            def warmup(self,phase,fn):calls.append(phase);fn()
        for reader in ('oracle','nla'):self.assertIsNone(W.native_warmup(Backend(),reader,Clock()))
        self.assertEqual(calls,['oracle_readout','nla_readout'])
        wanted=np.random.default_rng(20261028).standard_normal((32,DIM)).astype(np.float32)
        for reader,h,batch in seen:
            self.assertEqual(batch,32);np.testing.assert_array_equal(h,wanted)

    def test_cold_time_excluded_from_running_mean_forecast_but_charged(self):
        with tempfile.TemporaryDirectory() as t:
            now=[0.];clock=self.clock(t,now)
            before=clock.remaining.copy()
            def cold():now[0]+=1000;return 'discarded'
            self.assertIsNone(clock.warmup('oracle_readout',cold))
            self.assertEqual(now[0],1000);self.assertEqual(clock.remaining,before);self.assertEqual(clock.observed,{})
            self.assertEqual(clock.batch_totals,{});self.assertEqual(clock.batch_counts,{})
            for duration,left in ((2,3),(3,2),(1,1)):
                def real(d=duration):now[0]+=d;return 'retained'
                self.assertEqual(clock.call('oracle_readout',real,left),'retained')
            self.assertEqual(clock.observed['oracle_readout'],3)
            self.assertEqual(clock.remaining['oracle_readout'],2)
            self.assertEqual(clock.batch_counts['oracle_readout'],3)
            self.assertEqual(clock.batch_totals['oracle_readout'],6)
            events=read(Path(t)/'WARMUP_TIMING.json')
            self.assertEqual(len(events),1);self.assertEqual(events[0]['elapsed_seconds'],1000)
            self.assertTrue(events[0]['output_discarded'] and events[0]['excluded_from_forecast'])
            self.assertTrue(all('raw' not in event and 'text' not in event for event in events))
            with self.assertRaises(ValueError):clock.warmup('oracle_readout',lambda:None)

    def test_warmup_cannot_bypass_same_stage_deadline_or_leave_real_record(self):
        with tempfile.TemporaryDirectory() as t:
            now=[0.];clock=self.clock(t,now,end=1000)
            def cold():now[0]=900
            with self.assertRaises(W.NoFit):clock.warmup('nla_readout',cold)
            self.assertEqual(clock.observed,{})
            self.assertEqual({p.name for p in Path(t).iterdir()},{'ADMISSION.latest.json','WARMUP_TIMING.json'})
            self.assertEqual(read(Path(t)/'WARMUP_TIMING.json')[0]['elapsed_seconds'],900)

    def test_split_parity_dummy_precedes_real_and_uses_no_real_activations(self):
        with tempfile.TemporaryDirectory() as t:
            events=[];seen=[]
            class Backend:
                def load_oracle(self):pass
                def parity_scores(self,h,pairs):seen.append((h.copy(),pairs));return [[0.,1.] for _ in h]
            class Clock:
                def warmup(self,phase,fn):events.append(('dummy',phase));fn()
                def call(self,phase,fn,left=0):events.append(('real',phase));return fn()
            items=[{'id':f'{r}-{i}','feature':r} for r in P.ROWS for i in range(84)]
            templates={r:{'olens':[['A','B'],['a','b']]} for r in P.ROWS}
            P.generate(Backend(),Clock(),(items,templates,np.ones((252,DIM),np.float32)),t)
            self.assertEqual(events[:3],[('real','parity_setup'),('dummy','parity'),('real','parity')])
            np.testing.assert_array_equal(seen[0][0],np.random.default_rng(20261028).standard_normal((8,DIM)).astype(np.float32))
            self.assertEqual(len((Path(t)/'PARITY_SCORES.jsonl').read_text().splitlines()),252)


if __name__=='__main__':unittest.main()
