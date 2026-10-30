"""Metadata-only E113 first-token descriptive control. Never loads activations."""
import collections, hashlib, json
from pathlib import Path
BASE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/outputs')
OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
layout=BASE/'e113-run-v2/split_layout';raw=BASE/'e113-run-v2/pull';lab=BASE/'e113-inputs-v1/cpu_only'
pins={}
for folder,sealname,names in [(layout,'LAYOUT_SEAL.json',['ORDER.json']),(lab,'LABEL_SEAL.json',['LABELS.json']),(raw,'OUTPUT_SEAL.json',['INDEX.json'])]:
 seal=json.loads((folder/sealname).read_text());pins[str(folder/sealname)]=sha(folder/sealname)
 for name in names:
  p=folder/name;assert sha(p)==seal['files'][name],name;pins[str(p)]=sha(p)
order=json.loads((layout/'ORDER.json').read_text());labels={x['id']:x for x in json.loads((lab/'LABELS.json').read_text())}
index=json.loads((raw/'INDEX.json').read_text());index={x['id']:x for x in index}
rows={}
for row in ['nesting_depth','indent_level','page_range_digit']:
 result={};tokens=[]
 for split in ['dev','test']:
  items=order[row+':'+split];assert len(items)==84
  counts={}
  for c in [0,1]:
   group=[]
   for x in items:
    assert x==index[x['id']]
    y=labels[x['id']];assert y['row']==row and y['split']==split
    if y['label']==c:group.append(x['first_token_id'])
   assert len(group)==42;counts[str(c)]=dict(sorted(collections.Counter(group).items()));tokens+=group
  result[split]=counts
 if len(set(tokens))!=1:raise RuntimeError('Variable ID: separate frozen dev classifier implementation required before any fit/test')
 rows[row]={'constant_across_all_168':True,'token_id':tokens[0],'distribution_by_split_and_value_class':result,'classifier_status':'NOT_FIT_CONSTANT_TOKEN_ID','ID_only_constant_score_AUROC_by_definition':0.5}
v={'status':'DESCRIPTIVE_COMPLETE','rows':rows,'source_pins':pins,'registered_probe_refits':0,'test_AUROC_evaluations':0,'activation_array_loads':0,'gpu_hours':0,'posthoc':True}
(OUT/'RESULTS.json').write_text(json.dumps(v,indent=2,sort_keys=True)+'\n')
lines=['# E113 first-token-ID descriptive control','','All three bookkeeping rows have constant first-token ID **12** across all168 items per row. Counts below retain the original value-class orientation.','','| Row | Dev class0 | Dev class1 | Test class0 | Test class1 |','|---|---|---|---|---|']
for row in rows:lines.append('| '+row+' | ID12:42/42 | ID12:42/42 | ID12:42/42 | ID12:42/42 |')
lines+=['','No one-hot classifier was fit: every row meets the requested constant-token condition. An ID-only constant score has AUROC0.5 by definition; this is not an empirical fitted classifier result.','','Because token identity, position and its token embedding are constant across items, variation in the first token’s own embedding cannot by itself explain first-generated-token hidden-state AUROC1.00. The contextual hidden state may still carry injected/contextual information; this control does not establish unassisted reader knowledge or causal localization.','','Original registered probes/results/guards are unchanged. This is a posthoc metadata-only control, no activation loads/refits/retests/GPU/API. Injected-slot maxima include the reader’s own input. Original kernel preceded capture; exact final binder was finalized after capture and committed before the CPU claim. R-4 owns independent review under §227.','']
(OUT/'REPORT.md').write_text('\n'.join(lines))
(OUT/'SEAL.json').write_text(json.dumps({'status':'SEALED_METADATA_DESCRIPTIVE','files':{n:sha(OUT/n) for n in ['PLAN.md','count_tokens.py','RESULTS.json','REPORT.md']}},indent=2)+'\n')
print(json.dumps(rows,indent=2))
