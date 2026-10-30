"""§210 E103: E81 serial text path with registered stochastic decoding only."""
from pathlib import Path
import ast
import hashlib
import json
import re
import types
RUNTIME_SHA='0f588a959cef072cab058e1fa87e75cae54e139e289d8a1a0a767e07894362e5'
SEED=20261028

def require(value,message):
    if not value:raise ValueError(message)

def bind_sampling(backend,runtime_path):
    require(hashlib.sha256(Path(runtime_path).read_bytes()).hexdigest()==RUNTIME_SHA,'Pinned E81 Runtime source')
    tree=ast.parse(Path(runtime_path).read_text());cls=next(x for x in tree.body if isinstance(x,ast.ClassDef)and x.name=='Runtime');fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef)and x.name=='text')
    require(len(fn.args.defaults)==1 and fn.args.defaults[0].value==128,'Original text default')
    fn.args.defaults=[ast.Constant(64)]
    class Sampling(ast.NodeTransformer):
        changed=0
        def visit_Tuple(self,node):
            if all(isinstance(x,ast.Constant)for x in node.elts)and [x.value for x in node.elts]==[32,128]:
                self.changed+=1;return ast.copy_location(ast.Tuple(elts=[ast.Constant(64)],ctx=ast.Load()),node)
            return self.generic_visit(node)
        def visit_Call(self,node):
            node=self.generic_visit(node)
            if isinstance(node.func,ast.Attribute)and node.func.attr=='generate':
                flag=next(x for x in node.keywords if x.arg=='do_sample');require(isinstance(flag.value,ast.Constant)and flag.value.value is False,'Original greedy primitive')
                flag.value=ast.Constant(True);node.keywords.extend([ast.keyword(arg='temperature',value=ast.Constant(1.0)),ast.keyword(arg='top_p',value=ast.Constant(.95)),ast.keyword(arg='top_k',value=ast.Constant(0))]);self.changed+=1
            return node
    transform=Sampling();fn=transform.visit(fn);require(transform.changed==2,'Exact length/decoding changes only')
    fn.body.insert(0,ast.parse("require(len(sequences)==1,'E103 serial generation only')").body[0])
    scope={'require':require};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(runtime_path)+':E103-sampling','exec'),scope)
    backend.text=types.MethodType(scope['text'],backend)

def validate_public(items):
    require(bool(items)and len({x['id']for x in items})==len(items),'Unique opaque source jobs')
    for x in items:
        require(set(x)=={'id','prompt','input_ids','read_position'},'Public source prefixes only')
        require(isinstance(x['id'],str)and re.fullmatch('[A-Za-z0-9_:-]{1,128}',x['id']),'Safe opaque ID')
        require(x['input_ids']and all(type(t)is int and t>=0 for t in x['input_ids']),'Token IDs')
        require(x['read_position']==len(x['input_ids'])-1,'Prefix includes registered read token')

def write(path,value):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,sort_keys=True,allow_nan=False)+'\n');tmp.replace(path)

def acquire(items,backend,clock,out,runtime_path):
    """Uses the unchanged E81 Clock's real-pilot mean×1.25 admission and retrieval reserve."""
    validate_public(items);bind_sampling(backend,runtime_path)
    clock.call('base_setup',backend.load_base)
    clock.call('tokenizer_verification',lambda:backend.check_tokens([dict(text=x['prompt'],ids=x['input_ids'])for x in items]))
    clock.call('sample64_warmup_discarded',lambda:backend.text([backend.synthetic()[0]],max_new_tokens=64))
    backend.seed(SEED)  # One stream, reset after setup/warmup and before first retained sample.
    clock.remaining={'sample64':8*len(items)};jobs=out/'jobs';jobs.mkdir();seen=[]
    for item in items:
        for repeat in range(8):
            values=clock.call('sample64',lambda:backend.text([item['input_ids']],max_new_tokens=64),real=True)
            require(len(values)==1,'Exactly one serial continuation')
            write(jobs/f'{item["id"]}.{repeat}.json',dict(id=item['id'],repeat=repeat,raw=values[0]['raw'],token_ids=values[0]['token_ids'],temperature=1.0,top_p=.95,top_k=0,max_new_tokens=64,seed=SEED))
            seen.append((item['id'],repeat));clock.remaining['sample64']-=1;clock.admit()
    require(len(seen)==8*len(items)and len(set(seen))==len(seen),'Complete eight-sample inventory')
    write(out/'COUNTS.json',dict(source_items=len(items),samples=len(seen),serial_batch_size=1,reader_adapter_loads=0))


def literal_match(span,continuations):
    """Descriptive D4 only: exact case-sensitive substring in any of eight raw samples."""
    require(isinstance(span,str)and bool(span),'Frozen nonempty quoted span')
    require(len(continuations)==8 and all(isinstance(x,str)for x in continuations),'Eight raw continuations')
    return any(span in text for text in continuations)
