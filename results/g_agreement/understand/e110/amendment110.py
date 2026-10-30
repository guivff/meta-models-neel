"""Amendment1 transport adapter; original frozen belief estimator remains unchanged.

Only I-2's once watcher executes run(). Private quarter maps and labels never go to pods.
"""
import argparse,datetime,hashlib,json,random
from pathlib import Path
from source110 import HERE,SEED,read,write,sha,require,load_rows
from filter110 import build_index,classify,choose
MODEL='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
DECODE=dict(do_sample=False,max_new_tokens=16,no_CoT=True)

def quarter_ids(items):
 ids=sorted(x['id'] for x in items);require(len(ids)==len(set(ids)) and len(ids)%4==0,'Unique quarterable candidate grid')
 random.Random(SEED).shuffle(ids);n=len(ids)//4
 return [set(ids[i*n:(i+1)*n]) for i in range(4)]

def bind_quarter(items,jobs,quarter,crosswalk,public,number):
 """Pure input identity check, tested synthetically without opening filter outcomes."""
 by={x['id']:x for x in items};jobby={x['id']:x for x in jobs};mapping=crosswalk['original_job_to_shard_job']
 require(crosswalk['shard']==number and set(crosswalk['original_candidate_ids'])==quarter,'Seeded quarter identity')
 subset=crosswalk['quarter_items'];require(len(subset)==len(quarter) and {x['id'] for x in subset}==quarter,'Complete quarter candidates')
 for x in subset:require(x==by[x['id']],'Private item/labels/template bytes unchanged')
 needed={j for x in subset for j in x['onehop_job_ids']+[x['twohop_job_id']]}
 require(set(mapping)==needed and len(set(mapping.values()))==len(mapping),'Exact per-quarter job map')
 pub={x['id']:x for x in public};require(len(pub)==len(public)==len(needed) and set(pub)==set(mapping.values()),'Exact unique scoped public grid')
 for old,new in mapping.items():
  require(old in jobby and pub[new]==dict(jobby[old],id=new),'Only opaque job id may change')
 return subset,mapping

def validate_outputs(data,mapping,jobs):
 out={x['id']:x for x in data};require(len(out)==len(data)==len(mapping) and set(out)==set(mapping.values()),'Complete sealed quarter outputs')
 jobby={x['id']:x for x in jobs};original={}
 for old,new in mapping.items():
  x=out[new];require(isinstance(x['raw'],str),'Original completion text')
  require(isinstance(x.get('token_ids'),list) and len(x['token_ids'])<=16 and all(type(t)is int and t>=0 for t in x['token_ids']),'Greedy16 original token IDs')
  require(x.get('finish_reason') in ('eos','length','stop') and x.get('max_new_tokens')==16 and x.get('do_sample') is False,'Original termination and decoding')
  require(x.get('input_ids_sha256')==hashlib.sha256(json.dumps(jobby[old]['input_ids']).encode()).hexdigest(),'Prompt-to-output token binding')
  original[old]=dict(x,id=old)
 return original

def sealed_member_path(root,private,name):
 p=Path(name);require(not p.is_absolute() and '..' not in p.parts,'Safe sealed member path')
 return Path(private)/'terminal_pull/outputs/ASSIGNMENT.json' if name=='ASSIGNMENT.json' else Path(root)/p

def run(plan_path,out):
 # Verify all prospective code/input bindings before opening any completion text.
 seal=read(HERE/'AMENDMENT1_SELECTOR_SEAL.json')
 for n,h in seal['files'].items():require(sha(HERE/n)==h,'Amendment selector source changed: '+n)
 require(sha(plan_path)==seal['files']['AMENDMENT1_SELECTOR_PLAN.json'],'Frozen command plan')
 bank=read(HERE/'BANK_SEAL.json')
 for n,h in bank['files'].items():require(sha(HERE/n)==h,'Original frozen source changed: '+n)
 plan=read(plan_path);require(plan['bank_seal_sha256']==sha(HERE/'BANK_SEAL.json'),'Original bank seal')
 guard=HERE/'cache/FILTER_SELECTION_ONCE.json';out=Path(out)
 require(not out.exists(),'Fresh output directory required; preserve failed/partial attempts')
 with guard.open('x') as f:json.dump(dict(experiment='E110',adapter='amendment1',output=str(out.resolve()),plan_sha256=sha(plan_path),selector_seal_sha256=sha(HERE/'AMENDMENT1_SELECTOR_SEAL.json')),f)
 out.mkdir(parents=True,exist_ok=False)
 write(out/'ATTEMPT.json',dict(plan_sha256=sha(plan_path),selector_seal_sha256=sha(HERE/'AMENDMENT1_SELECTOR_SEAL.json')))
 m=read(HERE/'MANIFEST.json');cache=Path(m['cache_directory'])
 for n,h in m['cache_files'].items():require(sha(cache/n)==h,'Original bank cache changed: '+n)
 items=read(cache/'ITEMS.PRIVATE.json');jobs=read(cache/'PUBLIC_FILTER_INPUTS.json');quarters=quarter_ids(items)
 require(len(items)==3000 and len(plan['shards'])==4,'Current completed all-four release; no sampling')
 index=build_index(load_rows(Path(m['source_csv'])));classified=[];native={};custody=plan['excluded_original_custody_seconds'];receipts=[]
 for entry in plan['shards']:
  q=entry['shard'];root=Path(entry['published_directory']);private=Path(entry['private_directory'])
  for n,h in entry['published_metadata_sha256'].items():require(sha(root/n)==h,'Published seal metadata changed')
  for n,h in entry['private_input_sha256'].items():require(sha(private/n)==h,'Private quarter source changed')
  outputseal=read(root/'OUTPUT_SEAL.json');note=read(root/'PUBLICATION_NOTE.json');closed=read(private/'CLOSEOUT.json')
  require(outputseal['status']=='COMPLETE' and outputseal['experiment']=='E110_FILTER_AMEND1' and outputseal['shard']==q,'Complete amendment1 shard only')
  require(outputseal['old_NO_FIT_outputs_excluded'] is True and outputseal['model_revision']==MODEL and outputseal['decoding']==DECODE,'Original decoding and old192 exclusion')
  require(note['verified_pull']['verified'] is True and note['verified_pull']['status']=='COMPLETE' and note['verified_pull']['output_seal_sha256']==sha(root/'OUTPUT_SEAL.json'),'Integrator verified pull')
  require(closed['scientific_status']=='COMPLETE' and closed['output_seal_sha256']==sha(root/'OUTPUT_SEAL.json') and closed['gpu_seconds']>=0,'Closed exact shard custody')
  custody+=closed['gpu_seconds'];cw=read(private/'CROSSWALK.PRIVATE.json')
  require(cw['original_item_source_sha256']==sha(cache/'ITEMS.PRIVATE.json'),'Private source bank binding')
  subset,mapping=bind_quarter(items,jobs,quarters[q],cw,read(private/'PUBLIC_FILTER_INPUTS.json'),q)
  require(outputseal['input_sha256']==sha(private/'PUBLIC_FILTER_INPUTS.json') and outputseal['candidate_count']==750 and outputseal['total_jobs']==outputseal['completed_jobs']==len(mapping),'Seal exact input/job completeness')
  for n,h in outputseal['files'].items():
   target=sealed_member_path(root,private,n)
   require(sha(target)==h,'Quarter sealed member hash mismatch: '+n)
  # No merging repeated original jobs across quarters: each item uses only its own acquisition.
  outputs=validate_outputs(read(root/'FILTER_OUTPUTS.json'),mapping,jobs)
  for x in subset:
   classified.append(classify(x,outputs,index));native[x['id']]=outputs[x['onehop_job_ids'][0]]['raw']
  receipts.append(dict(shard=q,candidates=len(subset),jobs=len(mapping),output_seal_sha256=sha(root/'OUTPUT_SEAL.json'),crosswalk_sha256=sha(private/'CROSSWALK.PRIVATE.json'),filter_outputs_sha256=sha(root/'FILTER_OUTPUTS.json')))
 require(custody<=10800,'Cumulative filtering cap includes original closed attempt')
 require(len(classified)==3000 and len({x['candidate_id'] for x in classified})==3000,'All completed quarters, all candidates once')
 receipt=dict(experiment='E110',verified=True,amendment='aa8438c71',input_seal_sha256=sha(HERE/'BANK_SEAL.json'),model_revision=MODEL,decoding=DECODE,filter_gpu_seconds_total=custody,filter_gpu_cap_seconds=10800,completed_quarters=[0,1,2,3],total_candidates=3000,old_NO_FIT_outputs_excluded=True,quarter_scoped_outputs_not_collapsed=True,shards=receipts)
 write(out/'FILTER_RECEIPT.json',receipt)
 selection=choose(classified);by={x['id']:x for x in items};codes={x['candidate_id']:x for x in classified};jobby={x['id']:x for x in jobs};public=[];targets=[]
 for ident in sorted(set(selection['wrong']+selection['right'])):
  x=by[ident];c=codes[ident];job=jobby[x['twohop_job_id']]
  public.append(dict(id=ident,prompt=job['prompt'],input_ids=job['input_ids'],read_position=job['read_position']))
  targets.append(dict(id=ident,composition_type=x['composition_type'],source_uid=x['source_uid'],cohort='belief_wrong' if ident in selection['wrong'] else 'belief_right',belief_qid=c['native_belief_qid'],belief=index.labels[c['native_belief_qid']],belief_aliases=sorted(index.names[c['native_belief_qid']]),belief_raw_native=native[ident],truth_qid=x['e2_qid'],truth=x['e2'],truth_aliases=x['e2_aliases'],belief_stable=c['stable_belief']))
 write(out/'SELECTION.PRIVATE.json',selection);write(out/'DIAGNOSTICS.PRIVATE.json',classified);write(out/'TARGETS.PRIVATE.json',targets);write(out/'PUBLIC_READER_INPUTS.json',public)
 counts=dict(status=selection['status'],gate=selection['gate'],stable_wrong=selection['stable_wrong'],native_wrong=selection['native_wrong'],selected_wrong=len(selection['wrong']),matched_right=len(selection['right']),unmatched_wrong=len(selection['unmatched_wrong']),target_150_met=len(selection['wrong'])>=150,unknown_native_belief=sum(x['native_belief_qid'] is None for x in classified),unknown_twohop_answer=sum(x['answer_qid'] is None for x in classified),total_candidates=len(items))
 write(out/'COUNTS.json',counts)
 write(out/'SELECTION_SEAL.json',dict(experiment='E110',status='COMPLETE_ONCE',input_seal_sha256=sha(HERE/'BANK_SEAL.json'),filter_receipt_sha256=sha(out/'FILTER_RECEIPT.json'),selector_seal_sha256=sha(HERE/'AMENDMENT1_SELECTOR_SEAL.json'),files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
 print(json.dumps(counts,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.plan,a.out)
