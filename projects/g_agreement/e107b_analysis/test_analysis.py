import unittest
from projects.g_agreement.e107b_analysis.adapter import analyze, cohort, reading, targets
from projects.g_agreement.e107_analysis.adapter import evaluate


class ForecastTests(unittest.TestCase):
    def test_threshold(self):
        self.assertEqual(reading(dict(estimate=.20, CI95=[.01,.4])), 'MET')
        self.assertEqual(reading(dict(estimate=.199, CI95=[.01,.4])), 'NOT MET')

    def test_strict_ci(self):
        for lower in (0, -.1):
            self.assertEqual(reading(dict(estimate=.3, CI95=[lower,.4])), 'NOT MET')

    def test_unknown(self):
        for point, ci in ((None, None), (.3, None)):
            self.assertEqual(reading(dict(estimate=point, CI95=ci)), 'NOT EVALUABLE')

    def test_exact_cohort(self):
        xs=[dict(id=str(i), row='a', item_id=i, bank='E82', cohort='belief_wrong') for i in range(199)]
        self.assertEqual(len(cohort(xs)), 199)
        with self.assertRaises(ValueError): cohort(xs[:-1])
        xs[-1]['item_id']=0
        with self.assertRaises(ValueError): cohort(xs)

    def test_no_truth_invention(self):
        with self.assertRaises(ValueError): targets({'belief':{}}, lambda x:x)

    def test_independent_denominators(self):
        xs=[]
        for i in range(199):
            xs.append(dict(row='a',item_id=i,systems=dict(
                oracle=dict(belief=1, named=i<100),
                outside=dict(belief=0, named=i>=99))))
        result=analyze(xs)
        self.assertEqual(result['pooled']['counts']['oracle']['kept'],100)
        self.assertEqual(result['pooled']['counts']['outside']['kept'],100)
        self.assertEqual(result['pooled']['difference']['estimate'],1)
        self.assertEqual(result['forecast_survival'],'MET')

    def test_all_missing(self):
        result=analyze([dict(row='a',item_id=1,systems=dict(oracle=None,outside=None))])
        self.assertEqual(result['forecast_survival'],'NOT EVALUABLE')

    def data(self, category='states_value', values=None, evidence='value'):
        return dict(code=dict(id='x',category=category,values=['A'] if values is None else values,evidence=evidence),text='value',target_letter='A')

    def meta(self):
        return dict(bank='E82',cohort='belief_wrong',systems=['oracle','outside'],
                    target_letters_by_system={x:dict(belief='A',truth='A') for x in ('oracle','outside')})

    def test_overlap_preserved(self):
        targets={t:self.data(values=['A','B']) for t in ('belief','truth')}
        z=evaluate(self.meta(),dict(oracle=targets,outside=targets))['systems']['outside']
        self.assertEqual((z['belief'],z['truth'],z['named']),(1,1,True))

    def test_missing_one_target_invalidates_naming(self):
        targets=dict(belief=self.data(),truth=self.data('UNPARSEABLE',[],''))
        z=evaluate(self.meta(),dict(oracle=targets,outside=targets))['systems']['outside']
        self.assertIsNone(z['belief']); self.assertIsNone(z['named'])

    def test_evidence_not_rewritten(self):
        targets={t:self.data(evidence='absent') for t in ('belief','truth')}
        with self.assertRaises(ValueError): evaluate(self.meta(),dict(oracle=targets,outside=targets))


if __name__=='__main__': unittest.main()

class BindingTests(unittest.TestCase):
    def test_complete_sealed_fixture_and_rejected_grid(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from projects.g_agreement.e107b_analysis import adapter as a
        from projects.g_agreement.understand.wmech2 import core
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for name in ('source','inventory','old','primary','forecast'):
                (root/name).mkdir()
            code=dict(id='opaque',category='states_value',values=['A'],evidence='value')
            core.write(root/'source/values.json',dict(text='value',code=code,target_letter='A'))
            core.seal(root/'source','SEAL.json')
            source=dict(seal=str(root/'source/SEAL.json'),sha256=core.sha(root/'source/SEAL.json'))
            target={k:dict(seal_index=0,member='values.json',keys=[k]) for k in ('text','code','target_letter')}
            tg={t:target for t in ('belief','truth')}
            letters=dict(belief='A',truth='A')
            metadata=[dict(id=str(i),row='r',item_id=i,bank='E82',cohort='belief_wrong',target_letters_by_system=dict(oracle=letters)) for i in range(199)]
            core.write(root/'inventory/INVENTORY.json',metadata)
            core.seal(root/'inventory','SEAL.json')
            ih=core.sha(root/'inventory/SEAL.json')
            core.write(root/'old/MEASUREMENTS.json',[dict(id=str(i),systems=dict(oracle=tg)) for i in range(199)])
            generation=dict(model='synthetic',provider='synthetic')
            core.seal(root/'old','SEAL.json',source_seals=[source],outside_generation=generation)
            core.write(root/'primary/BINDING.json',dict(inventory_seal=str(root/'inventory/SEAL.json'),inventory_sha256=ih,output_seal=str(root/'old/SEAL.json'),output_sha256=core.sha(root/'old/SEAL.json')))
            core.write(root/'primary/RESULTS.json',{})
            core.seal(root/'primary','SEAL.json')
            ph=core.sha(root/'primary/SEAL.json')
            rows=[dict(id=str(i),row='r',item_id=i,target_letters=letters,targets=tg) for i in range(199)]
            core.write(root/'forecast/MEASUREMENTS.json',rows)
            flags={k:True for k in ('route_verified','privacy_verified','same_route_and_judge','redaction_audit_complete','full_original_cohort','source_mapping_verified')}
            def reseal():
                core.seal(root/'forecast','SEAL.json',experiment='E107b',status='COMPLETE',primary_sha256=ph,inventory_sha256=ih,outside_generation=generation,source_seals=[source],prompt='What will this model answer? Give the value.',redacted_records=0,unknown_cost_requests=0,booked_usd=.1,cap_usd=2,**flags)
                return dict(primary_seal=str(root/'primary/SEAL.json'),output_seal=str(root/'forecast/SEAL.json'),output_sha256=core.sha(root/'forecast/SEAL.json'))
            with patch.object(a,'PRIMARY',ph):
                self.assertEqual(len(a.inputs(reseal())),199)
                rows.pop();core.write(root/'forecast/MEASUREMENTS.json',rows)
                with self.assertRaisesRegex(ValueError,'skipped/added'): a.inputs(reseal())
