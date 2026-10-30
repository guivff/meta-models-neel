"""§249 E137, fresh anti-recency items; no models or old item/score reads."""
import hashlib,random,re
SEED=20261030
NAMES=('Alice','Bob','Carl','Dana','Erin')
PLACES=('Rome','Paris','London','Berlin','Tokyo')
RELATIONS=('object_holder','object_location','token_owner')
OBJECTS=('brass key','silver coin','blue folder','copper badge','paper ticket','wooden box','red notebook','green parcel','round seal','small case')
TOKENS=('brass token','silver token','blue token','copper token','paper token','wooden token','red token','green token','round token','small token')
def opaque(s):return hashlib.sha256(s.encode()).hexdigest()[:24]

def render(relation,obj,chain,style,back,tail):
    a=chain[0]
    if relation=='object_holder':
        head=f'The {obj} starts with {a}' if style==0 else f'Initially, {a} holds the {obj}'
        transfer=lambda a,b,r:f'{a} '+('hands' if style==0 else 'passes')+f' the {obj} '+('back ' if r else '')+f'to {b}'
        goal=f'The {obj} is now held by'
    elif relation=='object_location':
        head=f'The {obj} starts beside {a}' if style==0 else f'Initially, the {obj} is beside {a}'
        transfer=lambda a,b,r:(f'Workers move the {obj}' if style==0 else f'The {obj} is moved')+f' from beside {a} '+('back ' if r else '')+f'to beside {b}'
        goal=f'The {obj} is now by'
    elif relation=='token_owner':
        head=f'The {obj} is initially owned by {a}' if style==0 else f'Initially, the {obj} belongs to {a}'
        transfer=lambda a,b,r:(f'{a} transfers ownership of the {obj} ' if style==0 else f'Ownership of the {obj} passes from {a} ')+('back ' if r else '')+f'to {b}'
        goal=f'The {obj} is now owned by'
    else:raise ValueError('relation')
    parts=[head]+[transfer(a,b,back and i==len(chain)-2) for i,(a,b) in enumerate(zip(chain,chain[1:]))]
    story='. '.join(parts);start=story.rfind(chain[-1]);span=[start,start+len(chain[-1])]
    prompt=story+'. '+('. '.join(tail)+'. ' if tail else '')+goal
    return prompt,span

def trailing(relation,obj,pool,n):
    a,b,c=pool
    if relation=='object_location':return [f'Later, {a} and {b} are compared on a map',f'A note lists {b} and {c}'][:n]
    return [f'Later, {a} asks {b} about the {obj}',f'{b} waves to {c}'][:n]

def check(prompt):
    """Parse lexical transitions independently, never consult intended chain/labels."""
    parts=prompt.split('. ');goal=parts[-1]
    endings=[('object_holder',' is now held by'),('object_location',' is now by'),('token_owner',' is now owned by')]
    relation,ending=next(((r,e) for r,e in endings if goal.startswith('The ') and goal.endswith(e)),(None,None))
    if relation is None:raise ValueError('goal')
    obj=goal[4:-len(ending)];esc=re.escape(obj);pool=PLACES if relation=='object_location' else NAMES
    if relation=='object_holder':
        starts=[rf'The {esc} starts with (\w+)',rf'Initially, (\w+) holds the {esc}'];moves=[rf'(?P<src>\w+) (?:hands|passes) the {esc} (?P<back>back )?to (?P<dst>\w+)']
    elif relation=='object_location':
        starts=[rf'The {esc} starts beside (\w+)',rf'Initially, the {esc} is beside (\w+)'];moves=[rf'(?:Workers move the {esc}|The {esc} is moved) from beside (?P<src>\w+) (?P<back>back )?to beside (?P<dst>\w+)']
    else:
        starts=[rf'The {esc} is initially owned by (\w+)',rf'Initially, the {esc} belongs to (\w+)'];moves=[rf'(?P<src>\w+) transfers ownership of the {esc} (?P<back>back )?to (?P<dst>\w+)',rf'Ownership of the {esc} passes from (?P<src>\w+) (?P<back>back )?to (?P<dst>\w+)']
    first=next((m for p in starts if (m:=re.fullmatch(p,parts[0]))),None)
    if first is None or first[1] not in pool:raise ValueError('start')
    history=[first[1]];tails=[];returned=False;passed_tail=False
    distractors=([r'Later, (\w+) and (\w+) are compared on a map',r'A note lists (\w+) and (\w+)'] if relation=='object_location' else [rf'Later, (\w+) asks (\w+) about the {esc}',r'(\w+) waves to (\w+)'])
    for sentence in parts[1:-1]:
        m=next((m for p in moves if (m:=re.fullmatch(p,sentence))),None)
        if m is not None:
            if passed_tail or m['src']!=history[-1] or m['dst'] not in pool or m['dst']==history[-1]:raise ValueError('broken transfer')
            if m['back']:
                if len(history)!=3 or m['dst'] not in history[:-1] or returned:raise ValueError('return must be third transfer to earlier holder')
                returned=True
            elif m['dst'] in history:raise ValueError('unmarked repeated holder')
            history.append(m['dst'])
        else:
            m=next((m for p in distractors if (m:=re.fullmatch(p,sentence))),None)
            if m is None or any(v not in pool for v in m.groups()):raise ValueError('not a frozen non-transfer sentence')
            passed_tail=True;tails.append(sentence)
    if len(history)==4:
        if len(tails) not in (1,2):raise ValueError('three-transfer designs need1/2 trailing distractors')
    elif len(history)==2:
        if tails or returned:raise ValueError('original one-hop control')
    else:raise ValueError('hop count')
    mentions=re.findall(r'\b(?:'+'|'.join(pool)+r')\b',prompt)
    if len(history)==4 and mentions[-1]==history[-1]:raise ValueError('answer is latest mentioned name/place')
    return dict(relation=relation,object=obj,current=history[-1],previous=history[-2],chain=history,transfers=len(history)-1,returned=returned,trailing_sentences=len(tails),latest_mention=mentions[-1])

def generate():
    rng=random.Random(SEED);public=[];pairs=[];seen=set();seen_items=set()
    for design,n in [('D1',150),('D2',150),('one_hop',60)]:
        for order in range(n):
            relation=RELATIONS[order%3];pool=PLACES if relation=='object_location' else NAMES
            while True:
                a,b,c,d,e=rng.sample(pool,5);obj=rng.choice(TOKENS if relation=='token_owner' else OBJECTS);style=rng.randrange(2)
                recipients=[a,b] if design=='D2' else [d,e]
                safe=[x for x in pool if x not in recipients];rng.shuffle(safe)
                tail=trailing(relation,obj,safe,1+rng.randrange(2)) if design!='one_hop' else []
                chains=[[a,last] if design=='one_hop' else [a,b,c,last] for last in recipients]
                rendered=[render(relation,obj,chain,style,design=='D2',tail) for chain in chains]
                key=tuple(sorted(p for p,_ in rendered))
                if key not in seen and not any(p in seen_items for p,_ in rendered):seen.add(key);seen_items.update(p for p,_ in rendered);break
            pair_id=opaque(f'E137|{SEED}|{design}|{order}');members=[]
            for j,((prompt,span),chain) in enumerate(zip(rendered,chains)):
                actual=check(prompt);ident=opaque(f'E137|{SEED}|{design}|{order}|{j}')
                if actual['current']!=chain[-1] or actual['previous']!=chain[-2] or actual['returned']!=(design=='D2'):raise ValueError('independent state check')
                if design!='one_hop' and actual['latest_mention'] in recipients:raise ValueError('twin latest-mention shortcut')
                public.append(dict(id=ident,prompt=prompt));members.append(dict(id=ident,member=j,current_holder=chain[-1],previous_holder=chain[-2],twin_recipient=recipients[1-j],chain=chain,final_recipient_char_span=span,latest_mention=actual['latest_mention']))
            normalized=[p[:s[0]]+'<FINAL_RECIPIENT>'+p[s[1]:] for p,s in rendered]
            if normalized[0]!=normalized[1]:raise ValueError('twins differ outside final recipient')
            pairs.append(dict(pair_id=pair_id,family='one_hop' if design=='one_hop' else 'multi_hop',subdesign=design,generation_order=order,relation=relation,object=obj,style=style,recipients=recipients,previous_holder=chains[0][-2],current_holder=recipients,twin_recipient=recipients[::-1],members=members,trailing_sentences=len(tail)))
    if len(public)!=720 or len(pairs)!=360 or len({x['prompt'] for x in public})!=720:raise ValueError('complete unique bank')
    return public,pairs
