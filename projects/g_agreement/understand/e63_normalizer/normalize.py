"""Lossless CPU normalization. No fitting, judging, scoring, sampling or reshuffling."""
import argparse,hashlib,json,re,subprocess,time
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
HERE=Path(__file__).resolve().parent
BANKS=['E56','E57','E59','E62']
READERS=['oracle','nla']

def require(ok,why):
 if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text())
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
 return h.hexdigest()
def write(p,data):Path(p).write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
def unique(xs,key):
 out={}
 for x in xs:
  k=key(x);require(k not in out,'duplicate source identity');out[k]=x
 return out
def verify(p,h):
 p=Path(p);require(sha(p)==h,'seal digest changed');s=read(p);require(bool(s.get('files')),'empty seal')
 for n,d in s['files'].items():
  member=(p.parent/n).resolve();require(member.is_relative_to(p.parent.resolve()),'seal traversal');require(sha(member)==d,'sealed member changed: '+n)
 return s
def committed():
 for p in HERE.iterdir():
  if p.suffix not in ('.py','.json','.md'):continue
  relative=str(p.relative_to(ROOT));data=subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)
  require(hashlib.sha256(data).hexdigest()==sha(p),'commit normalizer before payload access')
 return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
def verify_config(cfg):
 for p,h in cfg['files'].items():require(sha(p)==h,'pinned metadata changed')
 for p,h in cfg['seals'].items():verify(p,h)

def native_status(rate):
 if rate is None or rate['S'] is None:return 'NOT_EVALUABLE'
 require(len(rate['CI95'])==2 and rate['CI95'][0] is not None,'invalid sealed rate')
 return 'REPORTED' if rate['S']>=.2 and rate['CI95'][0]>0 else 'MISSED'

def rate_grid(rate,audit,n):
 require(audit['total']==n and audit['kept']+audit['UNPARSEABLE']==n,'complete acquired judgment inventory')
 require(rate['readouts']==rate['items']==audit['kept'],'sealed rate uses parseable judgments; retain all native text')

def groups(value):return tuple(tuple(v) if isinstance(v,list) else (v,) for v in value)
def family_ids(bank,row,ids,annotations,entry):
 if entry['status']!='AVAILABLE':return {i:None for i in ids}
 fs=entry['families'];require(all(len(f['patterns'])==2 and f['policy']=='whole_word_or_frozen_regex' for f in fs),'unsupported frozen pattern policy')
 if bank=='E57' and row in ('antonym_crosslingual','multi_token_entity','page_range_digit','two_hop_answer'):
  by={i:groups(annotations[i].get('value_words',annotations[i].get('answer_pair'))) for i in ids}
  ordered=sorted(set(by.values()));require(len(ordered)==len(fs),'frozen family count')
  counts=Counter(by.values());require([counts[g] for g in ordered]==[f['weight'] for f in fs],'frozen family weights')
  return {i:ordered.index(g) for i,g in by.items()}
 require(len(fs)==1,'unmapped multiple frozen families')
 return {i:0 for i in ids}

def join_packet(packet,key):
 public=unique(packet,lambda x:x['id']);private=unique(key,lambda x:x['source_id'])
 require(len(key)==len(public) and {x['opaque_id'] for x in key}==set(public),'full sealed public/private join')
 return {k:public[v['opaque_id']] for k,v in private.items()}

def build_bank(bank,b,catalog):
 s=read(b['spec']);private=read(b['private']);pr=unique(private,lambda x:x['id'])
 input_items=read(Path(b['inputs']).parent/'items.json')
 require([x['id'] for x in private]==[x['id'] for x in input_items],'unchanged input order')
 for x in input_items:require((x['feature'],x['split'])==(pr[x['id']]['feature'],pr[x['id']]['split']),'input identity')
 # Complete row order and test sampling come from frozen inputs, not readouts or rates.
 if bank in ('E56','E57'):samples=read(b['sampling'])['native_ids']
 else:
  samples={}
  for x in private:
   if x['split']=='test':samples.setdefault(x['feature'],[]).append(x['id'])
 require(set(samples)==set(catalog),'complete catalog/bank row inventory')
 folder=Path(b['analysis']).parent;a=read(b['analysis']);once=read(folder/'ONCE.json')
 require(a['status']=='COMPLETE' and a['experiment']==bank and once['experiment']==bank,'actual completed once-only bank evidence')
 rates=read(folder/'NATIVE_RATES.json') if bank=='E56' else read(folder/'RESULTS.json')['rates']
 missingness=read(folder/'UNPARSEABLE_COUNTS.json')['rows']
 bs=read(b['blind']);require(bs['receipt_sha256']==sha(b['receipt']) and bs['private_key_sha256']==sha(b['key']),'blind binding')
 require(a.get('manifest_sha256',a.get('receipt_sha256'))==sha(b['receipt']),'analysis/packet same acquisition')
 receipt=read(b['receipt']);require(receipt['verified'] is True and receipt['experiment']==bank,'verified acquisition')
 blind=Path(b['blind']).parent;packet=read(blind/'JUDGE_PACKET.json')
 if 'EVAL_PACKET.json' in bs['files']:packet+=read(blind/'EVAL_PACKET.json')
 key=read(b['key']);joined=join_packet(packet,key);ann=read(b['annotations']) if bank=='E57' else {}
 rows=[];used=set()
 for row,ids in samples.items():
  require(len(ids)==84 and len(set(ids))==84,'registered84-item row grid')
  require(all(pr[i]['feature']==row and pr[i]['split']=='test' for i in ids),'frozen sampling row/split')
  entry=catalog[row];family=family_ids(bank,row,ids,ann,entry)
  for reader in READERS:
   acquired=not(bank=='E62' and reader=='nla');expected=[i+':'+reader+':0' for i in ids] if acquired else []
   rate_key=reader+'|'+row+('|text' if bank=='E56' else '')
   rate=rates.get(rate_key)
   recs=[]
   for i,ident in zip(ids,expected):
    require(ident in joined,'missing acquired source readout');p=joined[ident];used.add(ident)
    require(isinstance(p['readout'],str),'preserve empty native strings')
    label=pr[i]['label'];require(label in (None,0,1),'frozen label domain')
    recs.append(dict(id=ident,item_id=i,reader=reader,layer=44 if reader=='oracle' else 42,repeat=0,
     text=p['readout'],label=None if label is None else ('A' if label==1 else 'B'),family=family[i],
     source_opaque_id=p['id']))
   evaluable=acquired and entry['status']=='AVAILABLE' and all(x['label'] is not None for x in recs)
   reason=None if evaluable else ('NOT_RUN: E62 NLA not acquired under402be5f0' if not acquired else entry.get('reason','No registered binary truth'))
   if rate is not None:rate_grid(rate,missingness[reader+'|'+row+'|text'],len(recs))
   rows.append(dict(bank=bank,row=row,reader=reader,channel='native',layer=44 if reader=='oracle' else 42,
    prompt='unchanged native reader prompt (original sealed acquisition)',controlling_experiment=bank,
    acquisition_status='ACQUIRED' if acquired else 'NOT_RUN',native_status=native_status(rate),
    native_status_source=dict(file=str(folder/('NATIVE_RATES.json' if bank=='E56' else 'RESULTS.json')),key=rate_key,rate=rate,missingness=missingness.get(reader+'|'+row+'|text')),
    analysis_status=a['status'],analysis_seal_sha256=sha(b['analysis']),
    regex_status='AVAILABLE' if evaluable else 'NOT_EVALUABLE',regex_reason=reason,
    frozen_regex=entry,expected_item_ids=ids,expected_readout_ids=expected,readouts=recs))
 extras=[dict(source_id=k,opaque_id=v['id'],text=v['readout']) for k,v in joined.items() if k not in used]
 if bank=='E56':
  injection=read(Path(b['inputs']).parent/'injection/ITEMS.json')['items']
  want={x['id']+':'+r+':0' for x in injection for r in READERS}
  require({x['source_id'] for x in extras}==want,'all injection arms explicitly retained separately')
 else:require(not extras,'no unaccounted native readouts')
 return rows,extras

def validate(data):
 require(data['schema']=='e63-normalized-v2' and data['banks']==BANKS and data['scope_complete'] is True,'full schema scope')
 rows=data['rows'];keys=[[r['bank'],r['row'],r['reader']] for r in rows]
 require(keys==data['expected_rows'] and len(set(map(tuple,keys)))==len(keys),'exact row order/identity')
 require(Counter(r['bank'] for r in rows)==dict(E56=26,E57=40,E59=12,E62=60),'all138 row-reader cells')
 for r in rows:
  require([x['id'] for x in r['readouts']]==r['expected_readout_ids'],'unchanged readout order')
  require(len(r['expected_item_ids'])==84 and len(set(r['expected_item_ids']))==84,'all84 frozen test items')
  want=[] if r['acquisition_status']=='NOT_RUN' else [i+':'+r['reader']+':0' for i in r['expected_item_ids']]
  require(want==r['expected_readout_ids'],'frozen item grid')
  if r['acquisition_status']=='NOT_RUN':require(r['bank']=='E62' and r['reader']=='nla','only registered NLA omission')
  for x in r['readouts']:
   require(x['reader']==r['reader'] and x['layer']==r['layer'] and x['repeat']==0 and isinstance(x['text'],str),'native identity')
   if r['regex_status']=='AVAILABLE':require(x['label'] in ('A','B') and x['family'] in range(len(r['frozen_regex']['families'])),'complete frozen family join')
 pools=data['placebo'];unique(pools,lambda x:x['id']);require(len(pools)==800,'full800 pools')
 for reader in READERS:
  for arm in ('random','shuffled'):
   xs=[x for x in pools if (x['reader'],x['arm'])==(reader,arm)]
   require([x['item_id'] for x in xs]==[arm+':'+str(i).zfill(3) for i in range(200)],'original pool order, no reshuffle')
   require(all(x['id']==reader+':'+x['item_id'] and x['repeat']==0 and x['layer']==(44 if reader=='oracle' else 42) for x in xs),'pool identity')

def inventory(data):
 rows=[]
 for r in data['rows']:
  x={k:v for k,v in r.items() if k not in ('readouts','native_status_source')}
  x['readout_text_sha256']=[hashlib.sha256(v['text'].encode()).hexdigest() for v in r['readouts']]
  x['n_readouts']=len(r['readouts']);rows.append(x)
 return dict(schema=data['schema'],banks=BANKS,scope_complete=True,expected_rows=data['expected_rows'],rows=rows,
  placebo_ids=[x['id'] for x in data['placebo']],n_placebo=800,
  non_native_inventory={b:[dict(source_id=x['source_id'],text_sha256=hashlib.sha256(x['text'].encode()).hexdigest()) for x in xs] for b,xs in data['non_native_records'].items()})

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--spec',type=Path,default=HERE/'SPEC.json');args=parser.parse_args()
 started=time.monotonic();commit=committed();cfg=read(args.spec);verify_config(cfg)
 dest=Path(cfg['destination']);receipt_dest=Path(cfg['receipt_destination']);require(not dest.exists() and not receipt_dest.exists(),'normalization already exists; do not overwrite')
 catalog=read(cfg['catalog']);rows=[];extras={}
 for bank in BANKS:
  c={x['row']:x for x in catalog['rows'] if x['bank']==bank};rr,ee=build_bank(bank,cfg['banks'][bank],c);rows+=rr;extras[bank]=ee
 pools=read(Path(cfg['pool']).parent/'POOLS.json');require(read(cfg['pool'])['output_seal_sha256']==sha(cfg['e63_output']),'original E63 pool/output binding')
 data=dict(schema='e63-normalized-v2',banks=BANKS,scope_complete=True,rows=rows,expected_rows=[[x['bank'],x['row'],x['reader']] for x in rows],placebo=pools,non_native_records=extras)
 validate(data);dest.mkdir(parents=True,mode=0o700)
 for name,value in [('DATA.json',data),('INVENTORY.json',inventory(data)),('RECEIPT.json',dict(issuer='W-mech2',authority=cfg['authority'],verified=True,code_commit=commit,spec_sha256=sha(args.spec),source_seals=[dict(path=p,sha256=h) for p,h in cfg['seals'].items()],source_files=cfg['files'],gpu_calls=0,judge_calls=0,scientific_analyses_run=0))]:
  write(dest/name,value);(dest/name).chmod(0o600)
 write(dest/'INPUT_SEAL.json',dict(schema=data['schema'],experiment='E63',status='NORMALIZED_VERIFIED',files={n:sha(dest/n) for n in ['DATA.json','INVENTORY.json','RECEIPT.json']}))
 receipt=dict(verified=True,issuer='W-mech2',authority=cfg['authority'],e63_output_seal_sha256=sha(cfg['e63_output']),input_seal_sha256=sha(dest/'INPUT_SEAL.json'),code_commit=commit,spec_sha256=sha(args.spec),inventory_sha256=sha(dest/'INVENTORY.json'),rows=len(rows),acquired_readouts=sum(len(r['readouts']) for r in rows),placebo_readouts=800,wall_seconds=time.monotonic()-started,gpu_calls=0,judge_calls=0,scientific_analyses_run=0,compatibility_entrypoint='projects.g_agreement.understand.e63_normalizer.analyze',legacy_adapter_compatible=False)
 write(receipt_dest,receipt);receipt_dest.chmod(0o600)
 print(json.dumps({k:receipt[k] for k in ('rows','acquired_readouts','placebo_readouts','input_seal_sha256','wall_seconds')}))
if __name__=='__main__':main()
