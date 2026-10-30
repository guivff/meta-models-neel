"""Registered E136R cap exposed only to this prospective accounting process."""
from decimal import Decimal
from .transport import CAPS
from .accounting250 import snapshot as previous

def snapshot(new_banks=()):
    old=CAPS.get('E136R');CAPS['E136R']=Decimal(1)
    try:return previous(new_banks)
    finally:
        if old is None:CAPS.pop('E136R',None)
        else:CAPS['E136R']=old
