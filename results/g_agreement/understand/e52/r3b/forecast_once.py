"""Publish sealed J labels as prospective R3b predictions; never read reader outcomes."""
from pathlib import Path
import argparse
import json
import math
import subprocess
import sys
import time
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
CHANNEL=ROOT/'results/g_agreement/understand/e57/jlens'
sys.path.insert(0,str(CHANNEL))
from cpu_job import sha,read,dump,verify,committed,sealed_ref,validate_units
BANKS=('E56','E57','E59','E62')


def assemble(units,labels):
    byid={x['row']:x for x in labels}
    if len(byid)!=len(labels) or set(byid)!={u['id'] for u in units}:raise ValueError('exact frozen unit coverage required')
    rows=[];excluded=[]
    for u in units:
        x=byid[u['id']]
        if not u['binary']:
            if x['J_fraction'] is not None or x['label']!='NOT APPLICABLE':raise ValueError('nonbinary unit must have no invented contrast')
            excluded.append({'row':u['id'],'source_row':u['source_row'],'condition':u.get('condition'),
                'reason':'NO_REGISTERED_A_B_PAIR','authority':'section181 clarification1 2ba13670'})
            continue
        value=x['J_fraction'];label=x['label']
        if type(value) not in (float,int) or not math.isfinite(value) or value<0:raise ValueError('finite nonnegative J-fraction required')
        if label not in ('IN-J','OUT-J','DIFFUSE'):raise ValueError('all binary labels must be computed; no post-outcome backfill')
        prediction='REPORTED' if label=='IN-J' else 'MISSED'
        rows.append({'row':u['id'],'source_row':u['source_row'],'condition':u.get('condition'),
            'J_fraction':value,'label':label,'oracle_prediction':prediction,'nla_prediction':prediction})
    return rows,excluded


def run(bank):
    receipt_path=ROOT/'cache/g_agreement/understand/e52/r3b'/(bank+'_DELIVERY.json')
    plan_path=CHANNEL/(bank+'_INPUT_PLAN.json');labels_dir=CHANNEL/(bank+'_results')
    if not receipt_path.exists() or not plan_path.exists() or not (labels_dir/'LABEL_SEAL.json').exists():
        print(bank+' WAITING_FOR_DELIVERY_COMMITTED_PLAN_AND_SEALED_J_LABELS');return 2
    verify(ROOT,read(HERE/'CODE_SEAL_2026-10-27.json')['files']);committed(plan_path)
    receipt=read(receipt_path);plan=read(plan_path)
    if plan['experiment']!=bank or plan['layer']!=44 or plan['split']!='test':raise ValueError('bank/layer/split mismatch')
    if receipt.get('issuer')!='integrator' or receipt.get('experiment')!=bank or receipt.get('status')!='VERIFIED_CAPTURE_ONLY':raise ValueError('Integrator verified capture-only receipt required')
    if receipt['bank_seal_sha256']!=plan['bank_seal']['sha256'] or receipt['capture_seal_sha256']!=plan['capture_seal']['sha256']:raise ValueError('capture/bank receipt binding differs')
    delivery=receipt['delivered_epoch']
    if type(delivery) not in (float,int) or not math.isfinite(delivery) or not 0<delivery<=time.time():raise ValueError('valid delivery timestamp required')
    for key in ('reader_outputs_opened_at_registration','reader_outputs_opened_before_forecast','readers_held_until_forecast_commit'):
        if type(receipt.get(key)) is not bool:raise ValueError('explicit reader custody booleans required')
    retrospective=receipt['reader_outputs_opened_at_registration'] or receipt['reader_outputs_opened_before_forecast']
    if not retrospective and not receipt['readers_held_until_forecast_commit']:raise ValueError('prospective output custody not guaranteed')
    records=read(sealed_ref(plan['records'],plan['bank_seal']));order=read(sealed_ref(plan['order'],plan['capture_seal']))
    sealed_ref(plan['activations'],plan['capture_seal']);validate_units(plan['units'],records,order)
    verify(labels_dir,read(labels_dir/'LABEL_SEAL.json')['files']);labels=read(labels_dir/'ROW_LABELS.json')
    if labels['plan_sha256']!=sha(plan_path) or labels['reader_outcomes_accessed'] is not False:raise ValueError('sealed J labels not bound or outcomes accessed')
    if labels['experiment']!=bank or labels['label_role']!='PRIMARY_SPARSE' or labels['code_seal_sha256']!=sha(CHANNEL/'CODE_SEAL_2026-10-27.json'):raise ValueError('registered label implementation binding differs')
    rows,excluded=assemble(plan['units'],labels['rows'])
    out=HERE/(bank+'_JFORECAST.json');marker=receipt_path.parent/(bank+'_FORECAST_ONCE.json')
    if out.exists():raise ValueError('forecast already exists; never overwrite')
    with marker.open('x') as f:json.dump({'status':'CLAIMED_NEVER_RESET','epoch':time.time(),'receipt_sha256':sha(receipt_path)},f)
    now=time.time()
    result={'experiment':'E52_R3b','bank':bank,'authority_commit':'061d0e4a','exclusion_clarification_commit':'2ba13670',
        'rule':'REPORTED iff IN-J; identical fixed mapping for Oracle lens and NLA','label_method':'section169 amendment1 nonnegative sparse pursuit k16; frozen G3',
        'prospective_status':'RETROSPECTIVE_EXCLUDED_FROM_R3b' if retrospective else 'PROSPECTIVE_AWAITING_COMMIT',
        'eligible_for_R3b':not retrospective,'reader_outcomes_accessed':False,'created_epoch':now,'delivered_epoch':delivery,
        'elapsed_seconds_since_delivery':now-delivery,'target_commit_within_seconds':1800,
        'receipt_sha256':sha(receipt_path),'capture_seal_sha256':receipt['capture_seal_sha256'],'bank_seal_sha256':receipt['bank_seal_sha256'],
        'plan_sha256':sha(plan_path),'label_seal_sha256':sha(labels_dir/'LABEL_SEAL.json'),'code_seal_sha256':sha(HERE/'CODE_SEAL_2026-10-27.json'),
        'rows':rows,'exclusions':excluded,'no_backfill':True,
        'custody_note':'Integrator records this exact forecast SHA/commit time before unsealing reader outputs. No go-signal is sent by W-lens.'}
    dump(out,result);dump(HERE/(bank+'_JFORECAST.sha256.json'),{'file':out.name,'sha256':sha(out)})
    print(bank+' forecast sealed: '+str(len(rows))+' binary units; '+str(len(excluded))+' explicit exclusions; '+result['prospective_status'])
    return 0

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bank',choices=BANKS);args=parser.parse_args();raise SystemExit(run(args.bank))
