"""§236 amendment4: fail closed at the physical POST, including pacing delays."""
import time
from contextlib import contextmanager
from pathlib import Path
from projects.g_agreement.readerbench.scoring import require

PAID_CUTOFF=1793372400 # Friday30Oct2026 15:00UTC /16:00CET
AUTHORITY='8ba4ecacaa840ae6c2443b4dc1945bc92baf11ad'


@contextmanager
def paid_window(api,pauses=(),clock=time.time):
    original=api.requests.post
    def post(*args,**kwargs):
        require(clock()<PAID_CUTOFF,'paid judging authority expired; no physical POST')
        require(not any(Path(p).exists()for p in pauses),'shared HTTP402 pause; no physical POST')
        return original(*args,**kwargs)
    api.requests.post=post
    try:yield
    finally:api.requests.post=original
