"""§205(5) rival forecast comparison. Paired rows; does not modify E75."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np

TAGS = {'continuation constraint', 'numerical coordinate', 'binding to earlier context'}
SEED = 20261028
DRAWS = 2000


def balanced_accuracy(truth, prediction):
    truth, prediction = np.asarray(truth, bool), np.asarray(prediction, bool)
    if not truth.any() or truth.all():
        return None
    return float(((prediction[truth] == truth[truth]).mean() +
                  (prediction[~truth] == truth[~truth]).mean()) / 2)


def compare(rows):
    """Each record carries the two fixed forecasts and sealed reporting truth."""
    if len(rows) != 40 or len({r['row'] for r in rows}) != 40:
        raise ValueError('Exactly 40 distinct properties, one unit per property')
    if any(r['taxonomy'] not in TAGS for r in rows):
        raise ValueError('Only frozen taxonomy tags accepted')
    if any(type(r[k]) is not bool for r in rows for k in ('reported', 'j_reported')):
        raise ValueError('Explicit boolean truth and J forecast required')
    truth = np.array([r['reported'] for r in rows])
    jp = np.array([r['j_reported'] for r in rows])
    tp = np.array([r['taxonomy'] == 'continuation constraint' for r in rows])
    jba, tba = balanced_accuracy(truth, jp), balanced_accuracy(truth, tp)
    common = dict(n=40, reported=int(truth.sum()), missed=int((~truth).sum()),
                  agreement=float((jp == tp).mean()), seed=SEED, bootstrap_draws=DRAWS)
    if jba is None:
        return dict(common, verdict='NOT EVALUABLE', reason='Balanced accuracy requires both truth classes')
    rng = np.random.default_rng(SEED)
    deltas = []
    for _ in range(DRAWS):
        indices = rng.integers(0, 40, size=40)
        a = balanced_accuracy(truth[indices], jp[indices])
        b = balanced_accuracy(truth[indices], tp[indices])
        if a is not None:
            deltas.append(a-b)
    if not deltas:
        return dict(common, verdict='NOT EVALUABLE', reason='No defined bootstrap draws')
    ci = np.quantile(deltas, [.025, .975]).tolist()
    delta = jba - tba
    return dict(common, j_balanced_accuracy=jba, taxonomy_balanced_accuracy=tba,
                delta=delta, paired_row_bootstrap_95=ci,
                bootstrap_valid=len(deltas), bootstrap_undefined=DRAWS-len(deltas),
                verdict='MET' if delta >= .10 and ci[0] > 0 else 'NOT MET',
                falsifier=delta <= 0)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--plan', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    plan = json.loads(a.plan.read_text())
    # Integrator must freeze all bindings after judgments, before once-only invocation.
    import subprocess
    root = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
    relative = a.plan.resolve().relative_to(root)
    if subprocess.check_output(['git', 'show', 'HEAD:'+str(relative)]) != a.plan.read_bytes():
        raise ValueError('Committed analysis plan required')
    if digest(__file__) != plan['analysis_source_sha256']:
        raise ValueError('Frozen analysis source mismatch')
    refs = plan['inputs']
    for ref in refs.values():
        if digest(ref['path']) != ref['sha256']:
            raise ValueError('Input digest mismatch')
    custody = json.loads(Path(refs['custody']['path']).read_text())
    if not (custody['taxonomy_committed_epoch'] < custody['capture_started_epoch'] <
            custody['forecast_committed_epoch'] < custody['go_epoch'] <=
            custody['reader_started_epoch'] <= custody['outputs_opened_epoch']):
        raise ValueError('Prospective custody ordering failed')
    rows = json.loads(Path(refs['joined_rows']['path']).read_text())
    a.out.mkdir(parents=True, exist_ok=False)  # once-only namespace, never reset
    result = {reader: dict(compare(rows[reader]),
                role='CONFIRMATORY_R_T1' if reader == 'oracle' else 'DESCRIPTIVE')
              for reader in ('oracle', 'nla')}
    (a.out/'RESULTS.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    from datetime import datetime, timezone
    first = a.out/'RESULTS.json'
    (a.out/'ANALYSIS_SEAL.json').write_text(json.dumps({'experiment':'E97_TAXONOMY',
          'first_output_utc':datetime.fromtimestamp(first.stat().st_mtime, timezone.utc).isoformat(),
          'first_output_evidence':{'source':'archived_file_mtime', 'path':'RESULTS.json',
                                   'mtime_ns':first.stat().st_mtime_ns},
          'plan_sha256':digest(a.plan), 'files':{'RESULTS.json':digest(a.out/'RESULTS.json')}},indent=2)+'\n')


if __name__ == '__main__':
    main()
