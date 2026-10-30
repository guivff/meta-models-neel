"""New-epoch E110 selector custody adapter; original classifiers/matching unchanged.

I-2's once watcher alone invokes run(), after complete verified filter pulls.
"""
import argparse,datetime,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent
sys.path.insert(0,str(PARENT))
from source110 import read,write,require,sha,load_rows
from filter110 import build_index,classify,choose
from amendment110 import bind_quarter,validate_outputs,quarter_ids
from build_dev2 import MODEL
DECODE=dict(do_sample=False,max_new_tokens=16,no_CoT=True)

def receipt_check(r,bank_sha):
 require(r.get('experiment')=='E110' and r.get('phase')=='deviation2_obscure' and r.get('verified') is True,'Verified new-epoch I-2 receipt only')
 require(r.get('input_seal_sha256')==bank_sha and r.get('model_revision')==MODEL and r.get('decoding')==DECODE,'Exact bank/model/greedy16 recipe')
 shards=r['shards'];qs=[x['shard'] for x in shards]
 require(len(qs)==len(set(qs)) and set(qs)<=set(range(4)) and bool(qs),'Unique nonempty completed quarters')
 require(all(type(x.get('gpu_seconds')) in (int,float) and x['gpu_seconds']>=0 for x in shards),'Actual new-phase custody per shard')
 require(type(r.get('filter_gpu_seconds_total')) in (int,float) and abs(sum(x['gpu_seconds'] for x in shards)-r['filter_gpu_seconds_total'])<1e-6 and 0<=r['filter_gpu_seconds_total']<=3600,'New filter phase cap3600s, no cap borrowing')
 if len(qs)<4:
  when=datetime.datetime.fromisoformat(r['decision_utc'].replace('Z','+00:00'))
  require(r.get('cutoff_reached') is True and when.tzinfo is not None and when>=datetime.datetime(2026,10,29,15,tzinfo=datetime.timezone.utc),'Incomplete planned quarter set held until registered16CET cutoff')
 return sorted(shards,key=lambda x:x['shard'])

def run(receipt_path,out):
 bank=read(HERE/'BANK_SEAL.json')
 for n,h in bank['files'].items():require(sha(HERE/n)==h,'Frozen new bank/source changed: '+n)
 for n,h in bank['parent_dependencies'].items():require(sha(PARENT/n)==h,'Original scientific dependency changed: '+n)
 r=read(receipt_path);shards=receipt_check(r,sha(HERE/'BANK_SEAL.json'))
 out=Path(out);require(not out.exists(),'Fresh once-only output directory')
 guard=PARENT/'cache/FILTER_SELECTION_DEV2_ONCE.json'
 with guard.open('x') as f:json.dump(dict(experiment='E110',phase='deviation2_obscure',receipt_sha256=sha(receipt_path),out=str(out.resolve()),input_seal_sha256=sha(HERE/'BANK_SEAL.json')),f)
 out.mkdir(parents=True,exist_ok=False);write(out/'ATTEMPT.json',dict(receipt_sha256=sha(receipt_path),input_seal_sha256=sha(HERE/'BANK_SEAL.json')))
 m=read(HERE/'MANIFEST.json');cache=Path(m['cache_directory'])
 for n,h in m['cache_files'].items():require(sha(cache/n)==h,'Frozen bank data changed')
 items=read(cache/'ITEMS.PRIVATE.json');jobs=read(cache/'PUBLIC_FILTER_INPUTS.json');quarters=quarter_ids(items)
 index=build_index(load_rows(Path(m['source_csv'])));classified=[];native={}
 for entry in shards:
  q=entry['shard'];planned=m['shards'][q];private=Path(planned['directory'])
  for n,h in planned['files'].items():require(sha(private/n)==h,'Frozen new quarter source changed')
  s=Path(entry['output_seal']);require(sha(s)==entry['output_seal_sha256'],'Exact complete output seal');seal=read(s)
  require(seal.get('experiment')=='E110_FILTER_DEV2' and seal.get('status')=='COMPLETE' and seal.get('shard')==q,'Complete new-phase shard only; never earlier outputs')
  require(seal.get('model_revision')==MODEL and seal.get('decoding')==DECODE,'Frozen model/decoding')
  require(seal.get('input_sha256')==planned['files']['PUBLIC_FILTER_INPUTS.json'],'New scoped input hash')
  f=Path(entry['filter_outputs']);require(sha(f)==entry['filter_outputs_sha256']==seal['files']['FILTER_OUTPUTS.json'],'Original output bytes bound by complete seal')
  cw=read(private/'CROSSWALK.PRIVATE.json');require(cw['original_item_source_sha256']==m['cache_files']['ITEMS.PRIVATE.json'],'Private new epoch source map')
  subset,mapping=bind_quarter(items,jobs,quarters[q],cw,read(private/'PUBLIC_FILTER_INPUTS.json'),q)
  require(seal['total_jobs']==seal['completed_jobs']==len(mapping) and seal['candidate_count']==750,'Exact750 candidates / complete unique job grid')
  outputs=validate_outputs(read(f),mapping,jobs)
  for x in subset:
   classified.append(classify(x,outputs,index));native[x['id']]=outputs[x['onehop_job_ids'][0]]['raw']
 require(len(classified)==len({x['candidate_id'] for x in classified})==750*len(shards),'All completed candidate quarters, no partials or extra sampling')
 selection=choose(classified);by={x['id']:x for x in items};codes={x['candidate_id']:x for x in classified};jobby={x['id']:x for x in jobs};public=[];targets=[]
 for ident in sorted(set(selection['wrong']+selection['right'])):
  x=by[ident];c=codes[ident];job=jobby[x['twohop_job_id']]
  public.append(dict(id=ident,prompt=job['prompt'],input_ids=job['input_ids'],read_position=job['read_position']))
  targets.append(dict(id=ident,composition_type=x['composition_type'],source_uid=x['source_uid'],cohort='belief_wrong' if ident in selection['wrong'] else 'belief_right',belief_qid=c['native_belief_qid'],belief=index.labels[c['native_belief_qid']],belief_aliases=sorted(index.names[c['native_belief_qid']]),belief_raw_native=native[ident],truth_qid=x['e2_qid'],truth=x['e2'],truth_aliases=x['e2_aliases'],belief_stable=c['stable_belief'],source_bank='E110_deviation2_obscure'))
 write(out/'FILTER_RECEIPT.json',r);write(out/'SELECTION.PRIVATE.json',selection);write(out/'DIAGNOSTICS.PRIVATE.json',classified);write(out/'TARGETS.PRIVATE.json',targets);write(out/'PUBLIC_READER_INPUTS.json',public)
 counts=dict(status=selection['status'],gate=selection['gate'],stable_wrong=selection['stable_wrong'],native_wrong=selection['native_wrong'],selected_wrong=len(selection['wrong']),matched_right=len(selection['right']),unmatched_wrong=len(selection['unmatched_wrong']),target_150_met=len(selection['wrong'])>=150,unknown_native_belief=sum(x['native_belief_qid'] is None for x in classified),unknown_twohop_answer=sum(x['answer_qid'] is None for x in classified),total_candidates=len(classified),completed_quarters=[x['shard'] for x in shards],companion_E82_excluded_from_primary=True)
 write(out/'COUNTS.json',counts);write(out/'SELECTION_SEAL.json',dict(experiment='E110',phase='deviation2_obscure',status='COMPLETE_ONCE',input_seal_sha256=sha(HERE/'BANK_SEAL.json'),filter_receipt_sha256=sha(out/'FILTER_RECEIPT.json'),files={p.name:sha(p) for p in out.iterdir() if p.is_file()}));print(json.dumps(counts,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--receipt',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();run(a.receipt,a.out)
