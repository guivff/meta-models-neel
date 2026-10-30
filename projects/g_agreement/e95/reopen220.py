"""Mechanical §220 gate. Reads sealed E87 outputs; never recomputes E87 statistics."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

MISSED = ('container_after_move','holder_after_handovers','branch_taken','var_type_at_use',
          'user_expertise','unit_system','nesting_depth','indent_level')


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def sealed(path):
    value = json.loads(path.read_text())
    for name, digest in value['files'].items():
        p = path.parent/name
        assert p.resolve().is_relative_to(path.parent.resolve()) and sha(p) == digest, name
    return value


def evaluate(analysis_seal=None, depth_seal=None):
    result = dict(experiment='E95',authority='§220 / 9c56f1a5',status='WAITING_E87_ANALYSIS_SEAL',
                  production_admitted=False,conditional_ceiling_gpu_hours=47)
    if analysis_seal is None:
        return result
    a = sealed(analysis_seal)
    assert a.get('experiment') == 'E87' and a.get('status') == 'COMPLETE_ONCE'
    assert 'RESULTS.json' in a['files']
    results = json.loads((analysis_seal.parent/'RESULTS.json').read_text())
    status = results['R_L1']['status']
    assert status in ('MET','NOT MET','FALSIFIED (single-site blind spot)',
                      'NOT EVALUABLE (a positive control failed)'), 'unrecognized sealed R-L1 status'
    result.update(e87_analysis_seal_sha256=sha(analysis_seal),R_L1=status)
    count = None
    if depth_seal is not None:
        d = sealed(depth_seal)
        assert 'DEPTH_PROFILE.json' in d['files']
        depth = json.loads((depth_seal.parent/'DEPTH_PROFILE.json').read_text())
        assert depth['experiment'] == 'E87' and set(MISSED) <= set(depth['rows'])
        classes = {r:depth['rows'][r]['class'] for r in MISSED}
        assert all(isinstance(v,str) and v for v in classes.values())
        count = sum(v in ('consumed','late') for v in classes.values())
        result.update(e87_depth_seal_sha256=sha(depth_seal),missed_row_classes=classes,
                      consumed_or_late_missed_rows=count)
    if status == 'NOT MET' or (count is not None and count >= 2):
        result['status'] = 'REOPEN_E95_DEVIATION_2'
    elif count is None:
        result['status'] = 'WAITING_E87_DEPTH_SEAL'
    else:
        result['status'] = 'KEEP_NOT_RUN'
    return result


def discover(root, corrected=False):
    tracked = subprocess.check_output(['git','ls-files','results/g_agreement'],cwd=root,text=True).splitlines()
    analysis, depth = [], []
    for name in tracked:
        p = root/name
        if corrected and 'correct' not in name.casefold():
            continue
        if p.name not in ('ANALYSIS_SEAL.json','DEPTH_SEAL.json'):
            continue
        value = json.loads(p.read_text())
        if p.name == 'ANALYSIS_SEAL.json' and value.get('experiment') == 'E87':
            analysis.append(p)
        if p.name == 'DEPTH_SEAL.json' and 'DEPTH_PROFILE.json' in value.get('files',{}):
            v = json.loads((p.parent/'DEPTH_PROFILE.json').read_text())
            if v.get('experiment') == 'E87':
                depth.append(p)
    assert len(analysis) <= 1 and len(depth) <= 1, 'ambiguous E87 seals; do not choose by outcome'
    return (analysis[0] if analysis else None, depth[0] if depth else None)


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);args=p.parse_args()
    result=evaluate(*discover(args.root));args.out.mkdir(parents=True,exist_ok=True)
    pending=result['status'].startswith('WAITING')
    path=args.out/('WATCH_STATUS.json' if pending else 'GATE_DECISION.json')
    data=json.dumps(result,indent=2)+'\n'
    if pending:
        path.write_text(data)
    elif path.exists():
        assert json.loads(path.read_text()) == result, 'once-only gate evidence changed'
    else:
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o644)
        with os.fdopen(fd,'w') as f:f.write(data)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
