"""CPU-only blind sampler. stdout contains aggregate counts only."""
import argparse,collections,hashlib,hmac,json,random,re,secrets
from pathlib import Path

SEED=20261027
STRATA=('S1','S2','S3','S4','C')
LANGS={'','python','py','javascript','js','typescript','ts','jsx','tsx','c','cpp','c++','java','rust','go','ruby','json','php','swift','kotlin','scala','sql','bash','sh','shell'}
READOUT_COLUMNS={'rl_greedy','rl_s1','rl_s2','rl_s3','rl_s4','sft_greedy','sft_s1','sft_s2','sft_s3','sft_s4'}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,d):Path(p).write_text(json.dumps(d,sort_keys=True,indent=2)+'\n')
def rng(key):return random.Random(int.from_bytes(hashlib.sha256((str(SEED)+'|'+key).encode()).digest(),'big'))


def lex(code,language):
    quote=None;stack=[];comment=False;block=False;i=0;bad=False
    hashes=language in ('','python','py','ruby','bash','sh','shell')
    while i<len(code):
        c=code[i]
        if comment:
            if c=='\n':comment=False
            i+=1;continue
        if block:
            if code.startswith('*/',i):block=False;i+=2
            else:i+=1
            continue
        if quote:
            if c=='\\':i+=2;continue
            if code.startswith(quote,i):i+=len(quote);quote=None;continue
            i+=1;continue
        if code.startswith('//',i) and language not in ('python','py','bash','sh','shell'):comment=True;i+=2;continue
        if hashes and c=='#':comment=True;i+=1;continue
        if code.startswith('/*',i):block=True;i+=2;continue
        if c in ('"',"'"):
            quote=c*3 if code.startswith(c*3,i) else c;i+=len(quote);continue
        if c in '([{':stack.append(c)
        elif c in ')]}':
            if stack and stack[-1]=='([{'[')]}'.index(c)]:stack.pop()
            else:bad=True
        i+=1
    return quote,stack,comment or block,bad


def classify(prefix):
    # Strip template boundaries only to limit the structural parser to the current message.
    message=re.split(r'<\|(?:system|user|assistant|observation)\|>|</?think>|</?tool_call>',prefix)[-1]
    lines=message.splitlines() or [''];fence=None;language='';code=[]
    for line in lines:
        m=re.match(r'^ {0,3}(`{3,}|~{3,})([^\s`]*)',line)
        if m:
            if fence is None:fence=m[1];language=m[2].lower();code=[]
            elif m[1][0]==fence[0] and len(m[1])>=len(fence):fence=None;code=[]
            continue
        if fence is not None:code.append(line)
    current=lines[-1]
    if fence is not None:
        if language not in LANGS:return None,{'reason':'unsupported_code_language'}
        body='\n'.join(code);quote,stack,comment,bad=lex(body,language)
        if bad or comment:return None,{'reason':'ambiguous_code_or_comment'}
        state={'open_quote':quote,'open_brackets':len(stack),'indent_spaces':len(current)-len(current.lstrip(' '))}
        if quote:return 'S1',state
        if stack:return 'S2',state
        if not current.startswith('\t') and state['indent_spaces']>=8:return 'S4',state
        return None,{'reason':'code_without_target_state'}
    # Require a preceding markdown delimiter row, with same table contiguous.
    prior=lines[:-1];separator=False
    for line in reversed(prior):
        if not line.strip() or '|' not in line:break
        if re.fullmatch(r'\s*\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?\s*',line):separator=True;break
    if separator and '|' in current and not current.rstrip().endswith('|'):
        pipes=len(re.findall(r'(?<!\\)\|',current));column=pipes if current.lstrip().startswith('|') else pipes+1
        if column>0:return 'S3',{'column_index_1based':column}
    # Known markup/code is not a content control, even if outside a recognised fence.
    if any(c in current for c in '|`{}[]') or re.match(r'^\s*(?:def |class |import |from |if |for |while |return |#|>>>|\$)',current) or len(current)-len(current.lstrip(' '))>=4:
        return None,{'reason':'nonprose_or_ambiguous_markup'}
    if not re.search(r'[^\W\d_]',current,re.UNICODE):return None,{'reason':'no_prose_content'}
    return 'C',{}


def choose(candidates):
    pools={s:{} for s in STRATA}
    for key,positions in sorted(candidates.items()):
        for s in STRATA:
            choices=sorted((p for p in positions if p['stratum']==s),key=lambda x:(x['pos'],x['row']))
            if choices:pools[s][key]=choices
    counts={s:{'eligible_rollouts':len(pools[s]),'selected':0,
               'status':'INCLUDED' if len(pools[s])>=50 else 'EXCLUDED_LT_50'} for s in STRATA}
    selected=[];used=set();randomizer=random.Random(SEED)
    while True:
        active=[s for s in STRATA if counts[s]['status']=='INCLUDED' and counts[s]['selected']<150 and set(pools[s])-used]
        if not active:break
        randomizer.shuffle(active)
        for s in active:
            available=sorted(set(pools[s])-used)
            if not available:continue
            key=randomizer.choice(available);p=randomizer.choice(pools[s][key])
            selected.append(p);used.add(key);counts[s]['selected']+=1
    for s in STRATA:
        counts[s]['overlap_exhausted']=counts[s]['status']=='INCLUDED' and counts[s]['selected']<150
    assert len({p['rollout'] for p in selected})==len(selected)
    return selected,counts


def plan(data,out):
    import pyarrow.parquet as pq
    from tokenizers import Tokenizer
    out.mkdir(parents=True,exist_ok=False)
    tok=Tokenizer.from_file(str(data/'tokenizer/tokenizer.json'))
    files=json.loads((data/'FILES.json').read_text())
    for name in ('transcripts.parquet','olens_wild_rollouts.parquet'):
        if sha(data/name)!=next(x['lfs']['oid'] for x in files if x['path']==name):raise ValueError('download hash mismatch')
    # Explicit column allowlist: no readout column is decoded in this phase.
    columns=['source','family','tid','pos','token','role']
    assert not READOUT_COLUMNS.intersection(columns)
    positions=pq.read_table(data/'olens_wild_rollouts.parquet',columns=columns).to_pylist()
    by=collections.defaultdict(list)
    for i,r in enumerate(positions):r['row']=i;by[(r['source'],r['tid'])].append(r)
    transcripts=pq.read_table(data/'transcripts.parquet',columns=['source','tid','text','ids','family']).to_pylist()
    candidates={};rejected=collections.Counter();seen=set();eligible_positions=collections.Counter()
    identity_counts=collections.Counter((t['source'],t['tid']) for t in transcripts)
    for tr in transcripts:
        key=(tr['source'],tr['tid'])
        if identity_counts[key]>1:rejected['ambiguous_transcript_identity']+=1;continue
        if key in seen:raise ValueError('duplicate transcript key')
        seen.add(key);text=tr['text'];ids=tr['ids'];encoded=tok.encode(text,add_special_tokens=False)
        if encoded.ids!=ids or tok.decode(ids,skip_special_tokens=False)!=text:
            rejected['transcript_alignment']+=1;continue
        cs=[];used=set()
        for r in by.get(key,[]):
            pos=r['pos']
            if pos in used:raise ValueError('duplicate transcript position')
            used.add(pos)
            if pos<0 or pos>=len(ids) or not encoded.offsets[pos][1]:rejected['position_bounds']+=1;continue
            if tok.decode([ids[pos]],skip_special_tokens=False)!=r['token']:rejected['token_alignment']+=1;continue
            end=encoded.offsets[pos][1]
            s,state=classify(text[:end])
            if s is None:rejected[state['reason']]+=1;continue
            eligible_positions[s]+=1
            cs.append({'rollout':json.dumps(key),'row':r['row'],'pos':pos,'char_end':end,'stratum':s,'state':state,'family':r['family'],'role':r['role'],'eval_rl':'RL_TRAINING' if r['family']=='rlvr1' else 'UNKNOWN'})
        if cs:candidates[json.dumps(key)]=cs
    selected,counts=choose(candidates)
    dump(out/'SELECTION.PRIVATE.json',selected)
    report={'seed':SEED,'strata':counts,'eligible_positions':dict(eligible_positions),'rejections':dict(rejected),'total_positions':len(positions),'total_transcripts':len(transcripts),'recoverable_transcripts':len(transcripts)-rejected['transcript_alignment']-rejected['ambiguous_transcript_identity'],'readout_column':'rl_greedy','readout_columns_opened':False,'dataset_revision':json.loads((data/'REVISION.json').read_text())['revision'],'input_sha256':{n:sha(data/n) for n in ['olens_wild_rollouts.parquet','transcripts.parquet','tokenizer/tokenizer.json']}}
    dump(out/'COUNTS.json',report)
    print(json.dumps(report,indent=2))


def materialize(data,plan_dir):
    import pyarrow.parquet as pq
    from pyarrow import array
    counts=json.loads((plan_dir/'COUNTS.json').read_text())
    if sha(data/'olens_wild_rollouts.parquet')!=counts['input_sha256']['olens_wild_rollouts.parquet']:raise ValueError('input changed')
    selected=json.loads((plan_dir/'SELECTION.PRIVATE.json').read_text())
    if not selected:raise ValueError('no eligible strata; no packet created')
    with (plan_dir/'MATERIALIZE_ONCE.lock').open('x') as f:f.write(sha(plan_dir/'SELECTION.PRIVATE.json'))
    salt=secrets.token_bytes(32)
    texts=pq.read_table(data/'olens_wild_rollouts.parquet',columns=['rl_greedy']).take(array([r['row'] for r in selected]))['rl_greedy'].to_pylist()
    packet=[];mapping=[]
    for r,text in zip(selected,texts):
        if not isinstance(text,str) or not text.strip():raise ValueError('selected readout missing; no replacement')
        opaque=hmac.new(salt,str(r['row']).encode(),'sha256').hexdigest()[:24]
        packet.append({'id':opaque,'readout':text});mapping.append({'id':opaque,**r})
    rng('packet_shuffle').shuffle(packet)
    for name,records in [('BLIND_PACKET.jsonl',packet),('STRATUM_MAP.PRIVATE.jsonl',mapping)]:
        with (plan_dir/name).open('x') as f:
            for record in records:f.write(json.dumps(record,ensure_ascii=False)+'\n')
    dump(plan_dir/'PACKET_SEAL.json',{'status':'BLIND_PACKET_READY','n':len(packet),'seed':SEED,'dataset_revision':counts['dataset_revision'],'packet_sha256':sha(plan_dir/'BLIND_PACKET.jsonl'),'private_map_sha256':sha(plan_dir/'STRATUM_MAP.PRIVATE.jsonl'),'counts_sha256':sha(plan_dir/'COUNTS.json'),'selection_sha256':sha(plan_dir/'SELECTION.PRIVATE.json'),'readouts_inspected_by_agent':False})
    print('Blind packet written; text suppressed. Records:',len(packet))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('phase',choices=['plan','materialize']);p.add_argument('--data',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    # Raw text/key custody is always under ignored cache, never public results.
    root=Path(__file__).resolve().parents[4]
    if not a.out.resolve().is_relative_to(root/'cache'):raise ValueError('output must be under repository cache')
    if a.phase=='plan':plan(a.data,a.out)
    else:materialize(a.data,a.out)
