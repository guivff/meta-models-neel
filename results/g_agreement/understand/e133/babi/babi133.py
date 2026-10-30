"""Own QA2 data parser and counterfactual checker; executes no dataset code."""
from collections import Counter
import hashlib
import random
import re

SEED=20261030
MOVE=re.compile(r'(?P<actor>\w+) (?:moved|journeyed|travelled|went(?: back)?) to the (?P<location>\w+)\.')
PICK=re.compile(r'(?P<actor>\w+) (?:got|grabbed|took|picked up) the (?P<object>\w+)(?: there)?\.')
DROP=re.compile(r'(?P<actor>\w+) (?:put down|discarded|dropped|left) the (?P<object>\w+)(?: there)?\.')
QUESTION=re.compile(r'Where is the (\w+)\?')


def episodes(text):
    """Keep narrative facts and each episode's original FINAL question only."""
    output=[];facts=[];questions=[];index=-1
    def save():
        if questions:
            output.append(dict(episode=index,facts=questions[-1]['facts'],question=questions[-1]))
    for line in text.splitlines():
        if not line.strip():continue
        number,body=line.split(' ',1);number=int(number)
        if number==1:
            save();index+=1;facts=[];questions=[]
        if '\t' in body:
            parts=body.split('\t')
            if len(parts)!=3:raise ValueError('unexpected source question schema')
            questions.append(dict(line=number,text=parts[0].rstrip(),answer=parts[1],
                                  supporting_ids=[int(v) for v in parts[2].split()],facts=list(facts)))
        else:
            facts.append(dict(line=number,text=body))
    save()
    return output


def replay(facts):
    actors={};owner={};locations={};events={};seen=[]
    for index,fact in enumerate(facts):
        text=fact['text'];move=MOVE.fullmatch(text);pick=PICK.fullmatch(text);drop=DROP.fullmatch(text)
        if move:
            actor,place=move['actor'],move['location']
            if place not in seen:seen.append(place)
            actors[actor]=place
            for obj,carrier in list(owner.items()):
                if carrier==actor:
                    old=locations.get(obj)
                    if old!=place:
                        events.setdefault(obj,[]).append(dict(index=index,line=fact['line'],actor=actor,
                            previous=old,current=place,location_span=list(move.span('location')),locations_seen=list(seen)))
                    locations[obj]=place
        elif pick:
            actor,obj=pick['actor'],pick['object'];where=actors.get(actor)
            if owner.get(obj) is not None:raise ValueError('pickup already-held object')
            known=locations.get(obj)
            if known is not None and where is not None and known!=where:raise ValueError('pickup not co-located')
            if where is None and known is not None:
                # Pickup establishes co-location; no fabricated new room.
                actors[actor]=known;where=known
            owner[obj]=actor;locations[obj]=where
        elif drop:
            actor,obj=drop['actor'],drop['object']
            if owner.get(obj)!=actor:raise ValueError('drop not carried by actor')
            owner[obj]=None;locations[obj]=actors.get(actor)
        else:
            raise ValueError('unrecognised data sentence; never execute it')
    return dict(actor_locations=actors,owners=owner,object_locations=locations,events=events,locations_seen=seen)


def prompt(facts,question,obj):
    # Earlier question/answer lines are not narrative facts. Preserve the final
    # QA2 question verbatim; never put source answers/support IDs in the prompt.
    return '\n'.join(f'{f["line"]} {f["text"]}' for f in facts)+f'\n{question["line"]} {question["text"]}\nThe {obj} is now by'


def build_pairs(source_text,source_digest):
    rng=random.Random(SEED);public=[];pairs=[];excluded=Counter();total=episodes(source_text)
    seen_prompts=set()
    for ep in total:
        q=ep['question'];match=QUESTION.fullmatch(q['text'])
        if not match:
            excluded['not_current_object_question']+=1;continue
        obj=match[1];facts=ep['facts']
        try:state=replay(facts)
        except ValueError:
            excluded['ambiguous_or_inconsistent_source_story']+=1;continue
        current=state['object_locations'].get(obj)
        if current is None or current!=q['answer']:
            excluded['source_answer_not_parser_verified']+=1;continue
        history=state['events'].get(obj,[])
        if not history or history[-1]['previous'] is None:
            excluded['no_known_previous_location']+=1;continue
        event=history[-1];previous=event['previous'];idx=event['index'];a,b=event['location_span']
        if event['current']!=current:
            excluded['final_movement_not_final_location']+=1;continue
        alternatives=[p for p in event['locations_seen'] if p not in (current,previous)]
        rng.shuffle(alternatives);chosen=None
        for alternative in alternatives:
            original=facts[idx]['text']
            if original[a:b]!=current:raise ValueError('source movement location span mismatch')
            twin=[dict(f) for f in facts];twin[idx]['text']=original[:a]+alternative+original[b:]
            try:counterfactual=replay(twin)
            except ValueError:continue
            newhist=counterfactual['events'].get(obj,[])
            if counterfactual['object_locations'].get(obj)!=alternative or not newhist or newhist[-1]['index']!=idx or newhist[-1]['previous']!=previous:
                continue
            other_objects=set(state['object_locations'])|set(counterfactual['object_locations'])
            if any(state['object_locations'].get(o)!=counterfactual['object_locations'].get(o) for o in other_objects if o!=obj):
                continue
            chosen=alternative,twin,counterfactual;break
        if chosen is None:
            excluded['no_existing_alternative_with_only_target_object_change']+=1;continue
        alternative,twin,_=chosen
        texts=[prompt(facts,q,obj),prompt(twin,q,obj)]
        if any(t in seen_prompts for t in texts):
            excluded['duplicate_prompt']+=1;continue
        seen_prompts.update(texts)
        order=len(pairs);pairid=hashlib.sha256(f'E133babi|{source_digest}|qa2|{ep["episode"]}'.encode()).hexdigest()[:24]
        recipients=[current,alternative];members=[]
        for member,text in enumerate(texts):
            ident=hashlib.sha256(f'{pairid}|{member}'.encode()).hexdigest()[:24]
            public.append(dict(id=ident,prompt=text))
            members.append(dict(id=ident,member=member,current_holder=recipients[member],
                                previous_holder=previous,twin_recipient=recipients[1-member]))
        # One data-token replacement only; no question/answer or other fact rewrite.
        prefix='\n'.join(f'{f["line"]} {f["text"]}' for f in facts[:idx])
        line_prefix=f'{facts[idx]["line"]} '+facts[idx]['text'][:a]
        start=(len(prefix)+1 if prefix else 0)+len(line_prefix)
        normalized=[texts[j][:start]+'<FINAL_LOCATION>'+texts[j][start+len(recipients[j]):] for j in (0,1)]
        if normalized[0]!=normalized[1]:raise ValueError('twins differ outside final location')
        pairs.append(dict(pair_id=pairid,family='babi_qa2',generation_order=order,
              source_episode=ep['episode'],source_question_line=q['line'],source_question=q['text'],
              source_answer=current,asked_object=obj,original_final_movement_line=event['line'],
              original_previous_location=previous,recipients=recipients,previous_holder=previous,
              source_existing_locations=event['locations_seen'],final_location_char_start=start,
              source_supporting_ids=q['supporting_ids'],members=members))
    return public,pairs,dict(source_episodes=len(total),eligible_pairs=len(pairs),exclusions=dict(excluded))
