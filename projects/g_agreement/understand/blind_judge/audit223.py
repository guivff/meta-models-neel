"""§223.1 read-only audit using pure functions from exact executed archives.
No entrypoint from a paid dispatcher is imported or executed. No correction is
performed by this diagnostic, and strict outputs/guards/ledgers stay untouched.
"""
import argparse,ast,hashlib,json,re,tarfile,unicodedata
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
from projects.g_agreement.readerbench.io import read,sha,write
ROOT=Path(__file__).resolve().parents[4]
BANKS={
 'E81':dict(seal='65030bffdf5b9b245c3afdbbfef371a3ddaa610f8a84199b0df2fe03e8ecd259',cache='e81_judge_cpu_v3',job='E81_judgments',primary='E81',original='E81_original_25pct'),
 'E82':dict(seal='fd09388fb1a55b2e855fbef11d29e9ab8cc848b3e53dbedd2d5883af7200ae52',cache='e82_judge_cpu_v1',job='E82_judgments',primary='E82',original='E82_original_25pct')}
I2=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-i2/cache/g_agreement/i2')


def require(ok,message):
    if not ok:raise ValueError(message)


def functions(source,names,env):
    tree=ast.parse(source);nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
    require({n.name for n in nodes}==set(names),'exact frozen pure functions present')
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<sealed pure validators>','exec'),env)
    return env


def frozen(bank):
    p=ROOT/'results/g_agreement/sealed'/(bank+'_FULL_BLIND_JUDGMENTS')
    with tarfile.open(p/'EXECUTED_SOURCE.tar.gz') as t:
        get=lambda n:t.extractfile(n).read().decode()
        scoring=get('runtime/projects/g_agreement/readerbench/scoring.py')
        env={'re':re,'unicodedata':unicodedata,'__name__':'sealed_offline_validator'}
        for n in ast.parse(scoring).body:
            if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ('E56','D5'):env[n.targets[0].id]=ast.literal_eval(n.value)
        functions(scoring,['require','validate_judgments'],env)
        later=get('runtime/projects/g_agreement/understand/blind_judge/later_runner.py')
        functions(later,['normalize','classify'],env)
        if bank=='E82':
            g=functions(get('e82_grouped_judge.py'),['validate_code'],dict(env))
            env['G']=SimpleNamespace(validate_code=g['validate_code']);env['L']=SimpleNamespace(normalize=env['normalize'])
            functions(get('e82_dispatch.py'),['classify'],env)
        return env


def rejection(bank,item,value,env):
    codes=value.get('records',[]) if isinstance(value,dict) else []
    if not isinstance(codes,list):return 'records_not_list',{}
    matches=[c for c in codes if isinstance(c,dict) and c.get('id')==item['id']]
    if len(matches)!=1:return 'missing_or_duplicate_opaque_ID',dict(returned_records=len(codes),matching_records=len(matches))
    code=matches[0];facts=dict(category=code.get('category'),evidence_empty=code.get('evidence')=='',values_empty=code.get('values')==[],extra_first_position='first_position' in code)
    try:
        if bank=='E81':
            p=dict(item,readout=env['normalize'](item['readout']));c=dict(code)
            if isinstance(c.get('evidence'),str):c['evidence']=env['normalize'](c['evidence'])
            env['validate_judgments']([p],[c],'E56')
        else:
            if set(code)!={'id','category','values','evidence'}:return 'group_code_field_set',facts
            allowed=['A'] if item['rubric'].endswith('\nB: \n') else ['A','B']
            p=dict(item,positions=[dict(x,readout=env['normalize'](x['readout'])) for x in item['positions']])
            c=dict(code,evidence=env['normalize'](code['evidence']))
            env['G'].validate_code(p,c,allowed,env['validate_judgments'])
    except (ValueError,AssertionError,TypeError,KeyError) as exc:
        reason=str(exc) if isinstance(exc,(ValueError,AssertionError)) and str(exc) else type(exc).__name__
        return reason,facts
    return 'VALID_REJECTED_BY_PIPELINE',facts


def audit(bank):
    spec=BANKS[bank];pub=ROOT/'results/g_agreement/sealed'/(bank+'_FULL_BLIND_JUDGMENTS');local=I2/spec['cache'];job=local/'judging'/spec['job']
    require(sha(pub/'RESULT_SEAL.json')==spec['seal']==sha(job/'RESULT_SEAL.json'),'published/source strict seal identity')
    seal=read(job/'RESULT_SEAL.json')
    for n,h in seal['files'].items():require(sha(job/n)==h,'strict member '+n)
    intake=read(pub/'INTAKE.json')
    expected_raw=intake['raw_responses_archive_sha256'] if bank=='E81' else intake['files']['RAW_RESPONSES.tar.gz']
    require(sha(pub/'RAW_RESPONSES.tar.gz')==expected_raw,'raw archive binding')
    expected_source=intake['executed_source_archive_sha256'] if bank=='E81' else intake['files']['EXECUTED_SOURCE.tar.gz']
    require(sha(pub/'EXECUTED_SOURCE.tar.gz')==expected_source,'executed source binding')
    env=frozen(bank);index={};bindings=[]
    with tarfile.open(pub/'RAW_RESPONSES.tar.gz') as t:
        for member in t:
            if not member.isfile() or not member.name.endswith('.response.json'):continue
            relative=Path(member.name);require(len(relative.parts)==2,'stage/response archive path')
            stage=relative.parts[0];rid=relative.name.removesuffix('.response.json');qp=local/'judging'/stage/(rid+'.request.json')
            wire=read(qp)['wire'];label,attempt=stage.rsplit('_attempt',1)
            canonical=json.dumps(wire,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)
            require(hashlib.sha256((label+':'+attempt+':'+canonical).encode()).hexdigest()==rid,'original raw response/wire digest')
            raw=t.extractfile(member).read();saved=json.loads(raw);items=json.loads(wire['messages'][1]['content'])
            for item in items:
                key=stage,item['id'];require(key not in index,'unique stage/item raw response')
                index[key]=(saved,item,rid,hashlib.sha256(raw).hexdigest())
    report={};details=[]
    for name,filename in [('primary','JUDGMENTS.json'),('original','ORIGINAL_JUDGMENTS.json')]:
        rows=read(pub/filename);require(sha(pub/filename)==seal['files'][filename],'terminal publication/source member')
        missing=[x for x in rows if x['status']=='UNPARSEABLE'];counter=Counter();facts_counter=Counter()
        for row in missing:
            stage=f'{spec[name]}_attempt{row["attempts"]}';saved,item,rid,response_sha=index[stage,row['id']];body=saved['response'];choice=body.get('choices',[{}])[0]
            counter['HTTP_'+str(saved['http_status'])]+=1;counter['finish_'+str(choice.get('finish_reason'))]+=1
            require(saved['http_status']==200 and body.get('provider')=='Google' and body.get('model') in ('google/gemini-3.1-flash-lite','google/gemini-3.1-flash-lite-001'),'actual terminal response route')
            if choice.get('finish_reason')=='length':reason='CHARGED_LENGTH_TERMINAL_MISSING';facts={}
            else:
                require(choice.get('finish_reason')=='stop','unrecognized finish')
                try:value=json.loads(choice['message']['content'])
                except (ValueError,TypeError,KeyError):reason='INVALID_JSON';facts={}
                else:
                    original=env['classify']([item],value,'E56') if bank=='E81' else env['classify']([item],value,{item['id']:['A'] if item['rubric'].endswith('\nB: \n') else ['A','B']})
                    reason,facts=rejection(bank,item,value,env)
                    require((original[0]['status']=='KEPT')==(reason=='VALID_REJECTED_BY_PIPELINE'),'frozen exact classifier/reason reproduction')
            counter[reason]+=1
            if facts.get('category')=='silent' and facts.get('evidence_empty') and facts.get('values_empty'):facts_counter['silent_empty_evidence_and_values']+=1
            if facts.get('extra_first_position'):facts_counter['extra_first_position']+=1
            details.append(dict(channel=name,id=row['id'],request_id=rid,response_sha256=response_sha,stage=stage,reason=reason,facts=facts))
        report[name]=dict(total_records=len(rows),terminal_missing=len(missing),counts=dict(counter),special_cases=dict(facts_counter))
    return dict(bank=bank,strict_result_seal_sha256=spec['seal'],raw_archive_sha256=expected_raw,source_archive_sha256=expected_source,channels=report,details=details,new_calls=0,judgments_changed=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bank',choices=['E81','E82'],required=True);p.add_argument('--out',required=True);a=p.parse_args();result=audit(a.bank);out=Path(a.out);out.mkdir(parents=True,exist_ok=False);write(out/'AUDIT.json',result);print(json.dumps({k:v for k,v in result.items() if k!='details'},indent=2))
