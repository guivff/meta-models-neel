import json
from pathlib import Path
import tarfile
import pytest
import rebind_batch as R


def test_production_seeds_and_profile_flag(tmp_path,monkeypatch):
    source=tmp_path/'source';source.mkdir();root=tmp_path/'root';root.mkdir()
    (source/'stub.py').write_text('pass\n');R.write(source/'DEPENDENCIES.json',{})
    R.seal(source,'SOURCE_SEAL.json')
    # Package builder normally seals repository-relative files.
    monkeypatch.setattr(R,'HERE',source);monkeypatch.setattr(R,'ROOT',tmp_path)
    monkeypatch.setattr(R,'validate',lambda x:None)
    inp=tmp_path/'old'/'inputs';inp.mkdir(parents=True)
    R.write(inp/'PUBLIC_INPUTS.json',[])
    R.write(inp/'STAGE_REQUEST.json',dict(seed_seconds_per_batch={'base_text128':99,'base_text32':99}))
    ih=R.seal(inp,'INPUT_SEAL.json')
    archive=tmp_path/'old.tar.gz'
    with tarfile.open(archive,'w:gz') as tar:tar.add(inp,arcname='inputs')
    old=tmp_path/'REQUEST.json'
    R.write(old,dict(input_archive=str(archive),input_archive_sha256=R.sha(archive),input_seal_sha256=ih,
        argv=['python','worker81.py','--source-sha','old','--input-sha','old','--profile-only']))
    profile=tmp_path/'profile';profile.mkdir()
    R.write(profile/'MEASURED_PROFILE.json',dict(status='TIMING_ONLY_NOT_SCIENCE',batches_per_phase=3,parity_items_per_phase=8,forecast_seconds=200))
    R.write(profile/'PHASE_TIMINGS.json',[dict(phase=p,seconds=n,status='COMPLETE',real=True) for p,n in [('base_text128',4),('base_text32',2)] for _ in range(3)])
    R.seal(profile,'OUTPUT_SEAL.json',status='PROFILE_ONLY',synthetic=False)
    out=tmp_path/'new';R.build(old,out,250,False,profile/'MEASURED_PROFILE.json',profile/'PHASE_TIMINGS.json',profile/'OUTPUT_SEAL.json')
    assert '--profile-only' not in R.read(out/'REQUEST.json')['argv']
    assert R.read(out/'inputs/STAGE_REQUEST.json')['seed_seconds_per_batch']==dict(base_text128=4.,base_text32=2.)
    (profile/'PHASE_TIMINGS.json').write_text('[]')
    with pytest.raises(ValueError,match='pull binding'):
        R.build(old,tmp_path/'bad',250,False,profile/'MEASURED_PROFILE.json',profile/'PHASE_TIMINGS.json',profile/'OUTPUT_SEAL.json')
