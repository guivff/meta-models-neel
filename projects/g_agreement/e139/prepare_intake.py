"""Read-only original-source intake; incomplete staging cannot be sent to a pod."""
import json,hashlib
from pathlib import Path
import numpy as np
from tokenizers import Tokenizer
from .selection import select,graft
B=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers')
N=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers')
PINS={}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p,expected=None,lines=False):
 p=Path(p);h=sha(p)
 if expected and expected!=h:raise ValueError('source hash mismatch '+str(p))
 PINS[str(p)]=h
 return [json.loads(x)for x in p.read_text().splitlines()] if lines else json.loads(p.read_text())
def member(root,seal,name):
 h=seal['files'][name];h=h['sha256'] if isinstance(h,dict)else h
 return read(Path(root)/name,h,lines=name.endswith('.jsonl'))
def checked_array(p,expected):
 if sha(p)!=expected:raise ValueError('array hash mismatch')
 PINS[str(p)]=expected
 return np.load(p,allow_pickle=False)
def main(out):
 if out.exists():raise FileExistsError('preserve old intake; fresh destination required')
 out.mkdir(parents=True)
 tokfile=B/'outputs/e139-evidence-v1/tokenizer.json'
 if sha(tokfile)!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42':raise ValueError('pinned tokenizer data')
 PINS[str(tokfile)]=sha(tokfile);tok=Tokenizer.from_file(str(tokfile));encode=lambda s:tok.encode(s,add_special_tokens=False).ids
 stage=[];targets=[];dev=[]
 def add(state,rows,texts,acts,devrows,prefixes):
  for r in select(rows,state,'test',cell='genre' if state=='evaluation_cue'else None):
   strings,statements=graft(texts[r['id']],state,r['label'],encode)
   vector=np.asarray(acts[r['id']],dtype=np.float32)
   if vector.shape!=(5120,)or not np.isfinite(vector).all():raise ValueError('exact original finite h44')
   stage.append(dict(state=state,original_id=r['id'],label=r['label'],strings=strings,statements=statements,vector_index=len(targets)))
   targets.append(vector.copy())
  for r in select(devrows,state,'dev') if state!='evaluation_cue'else []:
   ids=prefixes[r['id']][-32:];text=tok.decode(ids,skip_special_tokens=False)
   if encode(text)!=ids:raise ValueError('lossless true-span token roundtrip required: '+state)
   dev.append(dict(state=state,original_id=r['id'],label=r['label'],text=text,input_ids=ids))
 # E73 structural/control original class metadata and native reader-input vectors.
 allnative={}
 for name,expected in [('operator_c_native_700_a6','b09ce5e2be66d536411863238ab7584c82a77990e8b2b3d61444e05b1ef3b547'),('operator_c_native_300_a6','de2fe37258094a4d64607279a686e50346bfcaee02d3e38a692fc77025d43e35'),('operator_c_controls_native_20261028_a2','3cb112ba993292c2b05509e027e1612030d8f4c1d90580460527c87aad48f287')]:
  root=B/'wt-i2/cache/g_agreement/i2'/name/'sealed_native_pull';s=read(root/'READER_SEAL.json',expected)
  for r in member(root,s,'oracle.jsonl'):
   if r['reader']!='oracle'or r['capture_layer']!=44 or r['id']in allnative:raise ValueError('unique native Oracle44 source')
   allnative[r['id']]=r['raw_output']
 for bank,inputs,ish,states in [('gated_345ae3de',B/'wt-wcensus/cache/g_agreement/e73/reader_inputs_6f9ea0e0','a4b2cb5251a8a57b723b0251aa6f10c4aa1bb182caf63b9517d961422913df25',{'inside_string':'W1','nesting_depth':'W2'}),('controls_19da3104',B/'wt-i2/cache/g_agreement/i2/e73_controls_a2_reader_inputs','908e007fd023aaca195f0aa167dd18a3e51f09b4e81b20c3a4a97d54cc0c5b6b',{'language':'W7'})]:
  root=B/'wt-wcensus/cache/g_agreement/e73'/bank
  manifest=read(root/'public/MANIFEST.json')
  if manifest['tokenizer_sha256']!=sha(tokfile):raise ValueError('original bank tokenizer identity')
  labels=read(root/'private/labels.jsonl',manifest.get('private_labels_sha256'),True)
  public=read(root/'public/items.jsonl',manifest.get('items_sha256'),True);prefixes={r['id']:r['input_ids']for r in public}
  rseal=read(inputs/'READER_INPUT_SEAL.json',ish);ri=member(inputs,rseal,'READER_INPUTS.json');acts={}
  for f in ri['shards']:
   arr=checked_array(inputs/f['file'],f['sha256'])
   for i,id_ in enumerate(arr['ids'].tolist()):acts[id_]=arr['block44'][i]
  for state,source in states.items():
   rs=[dict(id=r['id'],split=r['split'],label=r['label'])for r in labels if r['state']==source]
   eligible=[r for r in rs if r['id']in acts and r['id']in allnative]
   add(state,eligible,allnative,acts,rs,prefixes)
 # E85 exact original TEST raw activations/readouts; keep each genre/addressed cell balanced.
 cfg=read(Path(__file__).resolve().parents[3]/'results/g_agreement/understand/e85/CPU_CONFIG.json')
 labels=read(cfg['private_path'],cfg['private_sha256']);rows=[dict(id=r['public_id'],split=r['split'],label=r['addressed'],genre=r['genre'])for r in labels]
 if {r['genre']for r in rows}!={0,1}:
  genres=sorted({r['genre']for r in rows})
  if len(genres)!=2:raise ValueError('two original genre cells')
  for r in rows:r['genre']=genres.index(r['genre'])
 root=B/'outputs/e130-inputs-v1/inputs';s=read(root/'INPUT_SEAL.json','01086c34e01657dceac68b003abffde9115a6bfd206f4343a88101f42836c24d')
 texts={r['id']:r['text']for r in member(root,s,'READOUTS.json')}
 rawroot=B/'outputs/e120-inputs-v1/decoder';ss=read(rawroot/'INPUT_SEAL.json');order=member(rawroot,ss,'items.json');arr=checked_array(rawroot/'h44.npy',ss['files']['h44.npy']);acts={r['id']:arr[r['vector_index']]for r in order}
 add('evaluation_cue',rows,texts,acts,[],{})
 # Exact E123 source pointer only; never use judge code/readings for selection.
 cfg=read(Path(__file__).with_name('..')/'e123/unhooked.json')
 pointers=read(cfg['cpu_only_labels']['path'],cfg['cpu_only_labels']['sha256']);root=Path(cfg['public_input']['root']);s=read(root/'INPUT_SEAL.json',cfg['public_input']['input_sha256']);arr=checked_array(root/'H44.npy',s['files']['H44.npy']);acts={r['base_id']:arr[i]for i,r in enumerate(pointers)if r['row']=='fact_recall'}
 original=read(B/'outputs/e127-inputs-v2/cpu_only/LABELS.PRIVATE.json','9be8f8debb84cd04b364296cb86dcf6664102e5e09e153058800b5bef5af8996');value={r['original_base_id']:r['old_value']for r in original}
 refs=read(B/'outputs/e134-intake/private_cpu/FACT_UNHOOKED_ROWS.json')['T2'];texts={}
 from projects.g_agreement.e134.sources import SealedJSON
 io=SealedJSON()
 for r in refs:
  source=r['source_refs'];ss=io.seal(source['seal'],source['sha256']);texts[r['item_id']]=io.pointer(ss['source_seals'],source['cells']['44']['text'])
 PINS.update(io.pins)
 rows=[dict(id=i,split='test',label={'Lima':0,'Paris':1}[value[i]])for i in acts]
 root=B/'wt-wtext/results/g_agreement/understand/e56/cache/bank_2026-10-27_v1';s=read(root/'BANK_SEAL.json');xs=member(root,s,'items.PRIVATE.json');devrows=[dict(id=r['id'],split=r['split'],label=r['label'])for r in xs if r['feature']=='fact_recall'];prefixes={r['id']:r['ids']for r in xs if r['feature']=='fact_recall'}
 add('fact_recall',rows,texts,acts,devrows,prefixes)
 def write(n,x):(out/n).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
 write('READOUTS.PRIVATE.json',stage);write('DEV_SPANS.PRIVATE.json',dev);np.save(out/'h44.PRIVATE.npy',np.stack(targets),allow_pickle=False)
 # Reuse exactly the original sealed E130 DEV rebuilds, no new forward or mean yet.
 eroot=B/'outputs/e130-review238/canonical_evidence/capture/acq'
 es=read(eroot/'OUTPUT_SEAL.json','0e4cf54a1d335288359d90f17cbf2803155cb1a32e1874b786b8ea5a14adb9c4')
 if es['experiment']!='E130'or es['status']!='COMPLETE'or es['tag']!=44 or es['variant']!=['li','ln']:raise ValueError('same original E130 AR space')
 ix=member(eroot,es,'INDEX.json');ix=[r for r in ix if r['condition']=='span_32'and r['split']=='dev']
 eroot2=B/'outputs/e130-inputs-v1/inputs';is_=read(eroot2/'INPUT_SEAL.json','01086c34e01657dceac68b003abffde9115a6bfd206f4343a88101f42836c24d');spans=member(eroot2,is_,'DEV_SPANS.json')
 cl={r['public_id']:r['addressed']for r in labels if r['split']=='dev'}
 if len(ix)!=200 or len(cl)!=200 or {r['id']for r in ix}!=set(cl)or set(cl)!={r['id']for r in spans}:raise ValueError('all200 original E85 dev identities')
 av={};dv=[];dm=[]
 for r in ix:
  if r['file']not in av:av[r['file']]=checked_array(eroot/r['file'],es['files'][r['file']])
  dv.append(av[r['file']][r['index']].copy());dm.append(dict(original_id=r['id'],label=cl[r['id']],source_file=r['file'],source_index=r['index']))
 np.save(out/'E85_DEV_REBUILDS.PRIVATE.npy',np.stack(dv),allow_pickle=False);write('E85_DEV_ORDER.PRIVATE.json',dm)
 write('SOURCE_PINS.json',PINS)
 write('INTAKE_STATUS.json',dict(experiment='E139',status='INCOMPLETE_HOLD_NO_POD_INPUT',items=len(stage),dev_spans=len(dev),missing=['table_column source confirmation','complete once-only adapter/source seal'],real_scoring=False,GPU_calls=0,files={p.name:sha(p)for p in out.iterdir()if p.is_file()}))
 print('INCOMPLETE CPU intake',len(stage),'readouts',len(dev),'dev spans; no public packet/score')
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);main(p.parse_args().out)
