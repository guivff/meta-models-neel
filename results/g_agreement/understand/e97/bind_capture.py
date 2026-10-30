"""E97 v2 capture-only binding; no model, probe, pursuit or reader outputs."""
import argparse,collections,datetime,hashlib,json,math,subprocess,sys
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
CHANNEL=ROOT/'results/g_agreement/understand/e57/jlens'
R3B=ROOT/'results/g_agreement/understand/e52/r3b'
sys.path[:0]=[str(CHANNEL),str(R3B),str(ROOT/'results/g_agreement/understand/e52')]
from cpu_job import sha,read,dump,validate_units
from prepare import words_for
from forecast_adapter import require_scope
WORKER_SOURCE_SHA='aa67d4c9a72f2c8a9edc99b04740a694beac27f3752894d0ccd1fce94a138343'
PUBLIC_ITEMS_SHA='22a5870f5ab41e520787b88c79dab3af463bfb36461edeea518bc2501488a6ef'

def validate_worker_seal(cap):
    if cap.get('experiment')!='E97'or cap.get('version')!=2 or cap.get('status')!='COMPLETE':raise ValueError('complete v2 worker inventory required')
    if cap.get('reader_outputs')!=0 or cap.get('reader_outputs_opened')is not False:raise ValueError('worker reader custody')
    if cap.get('source_seal_sha256')!=WORKER_SOURCE_SHA or cap.get('public_items_sha256')!=PUBLIC_ITEMS_SHA:raise ValueError('exact frozen capture worker/input source')
    if 'FAILURE.json'in cap['files']:raise ValueError('failure evidence cannot be COMPLETE')
    if not {'acts42.npy','acts44.npy','items.order.json','CAPTURE_STARTED.json'}<=set(cap['files']):raise ValueError('complete worker members required')

def capture_grid(public,labels,order,positions):
    by={x['item_id']:x for x in public};private={x['item_id']:x for x in labels}
    if len(by)!=6720 or len(private)!=6720 or set(by)!=set(private):raise ValueError('exact6720 public/private identities')
    tests={i for i,x in private.items()if x['split']=='test'}
    if len(tests)!=3360 or len(order)!=len(set(order))or set(order)not in [set(by),tests]:raise ValueError('all6720 or exactly3360 test capture positions required')
    if len(positions)!=len(order)or [x['item_id']for x in positions]!=order:raise ValueError('exact per-row captured-position metadata')
    for i,p in zip(order,positions):
        x=by[i]
        if x['split']!=private[i]['split']or x['read_position']!=len(x['input_ids'])-1 or p['read_position']!=x['read_position']:raise ValueError('registered final raw-prefix token mismatch')
    return by,private,[j for j,i in enumerate(order)if i in tests]

def bind(delivery):
    delivery=Path(delivery).resolve();receipt=read(delivery);source=Path(receipt.get('capture_root',delivery.parent)).resolve()
    contract=read(HERE/'CAPTURE_INTAKE_CONTRACT.json');pin=read(HERE/'INTAKE_V2.json')
    for f,h in pin['sources'].items():
        if sha(f)!=h:raise ValueError('v2 bank bytes changed')
    if receipt['original_bank_seal_sha256']!=pin['bank_seal_sha256']or receipt['public_archive_sha256']!=pin['public_archive_sha256']:raise ValueError('v2 intake hash binding')
    if receipt.get('reviewer_correction_passed')is not True or not receipt.get('reviewer_correction_receipt_sha256'):raise ValueError('I-5 correction-review attestation required')
    for k,v in contract['required_custody'].items():
        if receipt.get(k)!=v:raise ValueError('capture-only custody '+k)
    cap=read(source/'CAPTURE_SEAL.json')
    if sha(source/'CAPTURE_SEAL.json')!=receipt['capture_seal_sha256']:raise ValueError('capture seal hash')
    worker_layout='items.order.json'in cap['files']
    member_names=['acts42.npy','acts44.npy','items.order.json','CAPTURE_STARTED.json']if worker_layout else ['acts44.npy','order.json','READ_POSITIONS.json']
    for name in member_names:
        if sha(source/name)!=cap['files'][name]:raise ValueError('capture member hash')
    if worker_layout:
        validate_worker_seal(cap)
        if cap['bank_seal_sha256']!=receipt['original_bank_seal_sha256']:raise ValueError('worker bank binding')
        source_raw=subprocess.check_output(['git','show','68809b96:results/g_agreement/understand/e97/CAPTURE_SOURCE_V2_R2.json'],cwd=ROOT)
        if hashlib.sha256(source_raw).hexdigest()!=WORKER_SOURCE_SHA:raise ValueError('frozen worker source manifest')
        source_manifest=json.loads(source_raw)
        backend_raw=subprocess.check_output(['git','show','68809b96:results/g_agreement/understand/e49/job/vendor/e36_worker.py'],cwd=ROOT)
        if hashlib.sha256(backend_raw).hexdigest()!=source_manifest['files']['results/g_agreement/understand/e49/job/vendor/e36_worker.py']or b'[[len(x["ids"]) - 1] for x in items]'not in backend_raw:raise ValueError('actual worker read-position implementation')
        started=read(source/'CAPTURE_STARTED.json')['epoch']
        sealed=datetime.datetime.fromisoformat(cap['completed_utc'].replace('Z','+00:00')).timestamp()
        if receipt.get('capture_started_epoch',started)!=started or receipt.get('capture_sealed_epoch',sealed)!=sealed:raise ValueError('worker timestamp binding')
        receipt=receipt|dict(capture_started_epoch=started,capture_sealed_epoch=sealed)
    else:
        for k in ['original_bank_seal_sha256','public_archive_sha256']:
            if cap[k]!=receipt[k]:raise ValueError('capture source identity '+k)
        if cap['experiment']!='E97'or cap['layer']!=44 or cap['width']!=5120:raise ValueError('capture model/site dimensions')
    banktime=int(subprocess.check_output(['git','show','-s','--format=%ct','a28621d5'],cwd=ROOT))
    times=[receipt[k]for k in ['capture_started_epoch','capture_sealed_epoch','delivered_epoch']]
    if not all(type(t)in [int,float]and math.isfinite(t)for t in times)or not banktime<times[0]<=times[1]<=times[2]:raise ValueError('actual v2 capture-to-delivery chronology')
    base=Path(next(f for f in pin['sources']if f.endswith('/BANK_SEAL.json'))).parent
    m=read(base/'MANIFEST.json');rows=read(base/'ROW_LIST.json')['rows'];defs={x['row']:x for x in rows}
    public=[json.loads(s)for s in (base/'cache/bank_2026-10-28_v2/PUBLIC_ITEMS.jsonl').read_text().splitlines()]
    labels=[json.loads(s)for s in Path(m['private_labels']).read_text().splitlines()]
    order=read(source/('items.order.json'if worker_layout else'order.json'))
    if worker_layout:
        byid={x['item_id']:x for x in public}
        positions=[dict(item_id=i,read_position=byid[i]['read_position'])for i in order]
        if len(order)!=6720:raise ValueError('worker COMPLETE must include full6720 inventory')
    else:positions=read(source/'READ_POSITIONS.json')
    by,private,ix=capture_grid(public,labels,order,positions)
    h=np.load(source/'acts44.npy',allow_pickle=False,mmap_mode='r')
    if h.shape!=(len(order),5120)or h.dtype not in [np.float16,np.float32]or not np.isfinite(h).all():raise ValueError('finite fp16/fp32 block44 vectors')
    if worker_layout:
        auxiliary=np.load(source/'acts42.npy',allow_pickle=False,mmap_mode='r')
        if h.dtype!=np.float32 or auxiliary.dtype!=np.float32 or auxiliary.shape!=(6720,5120)or not np.isfinite(auxiliary).all():raise ValueError('worker full block42/44 fp32 inventory')
    testorder=[order[j]for j in ix];records=[]
    for i in testorder:
        x=private[i];r=defs[x['row']]
        if x['label']not in ['A','B']or x['value']!=r['values'][x['label']]:raise ValueError('frozen label/target orientation')
        records.append(dict(id=i,feature=x['row'],split='test',label=int(x['label']=='A'),original_label=x['label']))
    from transformers import AutoTokenizer
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tr=read(ROOT/'results/g_agreement/understand/e52/BASIS_INPUTS_2026-10-27.json')['files']['tokenizer']
    if sha(tr['path'])!=tr['sha256']or m['tokenizer_sha256']!=tr['sha256']:raise ValueError('pinned tokenizer')
    tok=AutoTokenizer.from_pretrained(Path(tr['path']).parent,local_files_only=True)
    frozen=read(HERE/'VALUE_TOKEN_PLAN.json')
    if frozen['bank_seal_sha256']!=pin['bank_seal_sha256']or frozen['tokenizer_sha256']!=tr['sha256']:raise ValueError('pre-capture value plan binding')
    units=[];audit={}
    for row in sorted(defs):
        values=[defs[row]['values'][s]for s in ['A','B']];words,removed=words_for([[x]for x in values]);tokens=[token_variants(tok,x)for x in words]
        if frozen['rows'][row]['token_ids']!=tokens or frozen['rows'][row]['words']!=words or frozen['rows'][row]['literal_values']!=values:raise ValueError('frozen value-token plan drift')
        ids=[i for i in testorder if private[i]['row']==row]
        audit[row]=dict(literal_values=values,words=words,shared_removed=removed,token_ids=tokens,empty_side=[s for s,x in zip(['A','B'],tokens)if not x],taxonomy=defs[row]['taxonomy'],taxonomy_prediction=defs[row]['taxonomy_prediction'])
        units.append(dict(id=row,source_row=row,condition=None,binary=True,item_ids=ids,value_token_ids={i:tokens for i in ids},descriptive_token_sets={i:{}for i in ids}))
    validate_units(units,records,testorder)
    bound=ROOT/'cache/g_agreement/understand/e97/jlens/bound_capture';target=CHANNEL/'E97_INPUT_PLAN.json';normal=ROOT/'cache/g_agreement/understand/e52/r3b/E97_DELIVERY.json'
    if target.exists()or normal.exists()or bound.exists():raise ValueError('E97 binding already exists; never overwrite')
    bound.mkdir(parents=True);np.save(bound/'acts44.npy',np.array(h[ix]),allow_pickle=False)
    dump(bound/'order.json',testorder);dump(bound/'records.json',records);dump(bound/'WORD_AUDIT.json',audit)
    dump(bound/'READ_POSITION_PROOF.json',dict(source='68809b96 frozen worker validate + hash-bound inherited NativeBackend capture + exact public input IDs/order'if worker_layout else'explicit captured READ_POSITIONS.json',independently_measured_per_item_trace=not worker_layout,source_seal_sha256=cap.get('source_seal_sha256'),positions=positions))
    first_output=dict(first_output_utc=receipt.get('first_output_utc','unknown'),first_output_evidence=receipt.get('first_output_evidence',{'path':None,'mtime_ns':None}))
    dump(bound/'BANK_SEAL.json',dict(**first_output,experiment='E97',original_bank_seal_sha256=pin['bank_seal_sha256'],files={'records.json':sha(bound/'records.json')}))
    dump(bound/'CAPTURE_SEAL.json',dict(**first_output,experiment='E97',layer=44,split='test',original_capture_seal_sha256=sha(source/'CAPTURE_SEAL.json'),original_delivery_sha256=sha(delivery),test_indices=ix,files={n:sha(bound/n)for n in ['acts44.npy','order.json','WORD_AUDIT.json']}))
    def ref(p):return dict(path=str(p),sha256=sha(p),member=p.name)
    sources=[delivery,source/'CAPTURE_SEAL.json',bound/'READ_POSITION_PROOF.json',HERE/'INTAKE_V2.json',HERE/'VALUE_TOKEN_PLAN.json',Path(__file__).resolve(),base/'BANK_SEAL.json',base/'ROW_LIST.json',base/'MANIFEST.json',Path(m['private_labels']),Path(tr['path']),bound/'WORD_AUDIT.json']
    plan=dict(experiment='E97',layer=44,split='test',bank_seal=ref(bound/'BANK_SEAL.json'),capture_seal=ref(bound/'CAPTURE_SEAL.json'),records=ref(bound/'records.json'),order=ref(bound/'order.json'),activations=ref(bound/'acts44.npy'),units=units,value_sources=[{'path':str(p),'sha256':sha(p)}for p in sources],word_audit=audit,exclusions=[],value_word_policy='Unchanged E52 words_for extraction/shared removal/numeric expansion + Suraj single-token variants, literal v2 A/B values only. Empty sides retained as G3 NOT EVALUABLE; no synonym repair.',reader_outcomes_accessed=False)
    normalized=receipt|dict(bank_seal_sha256=sha(bound/'BANK_SEAL.json'),capture_seal_sha256=sha(bound/'CAPTURE_SEAL.json'),original_delivery_path=str(delivery),original_delivery_sha256=sha(delivery),original_capture_seal_sha256=sha(source/'CAPTURE_SEAL.json'))
    require_scope(plan,normalized,pin['rows']);dump(target,plan);normal.parent.mkdir(parents=True,exist_ok=True);dump(normal,normalized)
    print('E97 v2 bound: all3360 tests/40 binary units; commit input/token plan before channel; no scores computed')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--delivery',type=Path,required=True);args=p.parse_args();bind(args.delivery)
