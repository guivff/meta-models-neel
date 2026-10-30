"""W10b DEV ONLY: generate, blind-judge, seal >=16/20 gate BEFORE any capture.

No activation hooks, capture arrays, reader asked scoring, or capture launch.
Integrator owns GPU operations. Dev science/setup remain charged to W10b totals.
"""
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import signal
import statistics
import time
from . import protocol as P, run as R
from . import w10b_items as B

GATE_FROZEN_DEV_SOURCE = '379b6fa7a300d32f5559fefe726f0106e2b2524b24244e98721d723e3a178e16'
DEV_SOURCE_PATH = 'projects/g_agreement/blindspot/w10b_dev.py'

def seal(out,names,name,status):
    P.dump(Path(out)/name,{'status':status,'files':{n:P.sha(Path(out)/n) for n in names}})


def inputs(bank, *, operational_gate=False):
    bank=Path(bank);P.verify(bank,'INPUT_SEAL.json');R._labels_absent(bank)
    manifest=json.loads((bank/'manifest.json').read_text())
    expected=B.source_hashes()
    if operational_gate:
        # Only this gate's label-path plumbing changed after the dev judge sealed.
        # Bind the bank to the exact original version; every other source stays exact.
        expected[DEV_SOURCE_PATH]=GATE_FROZEN_DEV_SOURCE
    if manifest['experiment']!='W10b' or manifest['source_files']!=expected: raise ValueError('wrong frozen source/bank')
    checks=P.rows(bank/'mode_checks.input.jsonl')
    if len(checks)!=320 or len({r['id'] for r in checks})!=320 or Counter(r['feature'] for r in checks)!=dict.fromkeys(B.specs(),20):
        raise ValueError('need20dev checks for every16row')
    return manifest,checks


def generate(a):
    assignment=json.loads(a.assignment.read_text());manifest,checks=inputs(a.bank)
    if (assignment.get('issuer')!='integrator' or assignment.get('experiment')!='W10b_DEV_ONLY' or
        not assignment.get('pod_id') or assignment['pod_id']!=os.environ.get('RUNPOD_POD_ID') or
        assignment.get('source_files')!=manifest['source_files'] or
        assignment.get('manifest_sha256')!=P.sha(a.bank/'manifest.json') or
        assignment.get('previous_gpu_seconds')!=0 or assignment.get('science_cap_gpu_seconds')!=3600 or
        assignment.get('staging_allowance_seconds')!=1500 or
        any(assignment.get(k) is not True for k in ('brief_registered','brief_pushed','manifest_committed','external_hardstop_verified'))):
        raise ValueError('exact integrator dev-only assignment required')
    for field in ('source_commit','manifest_commit','brief_commit'):
        s=assignment.get(field,'')
        if len(s)!=40 or any(c not in '0123456789abcdef' for c in s): raise ValueError('missing pinned '+field)
    created=float(assignment['provider_created_epoch']);deadline=float(assignment['deadline_epoch'])
    if not 0<deadline-created<=float(assignment['allocated_gpu_seconds']): raise ValueError('invalid absolute custody')
    if not created<=time.time()<min(created+1500,deadline-180): raise ValueError('setup expired')
    a.out.mkdir(parents=True,exist_ok=False)
    end=min(created+1500,deadline-180);first=None;setup_elapsed=None
    def expired(*_): raise TimeoutError('W10b dev-only setup/science deadline')
    def check():
        if time.time()>=end: expired()
        signal.setitimer(signal.ITIMER_REAL,max(.001,end-time.time()))
    old=signal.signal(signal.SIGALRM,expired);check()
    try:
        assets=R._assets(a.assets,names=('model','olens'));ol=R._load_oracle(assets)
        import torch
        def continuation(row):
            check()
            ids=torch.tensor([row['prompt_ids']],dtype=torch.long,device=next(ol.model.parameters()).device)
            with ol.base(),torch.no_grad():
                generated=ol.model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,
                    max_new_tokens=48,pad_token_id=ol.tok.pad_token_id or ol.tok.eos_token_id)
            return ol.tok.decode(generated[0,len(row['prompt_ids']):],skip_special_tokens=True)
        # Unscored setup warm-up, one generation path, actual production shape.
        representative=max(checks,key=lambda r:(len(r['prompt_ids']),r['id']))
        continuation(representative);torch.cuda.synchronize();check()
        setup_elapsed=time.time()-created
        first=time.time();end=min(first+3600,deadline-180)
        with (a.out/'EXPERIMENT_CLOCK.json').open('x') as f:json.dump({'first_science_epoch':first,'experiment':'W10b_DEV_ONLY'},f)
        timings=[]
        # Worst-length dev unit, fixed by length, never by observed compliance.
        for _ in range(3):
            check();torch.cuda.synchronize();start=time.perf_counter();text=continuation(representative);torch.cuda.synchronize()
            seconds=time.perf_counter()-start
            tokens=max(1,len(ol.tok.encode(text,add_special_tokens=False)))
            timings.append(seconds*48/min(48,tokens))
        remaining=statistics.median(timings)*len(checks);F=time.time()-first+remaining;allocation=min(1.5*F+360,3600)
        end=min(end,first+allocation)
        fits=math.isfinite(F) and F>0 and F<=allocation and time.time()+remaining<=end
        P.dump(a.out/'FORECAST.json',{'status':'FIT' if fits else 'NO_FIT','forecast_s':F,'allocation_s':allocation,
            'warmed_unit_s':timings,'n_fresh_units':320,'timing_outputs_used':False,'first_science_epoch':first})
        if not fits:
            P.dump(a.out/'STATUS.json',{'status':'NO_FIT','capture_performed':False,'no_scope_reduction':True});return
        results=[]
        for row in checks:
            text=continuation(row);results.append({'id':row['id'],'text':text})
            with (a.out/'mode_generations.partial.jsonl').open('a') as f:f.write(json.dumps(results[-1],sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
        check();P.jsonl(a.out/'mode_generations.jsonl',results)
        P.dump(a.out/'provenance.json',{'input_seal_sha256':P.sha(a.bank/'INPUT_SEAL.json'),'source_files':manifest['source_files'],
            'assignment_sha256':P.sha(a.assignment),'assets_sha256':P.sha(a.assets),'model':'Qwen3.6-27B base (adapter disabled)',
            'generation':{'do_sample':False,'max_new_tokens':48},'teacher_forced_tokens':0,'capture_performed':False,'checks':320})
        check();seal(a.out,['mode_generations.jsonl','provenance.json','FORECAST.json'],
            'MODE_GENERATION_SEAL.json','DEV_GENERATIONS_COMPLETE_BEFORE_CAPTURE')
    except Exception as exc:
        P.dump(a.out/'FAILURE.json',{'status':'INCOMPLETE','error_type':type(exc).__name__,'no_automatic_retry':True,
            'science_elapsed_s':None if first is None else time.time()-first,'capture_performed':False});raise
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,old)
        completed=time.time();elapsed=0. if first is None else completed-first
        setup_used=completed-created if setup_elapsed is None else setup_elapsed
        P.dump(a.out/'SCIENCE_RECEIPT.json',{'first_science_epoch':first,'completed_epoch':completed,'elapsed_s':elapsed,
            'setup_elapsed_s':setup_used,'total_W10b_science_cap_seconds':3600,
            'remaining_W10b_science_cap_seconds':max(0,3600-elapsed),
            'remaining_W10b_setup_allowance_seconds':max(0,1500-setup_used),
            'capture_not_authorized_by_this_worker':True})
        if (a.out/'MODE_GENERATION_SEAL.json').exists():
            seal(a.out,['MODE_GENERATION_SEAL.json','SCIENCE_RECEIPT.json'],
                 'DEV_RUN_SEAL.json','DEV_GENERATION_AND_BUDGET_SEALED')


def packet(bank,generations,out):
    bank,generations,out=map(Path,(bank,generations,out));manifest,checks=inputs(bank)
    P.verify(generations,'MODE_GENERATION_SEAL.json')
    provenance=json.loads((generations/'provenance.json').read_text())
    if provenance['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or provenance['source_files']!=manifest['source_files']:
        raise ValueError('mode generation lineage mismatch')
    gens=P.rows(generations/'mode_generations.jsonl');lookup={r['id']:r for r in checks}
    if len(gens)!=320 or len({r['id'] for r in gens})!=320 or {r['id'] for r in gens}!=set(lookup): raise ValueError('wrong generation coverage')
    policy=json.loads((bank/'mode_active_policy.json').read_text())
    out.mkdir(parents=True,exist_ok=False);rows=[]
    for r in gens:
        mode=lookup[r['id']]['feature'].rsplit('_',1)[0];a,b=policy['criteria'][mode]
        prompt=policy['judge_prompt'].format(pair=mode,criterion_a=a,criterion_b=b,text=json.dumps(r['text'],ensure_ascii=False))
        rows.append({'id':r['id'],'prompt':prompt})
    import random
    random.Random(B.SEED).shuffle(rows)
    P.jsonl(out/'judge_packet.jsonl',rows)
    P.dump(out/'provenance.json',{'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
        'generation_seal_sha256':P.sha(generations/'MODE_GENERATION_SEAL.json'),'policy_sha256':P.sha(bank/'mode_active_policy.json')})
    seal(out,['judge_packet.jsonl','provenance.json'],'MODE_PACKET_SEAL.json','BLINDED_DEV_MODE_PACKET_FROZEN')


def judge(packet,out):
    """Same W10 model/HTTP route and reservation policy;320 new blind assessments."""
    import requests
    packet,out=map(Path,(packet,out));P.verify(packet,'MODE_PACKET_SEAL.json')
    if out.exists(): raise ValueError('judge directory exists, no duplicate/retry')
    rows=P.rows(packet/'judge_packet.jsonl')
    if len(rows)!=320 or len({r['id'] for r in rows})!=320: raise ValueError('need320blinded packets')
    key=os.environ.get('OPENROUTER_API_KEY')
    if not key: raise ValueError('judge credential unavailable; no requests made')
    model='openai/gpt-5-mini';cap=3.;limit=2048
    response=requests.get('https://openrouter.ai/api/v1/models',timeout=15);response.raise_for_status()
    meta=next(x for x in response.json()['data'] if x['id']==model);price=meta['pricing']
    inp,comp,fixed=(float(price.get(k,0)) for k in ('prompt','completion','request'))
    if not all(math.isfinite(x) and x>=0 for x in (inp,comp,fixed)): raise ValueError('invalid prices')
    reserves=[(len(r['prompt'].encode())+4096)*inp+limit*comp+fixed for r in rows]
    if sum(reserves)>cap: raise ValueError('full-pass conservative bound exceeds $3; no requests made')
    out.mkdir(parents=True,exist_ok=False);spent=0.;judged=[]
    ledger={'model':model,'cap_usd':cap,'pricing':price,'reserved_full_pass_usd':sum(reserves),'api_calls':0}
    for row,reserve in zip(rows,reserves):
        if spent+reserve>cap: raise RuntimeError('budget exhausted, no further request')
        spent+=reserve;ledger.update(api_calls=ledger['api_calls']+1,charged_or_reserved_usd=spent);P.dump(out/'budget.json',ledger)
        try:
            response=requests.post('https://openrouter.ai/api/v1/chat/completions',
                headers={'Authorization':'Bearer '+key},json={'model':model,'temperature':0,'max_tokens':limit,
                'messages':[{'role':'user','content':row['prompt']}]},timeout=60)
            response.raise_for_status();body=response.json();result=json.loads(body['choices'][0]['message']['content'])
            if any(type(result.get(k)) is not bool for k in ('A_follows','B_follows')): raise ValueError('invalid judge booleans')
            charge=body.get('usage',{}).get('cost')
            if isinstance(charge,(int,float)) and math.isfinite(charge) and charge>=0: spent+=charge-reserve
            ledger.update(charged_or_reserved_usd=spent);P.dump(out/'budget.json',ledger)
        except Exception as exc:
            P.dump(out/'FAILURE.json',{'error_type':type(exc).__name__,'api_calls':ledger['api_calls'],
                'charged_or_reserved_usd':spent,'no_automatic_retry':True})
            raise RuntimeError('judge stopped; sanitized failure receipt, no retries') from None
        assessed={'id':row['id'],'A_follows':result['A_follows'],'B_follows':result['B_follows'],
                  'reason':str(result.get('reason','')),'model':model,'request_id':body.get('id')}
        judged.append(assessed)
        with (out/'judged.partial.jsonl').open('a') as f:f.write(json.dumps(assessed,sort_keys=True)+'\n');f.flush();os.fsync(f.fileno())
    P.jsonl(out/'judged.jsonl',judged)
    P.dump(out/'provenance.json',{'packet_seal_sha256':P.sha(packet/'MODE_PACKET_SEAL.json'),'model':model,'judgements':320})
    seal(out,['judged.jsonl','budget.json','provenance.json'],'MODE_JUDGE_SEAL.json','BLINDED_DEV_JUDGE_COMPLETE')


def activity(labels,checks,judged,specs):
    expected={r['id']:r for r in checks};mapping={r['id']:r for r in judged}
    if len(mapping)!=len(judged) or len(mapping)!=320 or set(mapping)!=set(expected): raise ValueError('wrong judge coverage')
    rows=[]
    for feature,spec in specs.items():
        selected=[r['id'] for r in checks if r['feature']==feature]
        if len(selected)!=20 or any(labels[i]['split']!='dev' for i in selected): raise ValueError('dev-only20perrow required')
        active=0
        for i in selected:
            r=mapping[i]
            if any(type(r.get(k)) is not bool for k in ('A_follows','B_follows')): raise ValueError('typed judge booleans required')
            active+=int(r['A_follows' if labels[i]['value']==spec['values'][0] else 'B_follows'])
        rows.append({'feature':feature,'active':active,'n':20,'pass':active>=16,'status':'PASS' if active>=16 else 'NOT EVALUABLE'})
    return rows


def gate(bank,generations,packet_path,judgements,labels_path,out):
    bank,generations,packet_path,judgements,labels_path,out=map(Path,(bank,generations,packet_path,judgements,labels_path,out))
    manifest,checks=inputs(bank,operational_gate=True)
    P.verify(generations,'DEV_RUN_SEAL.json')
    for root,name in ((generations,'MODE_GENERATION_SEAL.json'),(packet_path,'MODE_PACKET_SEAL.json'),(judgements,'MODE_JUDGE_SEAL.json')):P.verify(root,name)
    pp=json.loads((packet_path/'provenance.json').read_text());jp=json.loads((judgements/'provenance.json').read_text())
    if (pp['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or pp['generation_seal_sha256']!=P.sha(generations/'MODE_GENERATION_SEAL.json') or
        jp['packet_seal_sha256']!=P.sha(packet_path/'MODE_PACKET_SEAL.json')): raise ValueError('gate lineage mismatch')
    if labels_path.resolve().is_relative_to(bank.resolve()):
        raise ValueError('labels must be supplied separately, outside the staged bank')
    if P.sha(labels_path)!=manifest['labels_sha256']: raise ValueError('labels do not match freeze')
    labels={r['id']:r for r in P.rows(labels_path)}
    rows=activity(labels,checks,P.rows(judgements/'judged.jsonl'),json.loads((bank/'templates.json').read_text()))
    out.mkdir(parents=True,exist_ok=False)
    P.dump(out/'mode_gate.json',{'experiment':'W10b','rows':rows,'active_count_threshold':16,'required_minimum_evaluable':8,
        'mode_rows_passing':sum(r['pass'] for r in rows),'all_rows_retained':True,'reader_gates_still_pending':True,
        'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),'generation_seal_sha256':P.sha(generations/'MODE_GENERATION_SEAL.json'),
        'judge_seal_sha256':P.sha(judgements/'MODE_JUDGE_SEAL.json'),'capture_performed':False,
        'labels_sha256':P.sha(labels_path),'operational_gate_source_sha256':P.sha(Path(__file__))})
    seal(out,['mode_gate.json'],'MODE_GATE_SEAL.json','DEV_MODE_GATE_SEALED_BEFORE_CAPTURE')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    g=s.add_parser('generate')
    for n in ('bank','assignment','assets','out'): g.add_argument('--'+n,type=Path,required=True)
    q=s.add_parser('packet')
    for n in ('bank','generations','out'):q.add_argument('--'+n,type=Path,required=True)
    j=s.add_parser('judge')
    for n in ('packet','out'):j.add_argument('--'+n,type=Path,required=True)
    t=s.add_parser('gate')
    for n in ('bank','generations','packet','judgements','labels','out'):t.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.command=='generate':
        with P.logged('w10b_dev_only_generate',gpu=True,extra={'capture_performed':False}):generate(a)
    elif a.command=='packet':packet(a.bank,a.generations,a.out)
    elif a.command=='judge':judge(a.packet,a.out)
    else:gate(a.bank,a.generations,a.packet,a.judgements,a.labels,a.out)
