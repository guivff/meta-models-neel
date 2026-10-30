from types import SimpleNamespace
import pytest
from . import e117_channel as ch
from .test_e117_source_units import fixture,records
from .e117_source_units import descriptor_rows,make_units
from .transport import ROOT,frozen_wire
from ..run import payload
from ..judgment_adapter402 import render_record


@pytest.mark.parametrize('part',['main','c'])
def test_exact_original_wire_and_phase_full_scope(part):
    d=descriptor_rows(*fixture());r,p=records(d,part);units,_=make_units(part,r,d,p)
    rubric=(ROOT/'projects/g_agreement/understand/wmech2/RUBRIC.md').read_text()
    unit=dict(units[0],rubric=rubric)
    protocol=SimpleNamespace(MODEL='google/gemini-3.1-flash-lite',PROVIDER='google-vertex/global',PROVIDER_NAME='Google')
    call,_=ch.original57_call(unit,protocol)
    assert frozen_wire(call,protocol)==payload([render_record(unit['data'],rubric)],rubric,'E56',protocol)
    custody=dict(experiment='E117',issuer='W-internals-C',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,part=part,original_E56_E57_rubric_sha256=ch.RUBRIC_SHA,original_E56_E57_descriptors_copied=True,all_degenerate_native_texts_retained=True)
    ch.check_scope(part,'E117',units,custody)
    with pytest.raises(ValueError):ch.check_scope('main' if part=='c' else 'c','E117',units,custody)


def test_process_local_four_total_two_c_deadline_and_null(monkeypatch):
    monkeypatch.setattr(ch,'source_gate',lambda:None);caps=dict(ch.transport.CAPS);expiry=ch.transport.EXPIRY;rate=ch.parallel_funded.MAX_429_RETRIES
    with pytest.raises(RuntimeError):
        with ch.worker('c'):
            assert ch.transport.CAPS['E117']==4 and ch.PHASE_LIMITS['c']==2
            assert ch.transport.EXPIRY==1793372400 and ch.parallel_funded.MAX_429_RETRIES==0
            assert ch.registered.normalized_code('original57',dict(status='UNPARSEABLE',result=None)) is None
            raise RuntimeError('restore')
    assert ch.transport.CAPS==caps and ch.transport.EXPIRY==expiry and ch.parallel_funded.MAX_429_RETRIES==rate


def test_paid_cutoff_after_pacing_and_phase_cost_ceiling(monkeypatch):
    sent=[];request=SimpleNamespace(post=lambda *a,**k:sent.append(a));obj=object.__new__(ch.E117Transport);obj.api=SimpleNamespace(requests=request);obj.admission=dict(part='c',phase_start_booked_usd='0.1')
    monkeypatch.setattr(ch.transport.Transport,'__enter__',lambda self:self);monkeypatch.setattr(ch.transport.Transport,'__exit__',lambda self,*a:None);monkeypatch.setattr(ch.E117Transport,'summary',lambda self:dict(actual_usd='0.1'))
    ch.E117Transport.__enter__(obj)
    assert str(obj.api.CAP)=='2.1'
    def expired():raise ValueError('authority ended')
    monkeypatch.setattr(ch.transport,'unpaused',expired)
    with pytest.raises(ValueError):request.post('https://openrouter.ai/api/v1/chat/completions')
    assert sent==[];ch.E117Transport.__exit__(obj,None,None,None)
