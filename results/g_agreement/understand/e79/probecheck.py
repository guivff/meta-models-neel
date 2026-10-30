"""Dev-only CPU manipulation check on already sealed vectors, no reader output."""
from worker import *
import torch
from mats.probes import fit_logreg

def run(out):
 base=ROOT.parent/'wt-blindspot-internals/results/g_agreement/understand/e79';s=read(base/'INPUTS.json');meta=Path(s['sources']['E57']['metadata']);require(sha(meta)==s['files'][str(meta)],'dev metadata');private=read(meta);by={x['id']:x for x in private};acts={}
 for cap in s['sources']['E57']['captures']:
  root=Path(cap['root']);verify(root,'CAPTURE_SEAL.json',s['seals'][str(root/'CAPTURE_SEAL.json')]);order=read(root/cap['order']);h=np.load(root/cap['acts'],allow_pickle=False)
  for i,k in enumerate(order):
   if by[k]['feature'] in A_ROWS and by[k]['split']=='dev':acts[k]=h[i]
 keypath=ROOT.parent/'wt-blindspot-internals/cache/g_agreement/understand/e79/inputs_v2_low_doses/KEY.DO_NOT_SHARE.json';receipt=read(base/'clarification2/BUILD_RECEIPT.json');require(sha(keypath)==receipt['private_map_sha256'],'private join');key=read(keypath);binding=read(HERE/'INPUT_BINDING.json');vectors=np.load(Path(binding['inputs'])/'vectors.npy',allow_pickle=False);items=read(Path(binding['inputs'])/'items.json');index={x['id']:x['vector_index'] for x in items};result={};torch.set_num_threads(1);torch.manual_seed(20261026)
 for row in sorted(A_ROWS):
  dev=[x for x in private if x['feature']==row and x['split']=='dev'];require(len(dev)==84 and all(x['id'] in acts for x in dev),'exact84dev, no test fit');model=fit_logreg(torch.from_numpy(np.array([acts[x['id']] for x in dev])),torch.tensor([x['label'] for x in dev]));selected=[k for k in key if k['row']==row];values=model.decision(torch.from_numpy(vectors[[index[k['id']] for k in selected]].copy())).detach().numpy();scores={k['id']:float(v) for k,v in zip(selected,values)};baseline={k['source_item_id']:scores[k['id']] for k in selected if k['condition']=='baseline'};cells={}
  for k in selected:
   if k['condition']=='baseline':continue
   delta=(scores[k['id']]-baseline[k['source_item_id']])*(1 if k['target_label']==1 else -1);cells.setdefault(k['condition']+':'+str(k['alpha']),[]).append(delta)
  result[row]={cell:dict(n=len(v),minimum=float(np.min(v)),mean=float(np.mean(v)),positive=sum(x>0 for x in v),all_toward_target=all(x>0 for x in v)) for cell,v in cells.items()}
 out.mkdir(parents=True,exist_ok=False);dump(out/'MANIPULATION.json',dict(fit_split='dev',rows=result,random_control_reported_without_filtering=True));seal(out,'MANIPULATION_SEAL.json',dict(experiment='E79',input_seal_sha256=binding['input_seal_sha256'],private_join_sha256=receipt['private_map_sha256'],reader_outputs_opened=False))
if __name__=='__main__':run(Path(sys.argv[1]))
