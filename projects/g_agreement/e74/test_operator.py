"""Synthetic CPU tests: no remote reads, actual weights, or GPU calls."""
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import torch
from . import ops, stage, resident as r, archive_stage
from .test_smoke50 import fixtures, Tok
from .test_smoke import runtime


def admission(now=None):
    now = time.time() if now is None else now
    return {'gpu_type':'B200', 'gpu_count':4, 'allocation_start_epoch': now-1, 'replica_hourly_usd': 31.96, 'other_cost_upper_bound_usd': 2,
            'provider_stop_epoch': now+9000, 'cap_usd': 100}


def go(req, digest, epoch):
    result = {k: 'a'*64 for k in r.GO_FIELDS}
    result.update(issuer='I-2', experiment='E74', decision='GO', checked_epoch=time.time(),
                  capture_seal_sha256=digest, port_seal_sha256=r.PORT_SHA,
                  reader_plan_sha256=req['reader_plan_sha256'], source_seal_sha256=req['source_seal_sha256'],
                  asset_card_sha256='dcb6d67bebaf06ab5312e2d30201e88d805d406bbc9bdfdc1502f3745ec748e5',
                  forecast_commit='b'*40, rg2_not_evaluable_permanent=True, forecast_commit_verified=True,
                  capture_pull_verified=True, cpu_probes_verified=True, reader_outputs_accessed=False,
                  provider_stop_epoch=req['admission_obj']['provider_stop_epoch'])
    return result


class Engine:
    n_workers=4; mpos=63; merged=None; tok=Tok()
    prompt_ids=[1]*63+[154518]+[1]*6
    def __init__(self): self.calls=[]
    def capture_h51(self, ids, positions):
        if len(ids)!=50: assert self.merged is None
        self.calls.append(('capture', len(ids)))
        return [torch.ones(1,6144)*(1+i) for i in range(len(ids))]
    def set_lens(self, path, keep_base=None): self.merged=path; self.calls.append(('merge',path))
    def verbalize(self, vecs, **kwargs):
        self.calls.append(('read',len(vecs),kwargs))
        return [['* a b'] for _ in vecs]


class OperatorTests(unittest.TestCase):
    def no_fit(self):
        try: ops.budget(admission(1000), 9133, 1000)
        except ops.NoFit as error: return error
        self.fail('expected cost rejection')
    def assert_rejection_sealed(self,out):
        seal=ops.verify_seal(out/'SEAL.json')
        self.assertEqual(seal['status'],'NO_FIT')
        evidence=json.loads((out/'NO_FIT.json').read_bytes())
        self.assertGreater(evidence['forecast_times_1_25_usd'],evidence['cap_usd'])
        self.assertEqual(evidence['cap_usd'],100)
        self.assertEqual(evidence['multiplier'],1.25)
        self.assertEqual(seal['rejected_forecast'],evidence)
    def test_no_fit_admission_cli_both_supervisors(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);now=time.time()
            a=dict(admission(now),issuer='I-2',experiment='E74',admitted=True,gpu_type='B200',gpu_count=4,
                   authorized_phases=['weight_staging','resident_smoke_capture'],provider_stop_verified=True,
                   environment_lock_verified=True,environment_lock_sha256='a'*64,other_cost_upper_bound_usd=81)
            ops.write(root/'admission.json',a)
            req={'admission':str(root/'admission.json'),'admission_sha256':ops.sha(root/'admission.json')}
            ops.write(root/'request.json',req)
            for module in ['stage','resident']:
                out=root/module
                result=subprocess.run([sys.executable,'-m','projects.g_agreement.e74.'+module,'--request',str(root/'request.json'),'--out',str(out)],capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,ops.NO_FIT_EXIT,result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'],'NO_FIT')
                self.assert_rejection_sealed(out)
                self.assertFalse((out/'worker.log').exists())
    def test_no_fit_workers_emit_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            for module in [stage,r]:
                out=Path(td)/module.__name__.split('.')[-1];out.mkdir()
                ops.write(out/'request.json',{})
                argv=['test','--worker',str(out/'request.json'),'--out',str(out)]
                with patch.object(sys,'argv',argv),patch.object(module,'worker',side_effect=self.no_fit()):
                    self.assertEqual(module.main(),ops.NO_FIT_EXIT)
                evidence=json.loads((out/'NO_FIT.json').read_bytes())
                self.assertEqual(evidence['status'],'NO_FIT')
                self.assertGreater(evidence['forecast_times_1_25_usd'],100)
    def test_no_fit_child_reports_are_sealed_by_both_supervisors(self):
        real_popen=subprocess.Popen
        with tempfile.TemporaryDirectory() as td:
            for module in [stage,r]:
                out=Path(td)/module.__name__.split('.')[-1];a=admission()
                req={'admission':'synthetic','admission_sha256':'a'*64,'deadline_epoch':time.time()+20}
                def start(*args,**kwargs):
                    script="import json,sys;from pathlib import Path;from projects.g_agreement.e74 import ops;ops.record_no_fit(Path(sys.argv[1]),ops.NoFit(json.loads(sys.argv[2])),'synthetic_worker');sys.exit(ops.NO_FIT_EXIT)"
                    return real_popen([sys.executable,'-c',script,str(out),json.dumps(self.no_fit().evidence)],**kwargs)
                with patch.object(ops,'admission',return_value=a),patch.object(r.smoke50,'validate_clocks'),patch.object(subprocess,'Popen',side_effect=start):
                    self.assertEqual(module.supervise(req,out),ops.NO_FIT_EXIT)
                self.assert_rejection_sealed(out)
    def test_no_fit_resident_cost_watchdog_seals_reserved_closeout_rejection(self):
        real_popen=subprocess.Popen; children=[]
        with tempfile.TemporaryDirectory() as td:
            now=time.time();a=admission(now)
            # Actual elapsed alone fits; elapsed plus required120s closeout exceeds.
            a['allocation_start_epoch']=now-8700
            req={'admission':'synthetic','admission_sha256':'a'*64,'deadline_epoch':now+20}
            def start(*args,**kwargs):
                child=real_popen([sys.executable,'-c','import time;time.sleep(60)'],**kwargs);children.append(child);return child
            with patch.object(ops,'admission',return_value=a),patch.object(r.smoke50,'validate_clocks'),patch.object(subprocess,'Popen',side_effect=start):
                self.assertEqual(r.supervise(req,Path(td)/'run'),ops.NO_FIT_EXIT)
            children[0].wait(timeout=5)
            self.assert_rejection_sealed(Path(td)/'run')
    def test_budget_includes_elapsed_wait_and_extra_reboot(self):
        a=admission(1000); a['allocation_start_epoch']=1000
        x=ops.budget(a,8473,1000)
        self.assertAlmostEqual(x['forecast_times_1_25_usd'],96.5267638889)
        for elapsed, remaining in [(660,8473),(0,9133)]:
            with self.assertRaises(ops.NoFit): ops.budget(a,remaining,1000+elapsed)
    def test_budget_rejects_nan_and_provider_timeout(self):
        a=admission(1000)
        for remaining in [float('nan'),-1,100000]:
            with self.assertRaises(ValueError): ops.budget(a,remaining,1000)
        with self.assertRaises(ValueError): ops.budget(dict(a,provider_stop_epoch=1001),2,1000)
    def test_staging_sha_gitblob_no_auth_and_no_overwrite(self):
        class Response(io.BytesIO): status=200
        class Opener:
            def open(self,request,timeout):
                assert not any(k.lower() in ('authorization','cookie') for k in request.headers)
                return Response(b'abc')
        for alg in ['sha256','git_blob_sha1']:
            with tempfile.TemporaryDirectory() as td:
                identity=hashlib.sha256(b'abc').hexdigest() if alg=='sha256' else hashlib.sha1(b'blob 3\0abc').hexdigest()
                entry={'area':'base','path':'synthetic.bin','identity':{'algorithm':alg,'value':identity},'size_bytes':3,'resolve_url':'https://invalid.test/synthetic'}
                got=stage.transfer(entry,Path(td),time.time()+10,Opener())
                self.assertEqual(got['sha256'],hashlib.sha256(b'abc').hexdigest())
                with self.assertRaises(ValueError):stage.transfer(entry,Path(td),time.time()+10,Opener())
    def test_corrupt_transfer_never_publishes_and_expired_never_opens(self):
        class Response(io.BytesIO):status=200
        class Opener:
            def open(self,*args,**kwargs):return Response(b'bad')
        e={'area':'base','path':'x','identity':{'algorithm':'sha256','value':'a'*64},'size_bytes':3,'resolve_url':'https://invalid.test/x'}
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):stage.transfer(e,Path(td),time.time()+10,Opener())
            self.assertFalse((Path(td)/'base/x').exists())
            with self.assertRaises(ValueError):stage.transfer(dict(e,path='y'),Path(td),time.time()-1,Opener())
            self.assertFalse((Path(td)/'base/y.partial').exists())
    def test_overlay_private_quant_copy_and_shared_immutable_weights(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); verified={}; manifest={'base':{'files':{}},'lens':{'files':{}}}
            for area,name,prefix in [('base','hf_quant_config.json','base/'),('base','weights','base/'),('lens','adapter','lens/'+stage.core.LENS_PATH+'/')]:
                p=root/'objects'/prefix/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'abc');p.chmod(0o400)
                verified[prefix+name]={'sha256':ops.sha(p),**stage.core.stat_identity(p)}
                manifest[area]['files'][name]={'sha256':ops.sha(p),'bytes':3}
            model,adapter,receipt=stage.overlay(root,manifest,verified)
            self.assertEqual((model/'hf_quant_config.json').stat().st_nlink,1)
            self.assertEqual((model/'weights').stat().st_ino,(root/'objects/base/weights').stat().st_ino)
            (model/'hf_quant_config.json').write_bytes(b'new')
            self.assertEqual((root/'objects/base/hf_quant_config.json').read_bytes(),b'abc')
            self.assertEqual(len(receipt),3)
    def test_label_field_and_bad_read_boundary_rejected(self):
        row={'id':'a'*64,'ids':[1,2],'read_position':1}
        r.validate_items([row],1)
        for bad in [dict(row,label='secret'),dict(row,read_position=0)]:
            with self.assertRaises(ValueError):r.validate_items([bad],1)
    def test_receipt_producer_roundtrips_through_existing_consumer(self):
        class Response(io.BytesIO): status=200
        class Opener:
            def open(self,*a,**k):return Response(b'abc')
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); now=time.time(); a=admission(now); a['allocation_start_epoch']=now-2
            a['source_seal_sha256']='f'*64
            files=[]; m={'base':{'repo':stage.core.BASE_REPO,'revision':stage.core.BASE_REVISION,'files':{}},
                        'lens':{'repo':stage.core.LENS_REPO,'revision':stage.core.LENS_REVISION,'adapter_path':stage.core.LENS_PATH,'files':{}}}
            for area,name in [('base','hf_quant_config.json'),('base','weights'),('lens','adapter')]:
                digest=hashlib.sha256(b'abc').hexdigest(); rel=name if area=='base' else stage.core.LENS_PATH+'/'+name
                files.append({'area':area,'path':rel,'size_bytes':3,'identity':{'algorithm':'sha256','value':digest},'resolve_url':'https://invalid.test/fixture'})
                m[area]['files'][name]={'sha256':digest,'bytes':3}
            archive={'status':'VERIFIED','source_seal_sha256':'f'*64,'started_epoch':now-2,'finished_epoch':now-1}
            req={'admission':'admission','admission_sha256':'a'*64,'stage_start_epoch':now,
                 'archive_receipt':'archive','archive_receipt_sha256':'b'*64,'transfer_manifest':'transfer',
                 'weight_manifest':'weights','fork_archive':'fork','additional_disk_reserve_bytes':2_000_000_000}
            objects={'archive':archive,'transfer':{'source_asset_manifest_sha256':stage.ASSET_SHA,'files':files},'weights':m}
            with patch.object(stage.ops,'admission',return_value=a),patch.object(stage.ops,'bound',side_effect=lambda p,h:objects[p]),patch.object(stage,'versions',return_value={}),patch.object(stage.core,'check_dependencies'),patch.object(stage.core,'verify_fork'),patch.object(stage,'nvme_evidence',return_value={'synthetic':True}),patch.object(stage.urllib.request,'build_opener',return_value=Opener()):
                stage.worker(req,root)
            receipt=json.loads((root/'STAGING_RECEIPT.json').read_bytes())
            result=stage.core.check_staging_receipt(receipt,m,root/'runtime/base',root/'runtime/adapter',now-2,4500)
            self.assertEqual(result['files_bound_to_cpu_checksums'],3)
            self.assertTrue(json.loads((root/'TRANSFER_RECEIPT.json').read_bytes())['anonymous'])
    def test_sealed_capture_hash_and_shape(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); p=root/'s.tar'
            r.write_capture(p,['a'*64],[torch.ones(1,6144)])
            ids,x=r.read_capture(p);self.assertEqual(x.shape,(1,6144))
            ops.seal(root,['s.tar'],status='TEST')
            ops.verify_seal(root/'SEAL.json')
            with p.open('ab') as f:f.write(b'x')
            with self.assertRaises(ValueError):ops.verify_seal(root/'SEAL.json')
    def test_go_rejects_bad_binding_future_uncommitted_or_accessed(self):
        req={'reader_plan_sha256':'c'*64,'source_seal_sha256':'d'*64,'admission_obj':admission()}
        now=time.time(); g=go(req,'e'*64,now-1)
        r.check_go(g,req,'e'*64,now-1,time.time())
        for key,value in [('capture_seal_sha256','f'*64),('checked_epoch',now+10),('forecast_commit_verified',False),('reader_outputs_accessed',True),('rg2_not_evaluable_permanent',False),('label','bad')]:
            with self.assertRaises(ValueError):r.check_go(dict(g,**{key:value}),req,'e'*64,now-1,time.time())
    def test_one_engine_complete_synthetic_lifecycle_and_once_claim(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td); e=Engine()
            items=[{'id':hashlib.sha256(str(i).encode()).hexdigest(),'ids':[10+i,20],'read_position':1} for i in range(6)]
            ids=[x['id'] for x in items[:3]]
            req={'adapter_dir':'adapter','admission_obj':admission(),'deadline_epoch':time.time()+1200,'boot_seconds':0,
                 'source_seal_sha256':'d'*64,'reader_plan_sha256':'c'*64,'go_file':str(out/'GO.json')}
            actual_wait=r.await_go
            def external_i2(req,out,digest,epoch):
                self.assertTrue((out/'capture/SEAL.json').exists())
                self.assertFalse((out/'readers').exists())
                ops.write(Path(req['go_file']),go(req,digest,epoch))
                actual_wait(req,out,digest,epoch)
            with patch.object(r,'BATCH',2),patch.object(r,'await_go',external_i2):
                r.run_resident(req,out,e,runtime(),fixtures(),items,ids)
            self.assertEqual([x[1] for x in e.calls if x[0]=='capture'],[50,2,2,2])
            self.assertEqual([x[1] for x in e.calls if x[0]=='read'],[50,2,1])
            self.assertEqual(ops.verify_seal(out/'readers/SEAL.json')['n'],3)
            self.assertNotIn('readout',(out/'smoke/STATISTICS.json').read_text().replace('readout_seconds',''))
            with self.assertRaises(FileExistsError):r.run_resident(req,out,e,runtime(),fixtures(),items,ids)
    def test_smoke_failure_stops_before_production_capture(self):
        with tempfile.TemporaryDirectory() as td:
            e=Engine();req={'adapter_dir':'adapter','admission_obj':admission(),'deadline_epoch':time.time()+10,'boot_seconds':0}
            with patch.object(r.smoke50,'run50',return_value={'passed':False}):
                with self.assertRaises(ValueError):r.run_resident(req,Path(td),e,runtime(),[],[],[])
            self.assertFalse(e.calls)
            self.assertFalse((Path(td)/'capture').exists())
    def test_archive_window_not_reset_and_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with self.assertRaises(ValueError):archive_stage.stage(root/'missing','a'*64,root/'out',time.time()-901,'b'*64)
            with self.assertRaises(ValueError):ops.safe(root,'../escape')
    def test_archive_cli_really_starts_worker_module(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); raw=b'synthetic'
            source=ops.encoded({'files':{'synthetic.txt':hashlib.sha256(raw).hexdigest()}})
            archive=root/'input.tar';r.pack(archive,{'SOURCE_SEAL.json':source,'synthetic.txt':raw})
            result=subprocess.run([sys.executable,'-m','projects.g_agreement.e74.archive_stage',
                '--archive',str(archive),'--sha256',ops.sha(archive),'--out',str(root/'out'),
                '--started-epoch',str(time.time()),'--source-sha256',hashlib.sha256(source).hexdigest()],
                capture_output=True,text=True,timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads((root/'out/ARCHIVE_RECEIPT.json').read_bytes())['status'],'VERIFIED')
    def test_real_supervisor_kills_stalled_child_at_original_science_deadline(self):
        with tempfile.TemporaryDirectory() as td:
            now=time.time(); a=admission(now); real_popen=subprocess.Popen; children=[]
            def start(*args,**kwargs):
                child=real_popen([sys.executable,'-c','import time;time.sleep(60)'],**kwargs);children.append(child);return child
            req={'deadline_epoch':now+.4,'admission':'synthetic','admission_sha256':'a'*64}
            with patch.object(r.ops,'admission',return_value=a),patch.object(r.smoke50,'validate_clocks'),patch.object(r.subprocess,'Popen',side_effect=start):
                code=r.supervise(req,Path(td)/'run')
            self.assertEqual(code,124); children[0].wait(timeout=5)
            self.assertNotEqual(children[0].returncode,0)
            self.assertEqual(ops.verify_seal(Path(td)/'run/SEAL.json')['status'],'STOP_INCOMPLETE')


if __name__=='__main__':unittest.main()
