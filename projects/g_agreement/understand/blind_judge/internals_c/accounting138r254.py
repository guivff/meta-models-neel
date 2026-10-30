"""Prospective E138R lifetime1 accounting; all prior exposure retained."""
from decimal import Decimal
from .transport import CAPS
from .accounting253 import snapshot as previous
def snapshot(new_banks=()):
    old=CAPS.get('E138R');CAPS['E138R']=Decimal(1)
    try:return previous(new_banks)
    finally:
        if old is None:CAPS.pop('E138R',None)
        else:CAPS['E138R']=old
