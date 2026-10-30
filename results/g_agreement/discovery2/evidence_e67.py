"""Read-only, local discovery helpers. Never serializes private joins or reruns analysis.
Run/import with python -B. Callers must output aggregates and public opaque excerpts only.
"""
import hashlib
import json
from pathlib import Path

INTEGRATION=Path('/Users/guivff/Documents/Neel_Exploration/activation-readers/.claude/worktrees/phase-r-integration-8abda6')
WORK=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers')

def read(p):
    return json.loads(Path(p).read_text())
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verified_read(p, expected):
    assert digest(p)==expected, 'Source hash changed'
    return read(p)
def verify_files(folder, seal, names=None):
    for name in (names or seal['files']):
        assert digest(folder/name)==seal['files'][name], 'Sealed source hash changed'

def load_e67(wave):
    """Return records with public id/text/prompt/claims + IN-MEMORY reader/bank/row/condition.
    Do not dump returned records: condition and row joins originate in private custody.
    """
    assert wave in (1,2)
    base=INTEGRATION/'results/g_agreement/r/e67_analysis'
    analysis=read(base/f'wave{wave}_once/ANALYSIS_SEAL.json')
    assert analysis['status']=='COMPLETE_ONCE'
    verify_files(base/f'wave{wave}_once', analysis)
    spec=verified_read(base/f'ANALYSIS_SPEC.wave{wave}.json',analysis['spec_sha256'])
    private=Path(spec['private_seal'])
    seal=verified_read(private,spec['private_seal_sha256'])
    mapping=verified_read(private.parent/'PAIRING_CONDITION_MAP.PRIVATE.json',seal['files']['PAIRING_CONDITION_MAP.PRIVATE.json'])
    public=WORK/f'wt-wtext/results/g_agreement/understand/e67/judge_wave{wave}'
    packet_seal=read(public/'JUDGE_PACKET_SEAL.json')
    assert digest(public/'JUDGE_PACKET_SEAL.json')==mapping['packet_seal_sha256']
    packets={}
    judgments={}
    for n in (1,2):
        path=public/f'packet_{n:02d}.jsonl'
        assert digest(path)==packet_seal['files'][path.name]
        packets.update({x['id']:x for x in map(json.loads,path.read_text().splitlines())})
        terminal=spec['terminal_grids'][str(n)]
        directory=Path(terminal['dir'])
        jseal=verified_read(directory/'RESULT_SEAL.json',terminal['result_seal_sha256'])
        j=verified_read(directory/'JUDGMENTS.json',jseal['files']['JUDGMENTS.json'])
        judgments.update({x['id']:x for x in j})
    result=[]
    for pair in mapping['pairs']:
        for rec in pair['records']:
            p=packets[rec['id']];j=judgments[rec['id']]
            assert hashlib.sha256(p['readout'].encode()).hexdigest()==pair['readout_sha256']
            code=j.get('code') or {}
            result.append(dict(wave=wave,id=p['id'],text=p['readout'],prompt=p['prompt_text'],claims=code.get('claims',[]),generic=code.get('generic'),status=j['status'],reader=pair['reader'],bank=pair['bank'],row=pair['row'],condition=rec['condition'],truncation_cohort=pair['truncation_cohort'],native_max_new_tokens=pair['native_max_new_tokens']))
    assert len(result)==len(packets)==len(judgments)
    return result

def load_e76():
    """Return public readout objects only; no source items or label maps are loaded."""
    base=WORK/'wt-wtext/results/g_agreement/understand/e76'
    seal=read(base/'regex_20261027/ANALYSIS_SEAL.json')
    assert seal['status']=='REGEX_COMPLETE_ONCE'
    verify_files(base/'regex_20261027',seal)
    once=read(base/'REGEX_ANALYSIS.RUN_ONCE.json')
    final=WORK/'wt-wsae/cache/g_agreement/understand/e76/verified-pull/final'
    source=verified_read(final/'OUTPUT_SEAL.json',once['output_seal_sha256'])
    assert source['status']=='COMPLETE'
    result=[]
    for reader in ('oracle','nla'):
        p=final/f'{reader}.jsonl'
        assert digest(p)==source['files'][p.name]
        result.extend(map(json.loads,p.read_text().splitlines()))
    assert len(result)==2000
    return result
