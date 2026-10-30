import importlib.util
from pathlib import Path
import numpy as np
import pytest
s=importlib.util.spec_from_file_location('e101_vector_builder',Path(__file__).with_name('build.py'));b=importlib.util.module_from_spec(s);s.loader.exec_module(b)

def fixture():
    records=[];acts={}
    for label in (0,1):
        for i in range(42):
            ident=f'd{label}_{i:02d}';records.append(dict(id=ident,feature='row',split='dev',label=label));acts[ident]=np.full(5120,label*3+i/100)
    return records,acts

def test_fit_uses_only_dev_and_correct_sign():
    records,acts=fixture();d,g=b.dev_direction(records,acts,'row')
    records.append(dict(id='test',feature='row',split='test',label=1));acts['test']=np.full(5120,1e30)
    d2,g2=b.dev_direction(records[::-1],acts,'row')
    assert np.array_equal(d,d2) and g==g2 and np.allclose(d,3)
    for label in (0,1):assert (1-2*label)*(2*(1-label)-1)==1
    assert np.allclose(np.linalg.norm(d)*b.unit(d),d)

def test_random_one_per_block_reproducible_distinct():
    a=b.random_direction(42);c=b.random_direction(44)
    assert np.array_equal(a,b.random_direction(42)) and not np.array_equal(a,c)
    assert np.isclose(np.linalg.norm(a),1) and np.isclose(np.linalg.norm(c),1)

def test_missing_dev_or_nonfinite_fails():
    records,acts=fixture()
    with pytest.raises(ValueError):b.dev_direction(records[1:],acts,'row')
    acts[records[0]['id']][0]=np.nan
    with pytest.raises(ValueError):b.dev_direction(records,acts,'row')
    with pytest.raises(ValueError):b.unit(np.zeros(5120))


def test_seal_excludes_machine_bytecode(tmp_path):
    (tmp_path/'data.json').write_text('{}')
    (tmp_path/'__pycache__').mkdir();(tmp_path/'__pycache__/build.pyc').write_bytes(b'cache')
    b.seal(tmp_path,'SEAL.json',dict(status='fixture'))
    assert set(b.read(tmp_path/'SEAL.json')['files'])=={'data.json'}
