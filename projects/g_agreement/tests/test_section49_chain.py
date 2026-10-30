"""Real CPU subprocess chain + automatic collector; no model/GPU/network calls."""
import json,os,subprocess,sys,time
from pathlib import Path
import pytest
from projects.g_agreement.r_bench import section49_supervisor as S
from projects.g_agreement.r_bench import section49_collector as C

REPO=Path(__file__).resolve().parents[3]

def run_chain(tmp_path,kind):
    root=tmp_path/'pod';root.mkdir();(root/'bytes').mkdir();out=root/'output';out.mkdir()
    script=tmp_path/'fake.py'
    script.write_text('''import sys,time,hashlib,json
from pathlib import Path
root=Path(sys.argv[1]); stage=sys.argv[2]; kind=sys.argv[3]
with (root/'output/order.txt').open('a') as f:f.write(stage+'\\n')
if stage=='download':
 if kind=='stall':time.sleep(20)
 else:
  for i in range(12):
   with (root/'bytes/data').open('ab') as f:f.write(b'x'*1024)
   time.sleep(.06)
if stage=='hash-check' and kind=='bad-hash':sys.exit(9)
if stage=='hash-check':assert (root/'bytes/data').read_bytes()==b'x'*(12*1024)
if stage=='projection' and kind=='reject':sys.exit(7)
if stage=='full':(root/'output/results.json').write_text('{"fake": true}')
''')
    now=time.time();cfg={'root':str(root),'cwd':str(REPO),'pod_id':'fake-pod','test_mode':True,'created_epoch':now,'deadline':now+12,'pull_reserve_s':3,'stall_s':.35,'poll_s':.02,'steps':[]}
    for name in ['download','hash-check','staging','smoke','projection','full']:
        cfg['steps'].append({'name':name,'argv':[sys.executable,str(script),str(root),name,kind],**({'byte_roots':[str(root/'bytes')]} if name=='download' else {})})
    S.save(root/'cfg.json',cfg)
    c={'root':str(root),'local':str(tmp_path/'mac'),'local_transport':True,'pod_id':'fake-pod','deadline':now+12,'poll_s':.02,'log_interval_s':.15}
    S.save(root/'collector.json',c)
    env=dict(os.environ,PYTHONPATH=str(REPO))
    supervisor=subprocess.Popen([sys.executable,'-m','projects.g_agreement.r_bench.section49_supervisor',str(root/'cfg.json')],cwd=REPO,env=env)
    collector=subprocess.Popen([sys.executable,'-m','projects.g_agreement.r_bench.section49_collector',str(root/'collector.json')],cwd=REPO,env=env)
    try:
        rc=supervisor.wait(timeout=15); cc=collector.wait(timeout=15)
    finally:
        for p in [supervisor,collector]:
            if p.poll() is None:p.kill();p.wait()
    return root,tmp_path/'mac',rc,cc

def test_chain_success_fake_download_through_verified_pull(tmp_path):
    root,mac,rc,cc=run_chain(tmp_path,'ok')
    assert rc==cc==0
    assert (mac/'final/order.txt').read_text().splitlines()==['download','hash-check','staging','smoke','projection','full']
    assert S.read(mac/'final/release.json')['status']=='VERIFIED_READY_TO_STOP'
    assert S.read(mac/'stop.json')['status']=='EXITED'
    assert S.read(mac/'log_pull_receipt.json')['snapshots']>=3
    assert (mac/'final/activity_bytes.txt').stat().st_size>0
    assert not (mac/'final/bytes').exists()

def test_stalled_download_closes_partial_and_pulls(tmp_path):
    root,mac,rc,cc=run_chain(tmp_path,'stall')
    assert rc==1 and cc==0
    report=S.read(mac/'final/chain_result.json')
    assert 'No download/staging byte growth' in report['error']
    assert (mac/'final/order.txt').read_text().splitlines()==['download']
    assert S.read(mac/'final/release.json')['status']=='VERIFIED_READY_TO_STOP'

def test_projection_rejection_never_starts_full(tmp_path):
    root,mac,rc,cc=run_chain(tmp_path,'reject')
    assert rc==1 and cc==0
    assert 'full' not in (mac/'final/order.txt').read_text().splitlines()
    assert not (mac/'final/results.json').exists()

def test_corrupt_pull_cannot_release(tmp_path):
    p=tmp_path/'x';p.write_text('original');S.package(tmp_path);p.write_text('corrupt')
    with pytest.raises(ValueError):S.receipt(tmp_path)

def test_no_receipt_stays_unreleased(tmp_path):
    root=tmp_path/'pod';root.mkdir();S.save(root/'cfg.json',{'root':str(root),'cwd':str(REPO),'pod_id':'fake','test_mode':True,'deadline':time.time()+.1,'pull_reserve_s':1,'steps':[]})
    assert S.supervise(S.read(root/'cfg.json'))==2
    assert not (root/'output/release.json').exists()
    assert S.read(root/'control/state.json')['state']=='PULL_FAILED'


def test_hash_failure_never_reaches_smoke(tmp_path):
    root,mac,rc,cc=run_chain(tmp_path,'bad-hash')
    assert rc==1 and cc==0
    assert (mac/'final/order.txt').read_text().splitlines()==['download','hash-check']
    assert S.read(mac/'final/release.json')['status']=='VERIFIED_READY_TO_STOP'

def test_retained_bytes_must_match_returned_receipt(tmp_path):
    p=tmp_path/'artifact';p.write_text('ok');S.package(tmp_path);S.receipt(tmp_path)
    p.write_text('changed remotely')
    with pytest.raises(ValueError,match='Retained'):S.release(tmp_path)

def test_production_chain_keeps_frozen_phases_and_cap(tmp_path):
    from projects.g_agreement.r_bench.section49_deploy import build
    now=time.time();b={'pod_id':'new-pod','created_epoch':now,'deadline':now+9000,'cap_seconds':9000,'verified_pull_bytes_per_second':1000000,'custody_acknowledged':True,'own_account_http200':True}
    from projects.g_agreement.r_bench.section49 import REG,sha
    b.update(shard_id=0,shards_sha256=sha(REG/'shards.json'))
    S.save(tmp_path/'booking.json',b);cfg=build(tmp_path)
    assert cfg['stall_s']==600 and cfg['pull_reserve_s']>=600
    assert [s['name'] for s in cfg['steps']]==['runtime-venv','runtime-download','download','hash-check','staging','target-smoke','nla-smoke','projection','target-full','nla-full','analyze']
    assert all(s['byte_roots'] for s in cfg['steps'][:3])
    b['deadline']+=1;S.save(tmp_path/'booking.json',b)
    with pytest.raises(ValueError,match='booking'):build(tmp_path)
