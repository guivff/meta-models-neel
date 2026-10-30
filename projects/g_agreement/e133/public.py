"""Label-free runtime compilation of sealed id/prompt-only E133 packets."""
import hashlib,itertools
from pathlib import Path
from projects.g_agreement.e100.contract import read,verify
VALUES={'synthetic':('Alice','Bob','Carl','Dana','Erin','Rome','Paris','London','Berlin','Tokyo'),
        'babi':('bathroom','bedroom','garden','hallway','kitchen','office')}


def compile_items(public,tok,arm,stage,*,multi_pairs=None):
    if arm not in VALUES or stage not in ('screen','main')or len(public)%2 or not public or len({x['id']for x in public})!=len(public):raise ValueError('unique complete public pairs/arm/stage')
    if any(set(x)!={'id','prompt'}or not isinstance(x['prompt'],str)for x in public):raise ValueError('public id/prompt ONLY; no private roles')
    if arm=='synthetic':
        if stage=='screen':
            if len(public)!=900:raise ValueError('900original synthetic screen prompts')
            multi_pairs=300
        elif type(multi_pairs)is not int or not 0<=multi_pairs<=84 or not 0<=len(public)//2-multi_pairs<=42:raise ValueError('frozen main84/42 count metadata')
    elif stage=='main'and len(public)>84:raise ValueError('up-to42babi pairs')
    candidates=[]
    for word in VALUES[arm]:
        ids=tok.encode(' '+word,add_special_tokens=False)
        if len(ids)!=1:raise ValueError('fixed global candidate must be single token; never truncate')
        candidates.append(ids)
    # EVERY item receives EVERY same unordered global vocabulary contrast, fixed order.
    # This reveals no per-item current/previous/twin role or correctness label.
    pairs=[[a,b]for a,b in itertools.combinations(candidates,2)];xs=[]
    for j in range(0,len(public),2):
        pair=public[j:j+2];pid=hashlib.sha256(('E133:'+arm+':'+pair[0]['id']+':'+pair[1]['id']).encode()).hexdigest()
        for k,x in enumerate(pair):
            ids=tok.encode(x['prompt'],add_special_tokens=False)
            if not ids or len(ids)<=9:raise ValueError('original available read/earlier sites')
            for word,c in zip(VALUES[arm],candidates):
                if tok.encode(x['prompt']+' '+word,add_special_tokens=False)!=ids+c:raise ValueError('full-prefix candidate boundary mismatch')
            family='babi'if arm=='babi'else 'multi_hop'if j//2<multi_pairs else 'one_hop'
            xs.append(dict(id=x['id'],pair_id=pid,family=family,member=k,ids=ids,read_index=len(ids)-1,candidate_ids=pairs))
    return xs


def load_public(root,digest,tok,arm,stage,*,multi_pairs=None):
    root=Path(root);seal=verify(root,'INPUT_SEAL.json',digest)
    if seal['experiment']!='E133'or seal['labels_on_pod']is not False or set(seal['files'])-{'items.json','MANIFEST.json'}:raise ValueError('public source seal and member allowlist')
    if seal.get('stage')not in (stage,None) and not(arm=='babi'and seal.get('stage')is None):raise ValueError('public stage mismatch')
    return compile_items(read(root/'items.json'),tok,arm,stage,multi_pairs=multi_pairs)
