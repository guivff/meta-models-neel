"""Once-only E96 label join and registered analysis, after complete judgment seal.

Primary: full-bank regex on registered regex rows (§204), otherwise the frozen
judge sample. The combined regex+judge channel is always reported separately.
Never promote a sensitivity channel based on its result. GPU/reader selection
and canonical-value aggregation remain answer-blind in aggregate.py.
"""
import argparse,datetime,gzip,json
from collections import defaultdict
from pathlib import Path
import numpy as np
from common.stats import wilson
from .aggregate import majority,reconstructor_best,any_of_16
from .analysis_core import signed,paired,rules
from .reconstructor_check import digest,write
from .prepare_smoke_inputs import verify


def values(record,mode,codes):
    if record['regex_values'] is not None:return record['regex_values']
    if mode=='regex_whole':return []  # zero detector hit, explicitly not a judgment of silence
    code=codes.get(record['id'])
    if code is None or code['category']=='UNPARSEABLE':return None
    return code['values'] if code['category']=='states_value' else []


def binary_rate(xs):
    known=[x for x in xs if x is not None]
    if not known:return {'status':'NOT EVALUABLE','n':0}
    p,lo,hi=wilson(sum(known),len(known))
    return {'status':'EVALUABLE','estimate':float(p),'CI95':[float(lo),float(hi)],'n':len(known),'missing':len(xs)-len(known)}


def score_items(item_groups,truths,mode,codes,scope='all',excluded=frozenset()):
    scored=[]
    for item_id,records in item_groups:
        if scope=='judged' and not records[0]['judge_scope']:continue
        if scope=='old' and not records[0]['old_rubric_scope']:continue
        if any(r['id'] in excluded for r in records):continue
        truth=truths[item_id];samples=sorted([r for r in records if r['kind']=='sample'],key=lambda r:r['sample_index'])
        greedy=[r for r in records if r['kind']=='greedy'];placebo=[r for r in records if r['kind']=='placebo']
        if len(samples)!=16 or [r['sample_index'] for r in samples]!=list(range(16)) or len(greedy)!=1 or len(placebo)!=1:raise ValueError('complete paired item grid')
        statements=[values(r,mode,codes) for r in samples]
        g=signed(values(greedy[0],mode,codes),truth)
        if all(v is not None for v in statements):
            result=majority(statements,('A','B'));m=signed([result['value']] if result['value'] is not None else [],truth)
            observed=any_of_16(statements,('A','B'))['values'];any_correct=int(truth in observed)
            any_mention=int(any(truth in v for v in statements))
        else:m=any_correct=any_mention=None
        errors=[r['reconstruction']['raw_native_mse'] for r in samples];parsed=[r['reconstruction']['parsed'] for r in samples]
        chosen=reconstructor_best(errors,parsed)
        selected=chosen['sample_index'];rec=signed(values(samples[selected],mode,codes),truth) if selected is not None else 0
        pv=values(placebo[0],mode,codes);phit=None if pv is None else int(pv==[truth]);pmention=None if pv is None else int(truth in pv)
        scored.append({'id':item_id,'truth':truth,'greedy':g,'majority':m,'recon':rec,'any_correct_only':any_correct,'any_correct_mention':any_mention,'placebo_correct_only':phit,'placebo_correct_mention':pmention,'recon_selected_sample':selected,'recon_error':chosen['error'],'recon_eligible_samples':chosen['eligible_samples']})
    return scored


def summarize(axis,items,channel):
    key=axis['bank']+'|'+axis['row']+'|'+axis['reader']+'|'+channel
    known=[r['greedy'] for r in items if r['greedy'] is not None]
    return {**axis,'channel':channel,'items':len(items),'greedy_known_items':len(known),'S_greedy_all_resolved':float(np.mean(known)) if known else None,
            'majority':paired([r['majority'] for r in items],[r['greedy'] for r in items],key+'|majority'),
            'recon':paired([r['recon'] for r in items],[r['greedy'] for r in items],key+'|recon'),
            'any_of_16_correct_only':binary_rate([r['any_correct_only'] for r in items]),
            'placebo_one_of_16_correct_only':binary_rate([r['placebo_correct_only'] for r in items]),
            'any_minus_placebo':paired([r['any_correct_only'] for r in items],[r['placebo_correct_only'] for r in items],key+'|any_placebo'),
            'any_of_16_correct_mention':binary_rate([r['any_correct_mention'] for r in items]),
            'placebo_correct_mention':binary_rate([r['placebo_correct_mention'] for r in items])}


def build_rows(axes,groups,truths,codes,channel,excluded=frozenset(),missing_cells=frozenset()):
    rows=[];item_scores=[]
    for axis in axes:
        key=(axis['key'],axis['reader'])
        if key not in groups:
            if key not in missing_cells:raise ValueError('missing reader cell without registered scope')
            row=summarize(axis,[],channel);row.update(status='NOT EVALUABLE',reason='slot1 outputs lost; rerun parked under§211')
            rows.append(row);item_scores.append({'key':axis['key'],'bank':axis['bank'],'row':axis['row'],'reader':axis['reader'],'channel':channel,'items':[],'status':'NOT EVALUABLE','reason':row['reason']});continue
        if channel=='primary':mode=axis['primary_channel'];scope='all' if mode=='regex_whole' else 'judged'
        elif channel=='regex_whole':mode='regex_whole';scope='all'
        elif channel in ('judged_sensitivity','current_on_old_subset','old_rubric_subset'):mode='judge_subsample';scope='judged' if channel=='judged_sensitivity' else 'old'
        else:raise ValueError('fixed analysis channel')
        scored=score_items(groups[key],truths[key],mode,codes,scope,excluded)
        rows.append(summarize(axis,scored,channel));item_scores.append({'key':axis['key'],'bank':axis['bank'],'row':axis['row'],'reader':axis['reader'],'channel':channel,'items':scored})
    return rows,item_scores


def run(packet,judgments,cpu,axes_path,out):
    # All custody/completeness validation precedes the once-only guard and labels.
    verify(packet,'PACKET_SEAL.json');verify(judgments,'JUDGMENT_SEAL.json');verify(cpu,'CPU_INPUT_SEAL.json')
    ps=json.loads((packet/'PACKET_SEAL.json').read_text());js=json.loads((judgments/'JUDGMENT_SEAL.json').read_text());axes=json.loads(axes_path.read_text())
    if js['packet_seal_sha256']!=digest(packet/'PACKET_SEAL.json') or js['status']!='TERMINAL_BLIND_GRID_NO_LABEL_JOIN':raise ValueError('sealed blind judgments required')
    if ps['cpu_truth_seal_sha256']!=digest(cpu/'CPU_INPUT_SEAL.json'):raise ValueError('CPU truth binding')
    if axes['sampling_input_seal_sha256']!=ps['sampling_input_seal_sha256']:raise ValueError('legacy axis/sampling input binding')
    current=json.loads((judgments/'current_JUDGMENTS.json').read_text());old=json.loads((judgments/'original_JUDGMENTS.json').read_text())
    expected={r['id'] for r in json.loads((packet/'JUDGE_PACKET.json').read_text())};expected_old=set(json.loads((packet/'OLD_RUBRIC_IDS.json').read_text()))
    cur={r['id']:r for r in current};orig={r['id']:r for r in old}
    if len(cur)!=len(current) or len(orig)!=len(old) or set(cur)!=expected or set(orig)!=expected_old:raise ValueError('terminal judgment coverage')
    records=json.loads((packet/'RECORDS.DO_NOT_STAGE.json').read_text());meta=json.loads((cpu/'SCORING.DO_NOT_STAGE.json').read_text())
    selection_scope=ps.get('scope',{'records':59760,'samples':53120,'missing_reader_cells':[],'mode':'complete53120','rows_retained':54,'reader_cells_retained':83})
    missing_cells={(r['key'],r['reader']) for r in selection_scope['missing_reader_cells']}
    if len(records)!=selection_scope['records'] or len({r['id'] for r in records})!=selection_scope['records'] or len(axes['rows'])!=83:raise ValueError('exact admitted analysis grid')
    if {(r['row_key'],r['reader']) for r in records}&missing_cells:raise ValueError('records from excluded lost shard')
    if out.exists():raise ValueError('analysis already attempted; never overwrite or rerun')
    root=Path(__file__).resolve().parents[3]
    if digest(root/'projects/g_agreement/e96/aggregate.py')!=ps['code_files']['projects/g_agreement/e96/aggregate.py']:raise ValueError('presampling aggregator changed')
    code_names=['projects/g_agreement/e96/'+n for n in ['analyze.py','analysis_core.py','aggregate.py','retained.py']]+['common/stats.py']
    code={n:digest(root/n) for n in code_names}
    out.mkdir(parents=True);write(out/'ONCE.json',{'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'packet_seal_sha256':digest(packet/'PACKET_SEAL.json'),'judgment_seal_sha256':digest(judgments/'JUDGMENT_SEAL.json'),'legacy_axes_sha256':digest(axes_path),'code_files':code})
    # Label join starts only here, after terminal seals and the once-only lock.
    by_meta={r['key']:r for r in meta['rows']};truths={};grouped=defaultdict(lambda:defaultdict(list))
    joined=[]
    for axis in axes['rows']:
        truths[axis['key'],axis['reader']]={r['id']:r['truth'] for r in by_meta[axis['key']]['items']}
    for r in records:
        key=(r['row_key'],r['reader']);truth=truths[key][r['item_id']]
        grouped[key][r['item_id']].append(r)
        joined.append({**r,'truth':truth,'current_judgment':cur.get(r['id']),'original_judgment':orig.get(r['id'])})
    raw=out/'RAW_JUDGED_RECORDS.json.gz';temp=raw.with_suffix('.tmp')
    with temp.open('wb') as handle:
        with gzip.GzipFile(fileobj=handle,mode='wb',mtime=0) as stream:stream.write(json.dumps(joined,ensure_ascii=False,separators=(',',':')).encode())
    temp.replace(raw);first=datetime.datetime.fromtimestamp(raw.stat().st_mtime,datetime.timezone.utc).isoformat();write(out/'FIRST_OUTPUT.json',{'first_output_utc':first,'source':'first joined raw judged analysis file mtime'})
    groups={}
    for key,items in grouped.items():
        order=[r['id'] for r in by_meta[key[0]]['items']]
        if set(items)!=set(order) or len(order)!=40:raise ValueError('40 frozen test items per reader cell')
        groups[key]=[(item_id,items[item_id]) for item_id in order]
    results={};scores={}
    for channel,codes in [('primary',cur),('regex_whole',cur),('judged_sensitivity',cur),('current_on_old_subset',cur),('old_rubric_subset',orig)]:
        results[channel],scores[channel]=build_rows(axes['rows'],groups,truths,codes,channel,missing_cells=missing_cells)
    primary_rules=rules(results['primary']);sensitivity_rules=rules(results['judged_sensitivity'])
    affected=set(js.get('redacted_opaque_ids',[]))
    if affected:
        redacted_rows,redacted_items=build_rows(axes['rows'],groups,truths,cur,'primary',affected,missing_cells);redaction_rules=rules(redacted_rows);results['excluding_redacted_items']=redacted_rows;scores['excluding_redacted_items']=redacted_items
    else:redaction_rules={'same_as_primary':True,**primary_rules}
    report={'experiment':'E96','authority':selection_scope.get('authority','§204clarification1,5902d5df'),'primary_scoring_policy':axes['primary_channel_policy'],'rows':54,'reader_cells':83,'samples':selection_scope['samples'],'scope':selection_scope,'achieved_rows':selection_scope['rows_retained'],'achieved_reader_cells':selection_scope['reader_cells_retained'],'E62_median_J_fraction':axes['E62_median_J_fraction'],'R_SC1':primary_rules['R_SC1'],'falsifier':primary_rules['falsifier'],'H_SC2':primary_rules['H_SC2'],'judged_channel_sensitivity_rules':sensitivity_rules,'redaction_sensitivity_rules':redaction_rules,'redacted_opaque_ids':sorted(affected),'all_channels':results,'not_evaluable':{'controls':['E57/capacity_list','E57/category_switch','E57/focus_none']+['E62/S6_C'+str(i) for i in range(5)],'lost_slot1_cells':selection_scope['missing_reader_cells'],'controls_reason':'no statement score; not sampled','E62_NLA_cells':25,'E62_NLA_reason':'no greedy baseline; not sampled; none generated'},'missingness_policy':'UNPARSEABLE and unjudged records are missing in judge channel; primary regex zero is explicitly no detector hit, never imputed judge silence. Majorities require16 resolved codes; recon needs the selected code only. Paired bootstrap excludes unresolved pairs.','bootstrap':{'unit':'matched item','draws':2000,'base_seed':20261028,'derived_seeds':'SHA256 bank,row,reader,channel,aggregator; see each CI'},'any_of_16':'descriptive correct-only hit and correct-mention hit both shown against a matched one-of16 E76 random-pool opportunity; neither changes a rule','first_output_utc':first,'first_output_source':'RAW_JUDGED_RECORDS.json.gz mtime','sampling_first_output_utc':ps['sampling_first_output_utc'],'first_judgment_output_utc':js['first_output_utc'],'judging_cost':json.loads((judgments/'COST.json').read_text()),'code_files':code,'rule_status_is_integrator_provisional':True,'reviewer':'R-4 PENDING'}
    if selection_scope.get('mode')=='separate_slot1_17920':
        report['experiment']='E96_SLOT1_SECOND_FINAL_SEPARATE'
        report['reporting']='Separate18rows28cells17920samples only; never pooled with/re-analyzed retained35200primary'
        report['not_evaluable']['outside_separate_scope_cells']=report['not_evaluable'].pop('lost_slot1_cells')
    write(out/'RESULTS.json',report);write(out/'ITEM_SCORES.json',scores);write(out/'LEGACY_AXES.json',axes)
    lines=['# E96 inference-time scaffold','',f"Integrator provisional R-SC1: **{primary_rules['R_SC1']['status']}**. Falsifier: **{primary_rules['falsifier']['status']}**. R-4 review pending.",'',axes['primary_channel_policy'],'','| Bank / row | Reader | J group | Primary | S greedy | Δ majority [95% CI] | Δ recon [95% CI] |','|---|---|---|---|---:|---:|---:|']
    def delta(x):return 'NOT EVALUABLE' if x['status']!='EVALUABLE' else f"{x['delta']:.3f} [{x['CI95'][0]:.3f}, {x['CI95'][1]:.3f}] (n={x['n']})"
    for r in results['primary']:
        g='N/A' if r['S_greedy_all_resolved'] is None else f"{r['S_greedy_all_resolved']:.3f}"
        lines.append(f"| {r['bank']}/{r['row']} | {r['reader']} | {r['J_group']} | {r['primary_channel']} | {g} | {delta(r['majority'])} | {delta(r['recon'])} |")
    lines+=['','Eight controls and25 E62 NLA cells are NOT EVALUABLE under clarification1. Any-of16 is descriptive only. Whole-bank regex, combined regex+judge subsample, matched original-rubric25% and redaction sensitivities are in RESULTS.json. No channel is selected after its result.','',f'first_output_utc: {first}; first sampling output: {ps["sampling_first_output_utc"]}; first judgment output: {js["first_output_utc"]}.']
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    write(out/'ANALYSIS_SEAL.json',{'status':'COMPLETE_ONCE_R4_PENDING','experiment':'E96','first_output_utc':first,'first_output_source':'FIRST_OUTPUT.json; joined raw judged analysis file mtime','sampling_first_output_utc':ps['sampling_first_output_utc'],'first_judgment_output_utc':js['first_output_utc'],'packet_seal_sha256':digest(packet/'PACKET_SEAL.json'),'judgment_seal_sha256':digest(judgments/'JUDGMENT_SEAL.json'),'code_files':code,'files':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='ANALYSIS_SEAL.json'}})
    print(json.dumps({'R_SC1':primary_rules['R_SC1']['status'],'falsifier':primary_rules['falsifier']['status'],'first_output_utc':first,'sealed':str(out/'ANALYSIS_SEAL.json')}))


def main():
    p=argparse.ArgumentParser()
    for n in ('packet','judgments','cpu','axes','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.packet,a.judgments,a.cpu,a.axes,a.out)
if __name__=='__main__':main()
