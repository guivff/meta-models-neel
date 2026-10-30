import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
from .e133_channel import terminal,check_scope,unit_call
from .e133_judge import RUBRIC_SHA

class ChannelTest(unittest.TestCase):
    def test_exhausted_rate_and_charged_length_never_start_schema_retry(self):
        self.assertTrue(terminal(dict(status='UNPARSEABLE',reason='RATE_LIMIT_EXHAUSTED')))
        self.assertTrue(terminal(dict(status='UNPARSEABLE',reason='CHARGED_LENGTH')))
        self.assertTrue(terminal(dict(status='KEPT')))
        self.assertFalse(terminal(dict(status='UNPARSEABLE',reason='FROZEN_SCHEMA_OR_EVIDENCE_FAILED')))
    def test_prepared_or_partial_source_cannot_claim_complete_custody(self):
        c=dict(issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,arm='synthetic',rubric_sha256=RUBRIC_SHA,selected_items=2,native_status='NO_FIT',screened_cohort_bound=True)
        with self.assertRaises(ValueError):check_scope('E133',[],c)
    def test_extra_private_unit_metadata_rejected(self):
        u=dict(id='a'*32,kind='e133_naming',data=dict(id='a'*32,property='holder',values={'A':['Ada'],'B':['Bea']},readout=''),current='Ada')
        with self.assertRaises(ValueError):unit_call(u,None)

    def test_full_prepare_keeps_six_units_and_all_eighteen_attempt_wires(self):
        from . import e133_channel as channel,registered
        from .runner import seal_phase
        from projects.g_agreement.readerbench.io import write,sha,read
        with tempfile.TemporaryDirectory()as temp:
            root=Path(temp);source=root/'source';source.mkdir()
            units=[dict(id=('%032x'%i),kind='e133_naming',data=dict(id=('%032x'%i),property='holder',values={'A':['Ada'],'B':['Bea']},readout=''))for i in range(6)]
            custody=dict(issuer='W-internals-C',experiment='E133',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,arm='synthetic',rubric_sha256=RUBRIC_SHA,selected_items=2,native_status='COMPLETE',screened_cohort_bound=True,source_seals=[])
            write(source/'UNITS.json',units);write(source/'CUSTODY.json',custody)
            write(source/'UNIT_SEAL.json',dict(experiment='E133',files={n:sha(source/n)for n in ('UNITS.json','CUSTODY.json')}))
            spec=root/'spec.json';write(spec,dict(bank='E133',unit_seal=str(source/'UNIT_SEAL.json'),unit_sha256=sha(source/'UNIT_SEAL.json'),phase_name='pure_synthetic'))
            def sealed(bank,phase,calls,provenance,sources):
                dest=root/phase;dest.mkdir();write(dest/'CALLS.json',calls);write(dest/'PROVENANCE.json',provenance)
                write(dest/'INPUT_SEAL.json',dict(experiment=bank,phase=phase,files={},source_seals=sources));return dest
            def preflight(dest):
                calls=read(dest/'CALLS.json');self.assertEqual(len(calls),18)
                self.assertTrue(all(set(__import__('json').loads(c['rendered']['user'])[0])=={'id','property','values','readout'}for c in calls))
                return dict(first_pass_upper_usd='0') # synthetic source test, not a cost estimate
            with patch.object(channel,'source_gate',return_value=None),patch.object(registered,'source_gate'),patch.object(registered,'seal_phase',side_effect=sealed),patch.object(registered,'preflight',side_effect=preflight):
                with channel.worker():out=registered.prepare(spec)
            self.assertEqual(out[0]['units'],6)
            self.assertEqual(out[0]['preflight']['max_schema_retries'],2)

if __name__=='__main__':unittest.main()
