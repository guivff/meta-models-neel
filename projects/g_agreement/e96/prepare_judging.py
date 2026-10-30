"""After complete sampling: regex first, then a frozen unresolved-only blind packet.

Never joins true labels. CPU truth stays separately sealed until judgments seal.
Both rubric versions use the precommitted item-cluster indices. A placebo is one
preselected E76 random-vector record; its15 unused candidates are never coded.
"""
import argparse,datetime,hashlib,json
from pathlib import Path
from .reconstructor_check import digest,write
from .prepare_smoke_inputs import verify
from .regex import apply
from .retained import scope


def opaque(row_key,reader,item_id,kind,sample):
    return hashlib.sha256(f'E96:20261028:{row_key}:{reader}:{item_id}:{kind}:{sample}'.encode()).hexdigest()[:32]


def blind_record(key,item,text):
    return {'id':key,'property':item['property'],'values':item['values'],'readout':text}


def prepare(inputs,cpu,collections,index_path,placebo_path,catalog_path,out,retained=False):
    if out.exists():raise ValueError('judging packet already exists')
    plan=json.loads((inputs/'PLAN.json').read_text())
    if digest(Path(__file__).with_name('aggregate.py'))!=plan['aggregator_sha256']:raise ValueError('presampling aggregator changed')
    idx=json.loads(index_path.read_text());placebo=json.loads(placebo_path.read_text())
    if idx['input_seal_sha256']!=digest(inputs/'INPUT_SEAL.json') or placebo['sampling_input_seal_sha256']!=digest(inputs/'INPUT_SEAL.json'):raise ValueError('frozen index binding')
    verify(cpu,'CPU_INPUT_SEAL.json');metadata=json.loads((cpu/'SCORING.DO_NOT_STAGE.json').read_text());meta={r['key']:r for r in metadata['rows']}
    selection={(r['row_key'],r['reader']):r for r in idx['cells']}
    catalog=json.loads(catalog_path.read_text());cats={(r['bank'],r['row']):r for r in catalog['rows']}
    pool=Path(placebo['pool']);verify(pool,'OUTPUT_SEAL.json')
    if digest(pool/'OUTPUT_SEAL.json')!=placebo['pool_output_seal_sha256']:raise ValueError('E76 source changed')
    pool_rows={}
    for reader in ('oracle','nla'):
        for line in (pool/(reader+'.jsonl')).read_text().splitlines():
            r=json.loads(line)
            if r['arm']=='random':pool_rows[reader,r['pool_index']]=r
    place={(r['row_key'],r['reader'],r['id']):r for r in placebo['rows']}
    hardware=json.loads((Path(__file__).resolve().parents[3]/'results/g_agreement/e96/HARDWARE_RECEIPT.json').read_text())
    if hardware['placebo']['pool_output_seal_sha256']!=digest(pool/'OUTPUT_SEAL.json'):raise ValueError('placebo hardware receipt binding')
    selection_scope=scope(plan,retained)
    generated={};errors={};sources=[];upstream_first=[]
    for slot in selection_scope['slots']:
        root=collections/str(slot);pull=json.loads((root/'PULL_VERIFIED.json').read_text())
        if pull['gpu_type']!=hardware['placebo']['gpu_type']:raise ValueError('real/placebo hardware type differs within analysis unit')
        verify(root/'out','OUTPUT_SEAL.json');seal=json.loads((root/'out/OUTPUT_SEAL.json').read_text());run=json.loads((root/'out/RUN.json').read_text())
        if seal['status']!='COMPLETE' or run['slot']!=slot or run['status']!='COMPLETE':raise ValueError('sampling must be complete before judging')
        upstream_first.append(seal['first_output_utc']);sources.append({'slot':slot,'gpu_type':pull['gpu_type'],'output_seal_sha256':digest(root/'out/OUTPUT_SEAL.json')})
        for phase,target in [('generate',generated),('reconstruct',errors)]:
            for p in (root/'out').glob('*/**/'+phase+'.*.json'):
                for r in json.loads(p.read_text()):
                    key=(r['row_key'],r['reader'],r['id'],r['sample_index'])
                    if key in target:raise ValueError('duplicate sample')
                    target[key]=r
    want={(row['key'],reader,item,k) for row in plan['rows'] if row['slot'] in selection_scope['slots'] for reader in row['readers'] for item in json.loads((inputs/row['key']/'ids.json').read_text()) for k in range(16)}
    if len(generated)!=selection_scope['samples'] or set(generated)!=want or set(generated)!=set(errors):raise ValueError('exact admitted sample grid')
    resolved=[];packet=[];private=[];old_ids=[];all_records=[]
    for row in plan['rows']:
        if row['slot'] not in selection_scope['slots']:continue
        m=meta[row['key']];ids=json.loads((inputs/row['key']/'ids.json').read_text())
        if [r['id'] for r in m['items']]!=ids:raise ValueError('CPU metadata order')
        for reader in row['readers']:
            chosen=selection[row['key'],reader];selected=set(chosen['selected_item_indices']);old=set(chosen['old_rubric_item_indices'])
            for i,item in enumerate(m['items']):
                samples=[('sample',k,generated[row['key'],reader,item['id'],k]['text']) for k in range(16)]
                pr=place[row['key'],reader,item['id']];ptext=pool_rows[reader,pr['selected_pool_index']]['text']
                for kind,k,text in samples+[('greedy',0,item['greedy'][reader]),('placebo',pr['selected_index'],ptext)]:
                    key=opaque(row['key'],reader,item['id'],kind,k)
                    values=apply(text,item['values'],cats.get((row['bank'],row['row'])))
                    record={'id':key,'row_key':row['key'],'reader':reader,'item_id':item['id'],'kind':kind,'sample_index':k,'text':text,'regex_values':values,'judge_scope':i in selected,'old_rubric_scope':i in old}
                    if kind=='sample':record['reconstruction']=errors[row['key'],reader,item['id'],k]
                    all_records.append(record)
                    if values is not None:
                        resolved.append({'id':key,'values':values,'source':'frozen_regex_with_202_ambiguity_deferral'})
                    elif i in selected:
                        packet.append(blind_record(key,item,text))
                        private.append({'id':key,'row_key':row['key'],'reader':reader,'item_id':item['id'],'kind':kind,'sample_index':k,'original_rubric':i in old})
                        if i in old:old_ids.append(key)
    if len(all_records)!=selection_scope['records']:raise ValueError('samples+greedy+matched placebo grid')
    out.mkdir(parents=True)
    write(out/'HARDWARE_RECEIPT.json',hardware)
    write(out/'REGEX_CODES.json',resolved)
    first=datetime.datetime.fromtimestamp((out/'REGEX_CODES.json').stat().st_mtime,datetime.timezone.utc).isoformat()
    for name,data in [('JUDGE_PACKET.json',packet),('JUDGE_MAP.PRIVATE.json',private),('OLD_RUBRIC_IDS.json',old_ids),('RECORDS.DO_NOT_STAGE.json',all_records)]:write(out/name,data)
    repo=Path(__file__).resolve().parents[3]
    code_names=['projects/g_agreement/e96/'+n for n in ['prepare_judging.py','judge.py','regex.py','aggregate.py','retained.py']]
    code_names+=['projects/g_agreement/understand/blind_judge/'+n for n in ['run.py','later_runner.py','judgment_adapter402.py','privacy79.py','dispatch_lock.py','rubric202.py','wmech2_channel.py','e76_recovery.py']]
    code_names+=['projects/g_agreement/readerbench/scoring.py','projects/g_agreement/readerbench/io.py']
    code_files={n:digest(repo/n) for n in code_names}
    write(out/'PACKET_SEAL.json',{'scope':selection_scope,'code_files':code_files,'experiment':'E96','status':'REGEX_SCORED_UNRESOLVED_PACKET_FROZEN_NO_API_CALLS','first_output_utc':first,'first_output_source':'CPU REGEX_CODES.json mtime','sampling_first_output_utc':min(upstream_first),'sampling_input_seal_sha256':digest(inputs/'INPUT_SEAL.json'),'sampling_output_seals':sources,'judging_index_sha256':digest(index_path),'placebo_index_sha256':digest(placebo_path),'regex_catalog_sha256':digest(catalog_path),'cpu_truth_seal_sha256':digest(cpu/'CPU_INPUT_SEAL.json'),'records':len(all_records),'regex_resolved':len(resolved),'judge_unresolved':len(packet),'old_rubric_unresolved':len(old_ids),'judge_calls':0,'files':{p.name:digest(p) for p in sorted(out.iterdir()) if p.is_file()}})
    print(json.dumps({'records':len(all_records),'regex_resolved':len(resolved),'judge_unresolved':len(packet),'old_rubric_unresolved':len(old_ids)}))


def main():
    p=argparse.ArgumentParser()
    for n in ('inputs','cpu','collections','index','placebo','catalog','out'):p.add_argument('--'+n,type=Path,required=True)
    g=p.add_mutually_exclusive_group();g.add_argument('--retained-35200',action='store_true');g.add_argument('--separate-slot1',action='store_true');a=p.parse_args();prepare(a.inputs,a.cpu,a.collections,a.index,a.placebo,a.catalog,a.out,'slot1-separate' if a.separate_slot1 else a.retained_35200)
if __name__=='__main__':main()
