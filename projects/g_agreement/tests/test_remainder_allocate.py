"""Allocation failure-path tests: no requests, no subprocesses, no paid activity."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import urllib.error
import pytest
from projects.g_agreement.r_bench import remainder_allocate as a


@pytest.fixture
def intent():
    return {'names':{'r4':'mats-rem-r4-test'},'caps_seconds':{'r4':3600},
            'network_volume':'volume','data_center':'region'}


class FakeApi:
    def __init__(self,responses,check=None): self.responses=list(responses);self.calls=[];self.check=check
    def request(self,url,method='GET',payload=None):
        self.calls.append((url,method,payload))
        if self.check: self.check(url,method,payload)
        value=self.responses.pop(0)
        if isinstance(value,Exception): raise value
        return value


def guards(record):
    return SimpleNamespace(pid=123),Path('/unused'),{'local_guard_pid':123}


def armed(*args): pass


def alloc(intent,tmp_path,responses,**kwargs):
    api=FakeApi(responses)
    result,code=a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC comment',out=tmp_path,
                           guard_spawn=kwargs.get('spawn',guards),guard_await=kwargs.get('wait',armed))
    return result,code,api


def test_only_public_key_in_payload(intent,monkeypatch):
    monkeypatch.setenv('RUNPOD_API_KEY','secret-key');monkeypatch.setenv('HF_TOKEN','secret-token')
    payload=a.make_payload('r4',intent,'ssh-ed25519 PUBLIC comment')
    assert payload['env']=={'PUBLIC_KEY':'ssh-ed25519 PUBLIC comment'}
    assert 'secret-key' not in json.dumps(payload) and 'secret-token' not in json.dumps(payload)
    intent['caps_seconds']['r4']=3601
    with pytest.raises(ValueError): a.make_payload('r4',intent,'ssh-ed25519 PUBLIC comment')


def test_receipt_exists_before_post_and_before_guard(intent,tmp_path):
    path=tmp_path/'r4/allocation.json'
    def check(url,method,payload):
        if method=='POST': assert json.loads(path.read_text())['status']=='ALLOCATION_REQUEST_IN_FLIGHT'
    api=FakeApi([[],{'id':'new-id','name':intent['names']['r4']}],check)
    def spawn(record):
        persisted=json.loads(path.read_text())
        assert persisted['pod_id']=='new-id' and persisted['status']=='ALLOCATED_GUARD_PENDING'
        return guards(record)
    result,code=a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC',out=tmp_path,guard_spawn=spawn,guard_await=armed)
    assert code==0 and result['local_guard_armed'] is True
    assert [c[1] for c in api.calls]==['GET','POST']
    with pytest.raises(RuntimeError):
        a.allocate('r4',intent,FakeApi([]),'ssh-ed25519 PUBLIC',out=tmp_path)


def test_http_failure_zero_matches_remains_unknown(intent,tmp_path):
    result,code,api=alloc(intent,tmp_path,[[],a.ApiError('http_500:capacity_unavailable'),[]])
    assert code==2 and result['status']=='ALLOCATION_FAILED_OR_UNKNOWN'
    assert result['automatic_retry_allowed'] is False and result['reconciliation_required']
    assert result['matched_pods']==0 and len(api.calls)==3


def test_lagged_provider_creation_reconciles_exact_name(intent,tmp_path):
    pod={'name':intent['names']['r4'],'id':'late-id'}
    result,code,_=alloc(intent,tmp_path,[[],a.ApiError('TimeoutError'),[{'name':'another','id':'other'},pod]])
    assert code==0 and result['pod_id']=='late-id' and result['reconciled_after_error']=='TimeoutError'


def test_duplicate_matches_never_choose_first(intent,tmp_path):
    pods=[{'name':intent['names']['r4'],'id':x} for x in ['one','two']]
    result,code,_=alloc(intent,tmp_path,[[],a.ApiError('http_500:unclassified'),pods],
                        spawn=lambda _:pytest.fail('Do not guard an ambiguous ID'))
    assert code==2 and result['observed_candidate_ids']==['one','two'] and 'pod_id' not in result


def test_reconciliation_failure_retains_uncertainty(intent,tmp_path):
    result,code,_=alloc(intent,tmp_path,[[],a.ApiError('TimeoutError'),a.ApiError('TimeoutError')])
    assert code==2 and result['reconciliation_unavailable'] and result['reconciliation_required']


def test_missing_create_id_is_persisted_and_reconciled(intent,tmp_path):
    result,code,_=alloc(intent,tmp_path,[[],{'id':None},[]])
    assert code==2 and result['error']=='create_missing_valid_id'
    assert (tmp_path/'r4/allocation.json').exists()


def test_guard_spawn_failure_retains_billable_id(intent,tmp_path):
    def fail(_): raise OSError('private details must not be persisted')
    result,code,_=alloc(intent,tmp_path,[[],{'id':'new-id'}],spawn=fail)
    assert code==3 and result['pod_id']=='new-id'
    assert result['status']=='ALLOCATED_GUARD_UNCONFIRMED' and result['immediate_operator_action_required']
    assert result['guard_error']=='OSError' and 'private details' not in json.dumps(result)


def test_guard_must_confirm_arm(intent,tmp_path):
    def fail(*args): raise RuntimeError('unconfirmed')
    result,code,_=alloc(intent,tmp_path,[[],{'id':'new-id'}],wait=fail)
    assert code==3 and result['local_guard_pid']==123 and not result.get('local_guard_armed')


def test_preexisting_name_refuses_post(intent,tmp_path):
    api=FakeApi([[{'name':intent['names']['r4'],'id':'existing'}]])
    with pytest.raises(RuntimeError):
        a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC',out=tmp_path)
    assert len(api.calls)==1 and not (tmp_path/'r4/allocation.json').exists()


def test_exclusive_claim_cannot_overwrite(tmp_path):
    path=tmp_path/'receipt.json'
    a.save(path,{'first':True},exclusive=True)
    with pytest.raises(FileExistsError): a.save(path,{'second':True},exclusive=True)
    assert json.loads(path.read_text())=={'first':True}


def test_watchdog_log_must_match_pod_and_deadline(tmp_path):
    log=tmp_path/'guard.log'
    log.write_text(json.dumps({'event':'local_watchdog_armed','pod_id':'own','deadline':100})+'\n')
    proc=SimpleNamespace(poll=lambda:None)
    a.await_guard(proc,log,'own',100,timeout=.1)
    with pytest.raises(RuntimeError): a.await_guard(proc,log,'other',100,timeout=.01)
    with pytest.raises(RuntimeError): a.await_guard(SimpleNamespace(poll=lambda:1),log,'own',100,timeout=.1)


def test_error_body_and_credential_are_never_logged():
    def opener(req,timeout):
        assert req.get_header('Authorization')=='Bearer PRIVATE'
        raise urllib.error.HTTPError(req.full_url,500,'failure',{},io.BytesIO(b'No available instances PRIVATE'))
    with pytest.raises(a.ApiError) as error:
        a.AllocationApi('PRIVATE',opener=opener).request(a.URL,'POST',{})
    assert str(error.value)=='http_500:capacity_unavailable'


@pytest.fixture
def fallback():
    return {'name':'mats-rem-r4-ov1','data_center':'US-NC-2',
            'gpu_type':'NVIDIA RTX PRO 6000 Blackwell Server Edition'}


def original_receipt(intent,tmp_path,elapsed=1000,**updates):
    import time
    record={'experiment':'r4','name':intent['names']['r4'],'limit_seconds':3600,
            'started_epoch':time.time()-elapsed,'status':'ALLOCATION_FAILED_OR_UNKNOWN',**updates}
    path=tmp_path/'r4/allocation.json';path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(record));return path


def test_offvolume_payload_has_exact_approved_placement(intent,fallback):
    payload=a.make_payload('r4',intent,'ssh-ed25519 PUBLIC',fallback)
    assert payload['containerDiskInGb']==200 and payload['volumeInGb']==0
    assert 'networkVolumeId' not in payload and payload['cloudType']=='SECURE'
    assert payload['dataCenterIds']==['US-NC-2'] and payload['gpuTypeIds']==[fallback['gpu_type']]
    assert payload['env']=={'PUBLIC_KEY':'ssh-ed25519 PUBLIC'}
    with pytest.raises(ValueError): a.make_payload('r4',intent,'ssh-ed25519 PUBLIC',{**fallback,'data_center':'EUR-IS-3'})
    with pytest.raises(ValueError): a.make_payload('r4',intent,'ssh-ed25519 PUBLIC',{**fallback,'name':intent['names']['r4']})


def test_offvolume_preserves_old_receipt_and_records_fresh_reconciliation(intent,fallback,tmp_path):
    original=original_receipt(intent,tmp_path);before=original.read_bytes()
    api=FakeApi([[],{'id':'fallback-id','name':fallback['name']}])
    result,code=a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC',out=tmp_path,
                           guard_spawn=guards,guard_await=armed,fallback=fallback)
    assert code==0 and result['volume'] is None and result['limit_seconds']==3600
    assert result['boot_timeout_seconds']==240
    context=result['fallback_context']
    assert context['fresh_reconciliation']['names']==[intent['names']['r4']]
    assert context['fresh_reconciliation']['exact_matches']==0
    assert (tmp_path/'r4/allocations'/f"{fallback['name']}.json").exists()
    assert original.read_bytes()==before


def test_late_original_pod_blocks_fallback_without_post(intent,fallback,tmp_path):
    original_receipt(intent,tmp_path)
    api=FakeApi([[{'id':'late-old','name':intent['names']['r4']}]])
    with pytest.raises(RuntimeError,match='Prior intended name'):
        a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC',out=tmp_path,fallback=fallback)
    assert [x[1] for x in api.calls]==['GET']
    assert not (tmp_path/'r4/allocations'/f"{fallback['name']}.json").exists()


def test_shortage_wait_caps_and_known_ids_are_hard_gates(intent,fallback,tmp_path):
    original_receipt(intent,tmp_path,elapsed=899)
    with pytest.raises(ValueError,match='fifteen minutes'):
        a.fallback_context('r4',intent,fallback,tmp_path)
    original_receipt(intent,tmp_path,limit_seconds=3601)
    with pytest.raises(ValueError,match='cap'):
        a.fallback_context('r4',intent,fallback,tmp_path)
    original_receipt(intent,tmp_path,pod_id='known-id')
    with pytest.raises(ValueError,match='known pod ID'):
        a.fallback_context('r4',intent,fallback,tmp_path)


def test_fallback_preview_needs_no_key_or_network_and_redacts_public_key(intent,fallback,tmp_path,monkeypatch):
    original_receipt(intent,tmp_path)
    monkeypatch.delenv('RUNPOD_API_KEY',raising=False);monkeypatch.delenv('HF_TOKEN',raising=False)
    result=a.redacted_preview('r4',intent,fallback,out=tmp_path)
    assert result['mode']=='DRY_RUN_NO_NETWORK_OR_ALLOCATION'
    assert result['env_keys']==['PUBLIC_KEY'] and 'env' not in result['payload']
    assert 'ssh-ed25519' not in json.dumps(result)
    assert not (tmp_path/'r4/allocations').exists()


def test_fresh_query_must_reconcile_every_previous_fallback_name(intent,fallback,tmp_path):
    original_receipt(intent,tmp_path)
    prior=tmp_path/'r4/allocations/old.json';prior.parent.mkdir()
    prior.write_text(json.dumps({'experiment':'r4','name':'mats-rem-r4-old','status':'ALLOCATION_FAILED_OR_UNKNOWN'}))
    api=FakeApi([[{'id':'late-prior','name':'mats-rem-r4-old'}]])
    with pytest.raises(RuntimeError,match='Prior intended name'):
        a.allocate('r4',intent,api,'ssh-ed25519 PUBLIC',out=tmp_path,fallback=fallback)
    assert len(api.calls)==1


def test_same_experiment_allocation_lock_blocks_other_names(tmp_path):
    with a.allocation_lock('r4',tmp_path):
        with pytest.raises(RuntimeError,match='active'):
            with a.allocation_lock('r4',tmp_path): pass
        with a.allocation_lock('r5',tmp_path): pass


def test_offvolume_transport_supports_current_regions_without_credential_export(intent):
    calls=[]
    def opener(req,timeout):
        calls.append(req)
        return io.BytesIO(json.dumps({'data':{'podFindAndDeployOnDemand':{'id':'new','name':'offvol'}}}).encode())
    api=a.AllocationApi('FAKE_AUTH',opener=opener)
    payload=a.make_payload('r4',intent,'ssh-ed25519 PUBLIC',{'name':'offvol','data_center':'US-NC-2','gpu_type':'NVIDIA H200'})
    assert api.request(a.URL,'POST',payload)['id']=='new'
    assert calls[0].full_url=='https://api.runpod.io/graphql'
    query=json.loads(calls[0].data)['query']
    assert 'dataCenterId: "US-NC-2"' in query and 'containerDiskInGb: 200' in query
    assert 'volumeInGb: 0' in query and 'networkVolumeId' not in query
    assert 'FAKE_AUTH' not in query and 'HF_TOKEN' not in query
    payload['env']['HF_TOKEN']='forbidden'
    with pytest.raises(ValueError):a.offvolume_mutation(payload)


def test_graphql_capacity_errors_are_safe_and_unambiguous(intent):
    def opener(req,timeout):
        return io.BytesIO(json.dumps({'errors':[{'message':'There are no longer any instances available'}]}).encode())
    api=a.AllocationApi('FAKE_AUTH',opener=opener)
    payload=a.make_payload('r4',intent,'ssh-ed25519 PUBLIC',{'name':'offvol','data_center':'US-NC-2','gpu_type':'NVIDIA H200'})
    with pytest.raises(a.ApiError,match='graphql_capacity_unavailable'):api.request(a.URL,'POST',payload)
