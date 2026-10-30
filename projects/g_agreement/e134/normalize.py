"""§242 clarification1 scalar mapping, independent of truth."""
def binary_value(code):
    if code is None or code.get('category')=='UNPARSEABLE':return None
    values=code['values']
    if values not in ([],['A'],['B'],['A','B'],['B','A']):raise ValueError('original binary candidate values')
    return values[0] if len(values)==1 else None

def cue_value(mention):
    if mention is not None and type(mention) is not bool:raise ValueError('mention boolean or terminal missing')
    return 'told' if mention is True else None
