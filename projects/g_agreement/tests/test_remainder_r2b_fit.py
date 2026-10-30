import numpy as np
import pytest
from projects.g_agreement.r_bench import remainder_r2b_fit as F,remainder_r2b_runner as R,remainder_r2b as D


def fixture_records(tmp_path):
    rng=np.random.default_rng(3);cells=[];vectors={}
    for split,n in [('pool',40),('test',8)]:
        for i in range(n):
            cell=dict(item_id=f'{split}-{i}',dataset='family',split=split,arm='natural',label=i%2,
                      probe_group=f'{split}-g{i//4}',tap_blocks=[2])
            cells.append(cell);v=rng.normal(0,.05,4);v[0]+=3*(i%2);vectors[R.cell_key(cell)]=v.astype(np.float16)
    w=R.RunWriter(tmp_path,dict(cells=cells),D.stamp('synthetic','a','a'*64,'test'))
    for c in cells:w.append(c,{}, {2:vectors[R.cell_key(c)]})
    w.finish();return w,cells


def test_fit_roundtrip_and_test_label_does_not_select_fit(tmp_path):
    w,cells=fixture_records(tmp_path);records=F.read_process(w.root,'test')
    job=dict(job_id='family',block=2,train=[R.cell_key(c) for c in cells if c['split']=='pool'],evaluate=[R.cell_key(c) for c in cells if c['split']=='test'])
    fits,rows=F.fit_jobs([job],records,lambda:None)
    assert all(r['prediction']==r['label'] for r in rows)
    for key in job['evaluate']:records[key][1]['cell']['label']^=1
    fits2,_=F.fit_jobs([job],records,lambda:None)
    assert fits2==fits


def test_process_extra_file_decoy(tmp_path):
    w,_=fixture_records(tmp_path);(w.root/'decoy').write_text('x')
    with pytest.raises(ValueError,match='decoy'):F.read_process(w.root,'test')


def test_fit_nonpool_decoy(tmp_path):
    w,cells=fixture_records(tmp_path);records=F.read_process(w.root,'test');keys=list(records)
    records[keys[0]][1]['cell']['split']='decoy-test'
    job=dict(job_id='decoy-fit',block=2,train=keys[:40],evaluate=keys[40:])
    with pytest.raises(ValueError,match=keys[0]):F.fit_jobs([job],records,lambda:None)


def test_fit_missing_decoy(tmp_path):
    with pytest.raises(ValueError,match='decoy-missing'):
        F.fit_jobs([dict(job_id='j',block=2,train=['decoy-missing'],evaluate=['x'])],{},lambda:None)
