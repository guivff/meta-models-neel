"""Public E127 load gate; CPU-only value binding is deliberately not imported."""
from pathlib import Path
from projects.g_agreement.e100.contract import read,verify

def load(root,digest):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest);xs=read(root/'items.json');m=read(root/'MANIFEST.json')
    if s['experiment']!='E127'or s['labels_on_pod']is not False or set(s['files'])!={'items.json','MANIFEST.json','SCORER.json'}:raise ValueError('public E127 members')
    if len(xs)!=252 or len({x['id']for x in xs})!=252 or m['oracle_layers']!=[44,52,60]or m['hook_enabled']is not False:raise ValueError('E127 complete grid')
    groups={}
    for i,x in enumerate(xs):
        if set(x)!={'id','base_id','row','condition','ids','read_index','candidate_ids','input_index'}or x['row']!='fact_recall'or x['input_index']!=i or x['read_index']!=len(x['ids'])-1:raise ValueError('E127 public field/last read position')
        groups.setdefault(x['base_id'],{})[x['condition']]=x
    if len(groups)!=84:raise ValueError('84 original items')
    for g in groups.values():
        if set(g)!={'context_update','neutral_prefix','none'}:raise ValueError('all three conditions')
        a,b,z=[g[k]['ids']for k in ('context_update','neutral_prefix','none')]
        if len(a)!=len(b)or a[-len(z):]!=z or b[-len(z):]!=z:raise ValueError('matched prefix length and exact original suffix')
    return xs,m
