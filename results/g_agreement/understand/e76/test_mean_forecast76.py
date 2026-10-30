"""CPU-only admission regressions: the registered running mean, outliers, and fixed deadline."""
import tempfile,unittest
from pathlib import Path
import worker76 as W
from common76 import read


class Tests(unittest.TestCase):
    def test_one_slow_outlier_does_not_replace_mean_with_maximum(self):
        with tempfile.TemporaryDirectory() as t:
            now=[0.]
            clock=W.Clock({'absolute_deadline_epoch':700,'phase_forecasts_seconds':{p:(10. if p=='oracle_readout' else 0.) for p in W.PHASES}},t,clock=lambda:now[0])
            durations=[.08]*45+[.91]
            for i,duration in enumerate(durations):
                def real(d=duration):now[0]+=d;return 'retained'
                self.assertEqual(clock.call('oracle_readout',real,1045-i),'retained')
            mean=sum(durations)/len(durations)
            self.assertEqual(clock.batch_counts['oracle_readout'],46)
            self.assertAlmostEqual(clock.batch_totals['oracle_readout'],sum(durations))
            self.assertAlmostEqual(clock.remaining['oracle_readout'],mean*1000)
            self.assertGreater(now[0]+1.25*max(durations)*1000+360,clock.end)
            self.assertLess(now[0]+1.25*mean*1000+360,clock.end)
            detail=read(Path(t)/'ADMISSION.latest.json')
            self.assertEqual(detail['status'],'ADMIT');self.assertEqual(detail['reforecast_margin'],1.25)
            self.assertAlmostEqual(detail['remaining_forecast_seconds'],mean*1000)

    def test_completed_mean_overrides_initial_hint_and_other_phase_timings(self):
        with tempfile.TemporaryDirectory() as t:
            now=[0.]
            clock=W.Clock({'absolute_deadline_epoch':7000,'phase_forecasts_seconds':{p:200. for p in W.PHASES}},t,clock=lambda:now[0])
            def setup():now[0]+=100
            clock.call('oracle_setup',setup)
            self.assertNotIn('oracle_setup',clock.batch_counts)
            def real():now[0]+=1;return 1
            clock.call('oracle_readout',real,10)
            self.assertEqual(clock.remaining['oracle_readout'],10)
            self.assertEqual(clock.remaining['nla_readout'],200)
            self.assertEqual(clock.batch_totals,{'oracle_readout':1.})

    def test_warmup_is_not_a_sample_and_absolute_deadline_still_stops(self):
        with tempfile.TemporaryDirectory() as t:
            now=[0.]
            clock=W.Clock({'absolute_deadline_epoch':7000,'phase_forecasts_seconds':{p:10. for p in W.PHASES}},t,clock=lambda:now[0])
            def dummy():now[0]+=1000
            clock.warmup('nla_readout',dummy)
            self.assertEqual(clock.batch_counts,{});self.assertEqual(clock.batch_totals,{})
            def real():now[0]+=2
            clock.call('nla_readout',real,10)
            self.assertEqual(clock.batch_counts['nla_readout'],1);self.assertEqual(clock.remaining['nla_readout'],20)
            self.assertEqual(clock.end,7000-W.RESERVE)
            now[0]=7000
            with self.assertRaises(W.NoFit):clock.check()


if __name__=='__main__':unittest.main()
