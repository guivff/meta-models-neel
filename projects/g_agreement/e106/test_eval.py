"""E106 evaluation privacy and placebo reproducibility checks; no rule analysis."""
import json,unittest
from pathlib import Path
import numpy as np
from projects.g_agreement.e106.prepare_eval import make_placebos


class EvalInputs(unittest.TestCase):
    def test_placebos_reproduce_seed_and_use_no_binary_targets(self):
        root=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wsae/cache/g_agreement/understand/e76/verified-pull/final')
        if not root.exists():self.skipTest('CPU calibration not present')
        arrays,meta=make_placebos(root)
        z=np.random.default_rng(20261031).standard_normal((200,5120)).astype(np.float32)
        for layer,a in arrays.items():
            self.assertEqual(a.shape,(200,5120));self.assertTrue(np.isfinite(a).all())
            self.assertTrue(np.allclose(a/np.linalg.norm(a,axis=1,keepdims=True),z/np.linalg.norm(z,axis=1,keepdims=True),rtol=1e-5,atol=1e-7))
        self.assertEqual(meta['gaussian_seed'],20261031)
        self.assertIn('no binary',meta['metric'])

    def test_frozen_local_inventory_has_exact_grid_and_cpu_truth_only(self):
        root=Path('results/g_agreement/e106/evaluation')
        if not (root/'INVENTORY.json').exists():self.skipTest('CPU private inventory not present')
        inventory=json.loads((root/'INVENTORY.json').read_text())
        self.assertEqual(len(inventory),3760);self.assertEqual(len({x['id'] for x in inventory}),3760)
        for x in inventory:
            if x['row']=='placebo':self.assertNotIn('target_by_cell',x)
            else:self.assertEqual(x['split'],'test');self.assertEqual(x['target_by_cell']['original'],x['target_by_cell']['intervention'])
        public=json.loads(Path('cache/g_agreement/e106/eval_v1/EVAL_ITEMS.json').read_text())
        for x in public:self.assertFalse({'target_by_cell','label','value','expected_answer'}&x.keys())
        self.assertEqual(len(public),1208)

if __name__=='__main__':unittest.main()
