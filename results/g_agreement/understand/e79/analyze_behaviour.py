"""Once-only CPU export to W-text's sealed next-token scorer. Private join stays CPU."""
import argparse,subprocess
from worker import *
def run(spec):
 s=read(spec);c=read(HERE/'BEHAVIOUR_COMMAND.json');require(sha(spec)==c['spec_sha256'] and sha(HERE/'analyze_behaviour.py')==c['adapter_sha256'],'spec/adapter pin');req=read(HERE/'REQUEST.json');r=read(s['receipt']);require(r['verified'] is True and r['experiment']=='E79','verified integrator pull');root=Path(r['output']);o=verify(root,'OUTPUT_SEAL.json',r['output_seal_sha256']);require(o['status']=='COMPLETE' and o['source_seal_sha256']==req['source_seal_sha256'] and o['input_seal_sha256']==req['input_seal_sha256'],'complete source/input binding')
 binding=read(HERE/'INPUT_BINDING.json');require(sha(s['private_join'])==binding['private_join_sha256'],'private mapping pin');key={x['id']:x for x in read(s['private_join'])};items=read(Path(binding['inputs'])/'items.json');jj=jobs(items);require(read(root/'JOB_GRID.json')==jj and read(root/'COMPLETED.json')==list(range(len(jj))),'complete once-only jobs')
 cpu=HERE/'cpu_scorer';ss=verify(cpu,'SCORER_SEAL.json',req['scorer_seal_sha256']);document=[]
 for i,j in enumerate(jj):
  if j['kind']!='continuation':continue
  rows=read(root/'jobs'/f'{i:06d}.json');require(len(rows)==len(j['indices']),'ArmB job cardinality')
  for x,ix in zip(rows,j['indices']):
   item=items[ix];require(x['id']==item['id'],'opaque vector ID');k=key[x['id']];condition={'J':'d_J','nonJ':'d_perp','random':'random','none':'none'}[k['condition']];document.append(dict(id=k['source_item_id'],feature=k['row'],condition=condition,pair_logits=x['pair_logits']))
 require(len(document)==672,'all672patched forwards')
 # Preserve original fixed analysis path so changing specs cannot replay science.
 out=Path(s['out']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE.json',dict(spec_sha256=sha(spec),output_seal_sha256=r['output_seal_sha256']));dump(out/'NEXT_TOKEN_LOGITS.json',dict(schema='E79_ARM_B_NEXT_TOKEN_LOGITS_V1',candidate_token_ids=read(HERE/'CANDIDATES.json')['candidate_token_ids'],records=document))
 subprocess.run([sys.executable,str(cpu/'score79.py'),'--continuations',str(out/'NEXT_TOKEN_LOGITS.json'),'--sha256',sha(out/'NEXT_TOKEN_LOGITS.json'),'--private-items',s['private_items'],'--out',str(out/'metrics')],check=True)
 seal(out,'BEHAVIOUR_SEAL.json',dict(experiment='E79',authority='b3c1e6d0',output_seal_sha256=r['output_seal_sha256'],behaviour_only=True))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);run(p.parse_args().spec)
