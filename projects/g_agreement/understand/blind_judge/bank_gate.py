"""Metadata-only admission. Never opens a reader packet or calls an inference API."""
import argparse
import hashlib
import json
import subprocess
from decimal import Decimal
from pathlib import Path
from projects.g_agreement.readerbench.io import read, sha, write
from projects.g_agreement.readerbench.scoring import require

BANKS = {'E56', 'E57', 'E59', 'E61', 'E62', 'E63'}


def forecast_gate(bank, repo, commit, relative_path, expected_sha):
    require(bank in BANKS | {'E62P'}, 'bank outside explicit authorization')
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'full forecast commit required')
    path = Path(relative_path)
    require(not path.is_absolute() and '..' not in path.parts, 'repository-relative forecast path')
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit+':'+str(path)])
    require(hashlib.sha256(raw).hexdigest() == expected_sha, 'committed forecast bytes mismatch')
    require(sha(Path(repo)/path) == expected_sha, 'working forecast differs from committed version')
    data = json.loads(raw)
    require(data.get('experiment') == 'E52_R3b' and data.get('bank') == ('E62_PLACEBO' if bank == 'E62P' else bank),
            'actual bank-specific R3b forecast required; placeholder is insufficient')
    require(data.get('reader_outcomes_accessed') is False and data.get('no_backfill') is True,
            'prospective forecast provenance required')
    require(data.get('rows') and data.get('bank_seal_sha256') and data.get('capture_seal_sha256'),
            'forecast rows and bank/capture bindings required')
    epoch = int(subprocess.check_output(['git', '-C', str(repo), 'show', '-s', '--format=%ct', commit]))
    return {'bank': bank, 'forecast_commit': commit, 'forecast_sha256': expected_sha,
            'forecast_commit_epoch': epoch, 'bank_seal_sha256': data['bank_seal_sha256'],
            'capture_seal_sha256': data['capture_seal_sha256']}


def budget_gate(receipt):
    require(receipt.get('issuer') == 'integrator' and receipt.get('verified') is True,
            'integrator daily-budget allocation required')
    require(receipt.get('date_zurich') == '2026-10-27' and receipt.get('allocation_id'), 'dated allocation identity')
    require(set(receipt.get('banks', [])) == BANKS, 'authorized bank scope')
    require(receipt.get('reservation_included') is True, 'reserve new judging allocation in daily commitments')
    amount = Decimal(str(receipt['reserved_judging_usd']))
    daily = Decimal(str(receipt['daily_committed_including_reservation_usd']))
    require(amount.is_finite() and daily.is_finite() and amount == Decimal('15') and
            amount <= daily <= Decimal('300'), 'USD15 allocation must fit daily USD300 ceiling')
    return receipt['allocation_id']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    spec = read(a.spec)
    # Forecast check is first; no reader file path is accepted by this command.
    result = forecast_gate(spec['bank'], spec['forecast_repo'], spec['forecast_commit'],
                           spec['forecast_path'], spec['forecast_sha256'])
    require(sha(spec['budget_receipt']) == spec['budget_receipt_sha256'], 'budget receipt hash')
    result['daily_allocation_id'] = budget_gate(read(spec['budget_receipt']))
    require(not a.out.exists(), 'admission receipt exists')
    result.update(status='FORECAST_AND_BUDGET_GATES_PASS_NOT_PACKET_VERIFICATION',
                  judge_calls=0, reader_outputs_opened=False)
    write(a.out, result)


if __name__ == '__main__':
    main()


def coordinator_gate(bank, repo, commit, relative_path, expected_sha):
    """Only an explicit committed E63 no-forecast ruling can replace its forecast."""
    require(bank == 'E63', 'coordinator exception is scoped to E63')
    require(len(commit) == 40 and all(c in '0123456789abcdef' for c in commit), 'full coordinator commit')
    path = Path(relative_path)
    require(not path.is_absolute() and '..' not in path.parts, 'relative coordinator path')
    raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit+':'+str(path)])
    require(hashlib.sha256(raw).hexdigest() == expected_sha and sha(Path(repo)/path) == expected_sha,
            'committed coordinator record binding')
    data = json.loads(raw)
    require(data.get('experiment') == bank and data.get('status') == 'RATIFIED' and
            data.get('forecast_required') is False and data.get('ratified_by') and
            data.get('committed_before_any_reader_output') is True, 'explicit prospective ratified ruling required')
    require(data.get('bank_seal_sha256') and data.get('capture_seal_sha256'), 'ruling bank/capture scope')
    return dict(bank=bank,forecast_commit=commit,forecast_sha256=expected_sha,
                bank_seal_sha256=data['bank_seal_sha256'],capture_seal_sha256=data['capture_seal_sha256'])
