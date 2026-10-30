"""Independent replication of the six pinned render/read rules plus §206 clarifications."""
import re
PUNCT=re.compile(r'[\n.,;:!?\u3002\uff0c\uff1b\uff1a\uff01\uff1f\u060c\u061f]')
def display(tok,ids):return [t.replace('Ġ',' ').replace('▁',' ') for t in tok.convert_ids_to_tokens(ids)]
def clean(s):return s.replace('Ġ',' ').replace('▁',' ').replace('Ċ','\n')
def last_sentence(tokens):
    starts=[i for i,t in enumerate(tokens) if t=='<|im_start|>' and i+1<len(tokens) and clean(tokens[i+1]).strip()=='user']
    if not starts:raise ValueError('No user header')
    a=starts[-1]+2
    while a<len(tokens) and not clean(tokens[a]).strip():a+=1
    b=next(i for i in range(a,len(tokens)) if tokens[i]=='<|im_end|>')
    if a==b:return list(range(b,len(tokens)))
    i=b-2
    while i>a:
        if re.search(r'[.!?]\s*$',clean(tokens[i])):break
        i-=1
    return list(range(i+1 if i>a else a,len(tokens)))
def suffix_positions(tokens,text):
    target=text.strip();start=next((i for i in range(len(tokens)-1,-1,-1) if ''.join(clean(t) for t in tokens[i:]).lstrip().startswith(target)),None)
    if start is None:raise ValueError('Carrier not found in rendered suffix')
    acc=''
    for i in range(start,len(tokens)):
        acc=(acc+clean(tokens[i])).lstrip() if not acc else acc+clean(tokens[i])
        if len(acc)>=len(target):return list(range(start,i+1))
    return list(range(start,len(tokens)))
def punct_positions(read):
    a,b=map(int,read['span']);ts={int(k):str(v) for k,v in read['tokens'].items()}
    return sorted(set([p for p in range(a,b) if PUNCT.search(ts.get(p,''))][-10:]+[b]))
def chat(tok,messages):
    result=tok.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,enable_thinking=False)
    return list(result['input_ids'] if hasattr(result,'keys') else result)
def plan(f,item,tok,capture=None):
    extra=[];layers=[20,36,44,56];mode='chat'
    if f=='hallucination':
        ids=list(capture['input_ids']);grid=[int(s['pos']) for s in item['sites']];assert grid==capture['read_positions']
        assert all(p>=capture['prompt_len'] for p in grid)
        for site in item['sites']:assert tok.decode([ids[site['pos']]])==site['token']
        single=grid[-1];mode='captured'
    elif f=='buggy_code':
        ids=tok.encode(item['code'],add_special_tokens=False);grid=[len(ids)-1];single=grid[0];layers=sorted({44,60 if item['lang_group']=='python' else 56});mode='bare'
    else:
        if f=='user_modeling':messages=item['messages']
        elif f=='jailbreak_recognition':
            last=max(i for i,m in enumerate(item['messages']) if m['role']=='user');messages=item['messages'][:last+1]
        else:messages=([{'role':'system','content':item['system']}] if item.get('system') else [])+[{'role':'user','content':item['text'] if f=='agentic_misalignment' else item['prompt']}]
        ids=chat(tok,messages);single=len(ids)-1
        if f=='directed_modulation':
            ids+=tok.encode(item['assistant'],add_special_tokens=False);grid=suffix_positions(display(tok,ids),item['assistant']);extra=[single];mode='chat_dm'
            assert single<min(grid)
        elif f=='user_modeling':grid=last_sentence(display(tok,ids));assert single in grid
        elif f=='agentic_misalignment':grid=list(range(max(0,len(ids)-128),len(ids)));layers=[36,44,56]
        else:
            grid=punct_positions(item['read']);extra=[single];mode='chat_context'
            assert tok.decode([ids[item['read']['turn_end']]])=='<|im_end|>'
            # Frozen read metadata includes a closed empty assistant turn, two tokens longer.
            assert len(ids)+2==item['read']['n_tokens']
            for p in grid:assert tok.decode([ids[p]])==item['read']['tokens'][str(p)]
            assert single not in grid
    assert grid and all(0<=p<len(ids) for p in grid+extra)
    return dict(render=mode,rendered_prompt=tok.decode(ids),input_ids=ids,grid_positions=grid,grid_oracle_layers=layers,nla_layer=42,
                single_site_position=single,single_site_oracle_layer=44,single_site_nla_layer=42,extra_single_site_positions=extra)
