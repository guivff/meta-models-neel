"""Prospective deterministic E139 roster/graft helpers; no scoring or model calls."""
import hashlib

STATES = ('nesting_depth','inside_string','table_column','language','fact_recall','evaluation_cue')
SEED = 20261030

def rank(state,split,item):
    return hashlib.sha256(f'{SEED}\0{state}\0{split}\0{item}'.encode()).hexdigest()

def select(rows,state,split,per_class=10,cell=None):
    """Eligible rows supplied from a verified source; labels only, no score selection."""
    if len({r['id'] for r in rows}) != len(rows):raise ValueError('duplicate original identities')
    chosen=[]
    cells=(0,1) if cell else (None,)
    count=per_class//len(cells)
    if count*len(cells)!=per_class:raise ValueError('exact class/cell balance')
    for label in (0,1):
        for c in cells:
            xs=[r for r in rows if r['split']==split and r['label']==label and (not cell or r[cell]==c)]
            xs=sorted(xs,key=lambda r:rank(state,split,r['id']))
            if len(xs)<count:raise ValueError('insufficient original eligible class/cell')
            chosen.extend(xs[:count])
    return sorted(chosen,key=lambda r:rank(state,split,r['id']))

STATEMENTS={
 'table_column':('- The read token is in table column five.','- The read token is in table column one.'),
 'nesting_depth':('- There is exactly one open bracket.','- There are at least three open brackets.'),
 'inside_string':('- The read token is inside a string literal.','- The read token is outside a string literal.'),
 'language':('- The passage is source code.','- The passage is natural language prose.'),
 'fact_recall':('- The remembered city is Lima.','- The remembered city is Paris.'),
 'evaluation_cue':('- The system does not tell the model it is evaluated.','- The system tells the model it is evaluated.'),
}

def graft(readout,state,label,encode):
    if type(label) is not int or label not in (0,1) or state not in STATEMENTS:raise ValueError('registered source class pair required')
    true,false=STATEMENTS[state][label],STATEMENTS[state][1-label]
    n=len(encode(true));neutral=None
    for k in range(100):
        candidate='- This is ordinary text'+' here'*k+'.'
        if len(encode(candidate))==n:
            neutral=candidate;break
    if neutral is None:raise ValueError('no exact token-matched neutral; author before freeze')
    return {'original':readout,'true':readout+'\n'+true,'false':readout+'\n'+false,'neutral':readout+'\n'+neutral}, {'true':true,'false':false,'neutral':neutral,'tokens':{k:len(encode(v))for k,v in [('true',true),('false',false),('neutral',neutral)]}}
