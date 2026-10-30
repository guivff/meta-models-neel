"""CPU tests for gate order and once-only handoff."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_runtime import r, STAGE

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
O=module('e37_once',Path(__file__).with_name('analysis_once_2026_10_26.py'))

class GateOrder(unittest.TestCase):
    def test_rl_gate_precedes_sft_and_failed_rl_stops(self):
        items,h,t,pairs,carrier,parity,labels=r.load_inputs(STAGE)
        for fail in (False,True):
            active=[None];calls=[]
            def activate(model,arm):active[0]=arm
            def score(model,tok,unit,*args):
                calls.append((active[0],unit['feature'],len(unit['indices'])))
                return [{'id':items[i]['id'],'score':float(i%2),'scores':[float(i%2)]} for i in unit['indices']]
            answers=[parity['rl_reference_auc'][f]+(.2 if fail else 0) for f in r.PARITY_ROWS]
            with patch.object(r,'activate',side_effect=activate),patch.object(r,'score_unit',side_effect=score),patch.object(r,'auroc',side_effect=answers):
                result=r.run_parity(None,None,items,h,pairs,carrier,parity,labels,SimpleNamespace(guard=lambda:None))
            self.assertEqual(result['status'],'FAIL' if fail else 'PASS')
            if fail:self.assertTrue(all(arm=='RL' for arm,_,_ in calls))
            else:
                first_sft=next(i for i,c in enumerate(calls) if c[0]=='SFT')
                self.assertTrue(all(c[0]=='RL' for c in calls[:first_sft]))
                self.assertEqual([sum(n for arm,row,n in calls[:18] if row==f) for f in r.PARITY_ROWS],[84]*3)

class OnceOnly(unittest.TestCase):
    def test_atomic_claim_and_failure_never_retries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(O,'CLAIM',root/'CLAIM.json'),patch.object(O,'STATUS',root/'STATUS.json'),patch.object(O,'preflight',side_effect=ValueError),patch.object(O,'execute') as invoke:
                self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);invoke.assert_not_called()
                self.assertEqual(O.read(root/'STATUS.json')['registered_analysis_invocations'],0)

    def test_pull_requires_complete_transfer_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'out').mkdir();(root/'out/scores').write_text('synthetic')
            sums=root/'PULL_SUMS';sums.write_text(O.sha(root/'out/scores')+'  out/scores\n')
            O.verify_pull(root,O.sha(sums))
            (root/'out/unsealed').write_text('extra')
            with self.assertRaises(ValueError):O.verify_pull(root,O.sha(sums))

if __name__=='__main__':unittest.main()
