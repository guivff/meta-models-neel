"""§252 clarification1 CPU token transport/lookup; never changes selection.

X/Y, full normalized answer strings and their orientation stay on CPU. The GPU
writes the same final-prompt capture forward's complete fp32 vocabulary logits.
"""
from pathlib import Path
import numpy as np
from projects.g_agreement.e100.contract import sha
AUTHORITY='c33fcfb40'
TOKENIZER_REVISION='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
TOKENIZER_SHA='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42'


def load_tokenizer(snapshot):
    from transformers import AutoTokenizer
    p=Path(snapshot).resolve()
    if p.name!=TOKENIZER_REVISION or sha(p/'tokenizer.json')!=TOKENIZER_SHA:raise ValueError('original pinned Qwen tokenizer snapshot')
    return AutoTokenizer.from_pretrained(p,local_files_only=True,trust_remote_code=False)


def first_token_axis(tokenizer,X,Y):
    if not isinstance(X,str)or not isinstance(Y,str)or not X or not Y or X==Y:raise ValueError('original nonempty differing parsed X/Y')
    x=tokenizer.encode(' '+X,add_special_tokens=False)
    y=tokenizer.encode(' '+Y,add_special_tokens=False)
    if not x or not y or any(type(t)is not int or t<0 for t in x+y):raise ValueError('nonempty original leading-space tokenization')
    return dict(authority=AUTHORITY,tokenizer_revision=TOKENIZER_REVISION,tokenizer_sha256=TOKENIZER_SHA,
                X_token_ids=x,Y_token_ids=y,first_token_ids=[x[0],y[0]],
                status='NOT MEASURED'if x[0]==y[0]else'MEASURED',
                reason='shared first token'if x[0]==y[0]else'descriptive first-token X minus Y; same capture forward',
                readouts_count=True)


def measure(raw_vocab,axis):
    """CPU source lookup only; no forward, text generation, or statistic."""
    if axis.get('authority')!=AUTHORITY or axis.get('tokenizer_revision')!=TOKENIZER_REVISION or axis.get('tokenizer_sha256')!=TOKENIZER_SHA:
        raise ValueError('clarification1 pinned token source')
    x,y=axis['first_token_ids']
    expected='NOT MEASURED'if x==y else'MEASURED'
    if axis['status']!=expected:raise ValueError('first-token coincidence status')
    if x==y:return dict(status='NOT MEASURED',reason='shared first token',logit_X=None,logit_Y=None,logit_X_minus_Y=None,readouts_count=True)
    z=np.asarray(raw_vocab)
    if z.ndim!=1 or z.dtype!=np.float32 or not np.isfinite(z).all()or not(0<=x<len(z)and 0<=y<len(z)):raise ValueError('original finite raw fp32 capture-pass vocabulary')
    a,b=float(z[x]),float(z[y])
    return dict(status='MEASURED',logit_X=a,logit_Y=b,logit_X_minus_Y=a-b,readouts_count=True)
