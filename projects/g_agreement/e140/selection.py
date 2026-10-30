"""CPU-only registered first-line behaviour parser and source-order selection.

No actual screen is read by packet preparation. X/Y and original answers stay CPU.
"""
import string
from pathlib import Path
from projects.g_agreement.e100.contract import read,write,verify,sha
from projects.g_agreement.e140.runner import load,validate_items,screen_scope
from projects.g_agreement.e140.pair_binding import AUTHORITY,first_token_axis
PARSER_POLICY='first nonempty line; lower(); remove ASCII string.punctuation everywhere; strip exterior whitespace; no other normalization'


def parse(text):
    if not isinstance(text,str):raise ValueError('missing raw screen record is not an empty answer')
    for line in text.splitlines():
        if line.strip():return line.lower().translate(str.maketrans('','',string.punctuation)).strip()
    return ''


def choose(pair_ids,screen_answers):
    kept=[];qualifying=[];seen=set()
    for pair in pair_ids:
        if len(pair)!=2 or any(i in seen for i in pair)or not set(pair)<=set(screen_answers):raise ValueError('complete original paired screen IDs')
        seen.update(pair);x,y=[parse(screen_answers[i])for i in pair]
        if x and y and x!=y:qualifying.append(dict(member_ids=pair,X=x,Y=y))
    if len(seen)!=len(screen_answers):raise ValueError('no extra answer IDs')
    return qualifying[:84],len(qualifying)


def select(screen_root,screen_sha,public_root,input_sha,out,*,pair_measurement_rule_authority=AUTHORITY,tokenizer=None):
    if pair_measurement_rule_authority!=AUTHORITY:raise ValueError('exact c33fcfb40 first-token measurement ruling required')
    if tokenizer is None:raise ValueError('explicit pinned CPU Qwen tokenizer required')
    screen_root=Path(screen_root);s=verify(screen_root,'OUTPUT_SEAL.json',screen_sha)
    if s.get('experiment')!='E140'or s.get('stage')!='screen'or s.get('status')!='COMPLETE':raise ValueError('NEW complete original E140 screen only')
    items=load(public_root,input_sha,'screen');scope=screen_scope(public_root,input_sha,items);ans={}
    for f in sorted(k for k in s['files']if k.startswith('jobs/')):
        for x in read(screen_root/f):
            if x['id']in ans or 'text'not in x:raise ValueError('unique original raw answers')
            ans[x['id']]=x['text']
    pairs={}
    for x in items:pairs.setdefault(x['pair_id'],{})[x['member']]=x['id']
    if set(ans)!={x['id']for x in items}:raise ValueError('complete registered screen answers, no stitch/missing record')
    kept,n=choose([[p[0],p[1]]for p in pairs.values()],ans)
    for p in kept:p['pair_axis']=first_token_axis(tokenizer,p['X'],p['Y'])
    wanted={i for p in kept for i in p['member_ids']};records=[x for x in items if x['id']in wanted]
    out=Path(out);out.mkdir(parents=True,exist_ok=False);cpu=out/'cpu_only';cpu.mkdir()
    write(cpu/'SELECTION.PRIVATE.json',dict(kept=kept,original_answer_source_sha256=screen_sha))
    write(cpu/'CPU_SEAL.json',dict(experiment='E140',files={'SELECTION.PRIVATE.json':sha(cpu/'SELECTION.PRIVATE.json')}))
    for f in cpu.iterdir():f.chmod(0o600)
    result=dict(**scope,experiment='E140',qualifying_pairs=n,kept_pairs=min(84,n),action='MAIN'if n>=40 else'SCREEN_RESULTS_ONLY',screen_output_sha256=screen_sha,CPU_only_seal_sha256=sha(cpu/'CPU_SEAL.json'))
    if n>=40:
        validate_items(records,'main');root=out/'main';root.mkdir();write(root/'items.json',records);write(root/'MANIFEST.json',dict(experiment='E140',stage='main',labels_on_pod=False,prompts=len(records)))
        write(root/'SCREEN_SELECTION_SEAL.json',dict(**scope,experiment='E140',selection_basis='nonempty_different_paraphrase_answers',reader_calls_before_selection=0,screen_output_seal_sha256=screen_sha,kept_item_ids=[x['id']for x in records],parser_policy=PARSER_POLICY,selector_sha256=sha(__file__),pair_measurement_rule_authority=pair_measurement_rule_authority))
        write(root/'INPUT_SEAL.json',dict(experiment='E140',stage='main',labels_on_pod=False,files={p.name:sha(p)for p in root.iterdir()}));result['input_sha256']=sha(root/'INPUT_SEAL.json')
    write(out/'DISPOSITION.json',result);return result
