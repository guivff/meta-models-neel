from custody import *
from analysis_io import probe_aucs
from native_nla512 import truncation_summary
from counts57 import count_item

def metadata(spec):
 inp=Path(spec['inputs']);verify(inp,'INPUT_SEAL.json',spec['input_seal_sha256']);require(sha(spec['private_items'])==spec['private_items_sha256'],'private bank pin');items=read(inp/'items.json');private=read(spec['private_items']);require(len(private)==len(items) and [x['id'] for x in private]==[x['id'] for x in items],'private item order');return inp,items,{x['id']:x for x in private}

def unique_grid(rows,key,expected,message):
 keys=[key(x) for x in rows];require(len(keys)==len(set(keys)) and set(keys)==set(expected),message)

def collect(spec,e):
 inp,items,private=metadata(spec);pairs,caps,lineage=assemble(spec['receipt'],e);native=[];continuation=[];behaviour=[]
 for j,rows in pairs:
  if j['kind'] in ('native','injection'):native+=rows
  elif j['kind']=='continuation':continuation+=rows
  elif j['kind']=='behaviour':behaviour+=rows
  else:raise ValueError('unexpected analysis job kind')
 native.sort(key=lambda x:x['id']);probes=[];plan=None;counts=[]
 if e in ('E56','E57'):
  plan=read(inp/('RUN_PLAN.json' if e=='E57' else 'SHARDS.json'));samples=plan['native_ids'] if e=='E57' else read(inp/'SAMPLING.json')['native_ids'];units={k for ids in samples.values() for k in ids}
  if e=='E56':units|={x['id'] for x in read(inp/'injection/ITEMS.json')['items']}
  unique_grid(native,lambda x:(x['reader'],x['unit_id']),{(r,k) for r in ('oracle','nla') for k in units},'complete native union once')
  for x in native:require(x['id']==x['unit_id']+':'+x['reader']+':0' and x['repeat']==0,'single native ID')
  for slot in range(3):
   cap=Path(spec['outputs'][slot])/'capture';verify(cap,'CAPTURE_SEAL.json',caps[str(slot)]);rows=plan['shards' if e=='E57' else 'rows'][str(slot)];require(read(cap/'items.order.json')==[x['id'] for x in items if x['feature'] in rows],'original capture order')
   cpu=Path(spec['cpu_outputs'][str(slot)]);cs=verify(cpu,'CPU_SEAL.json');require(cs['capture_seal_sha256']==caps[str(slot)] and cs['private_items_sha256']==spec['private_items_sha256'] and cs['source_seal_sha256']==spec['source_seal_sha256'],'original dev-fit CPU probe binding');xs=read(cpu/'PROBE.json');expected={x['id'] for x in items if x['feature'] in rows and x['split']=='test' and (e=='E56' or plan['rows'][x['feature']]['probe_applicable'])};unique_grid(xs,lambda x:x['id'],expected,'probe grid');probes+=xs
  if e=='E57':
   own={(x['reader'],x['id']):x for x in continuation};require(len(own)==len(continuation) and all(x['arm']=='own' for x in continuation),'original E57 own-only acquisition')
   continuation=[dict(x,arm=arm,scores=x['scores'] if arm=='own' else own[x['reader'],plan['donors'][x['id']]]['scores']) for x in continuation for arm in ('own','swap')]
   counts=[count_item([x],plan['count_metadata'][x['unit_id']]) for x in native if x['feature'] in ('category_switch','capacity_list')]
  definitions=plan['rows'] if e=='E57' else read(inp/'CONTINUATIONS.json');eligible={row for row,v in definitions.items() if v['continuation_pairs' if e=='E57' else 'pairs'] is not None};expected={(r,x['id'],arm) for x in items if x['feature'] in eligible and x['split']=='test' for r in ('oracle','nla') for arm in ('own','swap')};unique_grid(continuation,lambda x:(x['reader'],x['id'],x['arm']),expected,'complete continuation own/swap grid')
 else:
  require(set(caps)=={e},'single ladder capture');cap=Path(spec['output'])/'capture';verify(cap,'CAPTURE_SEAL.json',caps[e]);require(read(cap/'items.order.json')==[x['id'] for x in items],'full ladder capture order');offsets=np.load(cap/'offsets.npy');full=np.load(cap/'all_positions44.npy',mmap_mode='r');require(full.dtype==np.float16 and full.shape==(int(offsets[-1]),5120) and offsets.tolist()==[0]+np.cumsum([x['read_index']-x['first_content_index']+1 for x in items]).tolist(),'all-position fp16 capture + exact offsets')
  cs=verify(spec['cpu_out'],'CPU_SEAL.json');require(cs['capture_seal_sha256']==caps[e] and cs['private_items_sha256']==spec['private_items_sha256'],'ladder CPU probe binding');probes=read(Path(spec['cpu_out'])/'PROBE.json');expected={x['id'] for x in items if x['split']=='test' and x.get('state')!='S6'};unique_grid(probes,lambda x:x['id'],expected,'ladder probe grid')
  expected={('oracle',x['id']) for x in items if x['split']=='test'};unique_grid(native,lambda x:(x['reader'],x['unit_id']),expected,'Oracle-only complete native grid')
  for x in native:require(x['id']==x['unit_id']+':oracle:0' and x['repeat']==0 and x['reader_native_layer']==44 and x['feature']==private[x['unit_id']]['feature'],'Oracle native identity')
  expected={x['id'] for x in items if x['split']=='test' and x['rung'] in ('L4','L4p')};unique_grid(behaviour,lambda x:x['id'],expected,'complete L4 behaviour grid')
  for x in behaviour:require(all(np.isfinite(x[k]) and 0<=x[k]<=1 for k in ('P_alpha','P_beta')) and abs(x['score']-(x['P_alpha']-x['P_beta']))<1e-7,'probability difference')
 return dict(private=private,native=native,probes=probes,continuation=continuation,capture_seals=caps,plan=plan,counts=counts,behaviour=behaviour,lineage=lineage,truncation=truncation_summary([x for x in native if x['reader']=='nla']) if e in ('E56','E57') else {'status':'NOT RUN','authority':'402be5f0'})
