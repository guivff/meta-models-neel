"""CPU-only roster envelope; unchanged E133 parser, no scientific scoring.

Track Q supplies the prospectively registered one-hop count and ruling. There
is no capacity-derived default and no execution by the source packet builder.
"""
from pathlib import Path
import inspect
from projects.g_agreement.e100.contract import read,write,sha,verify
from projects.g_agreement.e133b.selection import correct,answers,PARSER_SHA
from projects.g_agreement.e137.runner import load,count_disposition,validate_items
PAIR_SHA='92a5af53112e750be82336f0bdbfb996aa25cbe0d5b5e9102ba860f8b764e9dc'


def choose(pairs,screen_answers,one_hop_limit,authority):
    if type(one_hop_limit)is not int or not 0<=one_hop_limit<=60 or not authority:
        raise ValueError('explicit prospective one-hop quota and ruling required')
    groups={k:[]for k in ('D1','D2','one_hop')}
    seen=set()
    for pair in pairs:
        members=sorted(pair['members'],key=lambda x:x['member'])
        ids=[m['id']for m in members]
        if len(ids)!=2 or seen.intersection(ids)or not set(ids)<=set(screen_answers):
            raise ValueError('exact complete original member answers; no partial selection')
        seen.update(ids)
        cands=[*pair['recipients'],pair['previous_holder']]
        if all(correct(screen_answers[i],cands,m['current_holder'])for i,m in zip(ids,members)):
            groups[pair['subdesign']].append(ids)
    disposition=count_disposition(len(groups['D1']),len(groups['D2']))
    kept={k:groups[k][:(one_hop_limit if k=='one_hop'else 42)]for k in groups}
    ids={i for ps in kept.values()for p in ps for i in p}
    if 3*len(ids)>600:raise ValueError('registered native ceiling exceeded; no truncation')
    return kept,{k:len(v)for k,v in groups.items()},disposition


def select(screen_root,screen_sha,public_root,input_sha,original_pairs,pair_sha,out,*,one_hop_limit,authority):
    from projects.g_agreement.core.analysis_utils import parse_target_answer
    if sha(inspect.getfile(parse_target_answer))!=PARSER_SHA:raise ValueError('original parser pin')
    if sha(Path(screen_root)/'OUTPUT_SEAL.json')!=screen_sha:raise ValueError('explicit new complete screen seal')
    seal=read(Path(screen_root)/'OUTPUT_SEAL.json')
    if seal.get('experiment')!='E133'or seal.get('arm')!='synthetic':raise ValueError('unchanged E133 synthetic inner envelope')
    public=load(public_root,input_sha,'screen')
    ans,actual=answers(screen_root)
    if actual!=screen_sha or set(ans)!={x['id']for x in public}:raise ValueError('complete exact720 output census')
    if pair_sha!=PAIR_SHA or sha(original_pairs)!=PAIR_SHA:raise ValueError('frozen owner pair map')
    pairs=read(original_pairs)['pairs']
    kept,counts,d=choose(pairs,ans,one_hop_limit,authority)
    wanted={i for ps in kept.values()for p in ps for i in p}
    records=[x for x in public if x['id']in wanted]
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    result=dict(experiment='E137',qualifying=counts,disposition=d,screen_output_seal_sha256=screen_sha,selected_by='CPU behaviour only',one_hop_main_rule_authority=authority,one_hop_limit=one_hop_limit)
    if d['action']=='MAIN':
        validate_items(records,'main');root=out/'main';root.mkdir()
        write(root/'items.json',records)
        write(root/'MANIFEST.json',dict(experiment='E137',stage='main',labels_on_pod=False))
        write(root/'SCREEN_SELECTION_SEAL.json',dict(experiment='E137',selection_basis='behaviour_only_both_members_correct',reader_calls_before_selection=0,screen_output_seal_sha256=screen_sha,screen_input_sha256=input_sha,kept_item_ids=[x['id']for x in records],one_hop_main_rule_authority=authority,one_hop_limit=one_hop_limit,parser_sha256=PARSER_SHA,selector_sha256=sha(__file__)))
        write(root/'INPUT_SEAL.json',dict(experiment='E137',stage='main',labels_on_pod=False,files={p.name:sha(p)for p in root.iterdir()}))
        result['main_input_sha256']=sha(root/'INPUT_SEAL.json')
    write(out/'DISPOSITION.json',result)
    return result
