"""E49 row 7: execute restricted Python to determine the branch condition."""
import ast
from .interface import Item, RowSpec, length_match
SPEC = RowSpec('branch_taken', ('taken', 'not_taken'), 'semantic_state', ':')
PHRASINGS = (("- the conditional branch will run", "- the conditional branch will not run"),
             ("- The if condition evaluates to true.", "- The if condition evaluates to false."))
CONTINUATIONS = None  # Both conditions have the same syntactic continuation.
# Each family has a distinct arithmetic program, with identical operations per pair.
PARAMETERS = ((2, 2), (3, 2), (4, 2), (2, 3), (3, 3), (4, 3),
              (5, 2), (6, 2), (7, 2), (5, 3), (6, 3), (7, 3))

def generate():
    out = []
    for t, (offset, factor) in enumerate(PARAMETERS):
        for f in range(7):
            n = f + 1
            threshold = (n*factor+offset + (n+offset)*factor)//2
            add, mul = f'x = x + {offset}', f'x = x * {factor}'
            for v, operations in enumerate(((add, mul), (mul, add))):
                text = f'x = {n}\n' + '\n'.join(operations) + f'\nif x > {threshold}:'
                out.append(Item(SPEC.row_id, t, f, v, text, SPEC.values[v]))
    return out

def check_label(text):
    if not text.endswith(':'):
        raise ValueError('missing branch read position')
    try:
        tree = ast.parse(text + '\n    pass')
    except SyntaxError as exc:
        raise ValueError('invalid Python prefix') from exc
    allowed = (ast.Module, ast.Assign, ast.Name, ast.Store, ast.Load, ast.Constant,
               ast.BinOp, ast.Add, ast.Mult, ast.If, ast.Compare, ast.Gt, ast.Pass)
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        raise ValueError('outside the restricted execution grammar')
    if len(tree.body) != 4 or not all(isinstance(n, ast.Assign) for n in tree.body[:3]) or not isinstance(tree.body[-1], ast.If):
        raise ValueError('expected three assignments and one final condition')
    if any(isinstance(n, ast.Name) and n.id != 'x' for n in ast.walk(tree)):
        raise ValueError('unknown variable')
    if any(isinstance(n, ast.Constant) and (type(n.value) is not int or not 0 <= n.value <= 10000) for n in ast.walk(tree)):
        raise ValueError('invalid literal')
    scope = {}
    exec(compile(ast.Module(body=tree.body[:3], type_ignores=[]), '<e49-branch>', 'exec'), {'__builtins__': {}}, scope)
    result = eval(compile(ast.Expression(tree.body[-1].test), '<e49-condition>', 'eval'), {'__builtins__': {}}, scope)
    return 'taken' if result else 'not_taken'
