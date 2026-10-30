"""§247 deviation2: original E136/E109 arithmetic; exact400 subset, block44."""
from pathlib import Path
from types import FunctionType
from projects.g_agreement.e136 import runner as original
from projects.g_agreement.e100.contract import read,verify,sha
LAYERS=(44,)
BANK_SHA='435c5c729e8eac765f51b92e5d7ee63d9183c26ec6beeaaab6056b2d095af629'
validate_items=original.validate_items
batches=original.batches
# Only configuration changes: original unhooked capture and observer/scorer.
_natural=FunctionType(original.runner109.natural_capture.__code__,dict(original.runner109.natural_capture.__globals__,CAPTURE=LAYERS))
capture_batch=FunctionType(original.capture_batch.__code__,dict(original.capture_batch.__globals__,_natural=_natural))
oracle_batch=FunctionType(original.oracle_batch.__code__,dict(original.oracle_batch.__globals__,LAYERS=LAYERS))


def load(root,digest):
    if digest!=BANK_SHA:raise ValueError('exact sealed deviation2 subset required')
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s.get('experiment')!='E136'or s.get('deviation')!=2 or s.get('labels_on_pod')is not False or set(s['files'])!={'items.json','MANIFEST.json'}:
        raise ValueError('public deviation2 members only')
    items=read(root/'items.json');m=read(root/'MANIFEST.json');validate_items(items)
    if len(items)!=400 or m['pairs']!=200 or m['prompts']!=400 or m['labels_on_pod']is not False or m['deviation']!=2:
        raise ValueError('complete original400/200 subset no refill')
    if m['source_input_sha256']!=original.BANK_SHA or m['tokenizer_revision']!=original.TOKENIZER_REVISION:
        raise ValueError('unchanged original source/tokenizer')
    return items,m


def source_gate():
    root=Path(__file__).resolve().parents[4]
    for n,h in read(Path(__file__).with_name('SOURCE_SEAL.json'))['files'].items():
        if sha(root/n)!=h:raise ValueError('changed dev2 source '+n)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();items,_=load(a.input,a.input_sha)
    if a.validate_only:print('E136 DEV2 VALIDATE_OK',len(items),'capture_batches',len(list(batches(items,8))),'native_readouts',len(items),'no model loaded');return
    raise SystemExit('I2 original creation-clock/custody/forecast admission required; no standalone production')

if __name__=='__main__':main()
