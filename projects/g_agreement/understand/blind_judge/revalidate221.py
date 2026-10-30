"""Once-only OFFLINE correction of final sealed E87/E103 responses (§221.1).
No API/client, credentials, ledger writes, scientific analysis or paid retries.
"""
import argparse,hashlib,json,shutil,subprocess
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal
from pathlib import Path
from .validator221 import e87_classify,e103_parse
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
ROOT=Path(__file__).resolve().parents[4]
HERE=ROOT/'results/g_agreement/understand/blind_judge/validator221'
CACHE=ROOT/'cache/g_agreement/understand/funded_queue'
STRICT={'E87':'2a1cbbbdd3d950446c23275b4a084fdac17693bfb66a2d65d6fca232bc04baeb','E103':'413a790896a2a09acf4a2353939b4463be734fc41d4d52fc0d4320a2fba55343'}


def sources():
    for n,h in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'corrector source pin')
    for n in ['projects/g_agreement/understand/blind_judge/validator221.py','projects/g_agreement/understand/blind_judge/revalidate221.py','projects/g_agreement/understand/blind_judge/test_validator221.py']:
        blob=subprocess.check_output(['git','show','HEAD:'+n],cwd=ROOT)
        require(hashlib.sha256(blob).hexdigest()==sha(ROOT/n),'commit correction/tests before revalidation')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()


def response_ok(saved):
    body=saved['response'];require(saved['http_status']==200 and body.get('provider')=='Google' and body.get('model') in ('google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001'),'original actual route')
    cost=Decimal(str(body.get('usage',{}).get('cost')));require(cost.is_finite() and cost>=0,'known original charge')
    require(body['choices'][0]['finish_reason']=='stop','completion unchanged')
    return body['choices'][0]['message']['content']


def raw_index(bank,strict,audit):
    """Bind raw responses to sealed route audit and exact original wire digest.
    Do not select a different attempt or replay the retry decision sequence.
    """
    index={};receipts={x['request_id']:x['response_sha256'] for x in audit['requests']}
    for stage in (CACHE/bank/'ledger').iterdir():
        if not stage.is_dir() or not stage.name.startswith('E87_'):continue
        for rp in stage.glob('*.response.json'):
            rid=rp.name.removesuffix('.response.json');require(rid in receipts and sha(rp)==receipts[rid],'raw reply bound by original route audit')
            qp=stage/(rid+'.request.json');wire=read(qp)['wire']
            canonical=json.dumps(wire,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            expected=hashlib.sha256((stage.name+':'+strict['blind_seal_sha256']+':'+canonical).encode()).hexdigest()
            require(expected==rid,'original wire/response identity')
            items=json.loads(wire['messages'][1]['content']);require(len(items)==1,'original singleton grouped request')
            key=stage.name,items[0]['id'];require(key not in index,'unique stage/group response')
            index[key]=(rp,items[0],rid)
    return index


def e87_revalidate(old,strict,audit,out):
    index=raw_index('E87',strict,audit);changes=[];counts={}
    for channel,filename in [('main','JUDGMENTS.json'),('original','ORIGINAL_JUDGMENTS.json')]:
        flat=read(old/filename);terminal=read(old/(channel+'_TERMINAL.json'));items=read(old/(channel+'_JUDGE_COPY.json'))
        require([x['id'] for x in flat]==[x['id'] for x in terminal]==[x['id'] for x in items],'exact unchanged grouped grid/order')
        corrected=[];newterminal=[]
        for row,t,item in zip(flat,terminal,items):
            stage=f'E87_{channel}_attempt{t["attempts"]}';rp,sent,rid=index[stage,row['id']]
            require(sent==item,'chosen original final-attempt wire equals sealed judge copy')
            text=response_ok(read(rp))
            try:body=json.loads(text)
            except (ValueError,TypeError):body={}
            result=e87_classify([item],body)[0]
            if t['status']=='KEPT':
                require(result['status']=='KEPT' and result['code']==row==t['code'],'previously kept verdict stays byte-equivalent')
                code=row;nt=t
            elif result['status']=='KEPT':
                code=result['code'];require(row['category']=='UNPARSEABLE' and code['category']=='silent' and code['evidence']=='' and code['values']==[] and code['first_position'] is None,'silent-only recovery')
                nt=dict(t,status='KEPT',code=code)
                changes.append(dict(channel=channel,id=row['id'],old='UNPARSEABLE',new='silent',request_id=rid,response_sha256=sha(rp)))
            else:code=row;nt=t
            corrected.append(code);newterminal.append(nt)
        write(out/filename,corrected);write(out/(channel+'_TERMINAL.json'),newterminal)
        counts[channel]=dict(records=len(flat),categories=dict(Counter(x['category'] for x in corrected)),recovered=sum(x['channel']==channel for x in changes))
    for n in ['main_JUDGE_COPY.json','original_JUDGE_COPY.json','PATH_REDACTION_AUDIT.json','PARALLEL_EXECUTION.json']:shutil.copyfile(old/n,out/n)
    return changes,counts


def e103_revalidate(old,strict,audit,out):
    rows=read(old/'RESPONSES.json');receipts={x['request_id']:x['response_sha256'] for x in audit['requests']};corrected=[];changes=[]
    for row in rows:
        rid=row['request_id'];rp=CACHE/'E103/ledger/E103_yesno'/(rid+'.response.json')
        require(sha(rp)==row['response_sha256']==receipts[rid],'original response/audit binding')
        saved=read(rp);value=saved['response']['choices'][0]['message'].get('content')
        require(value==row['raw_response'],'saved raw response unchanged')
        new=dict(row)
        if row['status']=='KEPT' or (row['status']=='UNPARSEABLE' and row['reason']=='FROZEN_YES_NO_PARSE'):response_ok(saved)
        if row['status']=='KEPT':require(e103_parse(value)==row['response'],'kept answer unchanged')
        elif row['status']=='UNPARSEABLE' and row['reason']=='FROZEN_YES_NO_PARSE':
            try:parsed=e103_parse(value)
            except ValueError:pass
            else:
                new.update(status='KEPT',reason=None,response=parsed)
                changes.append(dict(id=row['id'],old='unparseable',new=parsed,request_id=rid,response_sha256=sha(rp)))
        corrected.append(new)
    require([x['id'] for x in rows]==[x['id'] for x in corrected],'exact E103 grid/order')
    write(out/'RESPONSES.json',corrected)
    return changes,dict(records=len(rows),responses=dict(Counter(x['response'] for x in corrected)),recovered=len(changes))


def run(bank):
    commit=sources();base=CACHE/bank;old=base/'judgments';strict=verify(old/'JUDGMENT_SEAL.json',STRICT[bank]);audit=read(old/'ROUTE_AUDIT.json')
    require(strict['route_verified'] is True and strict['redaction_audit_complete'] is True,'strict route/privacy receipt')
    ledger=base/'ledger/ledger.jsonl';ledger_sha=sha(ledger)
    if bank=='E87':
        packet=read(base/'PACKET_SEAL.json');require(sha(base/'PACKET_SEAL.json')==strict['blind_seal_sha256'],'same E87 packet')
        private=base/'PRIVATE_JOIN.json';expected_private=packet['files']['PRIVATE_JOIN.json']
    else:
        receipt_path=ROOT/'results/g_agreement/understand/e103/I5_JUDGE_PACKET_CPU_RECEIPT.json'
        require(sha(receipt_path)==strict['packet_receipt_sha256'],'same E103 source packet')
        packet=read(receipt_path);private=Path(packet['private_directory'])/'MAPPING.PRIVATE.json';expected_private=packet['files']['MAPPING.PRIVATE.json']
    private_sha=sha(private);require(private_sha==expected_private,'same original CPU private join')
    out=base/'validator_corrected221';out.mkdir(parents=True,exist_ok=False)
    write(out/'REVALIDATION_START.json',dict(bank=bank,authority='§221 item1',strict_judgment_seal_sha256=STRICT[bank],validator_fix_commit=commit,started_utc=datetime.now(timezone.utc).isoformat(),new_calls=0))
    changes,counts=e87_revalidate(old,strict,audit,out) if bank=='E87' else e103_revalidate(old,strict,audit,out)
    require(sha(ledger)==ledger_sha and sha(private)==private_sha,'ledger/private join unchanged')
    verify(old/'JUDGMENT_SEAL.json',STRICT[bank])
    write(out/'REVALIDATION_DIFF.json',changes);write(out/'COUNTS.json',counts)
    shutil.copyfile(old/'ROUTE_AUDIT.json',out/'ROUTE_AUDIT.json')
    receipt=dict(bank=bank,label=f'validator-corrected ({bank} deviation 1)',authority='§221 item1',strict_judgment_seal_sha256=STRICT[bank],validator_fix_commit=commit,correction_source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),final_attempt_only=True,strict_kept_preserved=True,all_other_missing_preserved=True,new_calls=0,new_cost_usd=0,ledger_sha256=ledger_sha,private_join_local_path=str(private),private_join_sha256=private_sha,strict_analyses_unchanged=True)
    write(out/'CORRECTION_RECEIPT.json',receipt)
    seal=dict(strict);seal.update(status='COMPLETE_VALIDATOR_CORRECTED_ONCE',label=receipt['label'],strict_judgment_seal_sha256=STRICT[bank],validator_fix_commit=commit,source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),strict_source_seal_sha256=strict['source_seal_sha256'],new_calls=0,files={p.name:sha(p) for p in out.iterdir() if p.is_file()})
    write(out/'JUDGMENT_SEAL.json',seal)
    print(json.dumps(dict(bank=bank,output=str(out),seal_sha256=sha(out/'JUDGMENT_SEAL.json'),counts=counts,new_calls=0),sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bank',choices=['E87','E103'],required=True);a=p.parse_args();run(a.bank)
