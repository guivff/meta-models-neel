"""Literal full native-index custody and whole original CPU values; no selection."""
from collections import Counter
from .transport import ROOT
from .banks import opaque
from .whole_values254 import e140_unit,assert_encoded
from projects.g_agreement.readerbench.io import read,sha,verify
from projects.g_agreement.readerbench.scoring import require
ORIGIN=ROOT.parent/'wt-i2/cache/g_agreement/i2/parallel_gpu230/e140-dev3'
NATIVE=ORIGIN/'terminal_pull/outputs/OUTPUT_SEAL.json'
NATIVE_SHA='c9b852f0d9461e0ef68f59f4dfb10b866a7848abca89682fdfe512ed0c7a077f'
POINTERS=ORIGIN/'NATIVE_INDEX_POINTERS.PRIVATE.json'
POINTERS_SHA='57ddbf7c41d8e4445a88f06f9c2114fa0ee8ad76ffb2ad7646f37d8db828bc75'
PROPERTY='answer to the factual question'

def assert_all(units,joins):
 require(len(units)==len(joins)==348 and len({u['id']for u in units})==348,'all348 unique original reads')
 for u,j in zip(units,joins):
  require(u['id']==j['id'] and set(u)=={'id','property','values','readout'} and u['property']==PROPERTY,'exact readout-only fields')
  assert_encoded(u['values'],{'X':j['X'],'Y':j['Y']})
 require(len({j['pair_id']for j in joins})==58 and Counter((j['pair_id'],j['paraphrase'],j['block'])for j in joins)==Counter((p,a,b)for p in{j['pair_id']for j in joins}for a in('A','B')for b in(44,52,60)),'exact58pairs/both/allblocks')

def build():
 s=verify(NATIVE,NATIVE_SHA);require(s['experiment']=='E140'and s['status']=='COMPLETE'and s['input_sha256']=='76dd4da7a78f210d903b29958b61b55818978a128bfe0e69731fd737cf70fdaa','original whole COMPLETE first300')
 cp=ORIGIN/'selection_cpu/cpu_only/CPU_SEAL.json';cs=verify(cp,sha(cp));require(cs['files']['SELECTION.PRIVATE.json']=='8199ce19d1b8dc560dffdd7ffca68b844987e3059e4e08a9bb872fa4ff7334e1','exact original whole CPU selected values')
 sel=read(cp.parent/'SELECTION.PRIVATE.json')['kept'];require(len(sel)==58,'owner selected58 no C selection')
 ip=ORIGIN/'selection_cpu/main/INPUT_SEAL.json';verify(ip,sha(ip));items=read(ip.parent/'items.json');require(len(items)==116,'whole selected members')
 by={x['id']:x for x in items};labels={}
 for pair in sel:
  require(type(pair['X'])is str and type(pair['Y'])is str and pair['X'] and pair['Y'],'original parsed whole strings')
  for k,i in enumerate(pair['member_ids']):require(i in by and by[i]['member']==k,'original explicit pair member');labels[i]=pair
 require(set(labels)==set(by),'exact owner selected identities')
 require(sha(POINTERS)==POINTERS_SHA,'I2 literal index/input pointer manifest');ptr=read(POINTERS);require(len(ptr)==348,'whole original pointer census')
 index=read(NATIVE.parent/'main/INDEX.json');units=[];joins=[]
 for p in ptr:
  ir=p['original_index_ref'];require(ir['member']=='main/INDEX.json'and len(ir['keys'])==1,'literal original index pointer');ix=index[ir['keys'][0]];item=items[p['original_input_ref']['keys'][0]]
  require(p['original_input_ref']['member']=='items.json'and ix['id']==item['id']==p['original_item_id']and ix['block']==p['block']and ix['kind']=='oracle'and item['pair_id']==p['pair_id']and item['member']==p['member'],'I2 explicit original identity agreement')
  nr=p['original_native_ref'];require(nr==dict(member='main/'+ix['member'],keys=[ix['record']]),'exact native member/record')
  native=read(NATIVE.parent/nr['member'])[ix['record']];require(type(native['text'])is str,'literal native text, empty preserved');pair=labels[item['id']];uid=opaque('E140','readout-only',ix['id'],str(ix['block']))
  units.append(e140_unit(uid,PROPERTY,native['text'],pair['X'],pair['Y']))
  joins.append(dict(id=uid,native_id=ix['id'],native_key=ix['id']+'@'+str(ix['block']),pair_id=item['pair_id'],paraphrase='A'if item['member']==0 else'B',block=ix['block'],X=pair['X'],Y=pair['Y'],native_seal=str(NATIVE),native_sha256=sha(NATIVE),native_index=ir,native=nr,original_input_seal=str(ip),original_input_sha256=sha(ip),original_input=p['original_input_ref'],original_cpu_seal=str(cp),original_cpu_sha256=sha(cp)))
 assert_all(units,joins);return units,joins,[dict(seal=str(p),sha256=sha(p))for p in(NATIVE,cp,ip)]
