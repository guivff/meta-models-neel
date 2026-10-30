import copy
from pathlib import Path
from types import SimpleNamespace
import unittest
from . import fuse_storage as s


def fixture():
    a = dict(allocation_start_epoch=1000, provider_stop_epoch=10000,
             replica_hourly_usd=21.16, other_cost_upper_bound_usd=2, cap_usd=100,
             allocation_receipt_sha256='a'*64, run_identity_sha256='b'*64)
    a['storage_exception'] = dict(authority_sha256=s.AUTHORITY_SHA256,
        allocation_receipt_sha256='a'*64, run_identity_sha256='b'*64,
        allocation_start_epoch=1000, provider_stop_epoch=10000, provider='RunPod',
        volume_mount_path='/workspace', allocated_volume_bytes=700_000_000_000,
        existing_volume_bytes=1_000_000_000, capacity_observed_epoch=1100,
        remaining_seconds=7000)
    m = {'filesystems': [dict(source='mfs', target='/workspace', fstype='fuse')]}
    return a, m


class FuseStorageTests(unittest.TestCase):
    def proof(self, a=None, m=None, free=s.MIN_REQUIRED_BYTES, now=1200):
        aa, mm = fixture()
        return s.contract(a or aa, m or mm, free, s.MIN_REQUIRED_BYTES, now)

    def test_truthful_fuse_proof(self):
        a, m = fixture(); p=self.proof(a,m)
        self.assertEqual(p['storage'], 'runpod_fuse')
        self.assertIs(p['local_nvme_verified'], False)
        self.assertEqual(s.verify_receipt(p,a,1300),p)

    def test_shared_pool_free_space_does_not_replace_volume_allocation(self):
        a,m=fixture();a['storage_exception']['allocated_volume_bytes']=50_000_000_000
        with self.assertRaises(ValueError):self.proof(a,m,free=10**18)

    def test_capacity_accounts_existing_bytes(self):
        a,m=fixture();a['storage_exception']['existing_volume_bytes']=300_000_000_000
        with self.assertRaises(ValueError):self.proof(a,m)

    def test_short_free_space(self):
        with self.assertRaises(ValueError):self.proof(free=s.MIN_REQUIRED_BYTES-1)

    def test_missing_authority_or_contract(self):
        a,m=fixture();del a['storage_exception']
        with self.assertRaises(ValueError):self.proof(a,m)

    def test_wrong_authority(self):self.reject_contract('authority_sha256','c'*64)
    def test_wrong_provider(self):self.reject_contract('provider','other')
    def test_wrong_mount(self):self.reject_contract('volume_mount_path','/tmp')
    def test_wrong_allocation(self):self.reject_contract('allocation_start_epoch',1001)
    def test_renewed_endpoint(self):self.reject_contract('provider_stop_epoch',11000)
    def test_future_capacity(self):self.reject_contract('capacity_observed_epoch',1300)
    def test_capacity_before_allocation(self):self.reject_contract('capacity_observed_epoch',999)
    def test_nonpositive_remaining(self):self.reject_contract('remaining_seconds',0)
    def test_endpoint_no_fit(self):self.reject_contract('remaining_seconds',9000)
    def test_nonfinite_forecast(self):self.reject_contract('remaining_seconds',float('nan'))
    def test_no_boolean_capacity(self):self.reject_contract('allocated_volume_bytes',True)
    def test_identity_required(self):self.reject_contract('allocation_receipt_sha256','')
    def test_other_pod_identity_rejected(self):self.reject_contract('allocation_receipt_sha256','c'*64)

    def reject_contract(self,k,v):
        a,m=fixture();a['storage_exception'][k]=v
        with self.assertRaises(ValueError):self.proof(a,m)

    def test_cost_includes_idle_extras_and_padding(self):
        a,m=fixture();p=self.proof(a,m)
        self.assertAlmostEqual(p['forecast_times_1_25_usd'],((200+7000)*21.16/3600+2)*1.25)
        a['cap_usd']=p['forecast_times_1_25_usd']-.01
        with self.assertRaises(ValueError):self.proof(a,m)

    def test_overlay_block_network_and_unknown_filesystems_not_waived(self):
        for typ in ('overlay','nfs','ext4','tmpfs','fuse.unknown'):
            a,m=fixture();m['filesystems'][0]['fstype']=typ
            with self.assertRaises(ValueError):self.proof(a,m)

    def test_proof_tamper(self):
        a,m=fixture();p=self.proof(a,m)
        for key,value in [('local_nvme_verified',True),('contract_sha256','c'*64),
                          ('allocated_volume_bytes',10**18),('storage','local_nvme')]:
            bad=copy.deepcopy(p);bad[key]=value
            with self.assertRaises(ValueError):s.verify_receipt(bad,a,1300)

    def test_contract_changed_after_proof(self):
        a,m=fixture();p=self.proof(a,m);a['storage_exception']['run_identity_sha256']='c'*64
        with self.assertRaises(ValueError):s.verify_receipt(p,a,1300)

    def test_original_endpoint_expired(self):
        a,m=fixture();p=self.proof(a,m)
        with self.assertRaises(ValueError):s.verify_receipt(p,a,10000)

    def test_observe_reads_metadata_without_mutation(self):
        a,m=fixture();calls=[]
        def metadata(argv):calls.append(argv);return m
        p=s.observe('/workspace/owned-run/stage',a,s.MIN_REQUIRED_BYTES,1200,metadata,
                    lambda p:SimpleNamespace(free=s.MIN_REQUIRED_BYTES))
        self.assertEqual(len(calls),1);self.assertEqual(calls[0][0],'findmnt')
        self.assertEqual(p['storage'],'runpod_fuse')

    def test_observe_rejects_other_tree_before_metadata(self):
        a,m=fixture()
        with self.assertRaises(ValueError):s.observe('/tmp',a,s.MIN_REQUIRED_BYTES,1200,
            lambda argv:self.fail('must not inspect'),lambda p:self.fail('must not inspect'))


if __name__ == '__main__':unittest.main()
