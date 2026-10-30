"""Read-only official-call provenance, independent of source basename/thread."""
import ast,hashlib,importlib,inspect,sys,threading
from pathlib import Path


def identity(function,root,expected_name):
    f=inspect.unwrap(function)
    if not inspect.isfunction(f) or f.__name__!=expected_name:raise ValueError('exact official Python function required')
    path=Path(inspect.getsourcefile(f)).resolve();code=f.__code__
    if not path.is_relative_to(Path(root).resolve()) or Path(code.co_filename).resolve()!=path:raise ValueError('official source/code path mismatch')
    module=importlib.import_module(f.__module__)
    if Path(module.__file__).resolve()!=path or inspect.unwrap(getattr(module,expected_name)) is not f:raise ValueError('official module/function identity mismatch')
    return f,{'module':f.__module__,'name':f.__name__,'source':str(path),'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'first_line':code.co_firstlineno}


def tilelang_target(backend,fla_root):
    # Resolve the import from the ACTUAL installed official method, not a filename guess.
    method=inspect.unwrap(backend.chunk_bwd_dqkwg)
    import textwrap
    tree=ast.parse(textwrap.dedent(inspect.getsource(method)))
    imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and any(a.name=='chunk_bwd_dqkwg_tilelang' for a in n.names)]
    if len(imports)!=1 or imports[0].level or not imports[0].module.startswith('fla.ops.common.backends.tilelang.'):
        raise ValueError('one explicit official TileLang backward import required')
    m=importlib.import_module(imports[0].module)
    return identity(getattr(m,'chunk_bwd_dqkwg_tilelang'),fla_root,'chunk_bwd_dqkwg_tilelang')


class CallProof:
    def __init__(self,function,description):self.function=function;self.description=description;self.calls=0
    def profile(self,frame,event,arg):
        if event=='call' and frame.f_code is self.function.__code__ and frame.f_globals.get('__name__')==self.function.__module__:
            self.calls+=1
    def __enter__(self):
        if not hasattr(threading,'setprofile_all_threads'):raise RuntimeError('Python3.12 all-thread provenance required')
        self.old_sys=sys.getprofile();self.old_thread=threading.getprofile()
        threading.setprofile_all_threads(self.profile);return self
    def __exit__(self,*args):
        threading.setprofile_all_threads(self.old_thread);sys.setprofile(self.old_sys)
    def receipt(self):
        if self.calls<1:raise RuntimeError('official exact function-code/module identity was not observed in backward')
        return dict(self.description,calls=self.calls,exact_code_identity=True,all_python_threads=True)
