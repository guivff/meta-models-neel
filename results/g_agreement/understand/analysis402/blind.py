"""Unchanged frozen judge packets with new verified-union custody, no judge API calls."""
from data import *
from missingness import validate_judgment

def prepare(spec,e,data):
 rows=list(data['native']);rng=np.random.default_rng(20261027 if e.startswith('E62') else 20261026);rng.shuffle(rows);packet=[];evals=[];key=[];inp=Path(spec['inputs'])
 if e=='E56':defs=read(inp/'ROW_DEFINITIONS.json')['rows'];inj=read(inp/'injection/PLAN.json')['rows']
 for x in rows:
  opaque=rng.bytes(16).hex();entry={'id':opaque,'readout':x['text']};is_eval=e=='E62' and data['private'][x['unit_id']]['state']=='S6'
  if is_eval:evals.append(entry)
  else:
   if e=='E56':values=defs[x['feature']]['values'] if x['kind']=='text' else inj[x['feature']];prop=x['feature']
   elif e=='E57':values=data['plan']['judge_values'][x['unit_id']];prop=data['plan']['rows'][x['feature']]['canonical_row']
   else:
    prop=x['feature'];by={lab:sorted({z['value'] for z in data['private'].values() if z['feature']==prop and z['label']==lab}) for lab in (0,1)};require(all(len(v)==1 for v in by.values()),'one A/B value per frozen row');values=[by[1][0],by[0][0]]
   entry.update(property=prop,values={'A':values[0],'B':values[1]});packet.append(entry)
  key.append({'opaque_id':opaque,'source_id':x['id'],'unit_id':x['unit_id'],'eval':is_eval})
 out=Path(spec['blind_out']);out.mkdir(parents=True,exist_ok=False);dump(out/'JUDGE_PACKET.json',packet);dump(out/'EVAL_PACKET.json',evals);dump(Path(spec['private_key']),key)
 seal(out,'BLIND_SEAL.json',{'experiment':e,'source_seal_sha256':spec['source_seal_sha256'],'input_seal_sha256':spec['input_seal_sha256'],'receipt_sha256':sha(spec['receipt']),'private_key_sha256':sha(spec['private_key']),'rubric_sha256':sha(U/'e56/job/JUDGE_RUBRIC.md'),'eval_rubric_sha256':sha(U/'e62/job/S6_RUBRIC.md'),'cohort_id':COHORT,'acquisition_lineage':data['lineage']})

def judgments(spec,data):
 root=Path(spec['blind_out']);b=verify(root,'BLIND_SEAL.json');require(b['receipt_sha256']==sha(spec['receipt']) and b['input_seal_sha256']==spec['input_seal_sha256'] and b['private_key_sha256']==sha(spec['private_key']) and b['cohort_id']==COHORT,'blind custody');require(b['rubric_sha256']==sha(U/'e56/job/JUDGE_RUBRIC.md') and b['eval_rubric_sha256']==sha(U/'e62/job/S6_RUBRIC.md'),'frozen rubrics')
 packets=read(root/'JUDGE_PACKET.json')+read(root/'EVAL_PACKET.json');packet={x['id']:x for x in packets};key=read(spec['private_key']);native={x['id']:x for x in data['native']};unique_grid(key,lambda x:x['source_id'],native,'blind source grid');unique_grid(key,lambda x:x['opaque_id'],packet,'blind opaque grid')
 js=Path(spec['judgments']);s=verify(js.parent,Path(spec.get('judgment_seal',js.parent/'JUDGMENT_SEAL.json')).name);require(s['blind_seal_sha256']==sha(root/'BLIND_SEAL.json'),'judgment source');jj=read(js);unique_grid(jj,lambda x:x['id'],packet,'complete judgment grid');by={x['id']:x for x in jj};out={}
 for k in key:
  x=native[k['source_id']];require(packet[k['opaque_id']]['readout']==x['text'],'unaltered text');j=by[k['opaque_id']]
  if k['eval']:require(type(j['eval_mention']) is bool and isinstance(j['evidence'],str) and j['evidence'] in x['text'] and bool(j['evidence'])==j['eval_mention'],'S6 blind coding')
  else:validate_judgment(j,x['text'])
  out[x['id']]=j
 return out
