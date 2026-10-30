import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import forecast_e49_deadline as D
import comparison_once as C

class DeadlineContracts(unittest.TestCase):
    def test_partial_headline_and_all_gated_sensitivity(self):
        rows=[{'row':str(i),'class':'tracked_state','probe_auroc':1.,'base_text_auroc':1.,'bow_auroc':.5,'correct_value_rate':1.,'wrong_only_rate':0.} for i in range(16)]
        forecast={str(i):'REPORTED' if i<8 else 'NO FORECAST' for i in range(16)};human={str(i):'REPORTED' for i in range(16)}
        result=C.evaluate_r3(rows,forecast,human,'scale_9_over_16')
        self.assertEqual((result['n_gated'],result['n_forecasted_gated'],result['accuracy']),(16,8,1.))
        self.assertTrue(result['met']);self.assertEqual(result['sensitivity_no_forecast_wrong']['accuracy'],.5)
        forecast['7']='NO FORECAST';result=C.evaluate_r3(rows,forecast,human,'scale_9_over_16')
        self.assertIsNone(result['met']);self.assertIsNone(result['falsifier_low_accuracy'])
        self.assertEqual(result['sensitivity_no_forecast_wrong']['accuracy'],7/16)
        rows[-1]['probe_auroc']=0
        result=C.evaluate_r3(rows,forecast,human,'scale_9_over_16')
        self.assertEqual(result['sensitivity_no_forecast_wrong']['denominator'],15)

    def test_missing_reason_and_no_later_backfill(self):
        with tempfile.TemporaryDirectory() as td,patch.object(D,'HERE',Path(td)):
            p=Path(td);raw=p/'raw';raw.mkdir()
            (p/'BASIS_SEAL_2026-10-27.json').write_text(json.dumps({'files':{'basis_L44_r1536.npy':'toyhash'}}))
            (p/'VALUE_WORD_SETS_2026-10-27.json').write_text('{}')
            seal=p/'toyseal';seal.write_text('{}')
            with patch.object(D,'SEAL',seal):
                D.finish({'a':{'class':'content'}},{},raw,'CAPTURE_NOT_DELIVERED_BY_COMPUTE_DEADLINE',None)
            forecast=json.loads((p/'E49_JFORECAST.json').read_text());r=forecast['rows'][0]
            self.assertEqual(r['label'],'NO FORECAST');self.assertEqual(r['computational_reason'],'CAPTURE_NOT_DELIVERED_BY_COMPUTE_DEADLINE')
            before=(p/'E49_JFORECAST.json').read_bytes()
            with patch.object(D,'verify') as verify,patch.object(D,'FullRankReader') as score:
                self.assertEqual(D.run(),0);verify.assert_not_called();score.assert_not_called()
            self.assertEqual((p/'E49_JFORECAST.json').read_bytes(),before)

    def test_deadline_is_0520_utc(self):
        self.assertEqual(D.datetime.fromtimestamp(D.STOP_AT,D.timezone.utc).isoformat(),'2026-10-27T05:20:00+00:00')

if __name__=='__main__':unittest.main()
