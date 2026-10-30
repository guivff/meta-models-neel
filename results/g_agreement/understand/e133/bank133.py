"""§241 E133 fixed benign CPU item definitions; no model calls or outcomes."""
import hashlib
import random
import re

SEED = 20261030
NAMES = ('Alice', 'Bob', 'Carl', 'Dana', 'Erin')
PLACES = ('Rome', 'Paris', 'London', 'Berlin', 'Tokyo')
RELATIONS = ('object_holder', 'object_location', 'token_owner')
OBJECTS = ('brass key', 'silver coin', 'blue folder', 'copper badge', 'paper ticket',
           'wooden box', 'red notebook', 'green parcel', 'round seal', 'small case')
TOKENS = ('brass token', 'silver token', 'blue token', 'copper token', 'paper token',
          'wooden token', 'red token', 'green token', 'round token', 'small token')


def opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def render(relation, obj, chain, style):
    start = chain[0]
    if relation == 'object_holder':
        head = f'The {obj} starts with {start}' if style == 0 else f'Initially, {start} holds the {obj}'
        transfer = lambda a,b: f'{a} hands the {obj} to {b}' if style == 0 else f'{a} passes the {obj} to {b}'
        goal = f'The {obj} is now held by'
    elif relation == 'object_location':
        head = f'The {obj} starts beside {start}' if style == 0 else f'Initially, the {obj} is beside {start}'
        transfer = lambda a,b: f'Workers move the {obj} from beside {a} to beside {b}' if style == 0 else f'The {obj} is moved from beside {a} to beside {b}'
        goal = f'The {obj} is now by'
    elif relation == 'token_owner':
        head = f'The {obj} is initially owned by {start}' if style == 0 else f'Initially, the {obj} belongs to {start}'
        transfer = lambda a,b: f'{a} transfers ownership of the {obj} to {b}' if style == 0 else f'Ownership of the {obj} passes from {a} to {b}'
        goal = f'The {obj} is now owned by'
    else:
        raise ValueError('unknown registered relation')
    sentences = [head] + [transfer(a,b) for a,b in zip(chain,chain[1:])]
    prefix = '. '.join(sentences) + '. ' + goal
    final_start = prefix.rfind(chain[-1], 0, len(prefix)-len(goal))
    if final_start < 0:
        raise ValueError('final recipient not found')
    return prefix, [final_start,final_start+len(chain[-1])]


def check(prompt):
    """Independent lexical state tracker: parse prose, not intended label metadata."""
    sentences = prompt.split('. ')
    goal = sentences[-1]
    if goal.endswith(' is now held by'):
        relation = 'object_holder'; obj = goal[len('The '):-len(' is now held by')];pool=NAMES
        starts = [rf'The {re.escape(obj)} starts with (\w+)',rf'Initially, (\w+) holds the {re.escape(obj)}']
        transitions = [rf'(\w+) (?:hands|passes) the {re.escape(obj)} to (\w+)']
    elif goal.endswith(' is now owned by'):
        relation = 'token_owner';obj=goal[len('The '):-len(' is now owned by')];pool=NAMES
        starts = [rf'The {re.escape(obj)} is initially owned by (\w+)',rf'Initially, the {re.escape(obj)} belongs to (\w+)']
        transitions = [rf'(\w+) transfers ownership of the {re.escape(obj)} to (\w+)',rf'Ownership of the {re.escape(obj)} passes from (\w+) to (\w+)']
    elif goal.endswith(' is now by'):
        relation='object_location';obj=goal[len('The '):-len(' is now by')];pool=PLACES
        starts=[rf'The {re.escape(obj)} starts beside (\w+)',rf'Initially, the {re.escape(obj)} is beside (\w+)']
        transitions=[rf'Workers move the {re.escape(obj)} from beside (\w+) to beside (\w+)',rf'The {re.escape(obj)} is moved from beside (\w+) to beside (\w+)']
    else:
        raise ValueError('unknown final read phrase')
    if not goal.startswith('The '):
        raise ValueError('malformed goal')
    first=next((m for p in starts if (m:=re.fullmatch(p,sentences[0]))),None)
    if first is None or first[1] not in pool:
        raise ValueError('invalid initial state')
    state=first[1];history=[state]
    for sentence in sentences[1:-1]:
        match=next((m for p in transitions if (m:=re.fullmatch(p,sentence))),None)
        if match is None or match[1]!=state or match[2] not in pool or match[2] in history:
            raise ValueError('broken/repeated/unknown transfer')
        state=match[2];history.append(state)
    if len(history) not in (2,4):
        raise ValueError('requires exactly one or three transfers')
    return dict(relation=relation,object=obj,current=history[-1],previous=history[-2],
                transfers=len(history)-1,chain=history)


def generate():
    rng=random.Random(SEED)
    seen=set();seen_items=set();public=[];pairs=[]
    for family,count,hops in [('multi_hop',300,3),('one_hop',150,1)]:
        for order in range(count):
            relation=RELATIONS[order%3]
            while True:
                pool=PLACES if relation=='object_location' else NAMES
                a,b,c,d,e=rng.sample(pool,5)
                obj=rng.choice(TOKENS if relation=='token_owner' else OBJECTS)
                style=rng.randrange(2)
                recipients=[d,e]
                chains=[[a,b,c,last] if hops==3 else [a,last] for last in recipients]
                rendered=[render(relation,obj,chain,style) for chain in chains]
                key=tuple(sorted(p for p,_ in rendered))
                if key not in seen and not any(prompt in seen_items for prompt,_ in rendered):
                    seen.add(key);seen_items.update(prompt for prompt,_ in rendered);break
            pair_id=opaque(f'E133|{SEED}|{family}|{order}')
            members=[]
            for member,((prompt,span),chain) in enumerate(zip(rendered,chains)):
                ident=opaque(f'E133|{SEED}|{family}|{order}|{member}')
                actual=check(prompt)
                if actual['current']!=recipients[member] or actual['previous']!=chain[-2] or actual['transfers']!=hops:
                    raise ValueError('independent label check failed')
                public.append(dict(id=ident,prompt=prompt))
                members.append(dict(id=ident,member=member,current_holder=recipients[member],
                    previous_holder=chain[-2],twin_recipient=recipients[1-member],
                    chain=chain,final_recipient_char_span=span))
            normalized=[p[:span[0]]+'<FINAL_RECIPIENT>'+p[span[1]:] for p,span in rendered]
            if normalized[0]!=normalized[1]:
                raise ValueError('twins differ outside final recipient')
            pairs.append(dict(pair_id=pair_id,family=family,generation_order=order,relation=relation,
                 object=obj,style=style,recipients=recipients,previous_holder=chains[0][-2],
                 current_holder=recipients,twin_recipient=recipients[::-1],members=members))
    if len(public)!=900 or len(pairs)!=450 or len({r['id'] for r in public})!=900 or len({r['prompt'] for r in public})!=900:
        raise ValueError('incorrect/duplicate bank')
    return public,pairs
