"""Mechanical §237 gates; no acquisition, outcome reading or trigger inference."""
from datetime import datetime, timezone
CUTOFF = datetime(2026,10,30,7,tzinfo=timezone.utc)
CREATE = datetime(2026,10,30,10,tzinfo=timezone.utc)
HARD_STOP = datetime(2026,10,30,12,50,tzinfo=timezone.utc)
DUTIES = {'E127':'f5fa22316977a07822e73717424b6495f41c92e8',
          'E128':'b82dbb52f87aada7bc6bc6088bb2762b7afe8750',
          'classifier':'8d1b4e1355eb042ab9702de6d14d9b40e5b1c1d8'}


def instant(s):
    x=datetime.fromisoformat(s.replace('Z','+00:00'))
    if x.tzinfo is None:raise ValueError('explicit timezone required')
    return x


def e129_trigger(report, sealed_at):
    """Only a sealed E127 analysis can trigger; never inspect raw outputs here."""
    if instant(sealed_at)>CUTOFF:return 'NOT_RUN_OPERATIONAL'
    if report.get('experiment')!='E127' or report.get('status')!='COMPLETE_ONCE':
        raise ValueError('actual sealed E127 analysis required')
    n=report['flipped_n']
    if type(n)is not int or not 0<=n<=84:raise ValueError('original84 flipped count')
    if n<50:return 'TRIGGERED'
    a,b=report['R_NAT1'],report['falsifier']
    if a not in ('MET','NOT MET','NOT EVALUABLE') or b not in ('MET','NOT MET','NOT EVALUABLE'):
        raise ValueError('sealed E127 registered rule dispositions')
    return 'TRIGGERED' if a!='MET' and b!='MET' else 'NOT_RUN_NOT_NEEDED'


def e130_admit(receipt, packet_sha, packet_sealed_at, now):
    if instant(packet_sealed_at)>CUTOFF or now>CREATE:raise ValueError('E130 deadline missed')
    if receipt.get('experiment')!='E130' or receipt.get('input_sha256')!=packet_sha:
        raise ValueError('exact E130 sealed packet admission')
    if receipt.get('runner_duties_delivered')!=DUTIES:raise ValueError('E127/E128 runner duties not delivered')
    if receipt.get('adapter_tests_passed') is not True or len(receipt.get('adapter_commit',''))!=40 or any(c not in '0123456789abcdef' for c in receipt.get('adapter_commit','')):
        raise ValueError('tested committed W-lens adapter before output opening')
    if receipt.get('operator')!='Track Q' or receipt.get('cap_seconds',0)<=0:
        raise ValueError('sole operator and explicit positive original cap')
    if receipt.get('attempt_kind')=='planning':
        if receipt['cap_seconds']>1800:raise ValueError('original .5GPUh planning cap')
    elif receipt.get('attempt_kind')=='measured':
        if len(receipt.get('prior_no_fit_seal',''))!=64 or receipt.get('measured_need_seconds',0)<=0 or receipt['cap_seconds']>1.25*receipt['measured_need_seconds']+60:
            raise ValueError('one registered measured reattempt requires original NO_FIT and measured bound')
    else:raise ValueError('explicit planning or sole measured attempt')
    if instant(receipt['hard_stop_utc'])>HARD_STOP:raise ValueError('Friday hard stop')
    return True
