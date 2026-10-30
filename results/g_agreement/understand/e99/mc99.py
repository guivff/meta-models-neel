"""Pinned UM/DM option construction and exact judge formatting, CPU only."""
import hashlib,json,random
from pathlib import Path
HERE=Path(__file__).resolve().parent
def constants(family):return json.loads((HERE/(family.upper()+'_PROMPTS.json')).read_text())['constants']
def seed(s):return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],'big')
def options(family,items):
    c=constants(family);out={};groups={}
    key,value=('attr_class','attr') if family=='user_modeling' else ('subfamily','concept')
    for it in items:groups.setdefault(str(it[key]),set()).add(str(it[value]))
    for it in items:
        gold=str(it[value]);pool=sorted(groups[str(it[key])]-{gold});rng=random.Random(seed(f"0:draw:{it['name']}"))
        picked=rng.sample(pool,min(4,len(pool)))
        if family=='user_modeling' and len(picked)<4:
            extra=[v for v in c['UM_OPTION_SUPPLEMENT'].get(str(it[key]),[]) if v!=gold and v not in picked]
            picked+=rng.sample(extra,min(4-len(picked),len(extra)))
        display=lambda x:x.replace('_',' ') if family=='user_modeling' else x
        gold=display(gold);opts=[gold,*map(display,picked)];random.Random(seed(f"0:order:{it['name']}")).shuffle(opts)
        out[it['id']]={'options':opts,'gold_position':opts.index(gold)+1}
    return out

def render(family,item,readout,options):
    c=constants(family);lines=[f'{i+1}. {v}' for i,v in enumerate(options)]
    if family=='user_modeling':
        lines.append(f"{len(options)+1}. {c['CANNOT_TELL']}")
        user=c['UM_ATTRIBUTE_USER'].format(user_turn='\n\n'.join(f"[{m['role']}] {m['content']}" for m in item['messages']),readout=readout,options_block='\n'.join(lines),cannot=c['CANNOT_TELL'])
        return dict(system=c['UM_ATTRIBUTE_SYSTEM'],user=user,schema=c['UM_ATTRIBUTE_SCHEMA'])
    lines.append(f"{len(options)+1}. {c['CANNOT']}")
    credit=c['CREDIT_SECRET'] if item['subfamily']=='secret' else c['CREDIT_PREFERENCE'] if item['subfamily']=='preference' else c['CREDIT_PAIR']
    pairs=[('readout_note',''),('prompt',item['prompt']),('readout',readout),('options_block','\n'.join(lines)),('credit_rules',credit),('composition_block',c['COMPOSITION_BLOCK']),('basis_note',c['BASIS_POS'] if item['polarity']=='think' else c['BASIS_NEG']),('n_content',str(len(options))),('cannot',c['CANNOT'])]
    user=c['USER']
    for k,v in pairs:user=user.replace('{'+k+'}',v)
    return dict(system=c['SYSTEM'],user=user,schema=c['SCHEMA'])
