import hashlib
import json
import subprocess
import pytest
from .bank_gate import BANKS, forecast_gate, budget_gate


def test_daily_reservation_not_just_old_balance():
    receipt = dict(issuer='integrator', verified=True, date_zurich='2026-10-27',
                   allocation_id='synthetic', banks=list(BANKS), reservation_included=True,
                   reserved_judging_usd='15', daily_committed_including_reservation_usd='300')
    assert budget_gate(receipt) == 'synthetic'
    assert budget_gate(dict(receipt, daily_committed_including_reservation_usd='232.16')) == 'synthetic'
    for change in [dict(reservation_included=False), dict(daily_committed_including_reservation_usd='300.01'),
                   dict(reserved_judging_usd='16'), dict(banks=['E56']), dict(date_zurich='2026-10-26')]:
        with pytest.raises(ValueError):
            budget_gate(dict(receipt, **change))


def test_forecast_commit_binding_and_placeholder_rejection(tmp_path):
    def git(*args):
        return subprocess.check_output(['git', '-C', str(tmp_path), *args])
    git('init', '-q')
    data = dict(experiment='E52_R3b', bank='E56', reader_outcomes_accessed=False,
                no_backfill=True, rows=[{'row': 'synthetic'}], bank_seal_sha256='bank', capture_seal_sha256='capture')
    p = tmp_path/'forecast.json';p.write_text(json.dumps(data))
    git('add', 'forecast.json')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'synthetic forecast')
    commit = git('rev-parse', 'HEAD').decode().strip()
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert forecast_gate('E56', tmp_path, commit, 'forecast.json', digest)['bank'] == 'E56'
    with pytest.raises(ValueError):
        forecast_gate('E57', tmp_path, commit, 'forecast.json', digest)
    p.write_text(json.dumps(dict(data, not_a_W_lens_forecast=True, experiment='binding')))
    with pytest.raises(ValueError):
        forecast_gate('E56', tmp_path, commit, 'forecast.json', digest)


def test_placebo_requires_separate_committed_forecast(tmp_path):
    def git(*args):return subprocess.check_output(['git','-C',str(tmp_path),*args])
    git('init','-q')
    data=dict(experiment='E52_R3b',bank='E62_PLACEBO',reader_outcomes_accessed=False,
              no_backfill=True,rows=[{}],bank_seal_sha256='placebo',capture_seal_sha256='placebo_capture')
    p=tmp_path/'forecast.json';p.write_text(json.dumps(data));git('add','forecast.json')
    git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','placebo')
    commit=git('rev-parse','HEAD').decode().strip();digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert forecast_gate('E62P',tmp_path,commit,'forecast.json',digest)['bank']=='E62P'
    with pytest.raises(ValueError):forecast_gate('E62',tmp_path,commit,'forecast.json',digest)


def test_e63_no_implicit_forecast_exception(tmp_path):
    from .bank_gate import coordinator_gate
    def git(*args):return subprocess.check_output(['git','-C',str(tmp_path),*args])
    git('init','-q')
    d=dict(experiment='E63',status='RATIFIED',forecast_required=False,ratified_by='synthetic coordinator',
           committed_before_any_reader_output=True,bank_seal_sha256='b',capture_seal_sha256='c')
    p=tmp_path/'record.json';p.write_text(json.dumps(d));git('add','record.json')
    git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','synthetic ruling')
    commit=git('rev-parse','HEAD').decode().strip();digest=hashlib.sha256(p.read_bytes()).hexdigest()
    assert coordinator_gate('E63',tmp_path,commit,'record.json',digest)['bank']=='E63'
    with pytest.raises(ValueError):coordinator_gate('E59',tmp_path,commit,'record.json',digest)
    p.write_text(json.dumps(dict(d,status='PROVISIONAL')))
    with pytest.raises(ValueError):coordinator_gate('E63',tmp_path,commit,'record.json',digest)
