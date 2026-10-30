"""Read pinned source as syntax/data only: never import or execute wsbench."""
import ast,hashlib,json,subprocess
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'e80/cache/workspace-bench'
PIN='86612fa4925100391b39c27894807a479595c61c'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2,sort_keys=True)+'\n')
def verify_pin():
    assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=SOURCE,text=True).strip()==PIN

def literal(node,env):
    if isinstance(node,ast.Constant):return node.value
    if isinstance(node,ast.Name):return env[node.id]
    if isinstance(node,(ast.List,ast.Tuple)):return [literal(n,env) for n in node.elts]
    if isinstance(node,ast.Dict):return {literal(k,env):literal(v,env) for k,v in zip(node.keys,node.values)}
    if isinstance(node,ast.JoinedStr):return ''.join(str(literal(n.value,env)) if isinstance(n,ast.FormattedValue) else n.value for n in node.values)
    if isinstance(node,ast.Call) and isinstance(node.func,ast.Name):
        if node.func.id=='list':return list(literal(node.args[0],env))
        if node.func.id=='schema_block':
            name,properties,required=[literal(n,env) for n in node.args]
            return dict(name=name,strict=True,schema=dict(type='object',additionalProperties=False,required=required,properties=properties))
    raise ValueError('Not a supported data literal')
def prompt_data(family):
    p=SOURCE/'src/wsbench/evals'/family/'prompts.py';env={}
    for n in ast.parse(p.read_text()).body:
        key=n.targets[0].id if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) else n.target.id if isinstance(n,ast.AnnAssign) and isinstance(n.target,ast.Name) else None
        if key:
            try:env[key]=literal(n.value,env)
            except (ValueError,KeyError):pass
    return dict(family=family,pin=PIN,source=str(p.relative_to(SOURCE)),source_sha256=sha(p),constants=env)
if __name__=='__main__':
    verify_pin();d=prompt_data('hallucination')
    frozen=json.loads((SOURCE/'evals/hallucination/judge_prompt_v5c_chat.json').read_text())
    for a,b in [('JUDGE_SYSTEM','system'),('JUDGE_USER','user'),('JUDGE_SCHEMA','schema')]:assert d['constants'][a]==frozen[b],a
    dump(HERE/'HALLUCINATION_PROMPTS.json',d)
