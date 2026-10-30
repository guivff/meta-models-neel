"""§133: W1 capture_and_score path, terminal-layer capture, never reader scoring."""
from projects.g_agreement.blindspot import run as W


def capture_at_layers(ol,items,layers):
    result={}
    for layer in layers:
        # Preserve the exact W1 [42,44] request at the parity anchor. At other
        # layers the only change to that path is its terminal capture layer.
        args={} if layer==44 else {'capture_layers':[layer]}
        captured,scores=W.capture_and_score(items,None,{},ol,None,batch=32,**args)
        if scores or layer not in captured:raise ValueError('W1 capture-only contract')
        result[layer]=captured[layer]
    return result
