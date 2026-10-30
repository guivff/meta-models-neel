from contextlib import nullcontext
from types import SimpleNamespace
import pytest
import torch
from projects.g_agreement.understand.w1_capture import capture_at_layers
from projects.g_agreement.blindspot import run as W


def test_frozen_w1_capture_path_unchanged_except_optional_layers():
    import ast,inspect
    from pathlib import Path
    old=ast.parse(Path('results/g_agreement/understand/e24d/frozen_w1_run.py').read_text())
    fn=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name=='capture_and_score')
    current=inspect.getsource(W.capture_and_score).replace(',capture_layers=None):','):').replace('[42,44] if capture_layers is None else capture_layers','[42,44]')
    assert ast.dump(fn)==ast.dump(ast.parse(current).body[0])


def test_exact_w1_call_no_scoring_and_no_all_grid_capture(monkeypatch):
    calls=[]
    def fake(items,donors,templates,ol,jl,batch,**kw):
        calls.append(kw);assert donors is None and templates=={} and jl is None and batch==32
        layers=kw.get('capture_layers',[42,44]);return {l:torch.full((2,3),float(l)) for l in layers},[]
    monkeypatch.setattr(W,'capture_and_score',fake)
    out=capture_at_layers(None,[{},{}],[44,20,60])
    assert calls==[{}, {'capture_layers':[20]}, {'capture_layers':[60]}]
    assert set(out)=={44,20,60}


def test_terminal_capture_avoids_later_inplace_mutation():
    class Block(torch.nn.Module):
        def forward(self,h):return h.add_(1)
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__();self.weight=torch.nn.Parameter(torch.zeros(1));self.layers=torch.nn.ModuleList([Block() for _ in range(64)])
        def forward(self,input_ids,attention_mask,logits_to_keep):
            h=input_ids.float()[:,:,None]
            for b in self.layers:h=b(h)
            return h
    model=Model();ol=SimpleNamespace(model=model,tok=SimpleNamespace(pad_token_id=0),base=nullcontext)
    result=capture_at_layers(ol,[{'ids':[1,3]}],[20,44,60])
    assert {l:v.item() for l,v in result.items()}=={20:24.,44:48.,60:64.}
    assert not any(b._forward_hooks for b in model.layers)
    # Demonstrate the failure mode on a toy model, not claim it for Qwen.
    from mats.capture import capture
    multi=capture(model,[[1,3]],[20,44,60],[[-1]],batch_size=32,pad_id=0)
    assert multi[44].item()==64.


def test_e32_uses_same_w1_path(monkeypatch):
    from projects.g_agreement.understand.e32 import Engine
    import projects.g_agreement.understand.w1_capture as C
    model=torch.nn.Module();model.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(64)])
    e=object.__new__(Engine);e.model=model;e.tok=SimpleNamespace(pad_token_id=0)
    def fake(ol,items,layers):
        assert ol.model is model and ol.tok is e.tok and layers==list(range(64))
        with ol.base():pass
        return {'captured':'base-only'}
    monkeypatch.setattr(C,'capture_at_layers',fake)
    assert e.capture([{'ids':[1]}])=={'captured':'base-only'}


@pytest.mark.parametrize('path',['old_e24','old_e32','new_e24','new_e32'])
def test_longest_w1_prefixes_keep_all_tokens_and_last_read_position(path):
    """Real longest W1 inputs + a 392-token input; toy forward, zero GPU work."""
    from projects.g_agreement.blindspot import protocol as P
    from projects.g_agreement.understand.e24_worker import Engine as E24,PRIORITY
    from projects.g_agreement.understand.e32 import Engine as E32
    from mats.capture import capture
    bank=P.ROOT/'cache/g_agreement/blindspot/w1-bank/items.DO_NOT_STAGE.jsonl'
    if not bank.exists():pytest.skip('sealed W1 bank unavailable')
    items=P.rows(bank);maximum=max(len(x['ids']) for x in items)
    chosen=[x for x in items if len(x['ids'])==maximum]
    at392=next(x for x in items if len(x['ids'])==392)
    chosen=chosen[:2]+[at392,min(items,key=lambda x:len(x['ids']))]
    seqs=[x['ids'] for x in chosen]
    class Model(torch.nn.Module):
        def __init__(self):
            super().__init__();self.weight=torch.nn.Parameter(torch.zeros(1));self.layers=torch.nn.ModuleList([torch.nn.Identity() for _ in range(64)]);self.calls=0
        def forward(self,input_ids,attention_mask,logits_to_keep):
            self.calls+=1
            # All four sequences fit one batch in old/new paths. No shortening,
            # extra special tokens, or reading a padded position is tolerated.
            assert input_ids.shape==(len(seqs),maximum)
            for row,original in enumerate(seqs):
                assert input_ids[row,:len(original)].tolist()==original
                assert attention_mask[row].sum().item()==len(original)
                assert attention_mask[row,len(original):].sum().item()==0
            pos=torch.arange(maximum).expand(len(seqs),-1)
            h=torch.stack((pos,input_ids),dim=-1).float()
            for block in self.layers:h=block(h)
            return h
    model=Model();tok=SimpleNamespace(pad_token_id=0)
    if path.startswith('old'):
        layers=list(PRIORITY) if path=='old_e24' else list(range(64))
        result={l:h[:,0] for l,h in capture(model,seqs,layers,[[-1]]*len(seqs),batch_size=8 if path=='old_e24' else 32,pad_id=0).items()}
    elif path=='new_e24':
        engine=object.__new__(E24);engine.ol=SimpleNamespace(model=model,tok=tok,base=nullcontext);result=engine.capture(chosen,list(PRIORITY))
    else:
        engine=object.__new__(E32);engine.model=model;engine.tok=tok;result=engine.capture(chosen)
    assert maximum>=392
    for h in result.values():
        assert h[:,0].tolist()==[len(s)-1 for s in seqs]
        assert h[:,1].tolist()==[s[-1] for s in seqs]
