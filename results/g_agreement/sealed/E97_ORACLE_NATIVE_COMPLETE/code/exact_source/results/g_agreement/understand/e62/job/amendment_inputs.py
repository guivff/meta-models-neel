"""Fail-closed contracts for the forthcoming 6aacc13d input freezes."""
from runtime62 import validate_items,require

def validate_placebo(items):
 validate_items(items);require(len(items)==2520,'15 cells x168')
 for s in ('S1','S2','S3','S4','S5'):
  for split in ('dev','test'):
   grids=[]
   for rung in ('L1p','L2p','L4p'):
    xs=[x for x in items if x['state']==s and x['rung']==rung and x['split']==split];require(len(xs)==84,'84 placebo items per split/cell');grids.append({x['base_item_id'] for x in xs})
   require(all(len(g)==84 and g==grids[0] for g in grids),'matched placebo base items')

def validate_d4a(items):
 require(items and len({x['id'] for x in items})==len(items),'unique D4a IDs')
 for x in items:
  require(x['split'] in ('dev','test') and x['ids'] and x['read_index']==len(x['ids'])-1,'frozen read boundary')
  require(x['concept'] in ('birds','citrus','musical_instruments','planets') and x['arm'] in ('think','ignore','none','cross','mention'),'registered concept and arm')
  if x['split']=='test':require(x['completion_ids'] and isinstance(x['answer_token_id'],int) and x['answer_token_id']>=0,'frozen completion channel')
  else:require(x['arm']=='think','dev-fit concept-probe arm')
 for c in ('musical_instruments','planets'):
  groups=[{x['pair_id'] for x in items if x['split']=='test' and x['concept']==c and x['arm']==a} for a in ('think','ignore','none','cross','mention')]
  require(all(len(g)==42 and g==groups[0] for g in groups),'42 new base items five arms')
 for c in ('birds','citrus'):
  groups=[{x['pair_id'] for x in items if x['split']=='test' and x['concept']==c and x['arm']==a} for a in ('think','ignore','none','cross','mention')]
  require(all(len(g)==42 and g==groups[0] for g in groups),'old concept read-point captures preserve five matched arms')
 require(sum(x['split']=='test' for x in items)==840,'four concepts x42 xfive test arms')
 require({x['concept'] for x in items if x['split']=='dev'}=={'birds','citrus','musical_instruments','planets'},'dev concept contrasts available')
