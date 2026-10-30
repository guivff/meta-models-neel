"""Freeze E106 NLA train selection:252target+252replay dev vectors at block42."""
import argparse,random,json,importlib.util
from pathlib import Path
import numpy as np
from projects.g_agreement.e96.reconstructor_check import write,digest
from projects.g_agreement.e96.prepare_smoke_inputs import verify


def build(cache,bank_root,e59_capture,templates,out,manifest):
    if out.exists():raise FileExistsError(out)
    verify(templates,'COMPLETE_TEMPLATES_SEAL.json')
    spec=importlib.util.spec_from_file_location('e106_page',templates/'page_range102.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    frozen=json.loads((templates/'TEMPLATES.json').read_text())['rows'];rng=random.Random(20261029)
    rows={'e57':['nesting_depth','indent_level','page_range_digit'],'e56':['fact_recall','tense_implicit'],'e59':['format_plan','language_plan']}
    sources=[];records=[];vectors=[]
    for bank,names in rows.items():
        root=bank_root/bank/'cache/bank_2026-10-27_v1';bank_seal=root/'BANK_SEAL.json'
        if digest(bank_seal)!=digest(Path('results/g_agreement/understand')/bank/'BANK_SEAL.json'):raise ValueError('bank identity')
        s=json.loads(bank_seal.read_text());ip=root/'items.PRIVATE.json'
        if digest(ip)!=s['files']['items.PRIVATE.json']:raise ValueError('item bytes')
        items=json.loads(ip.read_text());lookup={}
        sources.append({'path':str(bank_seal),'sha256':digest(bank_seal),'items_sha256':digest(ip)})
        caps=[e59_capture] if bank=='e59' else [cache/f'g_agreement/understand/e56_e57/verified_pull_single_v1/shard_{i}/out/{bank}/capture' for i in range(3)]
        for c in caps:
            verify(c,'CAPTURE_SEAL.json');order=json.loads((c/'items.order.json').read_text());a=np.load(c/'acts42.npy',allow_pickle=False)
            if a.shape!=(len(order),5120):raise ValueError('capture shape')
            for i,key in enumerate(order):
                if key in lookup:raise ValueError('duplicate capture')
                lookup[key]=a[i]
            sources.append({'path':str(c/'CAPTURE_SEAL.json'),'sha256':digest(c/'CAPTURE_SEAL.json'),'activation_sha256':digest(c/'acts42.npy')})
        for row in names:
            xs=[x for x in items if x['split']=='dev' and x['feature']==row]
            if len(xs)!=84:raise ValueError('84dev required')
            if bank!='e57':
                # Fixed seeded selection:63per content row; no outcome consulted.
                keep=set(random.Random('20261029:'+bank+':'+row).sample([x['id'] for x in xs],63));xs=[x for x in xs if x['id'] in keep]
            for x in xs:
                r={'key':bank+':'+x['id'],'id':x['id'],'bank':bank,'row':row,'split':'dev','position':len(x['ids'])-1,'block':42,'role':'target' if bank=='e57' else 'replay'}
                if bank=='e57':
                    texts=m.render_dev(x) if row=='page_range_digit' else frozen[row][x['value']]
                    ix=rng.randrange(5);r.update(text=texts[ix],template_index=ix)
                records.append(r);vectors.append(lookup[x['id']])
    if len(records)!=504 or sum(x['role']=='target' for x in records)!=252 or len({x['key'] for x in records})!=504:raise ValueError('balanced unique inventory')
    out.mkdir(parents=True);write(out/'DEV_PAIRS.json',records)
    a=np.stack(vectors)
    if not np.isfinite(a).all():raise ValueError('nonfinite vectors')
    np.save(out/'acts42.npy',a,allow_pickle=False)
    write(out/'INPUT_SEAL.json',{'status':'VECTORS_AND_TARGETS_FROZEN_REPLAY_TEACHER_PENDING','files':{p.name:digest(p) for p in sorted(out.iterdir())}})
    write(manifest,{'experiment':'E106','arm':'T','reader':'nla','status':'DEV_VECTORS_TARGETS_READY_REPLAY_TEXT_PENDING','target_items':252,'replay_items':252,'block':42,'positions':'one read-token vector per dev item','target_template_selection':'Random(20261029).randrange(5), frozen row/item order','replay_selection':'63perrow; Random("20261029:"+bank+":"+row).sample(all84devIDs,63), output in frozen bank order','sources':sources,'templates_seal_sha256':digest(templates/'COMPLETE_TEMPLATES_SEAL.json'),'input_seal_sha256':digest(out/'INPUT_SEAL.json'),'files':json.loads((out/'INPUT_SEAL.json').read_text())['files'],'directory':str(out.resolve()),'test_items_in_optimizer':0,'test_vectors_in_optimizer':0,'judge_outputs_used':0,'replay_teacher':'original unprefixed pinned NLA greedy512/closingtag; must be generated and sealed for these252dev items before production optimizer','pending':['Arm P complete','NLA gate PASS by14CET','252sealed dev replay texts','final training seal'],'first_output_utc':None})

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for k in ('cache','bank-root','e59-capture','templates','out','manifest'):p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();build(**vars(a))
