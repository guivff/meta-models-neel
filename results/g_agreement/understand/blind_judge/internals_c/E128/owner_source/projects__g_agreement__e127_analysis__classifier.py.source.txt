"""§236 clarification4: unchanged core matcher; CPU candidate strings only."""
import hashlib
from pathlib import Path
import numpy as np
from projects.g_agreement.core.analysis_utils import parse_target_answer
from .common import require

MATCHER_FILE=Path(__file__).resolve().parents[1]/'core/analysis_utils.py'
MATCHER_SHA256=hashlib.sha256(MATCHER_FILE.read_bytes()).hexdigest()


def classify(record,candidates):
    """Return old/new/other; missing acquisition stays None, never inferred from logits."""
    require(set(candidates)=={'old','new'} and all(isinstance(v,str) and v for v in candidates.values())
            and candidates['old']!=candidates['new'],'sealed distinct old/new candidate strings')
    if record is None:return None
    require(record['greedy_max_new_tokens']==3 and isinstance(record['text'],str)
            and isinstance(record['token_ids'],list) and len(record['token_ids'])<=3
            and all(type(t)is int for t in record['token_ids']),'registered original 3-token greedy answer')
    # No added aliases, normalization, punctuation handling, or alternative parser.
    item={'primary':{'candidates':[candidates['old'],candidates['new']],'answer':candidates['old']}}
    value=parse_target_answer(item,record['text'])
    return next((name for name,text in candidates.items() if value==text),'other')


def pair_preference(record,new_value):
    """Original E104 mean(A-B) preference, descriptive only; ties are not flips."""
    if record is None or 'pair_logits' not in record:return None
    require(new_value in ('A','B'),'original A/B orientation')
    pairs=np.asarray(record['pair_logits'],dtype=float)
    require(pairs.ndim==2 and pairs.shape[0]>0 and pairs.shape[1]==2 and np.isfinite(pairs).all(),'finite original candidate pairs')
    delta=float(np.mean(pairs[:,0]-pairs[:,1]))
    return bool(delta>0 if new_value=='A' else delta<0)
