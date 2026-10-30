"""CPU-only binding of frozen second-wave inputs; no labels enter pod archives."""
import argparse,shutil,tarfile,sys,json
from pathlib import Path
import numpy as np
from runtime62 import *
from bind62 import validate_full_grid

def manifest(out,experiment,meta):
 files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'INPUT_SEAL.json'}
 dump(out/'INPUT_SEAL.json',dict(experiment=experiment,files=files,**meta));archive=out.with_suffix('.tar.gz')
 with tarfile.open(archive,'w:gz') as t:t.add(out,arcname='inputs')
 return dict(inputs=str(out),input_seal_sha256=sha(out/'INPUT_SEAL.json'),input_archive={'path':str(archive),'sha256':sha(archive)},**meta)

def main():
 p=argparse.ArgumentParser();p.add_argument('--wtext',type=Path,required=True);p.add_argument('--w1',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 bindings={};banks={}
 for e in ('E62','E59'):
  directory=a.wtext/'results/g_agreement/understand'/e.lower();f=read(directory/'FREEZE_MANIFEST.json');root=Path(f['bank_directory']);verify(root,'BANK_SEAL.json',f['bank_seal_sha256']);require(sha(f['archive_path'])==f['archive_sha256'],'bank archive')
  private=read(root/'items.PRIVATE.json');public=[{k:x[k] for k in ('id','ids','text','feature','split','base_item_id','state','rung','first_content_index','read_index','alpha_token_id','beta_token_id') if k in x} for x in private]
  out=a.out/e.lower();out.mkdir();dump(out/'items.json',public)
  if e=='E62':
   validate_full_grid(public);b=read(E56/'INPUT_BINDING.json');shutil.copytree(Path(b['inputs'])/'parity',out/'parity')
  else:
   rows=sorted({x['feature'] for x in private});donors={}
   for x in private:
    if x['split']=='test':donors[x['id']]=next(z['id'] for z in private if z['split']==x['split'] and z['feature']==x['feature'] and z['label']!=x['label'] and z['cluster']!=x['cluster'])
   pairs={r:None for r in rows};pairs.update(format_plan=[['-','The']],language_plan=[['Je','The'],['Le','The']]);dump(out/'PLAN.json',{'continuation_pairs':pairs,'donors':donors});shutil.copyfile(root/'BOW_QA.json',out/'BOW_QA.json')
  bindings[e]=manifest(out,e,{'bank_seal_sha256':f['bank_seal_sha256'],'private_items':str(root/'items.PRIVATE.json'),'private_items_sha256':sha(root/'items.PRIVATE.json')});banks[e]=public
  job=HERE.parents[1]/e.lower()/'job';dump(job/'INPUT_BINDING.json',bindings[e])
 # Complete frozen test universe; W1 private metadata is used on CPU only to identify split/text.
 verify(a.w1,'INPUT_SEAL.json');w1public={x['id']:x for x in map(json.loads,(a.w1/'items.input.jsonl').read_text().splitlines())};w1=list(map(json.loads,(a.w1/'items.DO_NOT_STAGE.jsonl').read_text().splitlines()))
 require(set(w1public)=={x['id'] for x in w1},'W1 complete universe');require(all(w1public[x['id']]['ids']==x['ids'] for x in w1),'W1 exact token binding')
 banks['W1']=w1
 e36=a.wtext/'results/g_agreement/understand/e36/cache/v2_25_2026-10-25';verify(e36,'PREPARED_SEAL.json');banks['E36']=list(map(json.loads,(e36/'items.input.jsonl').read_text().splitlines()))
 pins={'W1':{'seal_sha256':sha(a.w1/'INPUT_SEAL.json'),'items_sha256':sha(a.w1/'items.input.jsonl'),'split_metadata_sha256':sha(a.w1/'items.DO_NOT_STAGE.jsonl')},'E36':{'seal_sha256':sha(e36/'PREPARED_SEAL.json'),'items_sha256':sha(e36/'items.input.jsonl')}}
 for e in ('E56','E57'):
  b=read(HERE.parents[1]/e.lower()/'job/INPUT_BINDING.json');root=Path(b['inputs']);verify(root,'INPUT_SEAL.json',b['input_seal_sha256']);banks[e]=read(root/'items.json');pins[e]={'input_seal_sha256':b['input_seal_sha256']}
 pins['E59']={'input_seal_sha256':bindings['E59']['input_seal_sha256']}
 universe=sorted([dict(bank=e,source_id=x['id'],**{k:x[k] for k in ('feature','ids','text','split')}) for e in ('W1','E36','E56','E57','E59') for x in banks[e] if x['split']=='test'],key=lambda x:(x['bank'],x['source_id']))
 require(len({(x['bank'],x['source_id']) for x in universe})==len(universe),'unique full universe')
 rng=np.random.default_rng(20261028);indices=rng.choice(len(universe),200,replace=False);selected=[dict(universe[int(i)],id=f'shuffled:{j:03d}') for j,i in enumerate(indices)]
 out=a.out/'e63';out.mkdir();dump(out/'items.json',selected);np.save(out/'random.npy',np.random.default_rng(20261027).standard_normal((200,5120)).astype(np.float32))
 dump(out/'POOL_SELECTION.json',{'seed':20261028,'universe_size':len(universe),'bank_counts':{e:sum(x['bank']==e for x in universe) for e in pins},'source_pins':pins,'selected_indices':indices.tolist(),'selected_ids':[{'bank':x['bank'],'id':x['source_id']} for x in selected],'capture':'fresh native-layer forward on frozen selected items before GO; no reader outputs'})
 bindings['E63']=manifest(out,'E63',{'random_seed':20261027,'selection_seed':20261028,'readouts_per_vector':1,'vectors_per_pool':200});dump(HERE.parents[1]/'e63/job/INPUT_BINDING.json',bindings['E63'])
 print('SECOND_WAVE_INPUTS_BOUND')
if __name__=='__main__':main()
