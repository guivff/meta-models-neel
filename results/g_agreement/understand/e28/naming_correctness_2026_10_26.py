"""§145 descriptive value-correctness check of sealed E28 step-400 free readouts.

No model calls, training, resampling, or registered-analysis invocation. Uses the
original E24 statement regex; both-value matches are separate from correct-only.
"""
from pathlib import Path
import argparse
import math
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import contract as C
sys.path.insert(0, str(C.ROOT))
from projects.g_agreement.understand.e24_statements import statement, PATTERNS


def report(input_dir, outputs, out):
    out=Path(out)
    if out.exists():raise ValueError('fresh descriptive output directory required')
    expected=C.read(C.HERE/'PULL_VERIFICATION_2026-10-26.json')
    preparation=C.read(C.HERE/'PREPARATION.json')
    sources=C.read(C.HERE/'SOURCE_MANIFEST.json')['files']
    regex_path='projects/g_agreement/understand/e24_statements.py'
    if C.sha(C.ROOT/regex_path)!=sources[regex_path]:raise ValueError('frozen E24 detector changed')
    sealed=C.HERE/'analysis_2026-10-26';C.verify(sealed,'ANALYSIS_SEAL.json')
    metrics=C.read(sealed/'METRICS.json')
    existing={(x['row'],x['arm']):x for x in metrics['cells']}
    C.verify(input_dir)
    if C.sha(input_dir/'INPUT_SEAL.json')!=preparation['input_seal_sha256']:
        raise ValueError('original E28 input seal required')
    private=input_dir/'test.labels.DO_NOT_STAGE.jsonl'
    if C.sha(private)!=preparation['private_test_labels_sha256']:
        raise ValueError('original sealed private label key required')
    labels=C.rows(private);lookup={x['id']:x for x in labels}
    test=C.rows(input_dir/'test.jsonl')
    if len(lookup)!=len(labels) or set(lookup)!={x['id'] for x in test}:
        raise ValueError('exact test label coverage required')
    expected_pulls={p['pod_id']:p for p in expected['pulls']}
    records={};bindings=[];seen=set()
    for root in map(Path,outputs):
        pod=root.parent.parent.name
        if pod not in expected_pulls or pod in seen:raise ValueError('original unique verified pulls required')
        seen.add(pod);ref=expected_pulls[pod]
        if C.sha(root/'RUN_RECEIPT.json')!=ref['run_receipt_sha256']:
            raise ValueError('original run receipt differs')
        for run,seal_hash in ref['score_seals'].items():
            row,arm=run.split('__');d=root/run
            if C.sha(d/'SCORE_SEAL.json')!=seal_hash:raise ValueError('original run seal differs')
            # Verify the original sealed free-readout bytes; do not reopen/recompute asked scores.
            seal=C.read(d/'SCORE_SEAL.json');free=d/'free.400.jsonl'
            if C.sha(free)!=seal['files'][free.name]:raise ValueError('sealed free readouts differ')
            raw=C.rows(free);ids={r['id'] for r in test if r['feature']==row}
            if len(raw)!=84 or {r['id'] for r in raw}!=ids or any(not isinstance(r['raw'],str) for r in raw):
                raise ValueError('84 unique matching free readouts required')
            if (row,arm) in records:raise ValueError('duplicate row/arm')
            statuses=[statement(row,r['raw']) for r in raw]
            status_counts={s:statuses.count(s) for s in sorted(set(statuses))}
            old=existing[row,arm]
            if status_counts!=old['free_statement_statuses']:
                raise ValueError('frozen detector does not reproduce sealed status counts')
            counts=None
            if row in PATTERNS:
                counts={'correct_only':0,'wrong_only':0,'both':0,'neither':0}
                for r,status in zip(raw,statuses):
                    target='A' if lookup[r['id']]['y'] else 'B'
                    if status in ('both','neither'):counts[status]+=1
                    elif status in ('A','B'):counts['correct_only' if status==target else 'wrong_only']+=1
                    else:raise ValueError('unexpected structure status')
                if sum(counts.values())!=84:raise ValueError('categories do not partition84')
                named=counts['correct_only']+counts['wrong_only']+counts['both']
                if (not math.isclose(counts['correct_only']/84,old['free_correct_statement_rate_ci95'][0],abs_tol=1e-12)
                    or not math.isclose(named/84,old['free_naming_rate_ci95'][0],abs_tol=1e-12)):
                    raise ValueError('descriptive counts disagree with sealed correctness/naming rates')
            else:
                named=None
                if status_counts!={'not_structure':84} or old['free_correct_statement_rate_ci95'] is not None:
                    raise ValueError('semantic naming must retain frozen not-evaluable handling')
            records[row,arm]={'row':row,'arm':arm,'status':'EVALUABLE' if counts is not None else 'NO_FROZEN_DETECTOR',
                'n':84,'counts':counts,'any_value_named':named,'frozen_statement_statuses':status_counts}
            bindings.append({'pod_id':pod,'run':run,'score_seal_sha256':seal_hash,'free_readouts_sha256':C.sha(free)})
    if seen!=set(expected_pulls) or set(records)!=set(C.RUNS):raise ValueError('all original14runs required')
    cells=[]
    for row in C.ROWS:
        for arm in ('L','S','B'):
            cells.append(records.get((row,arm),{'row':row,'arm':arm,'status':'NOT_REGISTERED_NOT_RUN','n':0,'counts':None,'any_value_named':None}))
    result={'experiment':'E28','date':'2026-10-26','authority':'BRIEF_UNDERSTAND §145 and direct user instruction',
        'status':'COMPLETE_DESCRIPTIVE_CHECK','checkpoint':400,'cells':cells,
        'category_definitions':{'correct_only':'Frozen regex names exactly the true A/B value',
            'wrong_only':'Frozen regex names exactly the opposite A/B value','both':'Frozen regex names both A and B; no correctness credit',
            'neither':'Frozen regex names neither A nor B'},
        'semantic_handling':'prose_sentiment has no frozen E24 detector; all84outputs per arm remain not evaluable, not counted as neither',
        'missing_arms':'S existed only for prose_paren and prose_sentiment; other S rows were not registered/run',
        'shuffled_paren_names_all84':records['prose_paren','S']['any_value_named']==84,
        'original_registered_verdicts_unchanged':True,'registered_analysis_invocations_this_check':0,
        'model_calls':0,'gpu_hours':0,'bootstrap_or_new_statistical_test':False,
        'verification':{'original_metrics_sha256':C.sha(sealed/'METRICS.json'),
            'original_analysis_seal_sha256':C.sha(sealed/'ANALYSIS_SEAL.json'),
            'private_labels_sha256':C.sha(private),'input_seal_sha256':C.sha(input_dir/'INPUT_SEAL.json'),
            'detector_sha256':C.sha(C.ROOT/regex_path),'script_sha256':C.sha(Path(__file__)),
            'pull_verification_sha256':C.sha(C.HERE/'PULL_VERIFICATION_2026-10-26.json'),
            'reproduces_sealed_status_counts_and_correctness_rates':True,'raw_files':bindings}}
    out.mkdir(parents=True,exist_ok=False);C.dump(out/'COUNTS.json',result)
    text=['# E28 step-400 naming correctness — 2026-10-26','','Descriptive only, under §145. The original sealed free-readout bytes and private label key were hash-verified. E24’s frozen regex was applied without changes; its status counts and correct-statement rates exactly reproduce the sealed analysis. No model calls, training, bootstrap or registered-analysis rerun.','','Correct and wrong mean **only** that value is named. Both-value matches are reported separately and receive no correctness credit. Counts in each evaluable row sum to84.','','| Row | Arm | Correct only | Wrong only | Both | Neither | Any value named |','|---|---|---:|---:|---:|---:|---:|']
    for c in cells:
        if c['counts'] is not None:
            v=c['counts'];vals=[str(v[k]) for k in ('correct_only','wrong_only','both','neither')]+[str(c['any_value_named'])+'/84']
        else:vals=[('not run' if c['status']=='NOT_REGISTERED_NOT_RUN' else 'N/E')]*5
        text.append('| '+c['row']+' | '+c['arm']+' | '+' | '.join(vals)+' |')
    shuffled=records['prose_paren','S']['counts']
    text+=['', '**The shuffled-label parentheses arm S also names a value in84/84 readouts:** '
        f"{shuffled['correct_only']} correct only, {shuffled['wrong_only']} wrong only, {shuffled['both']} both and {shuffled['neither']} neither.",
        'Thus the84/84 any-naming rate is not evidence of reading the correct value or of answering transferring to value-correct naming. In the shuffled arm it predominantly detects language naming both alternatives, consistent with the trained template. This is a descriptive reading of the frozen regex categories, not a new causal test.',
        '', 'S was not registered for strings, table role, depth or column; those cells are not run. The frozen E24 regex has no sentiment detector: L/S/B each has84 not_structure outputs, so correctness and naming remain N/E rather than being relabelled neither.',
        '', 'All original E28 verdicts remain unchanged. E39 stays as built and awaits E36’s verified captures; E37 stays ready.','']
    (out/'REPORT.md').write_text('\n'.join(text))
    C.seal(out,'DESCRIPTIVE_SEAL.json')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True)
    p.add_argument('--outputs',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();r=report(a.input,a.outputs,a.out)
    for c in r['cells']:print(c['row'],c['arm'],c['counts'] if c['counts'] is not None else c['status'])
