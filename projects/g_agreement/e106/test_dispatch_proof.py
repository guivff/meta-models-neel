"""Actual official-source provenance regression, including alternate basenames/threads."""
import importlib.util,sys,tempfile,threading,unittest
from pathlib import Path
from .dispatch_proof import identity,CallProof,tilelang_target
from .hardware_smoke import FiniteLogits

class Proof(unittest.TestCase):
    def test_exact_function_code_seen_across_threads_despite_chunk_o_filename(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'chunk_o.py';p.write_text('def chunk_bwd_dqkwg_tilelang():\n return 7\n')
            spec=importlib.util.spec_from_file_location('e106_cpu_official_fixture',p);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
            try:
                fn,d=identity(m.chunk_bwd_dqkwg_tilelang,t,'chunk_bwd_dqkwg_tilelang')
                with CallProof(fn,d) as proof:
                    worker=threading.Thread(target=fn);worker.start();worker.join()
                self.assertEqual(proof.receipt()['calls'],1)
                with CallProof(fn,d) as absent:pass
                with self.assertRaisesRegex(RuntimeError,'not observed'):absent.receipt()
                other=compile('def chunk_bwd_dqkwg_tilelang():\n return 9\n',str(p),'exec');ns={'__name__':m.__name__};exec(other,ns)
                with CallProof(fn,d) as spoof:ns['chunk_bwd_dqkwg_tilelang']()
                with self.assertRaisesRegex(RuntimeError,'not observed'):spoof.receipt()
                with self.assertRaisesRegex(ValueError,'source/code path'):identity(fn,Path(t)/'other','chunk_bwd_dqkwg_tilelang')
            finally:sys.modules.pop(spec.name,None)

    def test_official_reference_function_code_is_detected_without_cuda(self):
        import ast,types
        p=Path('cache/g_agreement/e106/backend_fix/fla-tilelang-chunk-bwd.py')
        if not p.exists():self.skipTest('official reference absent')
        tree=ast.parse(p.read_text());node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='chunk_bwd_dqkwg_tilelang')
        # Compile exact official body unchanged; intercept its first global read only.
        class Seen(Exception):pass
        def stop(*a):raise Seen
        ns={'__name__':'CPU_OFFICIAL_REFERENCE'}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(p),'exec'),ns)
        fn=ns[node.name]
        class Q:
            @property
            def shape(self):raise Seen
        with CallProof(fn,{'source':str(p)}) as proof:
            with self.assertRaises(Seen):fn(None,Q(),None,None,None,None)
        self.assertEqual(proof.receipt()['calls'],1)

    def test_read_only_finite_observer_preserves_outputs_removes_hook_and_rejects_nan(self):
        import torch
        from types import SimpleNamespace
        class Tiny(torch.nn.Module):
            def forward(self,x):return SimpleNamespace(logits=x)
        model=Tiny();wrapper=SimpleNamespace(get_base_model=lambda:model);x=torch.ones(2,3)
        with FiniteLogits(wrapper) as m:self.assertIs(model(x).logits,x)
        self.assertTrue(m.receipt()['all_logits_finite']);self.assertEqual(len(model._forward_hooks),0)
        with FiniteLogits(model) as bad:model(torch.tensor([float('nan')]))
        with self.assertRaisesRegex(RuntimeError,'nonfinite'):bad.receipt()

if __name__=='__main__':unittest.main()
