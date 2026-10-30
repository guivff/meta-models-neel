"""Freeze public-source UM/DM judging data on CPU; no upstream execution."""
import hashlib,json,re
from source99 import HERE,SOURCE,prompt_data,dump,sha,verify_pin
from mc99 import options
if __name__=='__main__':
    verify_pin();out=HERE/'cache/mc_2026-10-28';out.mkdir(parents=True,exist_ok=False);delivery={}
    for f in ('user_modeling','directed_modulation'):
        dump(HERE/(f.upper()+'_PROMPTS.json'),prompt_data(f))
        path=SOURCE/'evals'/f/'items.json';items=json.loads(path.read_text())['items']
        for it in items:it['id']=re.sub(r'[^A-Za-z0-9._-]','_',it['name'])
        opts=options(f,items)
        records=[dict(id=hashlib.sha256(('E99|'+f+'|'+it['id']).encode()).hexdigest()[:24],source_item=it,**opts[it['id']]) for it in items]
        dest=out/(f.upper()+'.PRIVATE.json');dump(dest,records)
        delivery[f]=dict(items=len(items),private_path=str(dest),private_sha256=sha(dest),source_sha256=sha(path))
    dump(HERE/'MC_DELIVERY.json',delivery)
