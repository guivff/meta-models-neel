"""CPU entry point; W-core adapters provide sealed cached readouts, never run here."""
import argparse
from pathlib import Path
from .io import load_bundle, write, seal_output, verify_sources
from .scoring import require, summarize, contrast, validate_judgments


def score(data, reader, judge=False):
    require(data.get('schema') == 'readerbench-scoring-v1', 'unknown schema')
    rows = [r for r in data['rows'] if r['reader'] == reader]
    require(bool(rows), 'reader has no rows')
    require(len({(r['bank'], r['row']) for r in rows}) == len(rows), 'duplicate rows')
    report = []
    for row in rows:
        require(row['analysis_status'] == 'COMPLETE_ONCE' and row['analysis_seal_sha256'],
                'bank once-only analysis must be sealed before scoring')
        require(row['native_status'] in ('REPORTED', 'MISSED', 'NOT_EVALUABLE'), 'native status required')
        require(row.get('channel') == 'native', 'off-distribution channel forbidden')
        judgments = None
        if judge:
            require(row.get('judge_route_seal_sha256') and row.get('judgment_seal_sha256'),
                    'sealed judge route and judgments required')
            j = validate_judgments(row['judge_packet'], row['judgments'], 'E56')
            # Public packet IDs are opaque; the private join maps each source record.
            join = row['private_join']
            require(set(join) == {r['id'] for r in row['readouts']} and
                    set(join.values()) == set(j) and len(join) == len(j), 'private join grid')
            judgments = {k: set(j[v]['values']) for k, v in join.items()}
        metric = summarize(row['readouts'], row['patterns'], judgments)
        floors = {}
        for arm in ('random', 'shuffled'):
            pool = [r for r in data['placebo'] if r['reader'] == reader and r['arm'] == arm]
            floors[arm] = contrast(row['readouts'], pool, row['patterns'],
                                   row['native_status'] == 'REPORTED') if pool else {'status': 'PENDING'}
        report.append({'bank': row['bank'], 'row': row['row'], 'native_status': row['native_status'],
                       'metric': metric, 'placebo_regex': floors,
                       'J_fraction': row.get('J_fraction'), 'J_label': row.get('J_label'),
                       'E58a_category': row.get('E58a_category'), 'layer': row['layer'],
                       'prompt': row['prompt'], 'controlling_experiment': row['controlling_experiment'],
                       'analysis_seal_sha256': row['analysis_seal_sha256']})
    return {'reader': reader, 'rows': report, 'E60_crossing': data.get('E60_crossing', {}).get(reader),
            'caveats': 'Native channels only. Regex measures word occurrence, not assertion. '
                       'Both-value and neither-value readouts score zero. Repeats cluster by item.'}


def card(report):
    lines = ['# Reader card: '+report['reader'], '', report['caveats'], '',
             'E60 P(report)=0.5 crossing: '+str(report['E60_crossing']), '',
             '| Bank / row | Registered status | S [95% CI] | E58a | J fraction | Control |',
             '|---|---|---|---|---|---|']
    for r in report['rows']:
        m = r['metric']
        lines.append(f"| {r['bank']} / {r['row']} | {r['native_status']} | {m['S']:.3f} {m['S_ci']} | "
                     f"{r['E58a_category']} | {r['J_fraction']} | {r['controlling_experiment']} |")
    lines += ['', '## Native channels and placebo floor', '']
    for r in report['rows']:
        lines.append(f"- {r['bank']}/{r['row']}: layer {r['layer']}; prompt {r['prompt']!r}.")
        for arm, floor in r['placebo_regex'].items():
            p = floor.get('placebo')
            lines.append(f"  - {arm}: S={p['S']:.3f}, N={p['N']:.3f}" if p else f'  - {arm}: pending.')
    return '\n'.join(lines)+'\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reader', required=True, help='W-core adapter identifier in sealed cached outputs')
    p.add_argument('--bundle-seal', type=Path, required=True)
    p.add_argument('--sha256', required=True)
    p.add_argument('--judge', action='store_true')
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    verify_sources()
    data, receipt = load_bundle(a.bundle_seal, a.sha256)
    result = score(data, a.reader, a.judge)
    a.out.mkdir(parents=True, exist_ok=False)
    write(a.out/'MAP.json', result)
    (a.out/'READER_CARD.md').write_text(card(result))
    seal_output(a.out, {'input_seal_sha256': a.sha256, 'reader': a.reader})


if __name__ == '__main__':
    main()
