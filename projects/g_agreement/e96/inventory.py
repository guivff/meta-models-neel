"""Read-only sealed-bank inventory; produces no samples or scientific analysis."""
import argparse
from collections import Counter
import json
from pathlib import Path
from .reconstructor_check import digest, write
from .prepare_smoke_inputs import verify


def inventory(cache, evidence):
    root = cache / 'g_agreement/understand'
    selection = evidence / 'g_agreement/understand/e49/job/analysis'
    verify(selection, 'ANALYSIS_SEAL.json')
    gates = json.loads((selection/'GATES.json').read_text())
    native = json.loads((selection/'NATIVE_PRIMARY.json').read_text())
    e49 = sorted(k for k, row in native['rows'].items()
                 if row['oracle']['forecast_truth'] == 'MISSED' and gates['rows'][k]['probe'] >= .9)
    paths = {'E49':root/'e49/job_inputs_v1', 'E57':root/'e57/inputs_v4_single',
             'E59':root/'follow402_v1/E59', 'E62':root/'second_wave_v1/e62'}
    controls = {'E57': {'capacity_list', 'category_switch', 'focus_none'},
                'E62': {'S6_C0','S6_C1','S6_C2','S6_C3','S6_C4'}}
    rows, sources = [], []
    for bank, source in paths.items():
        verify(source, 'INPUT_SEAL.json')
        items = json.loads((source/'items.json').read_text())
        sources.append({'bank':bank,'path':str(source),'seal_sha256':digest(source/'INPUT_SEAL.json')})
        for feature in dict.fromkeys(x['feature'] for x in items):
            if bank == 'E49' and feature not in e49:
                continue
            test = [x['id'] for x in items if x['feature'] == feature and x['split'] == 'test']
            if len(test) < 40 or len(set(test)) != len(test):
                raise ValueError('first-40 test contract unavailable: '+bank+'/'+feature)
            rows.append({'bank':bank,'row':feature,'selected_ids':test[:40],
                         'test_count':len(test),'samples_per_reader':640,
                         'registered_no_AB_or_no_S':feature in controls.get(bank,set())})
    return {'status':'CPU_INVENTORY_ONLY','new_readouts':0,'new_judgments':0,
            'selection':'first 40 test items in each frozen input order; no sorting or replacement',
            'sources':sources,'e49_selection_analysis_seal':digest(selection/'ANALYSIS_SEAL.json'),
            'rows':rows,'row_counts':dict(Counter(x['bank'] for x in rows)),
            'total_rows':len(rows),'total_items':40*len(rows),'total_readouts':1280*len(rows),
            'non_AB_or_no_S_rows':[x['bank']+'/'+x['row'] for x in rows if x['registered_no_AB_or_no_S']],
            'sampling_started':False,'scope_clarification_pending':True}


def main():
    p=argparse.ArgumentParser()
    for name in ('cache','evidence','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args(); report=inventory(a.cache,a.evidence)
    if a.out.exists():raise ValueError('inventory output already exists')
    write(a.out,report)
    print(json.dumps({k:report[k] for k in ('row_counts','total_rows','total_items','total_readouts','non_AB_or_no_S_rows')}))


if __name__=='__main__':main()
