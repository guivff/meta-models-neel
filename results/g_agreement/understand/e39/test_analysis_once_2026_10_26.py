"""Synthetic tests only: never invoke E39's scientific analysis."""
from pathlib import Path
import tempfile
import threading
import unittest
from unittest import mock
import analysis_once_2026_10_26 as O


class OnceOnly(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.claim=self.root/'cache/once/CLAIM.json';self.status=self.claim.parent/'STATUS.json'
        self.patch=mock.patch.multiple(O,ROOT=self.root,CLAIM=self.claim,STATUS=self.status)
        self.patch.start()
    def tearDown(self):self.patch.stop();self.temp.cleanup()
    def preflight(self):
        return ({'publish_directory':'published','publication_receipt':'RUN_BY_INTEGRATOR.json'},
            self.root/'input',[],self.root/'cache/output',self.root/'published',{'synthetic':True})
    def success(self,inp,paths,output,stdout,stderr):
        output.mkdir(parents=True)
        O.write_new(output/'METRICS.json',{'synthetic':True})
        O.write_new(output/'ANALYSIS_SEAL.json',{'files':{'METRICS.json':O.sha(output/'METRICS.json')}})
        return 0
    def test_success_and_second_invocation_blocked(self):
        with mock.patch.object(O,'preflight',side_effect=self.preflight),mock.patch.object(O,'execute',side_effect=self.success) as execute:
            self.assertEqual(O.run_once(),0);self.assertEqual(O.run_once(),3);self.assertEqual(execute.call_count,1)
        self.assertEqual(O.read(self.status)['status'],'COMPLETE_SEALED_UNINTERPRETED')
        self.assertEqual((self.root/'published/METRICS.json').read_bytes(),(self.root/'cache/output/METRICS.json').read_bytes())
    def test_validation_failure_consumes_claim_without_analysis(self):
        with mock.patch.object(O,'preflight',side_effect=ValueError('synthetic')),mock.patch.object(O,'execute') as execute:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);execute.assert_not_called()
        self.assertEqual(O.read(self.status)['registered_analysis_invocations'],0)
    def test_analysis_failure_no_retry_or_publication(self):
        with mock.patch.object(O,'preflight',side_effect=self.preflight),mock.patch.object(O,'execute',return_value=1) as execute:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);self.assertEqual(execute.call_count,1)
        self.assertFalse((self.root/'published').exists())
        self.assertEqual(O.read(self.status)['registered_analysis_invocations'],1)
    def test_interruption_consumes_claim(self):
        with mock.patch.object(O,'preflight',side_effect=KeyboardInterrupt),mock.patch.object(O,'execute') as execute:
            self.assertEqual(O.run_once(),2);self.assertEqual(O.run_once(),3);execute.assert_not_called()
    def test_concurrent_exclusive_claims(self):
        outcomes=[]
        def claim():
            try:O.claim_once(self.claim);outcomes.append('claimed')
            except FileExistsError:outcomes.append('blocked')
        threads=[threading.Thread(target=claim) for _ in range(8)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertEqual(outcomes.count('claimed'),1);self.assertEqual(outcomes.count('blocked'),7)
    def test_pull_manifest_hash_content_and_coverage(self):
        pull=self.root/'pull';(pull/'out').mkdir(parents=True)
        (pull/'out/a.json').write_text('{}\n');manifest=pull/'PULL_SUMS'
        manifest.write_text(O.sha(pull/'out/a.json')+'  ./out/a.json\n')
        digest=O.sha(manifest);self.assertEqual(O.verify_pull(pull,digest)['verified_file_count'],1)
        (pull/'out/unverified.json').write_text('{}')
        with self.assertRaises(ValueError):O.verify_pull(pull,digest)
        (pull/'out/unverified.json').unlink();(pull/'out/a.json').write_text('changed')
        with self.assertRaises(ValueError):O.verify_pull(pull,digest)
    def test_code_drift_and_path_escape_rejected(self):
        f=self.root/'file.py';f.write_text('original')
        digest=O.sha(f);O.verify_files(self.root,{'file.py':digest})
        f.write_text('changed')
        with self.assertRaises(ValueError):O.verify_files(self.root,{'file.py':digest})
        with self.assertRaises(ValueError):O.verify_files(self.root,{'../outside':digest})
    def test_real_preflight_binds_exact_paths_and_receipts(self):
        here=self.root/'source';here.mkdir()
        O.write_new(here/'PLAN.json',{'synthetic':True})
        (here/'analyze.py').write_text('# synthetic; never executed\n')
        O.write_new(here/'SOURCE_MANIFEST.json',{'files':{}})
        inp=self.root/'input';inp.mkdir();O.write_new(inp/'INPUT_SEAL.json',{'files':{}})
        source_hash=O.sha(here/'SOURCE_MANIFEST.json');input_hash=O.sha(inp/'INPUT_SEAL.json')
        O.write_new(self.root/'bound.json',{'input_seal_sha256':input_hash,'plan_sha256':O.sha(here/'PLAN.json'),'source_manifest_sha256':source_hash})
        pull=self.root/'slot0';(pull/'out').mkdir(parents=True)
        O.write_new(pull/'out/assignment.json',{'slot':0,'pod_count':1,'pod_id':'synthetic','input_seal_sha256':input_hash,'source_manifest_sha256':source_hash})
        O.write_new(pull/'out/RUN_RECEIPT.json',{'status':'COMPLETE_FULL_ASSIGNED_GRID'})
        (pull/'PULL_SUMS').write_text(''.join(O.sha(f)+'  ./out/'+f.name+'\n' for f in sorted((pull/'out').iterdir())))
        receipt={'experiment':'E39','issuer':'integrator','status':'VERIFIED_COMPLETE','production_complete':True,
            'pod_count':1,'input_seal_sha256':input_hash,'pulls':[{'slot':0,'pod_id':'synthetic','directory':'slot0','pull_sums_sha256':O.sha(pull/'PULL_SUMS')}]}
        O.write_new(self.root/'verified.json',receipt)
        request=self.root/'request.json';code_seal=self.root/'code.json'
        O.write_new(request,{'experiment':'E39','authority_commit':'886d03b0','verified_pull_receipt':'verified.json',
            'input_directory':'input','bound_launch_request':'bound.json','pull_directories':['slot0'],
            'analysis_cache_output':'cache/output','publish_directory':'published'})
        O.write_new(code_seal,{'files':{'request.json':O.sha(request)}})
        with mock.patch.multiple(O,HERE=here,REQUEST=request,CODE_SEAL=code_seal):
            result=O.preflight();self.assertEqual(result[2],[pull/'out'])
            (self.root/'published').mkdir()
            with self.assertRaisesRegex(ValueError,'existing output'):O.preflight()
            (self.root/'published').rmdir()
            receipt['pulls'][0]['directory']='different'
            (self.root/'verified.json').unlink();O.write_new(self.root/'verified.json',receipt)
            with self.assertRaisesRegex(ValueError,'exact slot path'):O.preflight()
    def test_publish_rejects_unsealed_file(self):
        output=self.root/'out';output.mkdir();O.write_new(output/'ANALYSIS_SEAL.json',{'files':{}})
        (output/'unsealed').write_text('x')
        with self.assertRaises(ValueError):O.publish_sealed(output,self.root/'published')


if __name__=='__main__':unittest.main()
