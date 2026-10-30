"""Once-only E49 analysis: validate -> gates -> seal inclusion -> qualified readers."""
import argparse,json,os,sys,time
from pathlib import Path
import numpy as np
from contract49 import *
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'vendor'));sys.path.insert(0,str(HERE.parent))
import rules49
from statements49 import categorize

def load_lines(p):return [json.loads(x) for x in Path(p).read_text().splitlines()]
def score_grid(records,ids,fields):
 require(len(records)==len(ids) and {x['id'] for x in records}==set(ids),'missing/duplicate/unexpected items')
 indexed={x['id']:x for x in records}
 for x in records:
  for k in fields:require(k in x,'missing score field '+k)
 return [indexed[k] for k in ids]

def summarize_native(row,records,ids,labels):
 ordered=score_grid(records,ids,['raw','text','malformed']);counts={k:0 for k in ['correct_only','wrong_only','both','neither']}
 for x in ordered:
  require(isinstance(x['text'],str) and isinstance(x['raw'],str) and type(x['malformed']) is bool,'native output format')
  counts[categorize(row,x['text'],labels[x['id']])]+=1
 n=len(ids);correct=counts['correct_only']+counts['both'];wrong=counts['wrong_only']
 return {'counts':counts,'n':n,'correct_mention_rate':correct/n,'correct_mention_Wilson95':wilson(correct,n),'wrong_only_rate':wrong/n,'wrong_only_Wilson95':wilson(wrong,n),'any_value_mention_rate':1-counts['neither']/n,'correct_only_minus_wrong_only':(counts['correct_only']-wrong)/n,'malformed':sum(x['malformed'] for x in ordered),'forecast_truth':'REPORTED' if correct/n>=.10 and correct>wrong else 'MISSED'}

def run(spec):
 root=Path(spec['verified_output']);out=Path(spec['out']);out.mkdir(parents=True,exist_ok=False)
 verify(HERE,'SOURCE_SEAL.json',spec['source_seal_sha256']);bind=read(HERE/'INPUT_BINDING.json')
 bank=Path(bind['bank_path']);verify(bank,'BANK_SEAL.json',BANK_SHA);require(sha(bind['private_items_path'])==bind['private_items_sha256'],'private bank identity')
 receipt=read(spec['verified_receipt']);require(receipt['verified'] is True and receipt['experiment']=='E49','integrator verification receipt')
 outer=verify(root,'OUTPUT_SEAL.json',receipt['output_seal_sha256']);a=read(root/'ASSIGNMENT.json');end=deadline(a)
 for d in (a,outer,receipt):
  require(d['source_seal_sha256']==spec['source_seal_sha256'] and d['input_seal_sha256']==bind['input_seal_sha256'],'input/source binding')
 require(outer['status']=='COMPLETE' and outer['pod_id']==a['pod_id']==receipt['pod_id'],'custody identity')
 require(read(root/'TIMING.json')['completed_epoch']<end,'custody exceeded')
 cap=root/'capture';verify(cap,'CAPTURE_SEAL.json',outer['capture_seal_sha256']);cm=read(cap/'CAPTURE_METADATA.json')
 require(cm['reader_calls_on_E49']==0 and cm['block']==44 and cm['pod_id']==a['pod_id'],'capture stage boundary')
 go=read(root/'GO_ACCEPTED.json');require(read(root/'TIMING.json')['completed_epoch']>=go['issued_epoch'],'completion predates release');validate_go(go,a,outer['capture_seal_sha256'],go['issued_epoch'],cm['captured_epoch'])
 require(receipt['go_sha256']==sha(root/'GO_ACCEPTED.json'),'integrator accepted release identity')
 verify(root/'gates','GATE_OUTPUT_SEAL.json');reader_seal=verify(root/'readers','READER_OUTPUT_SEAL.json')
 frozen_candidates=read(HERE/'CANDIDATES.json')['rows']
 expected_reader_files={r+'/'+name+'.jsonl' for r in frozen_candidates for name in ['oracle_native','oracle_asked','nla_native','nla_asked']}
 expected_reader_files|={r+'/continuation.jsonl' for r,m in frozen_candidates.items() if m['continuation']}
 require(set(reader_seal['files'])==expected_reader_files,'complete all-row reader acquisition manifest')
 for path in [root/'gates/GATE_OUTPUT_SEAL.json',root/'readers/READER_OUTPUT_SEAL.json']:
  s=read(path);require(s['go_sha256']==sha(root/'GO_ACCEPTED.json') and s['capture_seal_sha256']==outer['capture_seal_sha256'],'stage binding')
 import parity_gate
 inputs=Path(bind['public_path']);verify(inputs,'INPUT_SEAL.json',bind['input_seal_sha256'])
 _,py,_,_,pref=parity_gate.load_inputs({'path':str(inputs/'parity/INPUT_SEAL.json'),'sha256':parity_gate.INPUT_SHA256})
 pg=parity_gate.adjudicate(load_lines(root/'parity/PARITY_SCORES.jsonl'),py,pref);require(pg['status']=='PASS','W1 parity failed')
 allitems=read(bind['private_items_path']);items=[x for x in allitems if x['split']=='test'];labels={x['id']:x['label'] for x in items};candidates=read(HERE/'CANDIDATES.json')['rows'];ids=[x['id'] for x in items]
 require(read(cap/'items.order.json')==[x['id'] for x in allitems] and read(cap/'test.order.json')==ids,'capture item order')
 require(np.load(cap/'acts44.test.npy',mmap_mode='r').shape==(1344,5120),'test activation dimensions')
 probes=score_grid(read(root/'gates/probe.json'),ids,['score']);base=score_grid(read(root/'gates/base.json'),ids,['scores'])
 # Recompute BOW on the sealed bank using W-text's exact registered recipe;
 # never call the pre-seal QA CLI or mutate its attempt locks.
 from bow_once import score_row
 gates={};bowfits={}
 for row,m in candidates.items():
  ix=[i for i,x in enumerate(items) if x['feature']==row];y=[labels[ids[i]] for i in ix];require(len(ix)==84 and sum(y)==42,'row test balance')
  bow=score_row([x for x in allitems if x['feature']==row]);bowfits[row]=bow
  require(all(len(base[i]['scores'])==2 for i in ix),'base phrasing grid')
  gates[row]={'kind':m['spec']['kind'],'bow':bow['test_auroc'],'probe':auc(y,[probes[i]['score'] for i in ix]),'base':auc(y,[np.mean(base[i]['scores']) for i in ix])}
 qualified,excluded=rules49.qualify(gates)
 dump(out/'GATES.json',{'rows':gates,'qualified_rows':list(qualified),'excluded_rows':excluded,'reader_scores_parsed':False,'parity':pg});dump(out/'BOW_RECOMPUTED.json',bowfits)
 dump(out/'INCLUSION_SEAL.json',{'gates_sha256':sha(out/'GATES.json'),'bank_seal_sha256':BANK_SHA,'reader_scores_parsed':False})
 # Only now parse qualified rows' reader files. Excluded rows remain sealed/raw.
 native={};secondary={};rule_inputs={r:dict(v) for r,v in gates.items()}
 for row in qualified:
  rowitems=[x for x in items if x['feature']==row];rowids=[x['id'] for x in rowitems];y=[labels[k] for k in rowids];dest=root/'readers'/row
  native[row]={};secondary[row]={}
  for reader in ('oracle','nla'):
   native_records=load_lines(dest/(reader+'_native.jsonl'));require(all(x.get('block')==(44 if reader=='oracle' else 42) for x in native_records),'native reader layer')
   native[row][reader]=summarize_native(row,native_records,rowids,labels)
   score=score_grid(load_lines(dest/(reader+'_asked.jsonl')),rowids,['scores']);require(all(x.get('block')==(44 if reader=='oracle' else 42) for x in score),'asked reader layer');values=np.array([x['scores'] for x in score],float);require(values.shape==(84,2) and np.isfinite(values).all(),'asked score matrix')
   secondary[row][reader]={'label':'forced choice (off-distribution)','AUROC':auc(y,values.mean(1)),'phrasing_AUROC':[auc(y,values[:,i]) for i in range(2)]}
  rule_inputs[row]['oracle']=secondary[row]['oracle']['AUROC']
  pairs=candidates[row]['continuation']
  if pairs:
   score=score_grid(load_lines(dest/'continuation.jsonl'),rowids,['scores']);v=np.array([x['scores'] for x in score],float);require(v.shape==(84,len(pairs)),'continuation grid');secondary[row]['continuation']={'AUROC':auc(y,v.mean(1))}
  else:secondary[row]['continuation']={'status':'NOT APPLICABLE','reason':'no frozen pair supplied; E53 extensions separate'}
 precalls={x['name']:x['prediction'] for x in read(HERE/'PRECALLS.json')['predictions']};verdicts=rules49.evaluate(rule_inputs,precalls)
 dump(out/'NATIVE_PRIMARY.json',{'authority':'section168; forecast truth section169 clarification2','rows':native,'qualified_rows':list(qualified),'excluded_rows':excluded,'regex_sha256':sha(HERE/'statements49.py'),'sampling':'one greedy native readout/item,128 new tokens,84items/row/reader'})
 dump(out/'FORCED_CHOICE_SECONDARY.json',{'label':'forced choice (off-distribution)','rows':secondary,'registered_rules_unchanged':verdicts})
 report=['# E49 results','','Primary evidence: native unprompted value statements. Asked-channel rules below are forced choice (off-distribution).','',f'Qualified rows: {len(qualified)}/16. Excluded rows and gate values are in GATES.json.','', '| Row | Probe | Oracle correct mention | NLA correct mention | Oracle forecast truth |','|---|---:|---:|---:|---|']
 for row in qualified:report.append(f"| {row} | {gates[row]['probe']:.3f} | {native[row]['oracle']['correct_mention_rate']:.3f} | {native[row]['nla']['correct_mention_rate']:.3f} | {native[row]['oracle']['forecast_truth']} |")
 report+=['','Registered forced-choice rules: '+', '.join(k+' '+verdicts[k]['status'] for k in ('R1','R2','R3','falsifier'))+'.','', 'Frozen regex is a conservative explicit-statement detector; both-value and malformed outputs are retained. No conclusion about NLA reporting is drawn from forced choice alone.']
 (out/'RESULTS.md').write_text('\n'.join(report)+'\n');seal(out,'ANALYSIS_SEAL.json',{'experiment':'E49','status':'COMPLETE_ONCE','source_seal_sha256':spec['source_seal_sha256'],'output_seal_sha256':receipt['output_seal_sha256'],'bank_seal_sha256':BANK_SHA})

def main():
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);a=p.parse_args();s=read(a.spec)
 with Path(s['once_marker']).open('x') as f:json.dump({'status':'CONSUMED','spec_sha256':sha(a.spec),'started_epoch':time.time()},f)
 verify(HERE,'ANALYSIS_COMMAND_SEAL.json');require(sha(a.spec)==read(HERE/'ANALYSIS_COMMAND.json')['spec_sha256'],'analysis spec identity');os.environ['CUDA_VISIBLE_DEVICES']='';run(s)
if __name__=='__main__':main()
