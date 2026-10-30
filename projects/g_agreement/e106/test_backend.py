"""CPU-only isolated dependency/official-dispatch regression checks."""
import ast,hashlib,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from projects.g_agreement.e106.backend_install import verify_wheels
from projects.g_agreement.e106.backend_smoke import verify_overlay

ROOT=Path('cache/g_agreement/e106/backend_fix')


class BackendRepair(unittest.TestCase):
    def test_wheels_are_sha_pinned_and_cannot_replace_scientific_packages(self):
        manifest=Path('results/g_agreement/e106/backend_fix/DEPENDENCIES.json')
        if not (ROOT/'wheels_linux').exists():self.skipTest('private wheel cache not present')
        d=verify_wheels(manifest,ROOT/'wheels_linux')
        self.assertFalse({'torch','triton','fla','peft','transformers','numpy'}&set(d['pins']))
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/'torch').mkdir()
            with self.assertRaisesRegex(ValueError,'cannot replace'):verify_overlay(manifest,p)

    def test_official_default_dispatch_targets_hopper_not_forced_global_backend(self):
        p=ROOT/'fla-tilelang-common.py'
        if not p.exists():self.skipTest('pinned official reference absent')
        tree=ast.parse(p.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TileLangBackend')
        code=compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),cls],type_ignores=[])),str(p),'exec')
        ns={'BaseBackend':object,'os':os,'_TILELANG_AVAILABLE':True,'has_usable_nvcc':lambda:True,'IS_NVIDIA_HOPPER':True,'TRITON_ABOVE_3_4_0':True}
        with patch.dict(os.environ,{},clear=True):
            exec(code,ns);backend=ns['TileLangBackend'];self.assertTrue(backend.is_available());self.assertTrue(backend.is_enabled())
            ns['IS_NVIDIA_HOPPER']=False;self.assertFalse(backend.is_enabled())
            ns['IS_NVIDIA_HOPPER']=True;ns['has_usable_nvcc']=lambda:False;self.assertFalse(backend.is_available())

    def test_exact_official_verifier_accepts_gated_native_shape_and_rejects_unsupported(self):
        p=ROOT/'fla-tilelang-common.py'
        if not p.exists():self.skipTest('pinned official reference absent')
        tree=ast.parse(p.read_text());cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='TileLangBackend')
        code=compile(ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),cls],type_ignores=[])),str(p),'exec')
        ns={'BaseBackend':object,'os':os};exec(code,ns);backend=ns['TileLangBackend']()
        from types import SimpleNamespace as S
        q=S(shape=(1,128,16,128),dtype='bf16');k=q;v=S(shape=(1,128,48,128),dtype='bf16');h=S(dtype='bf16')
        self.assertEqual(backend.chunk_bwd_dqkwg_verifier(q,k,v,None,h,None,g=object()),(True,None))
        self.assertFalse(backend.chunk_bwd_dqkwg_verifier(q,k,v,None,h,None,g=None)[0])
        self.assertFalse(backend.chunk_bwd_dqkwg_verifier(q,k,v,None,S(dtype='fp32'),None,g=object())[0])

if __name__=='__main__':unittest.main()
