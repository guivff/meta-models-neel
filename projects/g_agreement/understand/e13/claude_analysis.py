"""Aggregate the externally sealed blind Claude codes; no annotation or API."""
import json
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from . import io as I, protocol as P
from .analyse import rate, paired


def kappa(a, b):
    if len(a) != len(b):
        raise ValueError('unmatched coders')
    n = len(a)
    if not n:
        return dict(n=0, agreement=None, expected_agreement=None, kappa=None, confusion={})
    ca, cb = Counter(a), Counter(b)
    po = sum(x == y for x, y in zip(a, b)) / n
    pe = sum(ca[c] * cb[c] for c in set(a) | set(b)) / n**2
    return dict(n=n, agreement=po, expected_agreement=pe,
                kappa=(po-pe)/(1-pe) if pe < 1 else None,
                confusion={f'{x}|{y}':v for (x,y),v in sorted(Counter(zip(a,b)).items())})


def accuracy(rows, flag, value):
    chosen = [r for r in rows if r[flag]]
    resolved = [r for r in chosen if r[value] in ['A','B']]
    correct = sum(r[value] == r['truth'] for r in resolved)
    truths = Counter(r['truth'] for r in resolved)
    ci = rate(correct, len(resolved))
    return dict(occurrence=rate(len(chosen), len(rows)),
                correct_among_occurrences=rate(correct, len(chosen)),
                correct_among_resolved=ci,
                unresolved=len(chosen)-len(resolved),
                resolved_truth_counts={v:truths[v] for v in ['A','B']},
                majority_truth_baseline=max(truths.values())/len(resolved) if resolved else None,
                resolved_wilson_lower_gt_half=ci['ci95'][0] > .5 if resolved else None)


def main():
    started = time.monotonic()
    check = I.read(I.OUT/'CLAUDE_PREJOIN_VERIFICATION.json')
    note = 'results/g_agreement/understand/e13/CLAUDE_JOIN_NOTE.md'
    if subprocess.check_output(['git','show','HEAD:'+note], cwd=I.ROOT) != (I.ROOT/note).read_bytes():
        raise ValueError('join note not committed')
    receipts = I.read(I.OUT/'CLAUDE_SAMPLES_RECEIPT.json')
    folder = I.CACHE/'claude_codes'
    if I.sha(folder/'CLAUDE_CODES_SEAL.json') != check['codes_seal_sha256']:
        raise ValueError('Claude code seal changed')
    s84 = I.read(I.OUT/'QUESTIONS_S84.json')
    all_rows = []
    for scope in ['w1','s84']:
        codefile = folder/f'{scope}.CLAUDE_CODES.jsonl'
        if I.sha(codefile) != check['samples'][scope]['codes_sha256']:
            raise ValueError('Claude codes changed')
        rec = receipts[scope]
        if I.sha(Path(rec['sample'])) != check['samples'][scope]['input_sha256'] or I.sha(Path(rec['key_cache_only'])) != rec['key_sha256']:
            raise ValueError('blind input or key changed')
        # First authorized local Claude-code/private-key join occurs here.
        keys = {r['id']:r for r in I.rows(Path(rec['key_cache_only']))}
        codes = I.rows(codefile)
        if len(codes) != 300 or {r['id'] for r in codes} != set(keys):
            raise ValueError('key/code coverage')
        for code in codes:
            key = keys[code['id']]
            values = P.QUESTIONS[key['feature']]['values'] if scope == 'w1' else s84[key['feature']]['values']
            if key['label'] not in values:
                raise ValueError('truth is outside question mapping')
            all_rows.append({**code,**key,'scope':scope,'truth':'A' if key['label']==values[0] else 'B'})
    results = []
    differences = []
    for scope in ['w1','s84']:
        features = list(dict.fromkeys(r['feature'] for r in all_rows if r['scope']==scope))
        for feature in features:
            group = [r for r in all_rows if r['scope']==scope and r['feature']==feature]
            for reader in ['oracle','nla']:
                rows = [r for r in group if r['reader']==reader]
                results.append(dict(scope=scope,feature=feature,reader=reader,layer=rows[0]['layer'],n=len(rows),
                                    mentions=accuracy(rows,'mentions','value'), enacts=accuracy(rows,'enacts','enact_value')))
            pairs = {}
            for r in group:
                pairs.setdefault(r['item'],{})[r['reader']]={'mention':r['mentions'],'correct':r['mentions'] and r['value']==r['truth']}
            if any(set(v)!={'oracle','nla'} for v in pairs.values()):
                raise ValueError('unpaired reader items')
            differences.append(dict(scope=scope,feature=feature,**paired(pairs)))
    apiseal = I.read(I.OUT/'CODING_SEAL.json')
    if I.sha(I.CACHE/'codes.blind.json') != apiseal['sha256']:
        raise ValueError('API codes changed')
    api = {r['case_id']:r for r in I.read(I.CACHE/'codes.blind.json')}
    w1 = [r for r in all_rows if r['scope']=='w1']
    if set(api) != {r['id'] for r in w1} or any(r['status']!='OK' for r in api.values()):
        raise ValueError('W1/API overlap invalid')
    kappas = []
    for feature in ['ALL'] + list(P.QUESTIONS):
        for reader in ['ALL','oracle','nla']:
            rows = [r for r in w1 if (feature=='ALL' or r['feature']==feature) and (reader=='ALL' or r['reader']==reader)]
            a = [str(r['mentions']) for r in rows]
            b = [str(api[r['id']]['code']['mentions']) for r in rows]
            both = [r for r in rows if r['mentions'] and api[r['id']]['code']['mentions']]
            canon = lambda v:v if v in ['A','B'] else 'unclear'
            kappas.append(dict(feature=feature,reader=reader,mentions=kappa(a,b),
                               values_among_both_mention=kappa([canon(r['value']) for r in both],[canon(api[r['id']]['code']['value']) for r in both])))
    data = dict(status='DESCRIPTIVE_INDEPENDENT_CLAUDE_CODES',at=datetime.now(timezone.utc).isoformat(),rows=results,
                w1_api_kappa=kappas,paired_differences=differences,
                prejoin_verification_sha256=I.sha(I.OUT/'CLAUDE_PREJOIN_VERIFICATION.json'),join_note_sha256=I.sha(I.OUT/'CLAUDE_JOIN_NOTE.md'),
                api_comparator='Original unchanged API codes failed the construct audit; kappa is agreement, not validity.',
                chance_reference='Resolved A/B accuracy versus0.5 is descriptive, unadjusted for multiple rows. Truth prevalence among resolved mentions and majority-class baseline also reported.',
                api_calls=0,gpu_hours=0,wall_s=time.monotonic()-started)
    I.save(I.OUT/'CLAUDE_METRICS.json',data)
    fmt = lambda r:'UNAVAILABLE' if r['rate'] is None else f"{r['k']}/{r['n']} = {100*r['rate']:.1f}% [{100*r['ci95'][0]:.1f}, {100*r['ci95'][1]:.1f}]"
    lines = ['# E13(b): independently blinded Claude codes', '',
             'DESCRIPTIVE. All600 codes/evidence and exact input hashes verified before key join; no missing codes or exclusions. W1:75readouts/reader/row; §84:15/reader/row. Native Oracle L44 and NLA L42. All intervals Wilson95%. Samples are matched within item and stratified by row/truth. No new API/GPU work.', '',
             '**Coding notes fixed before key join:** A/B/unclear replaced yes/no/specific; enact_value was added. Some coders treated explicit naming of the current token as a mention and derived the value from it. Codes are unchanged; mention here can therefore include token identification rather than an explicit feature assertion. Verbatim evidence proves source correspondence, not semantic coding correctness.', '',
             '| Row | Reader / site | Mention rate | Correct / all mentions | Correct / resolved mentions | Enact rate | Correct / all enacts | Correct / resolved enacts |',
             '|---|---|---|---|---|---|---|---|']
    for r in results:
        m,e=r['mentions'],r['enacts']
        lines.append(f"| {r['scope']} / {r['feature']} | {r['reader']} L{r['layer']} | {fmt(m['occurrence'])} | {fmt(m['correct_among_occurrences'])} | {fmt(m['correct_among_resolved'])} | {fmt(e['occurrence'])} | {fmt(e['correct_among_occurrences'])} | {fmt(e['correct_among_resolved'])} |")
    lines += ['', 'Unclear values remain in the all-mention/all-enact accuracy denominator and are never counted as correct. Resolved accuracy excludes unclear values and is shown separately. Zero denominators are unavailable. A/B follow each question, not a global yes/no interpretation.', '',
              '## NLA value accuracy and the0.5 reference', '',
              'No confirmatory chance test or multiple-comparison verdict was registered. Below are descriptive resolved-value Wilson intervals, not new inferential claims. Mention selection changes truth prevalence; the majority-truth baseline is shown and may exceed0.5.', '',
              '| Row | NLA correct/resolved mentions [Wilson95%] | Unclear mentions | Truth A/B among resolved | Majority-truth baseline | Lower bound >0.5 |',
              '|---|---|---:|---|---:|---|']
    for r in results:
        if r['reader']!='nla':continue
        m=r['mentions'];t=m['resolved_truth_counts'];base=m['majority_truth_baseline']
        lines.append(f"| {r['scope']} / {r['feature']} | {fmt(m['correct_among_resolved'])} | {m['unresolved']} | {t['A']}/{t['B']} | {base:.3f} | {m['resolved_wilson_lower_gt_half']} |" if base is not None else f"| {r['scope']} / {r['feature']} | UNAVAILABLE | {m['unresolved']} | 0/0 | UNAVAILABLE | UNAVAILABLE |")
    lines += ['', '## Agreement with the original API coder (W1 only)', '',
              'The API coder failed the earlier construct audit and is not a gold standard. Binary mention κ uses every overlap record; value κ uses only records where both coders mention (A/B/unclear). API UNSPECIFIED/CONFLICT map to unclear for this comparison only. The API did not code enactment, so enactment κ is unavailable.', '',
              '| Row | Reader | Mention n / agreement / κ | Both mention: n / value agreement / κ |',
              '|---|---|---|---|']
    def kfmt(k):
        return f"{k['n']} / {k['agreement']:.3f} / " + (f"{k['kappa']:.3f}" if k['kappa'] is not None else 'UNDEFINED') if k['n'] else '0 / UNAVAILABLE / UNDEFINED'
    for r in kappas:lines.append(f"| {r['feature']} | {r['reader']} | {kfmt(r['mentions'])} | {kfmt(r['values_among_both_mention'])} |")
    lines += ['', 'Registered item-paired NLA-minus-Oracle mention and accuracy differences (2000bootstrap draws, seed20261024, original implementation) are in CLAUDE_METRICS.json. Accuracy uses correct/all mentions; too few jointly evaluable bootstrap draws leave an interval unavailable. No coding exclusions, semantic repairs, new sample selection or changes to previous API/keyword seals. No whole-bank or model-mechanism verdict follows.']
    (I.OUT/'CLAUDE_RESULTS.md').write_text('\n'.join(lines)+'\n')
    I.save(I.OUT/'CLAUDE_ANALYSIS_SEAL.json',dict(status='SEALED_CLAUDE_AGGREGATES',files={n:I.sha(I.OUT/n) for n in ['CLAUDE_METRICS.json','CLAUDE_RESULTS.md','CLAUDE_JOIN_NOTE.md','CLAUDE_PREJOIN_VERIFICATION.json']}))
    print('Claude aggregates and kappa written')


if __name__=='__main__':main()
