"""§186 once-only CPU analysis; no native reader or judging."""
import argparse,math
from worker import *
from contract56 import auc

def rules(records,labels):
 rows=sorted({x['feature'] for x in records});result={}
 for row in rows:
  xs=[x for x in records if x['feature']==row];scores={}
  for arm in ('own','swap'):
   a=[x for x in xs if x['arm']==arm];require(len(a)==84 and len({x['base_item_id'] for x in a})==84,'84 unique per row/arm');scores[arm]=auc([labels[x['id']] for x in a],[x['score'] for x in a])
  result[row]={'normal_AUROC':scores['own'],'swapped_AUROC_against_A':scores['swap'],'swapped_AUROC_against_B':1-scores['swap'],'shown_used':scores['own']>=.8,'map_status':'used' if scores['own']>=.8 else 'decodable, not shown to be used'}
 n=len(rows);return {'rows':result,'R_B1':'MET' if sum(v['shown_used'] for v in result.values())>=math.ceil(.75*n) else 'NOT MET','falsifier':sum(v['normal_AUROC']<.65 for v in result.values())>=math.ceil(.5*n),'normal_arm_only':True,'rows_required':math.ceil(.75*n)}

def run(spec):
 s=read(spec);command=read(HERE/'E69_ANALYSIS_COMMAND.json');require(sha(spec)==command['spec_sha256'],'once-only spec pin');verify(HERE,'SOURCE_SEAL.json',command['source_seal_sha256']);require(sha(s['request'])==s['request_sha256'],'request pin');r=read(s['request']);require(sha(s['private_labels'])==s['private_labels_sha256'],'CPU private labels pin');labels={x['id']:x['label'] for x in read(s['private_labels'])};receipt=read(s['receipt']);require(receipt['verified'] is True and len(receipt['shards'])==len(r['shards']),'verified exact pull');records=[]
 for sh in r['shards']:
  rec=receipt['shards'][str(sh['shard'])];out=Path(rec['output']);o=verify(out,'OUTPUT_SEAL.json',rec['output_seal_sha256']);require(o['status']=='COMPLETE' and o['source_seal_sha256']==r['source_seal_sha256'] and o['input_seal_sha256']==sh['input_seal_sha256'] and o['experiment']=='E69','output identity');xs=read(out/'RECORDS.json');require({x['id'] for x in xs}==set(sh['item_ids']) and len(xs)==len(sh['item_ids']),'shard exact grid');records+=xs
 require(len(records)==len(labels) and {x['id'] for x in records}==set(labels),'complete labelled grid');out=Path(s['out']);out.mkdir(parents=True,exist_ok=False);dump(out/'ONCE_ONLY.json',dict(spec_sha256=sha(spec)));result=rules(records,labels);dump(out/'RESULTS.json',result);(out/'RESULTS.md').write_text('# E69\n\nR-B1: '+result['R_B1']+'\nFalsifier: '+str(result['falsifier'])+'\n');seal(out,'ANALYSIS_SEAL.json',dict(experiment='E69',request_sha256=sha(s['request']),receipt_sha256=sha(s['receipt'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--spec',type=Path,required=True);run(p.parse_args().spec)
