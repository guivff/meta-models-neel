import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest.mock import patch
import urllib.error


# Record only writes from this test process; concurrent pod output is unrelated.
from projects.g_agreement.tests import _write_guard as WG

REPO = Path(__file__).resolve().parents[3]
_GUARD = WG.ModuleWriteGuard([
    REPO / "results" / "g_agreement",
    REPO / "cache" / "g_agreement",
    REPO / "projects" / "g_agreement" / "dataset",
    REPO / "projects" / "g_agreement" / "manifest",
])
_write_guard = _GUARD.fixture()

spec = importlib.util.spec_from_file_location('guard', Path(__file__).resolve().parents[1] / 'r_bench' / 't_a02_controller.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class Reply:
    def __init__(self, payload): self.payload=payload
    def __enter__(self): return self
    def __exit__(self,*a): pass
    def read(self): return json.dumps(self.payload).encode()


class FakeEvent:
    def __init__(self, clock): self.clock=clock; self.flag=False
    def is_set(self): return self.flag
    def set(self): self.flag=True
    def wait(self, seconds): self.clock[0]+=seconds; return self.flag


class FakeStopper:
    def __init__(self, clock): self.requested=FakeEvent(clock); self.reasons=[]
    def stop(self, reason): self.reasons.append(reason); self.requested.set()


class GuardTests(unittest.TestCase):
    def test_absolute_cap_includes_startup(self):
        self.assertEqual(g.compute_deadline(1000,9900,60),10840)
        with self.assertRaises(ValueError): g.compute_deadline(1000,9901,60)
        with self.assertRaises(ValueError): g.compute_deadline(1000,9900,0)
        self.assertEqual(g.started_epoch('1970-01-01T00:16:40Z'),1000)
        with self.assertRaises(ValueError): g.started_epoch('2026-10-19T15:00:00')

    def test_idle_elapsed_full_15_minutes_and_all_gpus(self):
        tracker=g.IdleClock()
        self.assertFalse(tracker.observe([0,0],100))
        self.assertFalse(tracker.observe([0,0],999))
        self.assertTrue(tracker.observe([0,0],1000))
        self.assertFalse(tracker.observe([0,3],1001))
        self.assertFalse(tracker.observe([0,0],1100))
        self.assertFalse(tracker.observe([0,0],1999))
        self.assertTrue(tracker.observe([0,0],2000))
        self.assertFalse(tracker.observe(None,2001))
        self.assertFalse(tracker.observe([0],2100))

    def test_hard_watch_uses_elapsed_start_not_job_start(self):
        clock=[150.0]; stopper=FakeStopper(clock)
        with patch.object(g.time,'time',lambda:clock[0]): g.hard_watch(stopper,153)
        self.assertEqual(clock[0],153)
        self.assertEqual(stopper.reasons,['absolute_billed_deadline'])

    def test_idle_watch_900_seconds_and_telemetry_failure(self):
        clock=[0.0]; stopper=FakeStopper(clock)
        with patch.object(g.time,'monotonic',lambda:clock[0]), patch.object(g,'gpu_utilization',lambda:[0,0]):
            g.idle_watch(stopper)
        self.assertEqual(clock[0],900)
        self.assertEqual(stopper.reasons,['gpu_zero_for_900_seconds'])
        clock=[0.0]; stopper=FakeStopper(clock)
        with patch.object(g.time,'monotonic',lambda:clock[0]), patch.object(g,'gpu_utilization',side_effect=OSError):
            g.idle_watch(stopper)
        self.assertEqual(clock[0],60)
        self.assertEqual(stopper.reasons,['gpu_telemetry_unavailable'])

    def test_rest_failure_falls_back_to_graphql_and_never_leaks(self):
        seen=[]
        def opener(request,timeout):
            seen.append(request)
            self.assertIn('Mozilla/5.0',request.get_header('User-agent'))
            self.assertEqual(request.get_header('Authorization'),'Bearer secret-value')
            if 'rest.runpod.io' in request.full_url:
                raise urllib.error.HTTPError(request.full_url,403,'secret-value',{},None)
            return Reply({'data':{'podStop':{'id':'pod-id','desiredStatus':'EXITED'}}})
        api=g.Api('secret-value',opener)
        api.stop('pod-id')
        self.assertEqual(len(seen),2)
        self.assertEqual(seen[1].full_url,'https://api.runpod.io/graphql')
        self.assertNotIn('secret-value',seen[1].full_url)
        api=g.Api('secret-value',lambda *a,**kw:(_ for _ in ()).throw(ValueError('secret-value')))
        with self.assertRaises(g.ApiError) as caught: api.request('https://rest.runpod.io/v1/pods/x')
        self.assertNotIn('secret-value',str(caught.exception))

    def test_identity_mismatch_cannot_arm(self):
        def opener(request,timeout):
            if 'graphql' in request.full_url: return Reply({'data':{'pod':{'id':'other','desiredStatus':'RUNNING'}}})
            return Reply({'id':'other','desiredStatus':'RUNNING'})
        with self.assertRaises(g.ApiError): g.Api('key',opener).status('expected')

    def test_stop_retries_until_status_is_confirmed(self):
        class FakeApi:
            calls=0
            def stop(self,pod):
                self.calls+=1
                if self.calls==1: raise g.ApiError('http_503')
            def status(self,pod): return 'RUNNING' if self.calls==2 else 'EXITED'
        api=FakeApi(); stopper=g.Stopper(api,'explicit-id')
        with patch.object(g.time,'sleep'), patch.object(g,'log'):
            stopper.stop('job_failed')
            stopper.stop('duplicate')
        self.assertEqual(api.calls,3)
        self.assertTrue(stopper.confirmed.is_set())

    def test_bootstrap_is_self_contained_and_shell_valid(self):
        args=types.SimpleNamespace(pod_id='test-id',started_at='1000',run_dir='/workspace/a02-test',limit_seconds=9900,stop_margin_seconds=60,sync_grace_seconds=0)
        output=g.bootstrap(args)
        self.assertIn('readonly A02_EXPLICIT_POD_ID=test-id',output)
        self.assertLess(output.index('readonly A02_EXPLICIT_POD_ID'),output.index('source /workspace/.env'))
        self.assertIn('export RUNPOD_POD_ID="$A02_EXPLICIT_POD_ID"',output)
        self.assertNotIn('secret-value',output)
        result=subprocess.run(['bash','-n'],input=output,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_job_failure_still_stops_and_writes_durable_log(self):
        class Thread:
            def __init__(self,*a,**kw): pass
            def start(self): pass
        class Api:
            stopped=False
            def status(self,p): return 'EXITED' if self.stopped else 'RUNNING'
            def stop(self,p): self.stopped=True
        with tempfile.TemporaryDirectory() as td:
            args=types.SimpleNamespace(run_dir=td,pod_id='explicit',started_at='1000',limit_seconds=9900,stop_margin_seconds=60,sync_grace_seconds=0)
            (Path(td)/'job.sh').write_text('exit 7\n')
            real_replace=Path.replace
            def publish(self,target):
                out=real_replace(self,target)
                if Path(target).name=='ARMED': (self.parent/'READY').write_text('ready')
                return out
            api=Api()
            with patch.object(g.threading,'Thread',Thread),patch.object(g,'install_signals'),patch.object(g.signal,'signal'),patch.object(g.os,'dup2'),patch.object(g.Path,'replace',publish),patch.object(g,'log'):
                rc=g.pod_run(args,api,10000)
            self.assertEqual(rc,7)
            self.assertTrue(api.stopped)
            self.assertTrue((Path(td)/'guard.jsonl').exists())
            armed=json.loads((Path(td)/'ARMED').read_text())
            self.assertEqual(armed['pod_id'],'explicit')
            self.assertIs(armed['self_stop_armed'],True)
            self.assertIs(armed['idle_watchdog_armed'],True)
            self.assertEqual(armed['billed_start_epoch'],1000.0)
            self.assertIsInstance(armed['billed_start_epoch'],float)
            self.assertEqual(armed['hard_deadline_epoch'],10000)
            self.assertLessEqual(armed['sample_seconds'],60)

    def test_stale_ready_never_starts_job_and_stops(self):
        class Thread:
            def __init__(self,*a,**kw): pass
            def start(self): pass
        class Api:
            stopped=False
            def status(self,p): return 'EXITED' if self.stopped else 'RUNNING'
            def stop(self,p): self.stopped=True
        with tempfile.TemporaryDirectory() as td:
            args=types.SimpleNamespace(run_dir=td,pod_id='explicit',started_at='1000',limit_seconds=9900,stop_margin_seconds=60,sync_grace_seconds=0)
            (Path(td)/'READY').write_text('stale')
            api=Api()
            with patch.object(g.threading,'Thread',Thread),patch.object(g,'install_signals'),patch.object(g.signal,'signal'),patch.object(g.os,'dup2'),patch.object(g.subprocess,'Popen') as popen,patch.object(g.subprocess,'run'),patch.object(g,'log'):
                rc=g.pod_run(args,api,10000)
            popen.assert_not_called()
            self.assertEqual(rc,1)
            self.assertTrue(api.stopped)



class SyncAndLocalTests(unittest.TestCase):
    def test_sync_window_bounded_by_deadline_and_ack(self):
        with tempfile.TemporaryDirectory() as td:
            clock=[100.0]; stopper=FakeStopper(clock)
            with patch.object(g.time,'time',lambda:clock[0]),patch.object(g,'log'):
                g.await_sync(stopper,Path(td),120,45)
                self.assertEqual(clock[0],120)
                (Path(td)/'SYNCED').touch()
                g.await_sync(stopper,Path(td),180,45)
                self.assertEqual(clock[0],120)

    def test_failed_boot_local_watchdog_still_stops_at_deadline(self):
        class Thread:
            def __init__(self,*a,**kw): pass
            def start(self): pass
        class Api:
            stopped=False
            def status(self,p):
                if self.stopped: return 'EXITED'
                raise g.ApiError('http_503')
            def stop(self,p): self.stopped=True
        clock=[100.0]; api=Api()
        args=types.SimpleNamespace(pod_id='explicit',started_at='100')
        with patch.object(g.time,'time',lambda:clock[0]),patch.object(g.threading,'Thread',Thread),patch.object(g.threading,'Event',lambda:FakeEvent(clock)),patch.object(g,'install_signals'),patch.object(g,'log'):
            rc=g.local_watch(args,api,160)
        self.assertEqual(clock[0],160)
        self.assertEqual(rc,0)
        self.assertTrue(api.stopped)



class BootAckTests(unittest.TestCase):
    def test_independent_boot_guard_expires_without_ack(self):
        with tempfile.TemporaryDirectory() as td:
            clock=[100.0]; stopper=FakeStopper(clock)
            with patch.object(g.time,'time',lambda:clock[0]):
                g.boot_watch(stopper,Path(td)/'ack',280)
            self.assertEqual(clock[0],280)
            self.assertEqual(stopper.reasons,['bootstrap_ack_timeout'])

    def test_boot_guard_returns_on_ack_without_stopping(self):
        with tempfile.TemporaryDirectory() as td:
            ack=Path(td)/'ack'; ack.touch()
            clock=[100.0]; stopper=FakeStopper(clock)
            with patch.object(g.time,'time',lambda:clock[0]): g.boot_watch(stopper,ack,280)
            self.assertEqual(clock[0],100)
            self.assertEqual(stopper.reasons,[])

    def test_local_controller_boot_timeout_precedes_billed_cap(self):
        class Thread:
            def __init__(self,*a,**kw): pass
            def start(self): pass
        class Api:
            stopped=False
            def status(self,p): return 'EXITED' if self.stopped else 'RUNNING'
            def stop(self,p): self.stopped=True
        with tempfile.TemporaryDirectory() as td:
            clock=[100.0]; api=Api()
            args=types.SimpleNamespace(pod_id='explicit',started_at='100',boot_ack_path=str(Path(td)/'ack'),boot_timeout_seconds=180)
            with patch.object(g.time,'time',lambda:clock[0]),patch.object(g.threading,'Thread',Thread),patch.object(g.threading,'Event',lambda:FakeEvent(clock)),patch.object(g,'install_signals'),patch.object(g,'log'):
                rc=g.local_watch(args,api,9940)
            self.assertEqual(clock[0],280)
            self.assertTrue(api.stopped)
            self.assertEqual(rc,0)



def test_zz_protected_roots_untouched():
    _GUARD.assert_clean()


if __name__=='__main__': unittest.main()
