import copy,hashlib,json,unittest
from amendment110 import bind_quarter,quarter_ids,validate_outputs,sealed_member_path
class QuarterTests(unittest.TestCase):
 def fixture(self):
  items=[dict(id=str(i),onehop_job_ids=['j'],twohop_job_id='k') for i in range(4)]
  jobs=[dict(id=j,prompt=j,input_ids=[1,2],read_position=1) for j in ['j','k']]
  quarter=quarter_ids(items)[0];subset=[x for x in items if x['id'] in quarter]
  cw=dict(shard=0,original_candidate_ids=sorted(quarter),quarter_items=subset,original_job_to_shard_job=dict(j='q0j',k='q0k'))
  public=[dict(x,id=cw['original_job_to_shard_job'][x['id']]) for x in jobs]
  return items,jobs,quarter,cw,public
 def test_exact_binding(self):
  i,j,q,c,p=self.fixture();s,m=bind_quarter(i,j,q,c,p,0);self.assertEqual(len(s),1);self.assertEqual(m,c['original_job_to_shard_job'])
 def test_changed_prompt_rejected(self):
  i,j,q,c,p=self.fixture();p[0]['prompt']='changed'
  with self.assertRaises(ValueError):bind_quarter(i,j,q,c,p,0)
 def test_changed_label_or_quarter_rejected(self):
  i,j,q,c,p=self.fixture();c['quarter_items']=copy.deepcopy(c['quarter_items']);c['quarter_items'][0]['new_label']='invented'
  with self.assertRaises(ValueError):bind_quarter(i,j,q,c,p,0)
  i,j,q,c,p=self.fixture();c['shard']=1
  with self.assertRaises(ValueError):bind_quarter(i,j,q,c,p,0)
 def test_missing_and_duplicate_scoped_outputs_rejected(self):
  _,jobs,_,cw,_=self.fixture();data=[dict(id='q0'+j,raw='Answer',token_ids=[7],finish_reason='eos',max_new_tokens=16,do_sample=False,input_ids_sha256=hashlib.sha256(json.dumps([1,2]).encode()).hexdigest()) for j in ['j','k']]
  result=validate_outputs(data,cw['original_job_to_shard_job'],jobs);self.assertEqual(set(result),{'j','k'})
  for bad in [data[:1],data+[data[0]], [dict(x,input_ids_sha256='bad') for x in data]]:
   with self.assertRaises(ValueError):validate_outputs(bad,cw['original_job_to_shard_job'],jobs)
 def test_same_original_job_different_quarter_stays_local(self):
  _,jobs,_,cw,_=self.fixture();base=dict(raw='First',token_ids=[7],finish_reason='eos',max_new_tokens=16,do_sample=False,input_ids_sha256=hashlib.sha256(json.dumps([1,2]).encode()).hexdigest())
  a=validate_outputs([dict(base,id='q0'+x) for x in ['j','k']],cw['original_job_to_shard_job'],jobs)
  b=validate_outputs([dict(base,id='q1'+x,raw='Second') for x in ['j','k']],dict(j='q1j',k='q1k'),jobs)
  self.assertEqual(a['j']['raw'],'First');self.assertEqual(b['j']['raw'],'Second')
 def test_worker_assignment_not_staging_and_no_path_escape(self):
  self.assertEqual(str(sealed_member_path('/published','/private','ASSIGNMENT.json')),'/private/terminal_pull/outputs/ASSIGNMENT.json')
  self.assertEqual(str(sealed_member_path('/published','/private','batches/000000.json')),'/published/batches/000000.json')
  for bad in ['/absolute','../escape']:
   with self.assertRaises(ValueError):sealed_member_path('/published','/private',bad)
if __name__=='__main__':unittest.main()
