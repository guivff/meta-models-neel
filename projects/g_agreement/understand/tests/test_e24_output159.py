import json
import numpy as np
import pytest
from types import SimpleNamespace
from pathlib import Path
from projects.g_agreement.understand.e24_relaunch_analysis import dump_output,analyse

def test_numpy_output(tmp_path):
    p=tmp_path/'x';dump_output(p,{'a':np.bool_(True),'b':[np.int64(2),np.float64(.5)],'n':None})
    assert json.loads(p.read_text())=={'a':True,'b':[2,.5],'n':None}

def test_reject_public_output(tmp_path):
    with pytest.raises(ValueError,match='cache'):analyse(SimpleNamespace(out=tmp_path/'public'))
