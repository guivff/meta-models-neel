import pytest
from projects.g_agreement.ops.i5_e97_row_metrics import row_metrics

def fixture():
 meta={str(r):dict(taxonomy='continuation constraint'if r<20 else'numerical coordinate')for r in range(40)}
 forecast={str(r):dict(label='IN-J'if r<20 else'DIFFUSE',oracle_prediction='REPORTED'if r<20 else'MISSED',nla_prediction='REPORTED'if r<20 else'MISSED')for r in range(40)}
 records=[]
 for reader in ['oracle','nla']:
  for r in range(40):
   for i in range(84):
    label='A'if i%2 else'B';value=label if reader=='oracle'else('B'if label=='A'else'A')
    records.append(dict(id=f'{reader}:{r}:{i}',reader=reader,row=str(r),label=label,code=dict(category='states_value',values=[value],id=f'{reader}:{r}:{i}',evidence='SYNTHETIC')))
 return records,meta,forecast

def test_exact_polarity_and_reader_separation():
 a,m,f=fixture();v=row_metrics(a,m,f)
 assert len(v['oracle'])==len(v['nla'])==40
 assert all(r['S']==1 and r['reported']for r in v['oracle'])
 assert all(r['S']==-1 and not r['reported']for r in v['nla'])
def test_excluded_whole_row_retained_as_undefined_truth():
 a,m,f=fixture();excluded=[x['id']for x in a if x['reader']=='oracle'and x['row']=='0'];v=row_metrics(a,m,f,excluded);r=next(x for x in v['oracle']if x['row']=='0')
 assert len(v['oracle'])==40 and r['S']is None and r['reported']is None and r['included_items']==0 and r['excluded_affected']==84

def test_full_grid_no_drop_and_frozen_label_required():
 a,m,f=fixture()
 with pytest.raises(ValueError):row_metrics(a[:-1],m,f)
 a[0]['label']='0'
 with pytest.raises(ValueError):row_metrics(a,m,f)
def test_all_missing_never_silent_or_missed():
 a,m,f=fixture()
 for x in a:
  if x['reader']=='nla'and x['row']=='0':x['code']=dict(category='UNPARSEABLE',values=[],evidence='',id=x['id'])
 v=row_metrics(a,m,f);r=next(x for x in v['nla']if x['row']=='0');assert r['reported']is None and r['S']is None and r['UNPARSEABLE']==84

def test_original_rubric_exact_matched_subset():
 from projects.g_agreement.ops.i5_e97_row_metrics import old_rubric_summary
 a,m,f=fixture()
 for x in a:x['code_source']='judge'
 old=[dict(x['code'],values=['B'if x['label']=='A'else'A'])for x in a[:1667]]
 r=old_rubric_summary(a,old);assert r['retained_items']==1667 and len(r['rows'])==80
 row=next(x for x in r['rows']if x['reader']=='oracle'and x['row']=='0');assert row['amended_matched']['S']==1 and row['original_matched']['S']==-1
 excluded={x['id']for x in a[:84]};r=old_rubric_summary(a,old,excluded);assert r['retained_items']==1583 and r['excluded_affected']==84
 with pytest.raises(ValueError):old_rubric_summary(a,old[:-1])
