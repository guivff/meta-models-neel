"""b1ba81c12 operational partitions of the unchanged frozen E95 judge sample.

No scoring, sampling, parsing or acquisition is performed here.
"""
import os
import hashlib
from pathlib import Path

from projects.g_agreement.readerbench.io import read, write, sha, verify
from projects.g_agreement.readerbench.scoring import require

AUTHORITY = 'b1ba81c12f65194d85659084d66830de2d5190aa'
STAGES = {1: ('oracle', (44, 52, 60)),
          2: ('oracle', (20, 28, 36, 56)),
          3: ('nla', (42,))}


def stage_ids(expected, stage):
    require(type(stage) is int and stage in STAGES, 'registered E95 judging stage')
    reader, layers = STAGES[stage]
    return {gid for gid, (stratum, unit) in expected.items()
            if stratum.rsplit(':', 1)[1] == reader
            and int(unit.rsplit(':', 1)[1]) in layers}


def partition(wanted, expected, stage):
    """Intersect the original chosen IDs, without selecting any new group."""
    require(set(wanted) <= set(expected), 'only original E95 identities')
    return set(wanted) & stage_ids(expected, stage)


def claim(ledger, stage, packet_sha, out):
    """One canonical bank guard per stage, independent of packet/output names."""
    require(type(stage) is int and stage in STAGES, 'registered E95 judging stage')
    ledger = Path(ledger)
    require(ledger.name == 'e95_60usd', 'same lifetime E95 ledger')
    ledger.mkdir(parents=True, exist_ok=True)
    if stage > 1:
        previous = read(ledger / f'STAGE{stage-1}_ONCE.json')
        marker=ledger/f'STAGE{stage-1}_TERMINAL.json'
        completed=read(marker)if marker.exists()else None
        seal_path=Path(completed['seal'])if completed else Path(previous['out'])/'JUDGMENT_SEAL.json'
        if completed:verify(seal_path,completed['sha256'])
        seal = read(seal_path)
        require(seal.get('status') == 'TERMINAL_BLIND_GRID_NO_ANALYSIS'
                and seal.get('judging_stage') == stage-1,
                'previous complete terminal stage required')
    path = ledger / f'STAGE{stage}_ONCE.json'
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(fd)
    write(path, dict(authority=AUTHORITY, judging_stage=stage, pid=os.getpid(),
                     packet_seal_sha256=packet_sha, out=str(Path(out).resolve())))
    return path


def continuation(spec,items,api,protocol,io):
    """Continue only unsent groups, retaining the original guard and unknowns."""
    from projects.g_agreement.understand.blind_judge import e87
    ledger=Path(spec['ledger_root']);stage=spec['judging_stage'];r=spec['continuation']
    guard=ledger/f'STAGE{stage}_ONCE.json'
    require(sha(guard)==r['original_once_sha256'],'original stage onceguard unchanged')
    g=read(guard)
    require(g['packet_seal_sha256']==spec['packet_seal_sha256'],'same original stage packet')
    prior=Path(g['out'])/'JUDGMENT_SEAL.json'
    require(str(prior)==r['previous_partial_seal'],'original stopped output namespace')
    s=verify(prior,r['previous_partial_seal_sha256'])
    require(s['status']=='BLOCKED_PARTIAL_NO_ANALYSIS','only stopped prior stage, never terminal replay')
    book,done=api.Ledger(ledger/'ledger.jsonl').totals()
    expected={x['id']:x for x in items};held=set()
    require(spec['preserved_missing']==r['preserved_missing'] and bool(spec['preserved_missing']),
            'explicit unchanged unknown-group dispositions')
    for gid,rid in spec['preserved_missing'].items():
        require(gid in expected and rid in book and rid not in done,'original unknown reservation stays unknown')
        folder=ledger/('E95_'+spec['packet_seal_sha256'][:16]+'_attempt0')
        p=folder/(rid+'.request.json')
        require(sha(p)==r['request_sha256'][rid] and not(folder/(rid+'.response.json')).exists(),
                'original saved request without response; never fabricate a charge/output')
        wire=e87.wire([expected[gid]],protocol)
        require(read(p)['wire']==wire,'exact original admitted wire/group, no order join')
        prefix='E95_'+spec['packet_seal_sha256'][:16]+':0:'
        require(hashlib.sha256((prefix+io.canonical(wire)).encode()).hexdigest()==rid,
                'original physical request identity')
        held.add(rid)
    require(set(book)-done==held,'all unknowns explicitly retained, no other ambiguous send')
    path=ledger/f'STAGE{stage}_CONTINUATION1_ONCE.json'
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    write(path,dict(authority=AUTHORITY,stage=stage,pid=os.getpid(),
        original_once_sha256=sha(guard),previous_partial_seal_sha256=sha(prior),
        packet_seal_sha256=spec['packet_seal_sha256'],out=str(Path(spec['out']).resolve()),
        preserved_unknown_request_ids=sorted(held),resend_unknown=False,reset_guard=False))
    return path


def complete(ledger,stage,out):
    ledger=Path(ledger);seal=Path(out)/'JUDGMENT_SEAL.json';s=verify(seal,sha(seal))
    require(s.get('status')=='TERMINAL_BLIND_GRID_NO_ANALYSIS'and s.get('judging_stage')==stage,
            'complete stage seal only')
    p=ledger/f'STAGE{stage}_TERMINAL.json'
    fd=os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    write(p,dict(judging_stage=stage,seal=str(seal.resolve()),sha256=sha(seal),original_guard_reset=False))
