"""E49 row 6: product comparison; paired operands have identical digit counts."""
import re
from .interface import Item, RowSpec, length_match
SPEC = RowSpec('arith_compare', ('yes', 'no'), 'semantic_state', ':')
PHRASINGS = (("- the product is greater than the threshold", "- the product is not greater than the threshold"),
             ("- The answer to the comparison is yes.", "- The answer to the comparison is no."))
CONTINUATIONS = ((" Yes", " No"), (" yes", " no"))
HEADS = ('Decide the comparison below.', 'Work out the multiplication before answering.', 'Answer the following arithmetic question.', 'Compare the product with the given bound.', 'Evaluate this numerical comparison.', 'Consider the following product question.', 'Determine whether the inequality holds.', 'Multiply the operands and compare.', 'Solve the following comparison problem.', 'Check this multiplication question.', 'Use arithmetic to decide the answer.', 'Calculate the product to answer the question.')
OPERANDS = ((12, 34), (13, 24), (14, 23), (15, 26), (16, 25), (17, 28), (18, 27))

def generate():
    out = []
    for t, head in enumerate(HEADS):
        for f, (a, b) in enumerate(OPERANDS):
            c, d = int(str(a)[::-1]), int(str(b)[::-1])
            threshold = (a*b + c*d)//2
            for v, (x, y) in enumerate(((c, d), (a, b))):
                text = f'{head}\nIs {x} × {y} more than {threshold}? Answer:'
                out.append(Item(SPEC.row_id, t, f, v, text, SPEC.values[v]))
    return out

def check_label(text):
    m = re.fullmatch(r'[^\n]+\nIs ([1-9][0-9]) × ([1-9][0-9]) more than ([0-9]+)\? Answer:', text)
    if not m:
        raise ValueError('expected one complete product comparison prefix')
    a, b, threshold = map(int, m.groups())
    return 'yes' if a*b > threshold else 'no'
