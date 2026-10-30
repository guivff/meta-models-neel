import json
from pathlib import Path
import pytest
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.understand.e24_once149 import verified_outputs,run


def test_missing_admitted_shard_rejected(tmp_path):
    plan=tmp_path/'plan';plan.write_text('{}');out=tmp_path/'slot0';out.mkdir()
    P.dump(out/'ADMISSION.json',{'pods':[{},{}]});P.dump(out/'FORECAST.json',{'slot':0})
    P.dump(out/'SCORE_SEAL.json',{'files':{'ADMISSION.json':P.sha(out/'ADMISSION.json'),'FORECAST.json':P.sha(out/'FORECAST.json')}})
    receipt=tmp_path/'receipt';P.dump(receipt,{'issuer':'integrator','verified':True,'experiment':'E24','plan_sha256':P.sha(plan),'shards':[{'slot':0,'path':str(out),'score_seal_sha256':P.sha(out/'SCORE_SEAL.json')}]})
    with pytest.raises(ValueError,match='missing admitted'):verified_outputs({'verified_receipt':str(receipt),'plan':str(plan),'delivery_paths':[str(out)]})


def test_failure_retains_guard(tmp_path):
    spec=tmp_path/'spec';lock=tmp_path/'lock';P.dump(spec,{'lock':str(lock),'out':str(tmp_path/'out'),'pins':{},'verified_receipt':str(tmp_path/'missing')})
    with pytest.raises(FileNotFoundError):run(spec,P.sha(spec))
    with pytest.raises(FileExistsError):run(spec,P.sha(spec))
