"""§105 continuation pairs: authored before E15 dev/reference or reader scores."""
from projects.g_agreement.blindspot.items import load_pinned_tokenizer

PAIRS = {
    'prose_paren': [(')', '('), (')\n', '(\n')],
    'prose_quote': [('"', '.'), ('"\n', '.\n')],
    'python_string': [('"', '0'), ('"\n', '.\n')],
    'python_indent': [('\n    pass', '\n            pass'), ('\n    return', '\n            return')],
    'python_depth': [(']', ']]'), (']\n', ']]\n')],
    'list_depth': [('\n  - ', '\n    - '), ('\n  - next', '\n    - next')],
    'table_column': [(' |', '\n'), (' | next', '\nnext')],
    'table_role': [(' | Batch', ' | amber'), (' | Shelf', ' | cedar')],
}
CONSEQUENCES = {
    'prose_paren': 'Close an open parenthesis versus open a new parenthesis.',
    'prose_quote': 'Close a double-quoted span versus punctuation without a quote.',
    'python_string': 'Close a double-quoted string versus leave it open / continue outside a string.',
    'python_indent': 'Next statement at four versus twelve leading spaces; statement text identical.',
    'python_depth': 'Close one versus two square brackets; no lexical content change.',
    'list_depth': 'Next bullet at two versus four leading spaces; bullet text identical. This is a shallow/deep contrast, not an asserted perfect-level match.',
    'table_column': 'Continue into another cell versus break the line; optional same word next.',
    'table_role': 'Next cell has a header-like label versus an exemplar data value. Lexical header/data proxy; validity must be established on dev.',
}


def frozen_pairs(tok):
    rows = {}
    for feature, pairs in PAIRS.items():
        encoded = []
        for a, b in pairs:
            ids = [tok.encode(s, add_special_tokens=False) for s in (a,b)]
            if not 1 <= len(ids[0]) <= 4 or len(ids[0]) != len(ids[1]):
                raise ValueError('need equal 1–4 native tokens: '+feature)
            encoded.append({'A':a,'B':b,'A_ids':ids[0],'B_ids':ids[1],'tokens_per_candidate':len(ids[0])})
        rows[feature]={'pairs':encoded,'consequence':CONSEQUENCES[feature]}
    return {'section':105,'rows':rows,'orientation':'W1 value A positive, no sign reversal',
        'oracle_prefix':'- ','oracle_prompt':'unchanged native Oracle prompt, no E6 continuation instruction appended',
        'nla_prefix':'','nla_status':'DESCRIPTIVE, continuation scoring off native explanation mode',
        'base_reference':'base Qwen with adapter disabled; actual W1 input tokens then candidate tokens, no question or bullet prefix',
        'validity':'Each pair valid iff base-reference dev AUROC>=0.80. Primary test score averages ONLY dev-valid pairs; zero-valid-pair rows NOT EVALUABLE. Report every pair separately; no replacement.',
        'notes':'Frozen surface consequences may fail base validity; failed pairs/rows are reported, never reauthored after scores.'}
