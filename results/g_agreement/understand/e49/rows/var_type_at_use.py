"""E49 row 8: runtime type after noncommuting swaps; labels checked by execution."""
import ast
from .interface import Item, RowSpec, length_match
SPEC = RowSpec('var_type_at_use', ('int', 'str'), 'semantic_state', 'x')
PHRASINGS = (("- x holds an integer", "- x holds a string"),
             ("- The runtime type of x is int.", "- The runtime type of x is str."))
CONTINUATIONS = None  # Type does not uniquely determine the next program token.
# Equivalent spellings and 2/4/6 swaps define twelve distinct code families.

def generate():
    out = []
    for t in range(12):
        reverse = t % 2
        quote = "'" if (t//2)%2 else '"'
        extra = t//4
        swap_xy = 'y, x = x, y' if reverse else 'x, y = y, x'
        swap_yz = 'z, y = y, z' if reverse else 'y, z = z, y'
        neutral = [swap_yz, swap_yz] * extra
        for f in range(7):
            n = f + 2
            initial = f'x = {n}\ny = {quote}{n}{quote}\nz = {n+8}\n'
            for v, operations in enumerate(((swap_yz, swap_xy), (swap_xy, swap_yz))):
                text = initial + '\n'.join([*operations, *neutral, 'y = y', 'z = z']) + '\nprint(x'
                out.append(Item(SPEC.row_id, t, f, v, text, SPEC.values[v]))
    return out

def check_label(text):
    if not text.endswith('\nprint(x'):
        raise ValueError('expected x at the open print call')
    try:
        tree = ast.parse(text[:-len('\nprint(x')])
    except SyntaxError as exc:
        raise ValueError('invalid Python prefix') from exc
    allowed = (ast.Module, ast.Assign, ast.Name, ast.Store, ast.Load, ast.Constant, ast.Tuple)
    if any(not isinstance(n, allowed) for n in ast.walk(tree)):
        raise ValueError('outside the restricted assignment grammar')
    if any(isinstance(n, ast.Name) and n.id not in {'x', 'y', 'z'} for n in ast.walk(tree)):
        raise ValueError('unknown variable')
    if any(isinstance(n, ast.Constant) and type(n.value) not in (int, str) for n in ast.walk(tree)):
        raise ValueError('invalid literal')
    scope = {}
    try:
        exec(compile(tree, '<e49-types>', 'exec'), {'__builtins__': {}}, scope)
    except (NameError, TypeError, ValueError) as exc:
        raise ValueError('invalid assignment program') from exc
    value = scope.get('x')
    if type(value) not in (int, str):
        raise ValueError('x has no supported runtime type')
    return type(value).__name__
