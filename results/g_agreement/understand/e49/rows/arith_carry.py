"""E49 row 5: units carry; paired operand digit multisets are identical."""
import re
from .interface import Item, RowSpec, length_match
SPEC = RowSpec('arith_carry', ('carry', 'no_carry'), 'semantic_state', '=')
PHRASINGS = (("- a carry from the units column", "- no carry from the units column"),
             ("- The units sum carries into the tens.", "- The units sum does not carry into the tens."))
CONTINUATIONS = None  # Result suffixes depend on the operands, not just the carry bit.
HEADS = ('Calculate the addition below.', 'Work out the following sum.', 'Add these two integers.', 'Consider this arithmetic expression.', 'Complete the addition exercise.', 'Evaluate this sum carefully.', 'Find the result of this addition.', 'Compute the sum shown below.', 'Solve this addition problem.', 'Here is an integer addition.', 'Perform the following addition.', 'Determine the sum of these numbers.')
OPERANDS = ((16, 27), (17, 28), (18, 29), (26, 37), (27, 38), (28, 39), (36, 19))

def generate():
    out = []
    for t, head in enumerate(HEADS):
        for f, (a, b) in enumerate(OPERANDS):
            for v, (x, y) in enumerate(((a, b), (int(str(a)[::-1]), int(str(b)[::-1])))):
                out.append(Item(SPEC.row_id, t, f, v, f'{head}\n{x} + {y} =', SPEC.values[v]))
    return out

def check_label(text):
    m = re.fullmatch(r'[^\n]+\n([1-9][0-9]) \+ ([1-9][0-9]) =', text)
    if not m:
        raise ValueError('expected one complete two-operand addition prefix')
    a, b = map(int, m.groups())
    return 'carry' if a % 10 + b % 10 >= 10 else 'no_carry'
