"""Data-only bAbI TEST twins; no dataset code, models, behavioural selection or labels on pods."""
import re,json,hashlib,tarfile
from pathlib import Path
MOVE=re.compile(r'^(\w+) (?:moved|journeyed|travelled|went|went back) to the (\w+)\.$')
TAKE=re.compile(r'^(\w+) (?:got|grabbed|took|picked up) the (\w+)(?: there)?\.$')
DROP=re.compile(r'^(\w+) (?:left|discarded|dropped|put down) the (\w+)(?: there)?\.$')
QUESTION=re.compile(r'^Where is the (\w+)\?$')

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,allow_nan=False)+'\n')


def questions(text):
    facts=[];story=0
    for source_line,line in enumerate(text.splitlines(),1):
        number,body=line.split(' ',1);number=int(number)
        if number==1:facts=[];story+=1
        if '\t'in body:
            q,answer,support=body.split('\t');yield dict(story=story,source_line=source_line,question_number=number,question=q.strip(),answer=answer.strip(),support=support.strip(),facts=list(facts))
        else:facts.append((number,body))


def replay(facts,obj):
    people={};holders={};ground={};last=None;locations=[]
    for ix,(n,text)in enumerate(facts):
        m=MOVE.fullmatch(text)
        if m:
            person,destination=m.groups();old=people.get(person)
            if holders.get(obj)==person:last=dict(index=ix,number=n,previous=old,current=destination,person=person,start=m.start(2),end=m.end(2),prior_locations=list(locations))
            people[person]=destination
            if destination not in locations:locations.append(destination)
            continue
        m=TAKE.fullmatch(text)
        if m:
            person,thing=m.groups();holders[thing]=person;ground.pop(thing,None);continue
        m=DROP.fullmatch(text)
        if m:
            person,thing=m.groups();holders.pop(thing,None);ground[thing]=people.get(person);continue
        raise ValueError('unrecognised story statement; no inferred event')
    current=people.get(holders[obj])if obj in holders else ground.get(obj)
    return current,last


def prompt(facts,question):return '\n'.join(f'{n} {s}'for n,s in facts)+'\n'+question+'\nAnswer:'


def twin(q):
    m=QUESTION.fullmatch(q['question'])
    if not m:return None,'not_current_location_question'
    obj=m.group(1);current,event=replay(q['facts'],obj)
    if current!=q['answer']:return None,'source_answer_not_reproduced'
    if not event or event['previous']is None:return None,'no_known_previous_location_at_object_movement'
    previous=event['previous']
    if current!=event['current']or current==previous:return None,'final_location_not_distinct_last_movement'
    alternatives=[x for x in event['prior_locations']if x not in (current,previous)]
    if not alternatives:return None,'no_distinct_alternative_already_in_prior_story'
    # Frozen structural choice: first-mention order, never model/reader outcomes.
    alternate=alternatives[0];ix=event['index'];n,s=q['facts'][ix]
    edited=s[:event['start']]+alternate+s[event['end']:]
    facts=list(q['facts']);facts[ix]=(n,edited)
    got,new_event=replay(facts,obj)
    if got!=alternate or new_event['index']!=ix or new_event['previous']!=previous:return None,'twin_not_same_last_movement'
    assert all(a==b for j,(a,b)in enumerate(zip(q['facts'],facts))if j!=ix)
    assert edited==s[:event['start']]+alternate+s[event['end']:]
    return dict(original_prompt=prompt(q['facts'],q['question']),twin_prompt=prompt(facts,q['question']),object=obj,original_current=current,twin_current=alternate,previous=previous,event=event,original_statement=s,twin_statement=edited),None


def build(data_root,out):
    data=Path(data_root);out=Path(out);out.mkdir(exist_ok=False);pub=out/'public';cpu=out/'cpu_only';pub.mkdir();cpu.mkdir()
    receipt=json.loads((data/'DOWNLOAD_RECEIPT.json').read_text())
    assert sha(data/'tasks_1-20_v1-2.tar.gz')==receipt['archive_sha256']
    public=[];labels=[];audit=[]
    for member in receipt['members']:
        p=data/member['file'];assert sha(p)==member['sha256']
        task='qa2'if member['file'].startswith('qa2_')else 'qa3';counts={};total=0;kept=0
        for q in questions(p.read_text()):
            total+=1;r,reason=twin(q)
            if reason:counts[reason]=counts.get(reason,0)+1;continue
            ident=f'E133-babi-{task}-q{q["source_line"]:05d}'
            public.extend([dict(id=ident+':0',prompt=r['original_prompt']),dict(id=ident+':1',prompt=r['twin_prompt'])])
            labels.append(dict(pair_id=ident,member_ids=[ident+':0',ident+':1'],family='babi',source_task=task,source_split='test',source_member=member['member'],source_sha256=member['sha256'],source_line=q['source_line'],story=q['story'],question_number=q['question_number'],support_ids=q['support'],question=q['question'],**{k:v for k,v in r.items()if not k.endswith('_prompt')}));kept+=1
        audit.append(dict(task=task,questions=total,candidate_pairs=kept,excluded=counts))
    if len(labels)<42:raise ValueError('fewer than42structurally eligible candidates; no substitution')
    write(pub/'items.json',public)
    write(pub/'MANIFEST.json',dict(experiment='E133',arm='babi',stage='candidate_packet',authority='§242/bAbI addendum',language='en',split='test',candidate_pairs=len(labels),prompts=len(public),source_order='QA2 file questions in original source order, then QA3 file questions in original source order; all structurally eligible pairs retained',selection='NO behavioural selection; Track Q later keeps first42both-member-correct pairs',twin_rule='only asked-object last movement destination replaced by first prior-mentioned location distinct from current and previous; original question unchanged',question_wrapper='original numbered facts, original question without answer/support fields, newline Answer:',source_archive_sha256=receipt['archive_sha256'],audit=audit,labels_on_pod=False))
    write(pub/'INPUT_SEAL.json',dict(experiment='E133',arm='babi',labels_on_pod=False,files={p.name:sha(p)for p in pub.iterdir()}))
    write(cpu/'LABELS.PRIVATE.json',labels);write(cpu/'LABEL_SEAL.json',dict(experiment='E133',arm='babi',public_input_sha256=sha(pub/'INPUT_SEAL.json'),files={'LABELS.PRIVATE.json':sha(cpu/'LABELS.PRIVATE.json')}))
    for p in cpu.iterdir():p.chmod(0o600)
    with tarfile.open(out/'public.tar.gz','w:gz')as t:
        for p in sorted(pub.iterdir()):t.add(p,arcname=p.name)
    result=dict(experiment='E133',arm='babi',status='CANDIDATE_PACKET_SEALED_NOT_SCREENED',candidate_pairs=len(labels),public_root=str(pub),input_sha256=sha(pub/'INPUT_SEAL.json'),public_archive=str(out/'public.tar.gz'),public_archive_sha256=sha(out/'public.tar.gz'),CPU_only_root=str(cpu),CPU_only_label_seal_sha256=sha(cpu/'LABEL_SEAL.json'),download_receipt=str(data/'DOWNLOAD_RECEIPT.json'),download_receipt_sha256=sha(data/'DOWNLOAD_RECEIPT.json'),audit=audit,labels_on_pod=False,model_calls=0,selected_pairs=None,QA3_status='all original questions historical; ineligible under unchanged current-location restriction; no question rewrite')
    write(out/'DELIVERY.json',result);return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(build(a.data_root,a.out),indent=2))
