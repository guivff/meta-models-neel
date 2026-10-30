from pathlib import Path
import json,shutil
import numpy as np
from projects.g_agreement.understand.core import load_w1
from projects.g_agreement.understand.e32 import donors
from projects.g_agreement.blindspot import protocol as P
R=Path('results/g_agreement/understand/e32');B=Path('cache/g_agreement/understand/e32-stage-v1');B.mkdir(exist_ok=False)
wtext=Path('../wt-wtext/results/g_agreement/understand/e25');summary=json.loads((wtext/'analysis_0jexpj58lbtuk9/SUMMARY.json').read_text())
seal=json.loads((wtext/'analysis_0jexpj58lbtuk9/ANALYSIS_SEAL.json').read_text());assert P.sha(wtext/'analysis_0jexpj58lbtuk9/SUMMARY.json')==seal['files']['SUMMARY.json']
refs={x['feature']:{k:x[k] for k in ('D','class')} for x in summary['rows']}
items,acts,specs=load_w1();ix=[i for i,x in enumerate(items) if x['split']=='test' and x['feature'] in refs];chosen=[items[i] for i in ix]
assert len(chosen)==2100
source=Path('../wt-blindspot-internals/results/g_agreement/understand/e30/CANDIDATES.json');assert P.sha(source)=='f0632205097de5b5c7cd695a2c3a235fb4136e2e11cbf5034606a00387960b12'
c=json.loads(source.read_text())['candidates'];pairs={'w1':{f:specs[f]['olens'] for f in refs},'e30':{f:c[f] for f in refs}}
P.jsonl(B/'items.jsonl',[{k:x[k] for k in ('id','feature','text','ids','cluster')}|{'label':int(x['value']==specs[x['feature']]['values'][0])} for x in chosen])
P.dump(B/'pairs.json',pairs);P.dump(B/'DONORS.json',donors(chosen));P.dump(B/'references.json',refs);np.save(B/'reference44.npy',np.asarray(acts[44][ix]))
P.seal(B,['items.jsonl','pairs.json','DONORS.json','references.json','reference44.npy'],'FROZEN_BEFORE_CAPTURE')
for n in ('DONORS.json','pairs.json','references.json','INPUT_SEAL.json'):shutil.copyfile(B/n,R/n)
high=[f for f,r in refs.items() if r['class']=='structure' and r['D']>=.7];assert len(high)==8,high
P.dump(R/'PREPARE_RECEIPT.json',{'items':2100,'rows':25,'high_D_rows':high,'e25_analysis_seal_sha256':P.sha(wtext/'analysis_0jexpj58lbtuk9/ANALYSIS_SEAL.json'),'e30_candidate_sha256':P.sha(source),'w1_activation_manifest_sha256':P.sha('results/g_agreement/blindspot/w1/analysis/activations.json'),'input_seal_sha256':P.sha(B/'INPUT_SEAL.json'),'labels':'W1 original labels permitted for gate and fixed donor groups only','placeholder':'_','placeholder_token_id':62,'frame':'E25 encode_frame verbatim; no extra BOS beyond E25 actual tokenizer behavior','B':'replace placeholder output at every decoder block >=44 with source h44','Bprime':'replace placeholder output at each decoder block with source residual from that block'})
print('Staged 2100 exact W1 test items,25 rows,8 high-D rows; donor maps frozen')
