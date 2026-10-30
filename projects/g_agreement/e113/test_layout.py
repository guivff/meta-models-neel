import numpy as np
from projects.g_agreement.e101.contract import sha,write,read
from projects.g_agreement.e113.layout import export


def test_mixed_capture_batches_are_losslessly_separated_for_dev_only_fit(tmp_path):
    source=tmp_path/'source';source.mkdir();a=np.arange(4*3*2*4,dtype=np.float32).reshape(4,3,2,4)
    np.save(source/'mixed.npy',a,allow_pickle=False)
    xs=[dict(id=str(i),row='row',split='dev' if i%2==0 else 'test',member='mixed.npy',vector_index_in_file=i) for i in range(4)]
    write(source/'INDEX.json',xs);write(source/'OUTPUT_SEAL.json',dict(experiment='E113',status='COMPLETE',files={'mixed.npy':sha(source/'mixed.npy'),'INDEX.json':sha(source/'INDEX.json')}))
    out=tmp_path/'layout';export(source,sha(source/'OUTPUT_SEAL.json'),out)
    assert np.array_equal(np.load(out/'row_dev.npy'),a[[0,2]])
    assert np.array_equal(np.load(out/'row_test.npy'),a[[1,3]])
    assert read(out/'LAYOUT_SEAL.json')['bit_identical_items']==4
