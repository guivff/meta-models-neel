"""CPU-only source adapter: structure/ascending recipient tokens on pod, truth off."""
import json,tarfile
from pathlib import Path
from projects.g_agreement.e100.contract import read,write,sha,verify


def adapt(public,pairs,tok,arm):
    if arm not in ('synthetic','babi')or any(set(x)!={'id','prompt'}for x in public):raise ValueError('sealed original id/prompt source')
    lookup={x['id']:x for x in public}
    if len(lookup)!=len(public):raise ValueError('unique original public IDs')
    xs=[];cpu=[]
    for order,p in enumerate(pairs):
        if arm=='synthetic':
            members=p['members'];ids=[m['id']for m in members];recipients=p['recipients'];pid=p['pair_id'];family=p['family']
        else:
            ids=p['member_ids'];recipients=[p['original_current'],p['twin_current']];pid=p['pair_id'];family='babi';members=[dict(id=i,member=k)for k,i in enumerate(ids)]
        if ids!=[x['id']for x in public[2*order:2*order+2]]:raise ValueError('literal source member IDs/order mismatch')
        tokens=[tok.encode(' '+v,add_special_tokens=False)for v in recipients]
        if any(len(v)!=1 for v in tokens)or tokens[0]==tokens[1]:raise ValueError('distinct single-token recipients')
        sorted_ids=sorted(v[0]for v in tokens)
        for k,m in enumerate(members):
            if arm=='synthetic'and(m['member']!=k or m['current_holder']!=recipients[k]or m['previous_holder']!=p['previous_holder']):raise ValueError('original CPU role binding mismatch')
            x=lookup[m['id']];native=tok.encode(x['prompt'],add_special_tokens=False)
            for word,v in zip(recipients,tokens):
                if tok.encode(x['prompt']+' '+word,add_special_tokens=False)!=native+v:raise ValueError('original full-prefix token boundary')
            xs.append(dict(id=x['id'],pair_id=pid,family=family,member=k,ids=native,read_index=len(native)-1,candidate_ids=[[[sorted_ids[0]],[sorted_ids[1]]]]))
            cpu.append(dict(id=x['id'],pair_id=pid,original_pair_order=order,family=family,member=k,recipient_strings=recipients,recipient_token_ids=[v[0]for v in tokens],ascending_candidate_ids=sorted_ids,current_recipient_index=k,previous=p['previous_holder']if arm=='synthetic'else p['previous']))
    if len(xs)!=len(public):raise ValueError('all original source items accounted')
    return xs,cpu


def seal_packet(public,pairs,tok,arm,out,source):
    from .runner import validate_items
    xs,cpu=adapt(public,pairs,tok,arm);validate_items(xs,'screen')
    out=Path(out);out.mkdir(exist_ok=False);p=out/'inputs';p.mkdir();c=out/'cpu_only';c.mkdir()
    write(p/'items.json',xs)
    write(p/'MANIFEST.json',dict(experiment='E133',arm=arm,stage='screen',source=source,labels_on_pod=False,order='original frozen source pair/member order; no selection',candidate_policy='only pair recipient tokens, ascending numeric IDs; no current/previous role',fields_on_pod=['id','pair_id','family','member','ids','read_index','candidate_ids']))
    write(p/'INPUT_SEAL.json',dict(experiment='E133',arm=arm,stage='screen',labels_on_pod=False,files={x.name:sha(x)for x in p.iterdir()}))
    write(c/'ROLES.PRIVATE.json',cpu);write(c/'ROLE_SEAL.json',dict(experiment='E133',arm=arm,input_sha256=sha(p/'INPUT_SEAL.json'),files={'ROLES.PRIVATE.json':sha(c/'ROLES.PRIVATE.json')}))
    for f in c.iterdir():f.chmod(0o600)
    with tarfile.open(out/'inputs.tar.gz','w:gz',compresslevel=1)as t:
        for x in sorted(p.iterdir()):t.add(x,arcname=x.name)
    return dict(experiment='E133',arm=arm,public_root=str(p),input_sha256=sha(p/'INPUT_SEAL.json'),archive=str(out/'inputs.tar.gz'),archive_sha256=sha(out/'inputs.tar.gz'),CPU_only_root=str(c),CPU_only_role_seal_sha256=sha(c/'ROLE_SEAL.json'),prompts=len(xs),pairs=len(pairs),source=source,model_calls=0,selected_pairs=None)
