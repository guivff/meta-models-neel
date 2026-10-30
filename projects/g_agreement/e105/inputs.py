"""CPU-only E105 inputs. E100 T pairings/carriers are reused, never rebuilt."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile
import numpy as np
from projects.g_agreement.e101.contract import read,write,sha,verify
from projects.g_agreement.e101.bind_owner import PAIRS,member

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ROWS=('nesting_depth','indent_level','page_range_digit','format_plan','language_plan','fact_recall')
BANKS={r:('E57' if r in ROWS[:3] else 'E56' if r=='fact_recall' else 'E59') for r in ROWS}
N=84;DIM=5120;SEED=20261030
E100_VECTOR_SHA='dd1ff8dc2ec742e001d8d0e59b700b33fa904680d420d9fb9350088f752317b0'
E100_TARGET_SHA='f1c97d6800972346241385ee2e18e02ffc12c01767827d6e44d26da7cace2e35'
PUBLIC_FIELDS={'id','inventory_id','base_id','row','condition','block','ids','read_index','candidate_ids','vector_index','donor_id'}
PUBLIC_FILES={'MANIFEST.json','items.json','vectors.npy','T_PAIRINGS.json','S_PAIRINGS.json'}


def digest(x):return hashlib.sha256(json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def opaque(row,base,condition=None):
    text=f'E105:{row}:{base}'+(':'+condition if condition is not None else '')
    return hashlib.sha256(text.encode()).hexdigest()


def frozen():
    f=read(HERE/'FROZEN_SCORERS.json')
    if (sha(HERE/'frozen_e101_acquisition.py')!=f['scorer_sha256'] or
        sha(HERE/'frozen_unpatched.py')!=f['unpatched_function_sha256'] or
        sha(ROOT/'projects/g_agreement/e101/bind_owner.py')!=f['candidate_recipe_sha256']):
        raise ValueError('frozen E101 continuation/candidate source changed')
    return f


def same_pairs(ids,labels,values,seed=SEED):
    if len(ids)!=len(set(ids)) or len(ids)!=len(labels) or len(ids)!=len(values):raise ValueError('unique aligned donor inventory')
    rng=np.random.default_rng(seed);result=[]
    for i,ident in enumerate(ids):
        eligible=[j for j in range(len(ids)) if j!=i and labels[j]==labels[i] and values[j]==values[i]]
        if not eligible:raise ValueError('same-value different-item donor absent')
        j=int(rng.choice(eligible));result.append(dict(id=ident,slot=i,donor_id=ids[j],donor_slot=j))
    return result


def compose(row,records,carriers,t_pairs,scorer_sha):
    """Records and labels remain CPU-side. Three public evaluations per recipient."""
    ids=[r['id'] for r in records];labels=[r['label'] for r in records];values=[r['value'] for r in records]
    h=np.asarray(carriers)
    if len(ids)!=N or h.shape!=(N,DIM) or h.dtype!=np.float32 or not np.isfinite(h).all():raise ValueError('84 finite original fp32 carriers')
    if any(v not in (0,1) for v in labels) or set(labels)!={0,1}:raise ValueError('binary CPU values')
    if [p['id'] for p in t_pairs]!=ids or [p['slot'] for p in t_pairs]!=list(range(N)):raise ValueError('exact E100 pairing order')
    s_pairs=same_pairs(ids,labels,values);public=[];vectors=[];inventory=[]
    for i,(r,t,s) in enumerate(zip(records,t_pairs,s_pairs)):
        j=t['donor_slot'];k=s['donor_slot']
        if not 0<=j<N or t['donor_id']!=ids[j] or labels[j]==labels[i] or values[j]==values[i]:raise ValueError('original other-value T donor')
        if k==i or labels[k]!=labels[i] or values[k]!=values[i]:raise ValueError('same-value S donor')
        common=dict(inventory_id=opaque(row,r['id']),base_id=r['id'],row=row,block=44,
                    ids=r['ids'],read_index=len(r['ids'])-1,candidate_ids=r['candidate_ids'])
        for condition,slot in [('T',j),('S',k),('0',None)]:
            index=len(vectors) if slot is not None else None
            if slot is not None:vectors.append(h[slot].copy())
            public.append(dict(common,id=opaque(row,r['id'],condition),condition=condition,
                               vector_index=index,donor_id=ids[slot] if slot is not None else None))
        inventory.append(dict(id=common['inventory_id'],item_id=r['id'],row=row,split='test',
            T_donor_id=ids[j],S_donor_id=ids[k],source_label=labels[i],T_label=labels[j],S_label=labels[k],
            candidate_A_label=1,frozen_scorer_sha256=scorer_sha,
            candidate_ids_sha256=digest(r['candidate_ids']),candidate_pair_count=len(r['candidate_ids'])))
    return public,np.stack(vectors),s_pairs,inventory


def validate(items,vectors,manifest,t_pairs,s_pairs):
    if (manifest['experiment']!='E105' or manifest['block']!=44 or manifest['same_value_seed']!=SEED or
        manifest['behaviour_mode']!='frozen_continuation' or manifest['baseline_mode']!='unpatched'):
        raise ValueError('registered E105 mode')
    if len(items)!=N*3 or vectors.shape!=(N*2,DIM) or vectors.dtype!=np.float32 or not np.isfinite(vectors).all():raise ValueError('full finite T/S/0 grid')
    if len({x['id'] for x in items})!=N*3 or [p['slot'] for p in t_pairs]!=list(range(N)) or [p['id'] for p in t_pairs]!=[p['id'] for p in s_pairs]:raise ValueError('unique ordered donor grid')
    used=[]
    base_ids=[p['id'] for p in t_pairs]
    for i,(t,s) in enumerate(zip(t_pairs,s_pairs)):
        if s['slot']!=i:raise ValueError('same-value pairing order')
        for p in (t,s):
            j=p['donor_slot']
            if type(j)is not int or not 0<=j<N or p['donor_id']!=base_ids[j] or j==i:raise ValueError('paired donor slot')
        xs=items[i*3:i*3+3]
        if [x['condition'] for x in xs]!=['T','S','0']:raise ValueError('all three conditions in frozen order')
        for x in xs:
            if set(x)!=PUBLIC_FIELDS or x['base_id']!=t['id'] or x['row']!=manifest['row'] or x['block']!=44:raise ValueError('public label-free schema')
            if not x['ids'] or x['read_index']!=len(x['ids'])-1 or any(type(v)is not int or v<0 for v in x['ids']):raise ValueError('original prompt tokens')
            if not x['candidate_ids'] or any(len(p)!=2 or any(not c or any(type(v)is not int or v<0 for v in c) for c in p) for p in x['candidate_ids']):raise ValueError('frozen full continuation pairs')
            if x['inventory_id']!=opaque(x['row'],x['base_id']) or x['id']!=opaque(x['row'],x['base_id'],x['condition']):raise ValueError('opaque identity')
            if x['condition']=='0':
                if x['vector_index'] is not None or x['donor_id'] is not None:raise ValueError('baseline must be unpatched')
            else:
                p=t if x['condition']=='T' else s
                if x['donor_id']!=p['donor_id'] or x['donor_id']==x['base_id']:raise ValueError('donor identity')
                if type(x['vector_index'])is not int:raise ValueError('supplied vector index')
                used.append(x['vector_index'])
        if any(x['ids']!=xs[0]['ids'] or x['candidate_ids']!=xs[0]['candidate_ids'] for x in xs):raise ValueError('T/S/0 prompts and scores identical')
    if used!=list(range(N*2)):raise ValueError('supplied vector alignment')


def load(public,input_sha):
    seal=verify(public,'INPUT_SEAL.json',input_sha)
    if seal['experiment']!='E105' or seal['labels_on_pod'] is not False or set(seal['files'])!=PUBLIC_FILES:raise ValueError('public archive allowlist')
    if {p.name for p in public.iterdir()}!=PUBLIC_FILES|{'INPUT_SEAL.json'}:raise ValueError('no CPU keys in pod package')
    m=read(public/'MANIFEST.json');xs=read(public/'items.json');h=np.load(public/'vectors.npy',allow_pickle=False)
    validate(xs,h,m,read(public/'T_PAIRINGS.json'),read(public/'S_PAIRINGS.json'))
    if (m['frozen_scorer_sha256']!=frozen()['scorer_sha256'] or
        sha(public/'T_PAIRINGS.json')!=m['e100_T_pairings_sha256'] or m['e100_vector_seal_sha256']!=E100_VECTOR_SHA):
        raise ValueError('frozen scorer/donor source identity')
    return xs,h,m


def build(owner,model,out,inventory_out):
    f=frozen();verify(owner,'VECTOR_SEAL.json',E100_VECTOR_SHA)
    pub=owner/'public';root_seal=read(owner/'VECTOR_SEAL.json');parent_sha=root_seal['files']['public/INPUT_SEAL.json'];verify(pub,'INPUT_SEAL.json',parent_sha)
    targets_path=ROOT/'results/g_agreement/understand/e100/analysis/cpu_only/TARGET_SEAL.json'
    verify(targets_path.parent,targets_path.name,E100_TARGET_SHA);targets={x['id']:x for x in read(targets_path.parent/'TARGETS.json')}
    joins={x['id']:x for x in read(owner/'cpu_only/JOIN.DO_NOT_STAGE.json')};sources=read(owner/'cpu_only/SOURCES.json')['banks']
    if sha(model/'tokenizer.json')!=f['tokenizer_sha256']:raise ValueError('frozen tokenizer')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True)
    banks={};annotations={}
    for bank,src in sources.items():
        p=Path(src['metadata_path']);names=[p.name]+(['ANNOTATIONS.PRIVATE.json'] if bank=='E57' else [])
        member(p.parent,'BANK_SEAL.json',src['bank_seal_sha256'],names)
        if sha(p)!=src['metadata_sha256']:raise ValueError('original bank metadata identity')
        banks[bank]={x['id']:x for x in read(p)}
        if bank=='E57':annotations=read(p.parent/'ANNOTATIONS.PRIVATE.json')
    rows={r['row']:r for r in read(pub/'MANIFEST.json')['rows']};out.mkdir(parents=True,exist_ok=False)
    inventory_out.mkdir(parents=True,exist_ok=False);inventory=[];packages=[];audit=[]
    for row in ROWS:
        r=rows[row];bank=BANKS[row];pairs_path=pub/r['pairings'];t_pairs=read(pairs_path)
        carriers=np.load(pub/r['h44'],allow_pickle=False);records=[]
        for ident in r['ids']:
            j=joins[ident];x=banks[bank][j['source_item_id']]
            if (j['bank']!=bank or j['row']!=row or x['split']!='test' or x['feature']!=row or
                x['label']!=j['true_label'] or x['value']!=j['source_value']):raise ValueError('E100 original item/value join')
            strings=[[' '+s for s in annotations[x['id']]['answer_pair']]] if row=='page_range_digit' else PAIRS[row]
            candidates=[[tok.encode(s,add_special_tokens=False) for s in pair] for pair in strings]
            records.append(dict(id=ident,label=x['label'],value=x['value'],ids=x['ids'],candidate_ids=candidates))
            audit.append(dict(item_id=ident,bank=bank,source_item_id=x['id'],strings=strings,candidate_ids=candidates))
        xs,h,s_pairs,private=compose(row,records,carriers,t_pairs,f['scorer_sha256'])
        for x in private:
            target=targets[x['item_id']]
            if target['donor_id']!=x['T_donor_id'] or target['row']!=row or x['T_label']!=(1 if target['target']=='A' else 0):raise ValueError('E100 target donor orientation')
            if x['S_label']!=(0 if targets[x['S_donor_id']]['target']=='A' else 1):raise ValueError('E100 same-value donor orientation')
        inventory.extend(private);dest=out/'public'/row;dest.mkdir(parents=True)
        manifest=dict(experiment='E105',row=row,block=44,items=N,condition_cells=N*3,supplied_vectors=N*2,
            conditions=['T','S','0'],same_value_seed=SEED,same_value_sampling='per-row default_rng(seed); uniform with replacement among different same-value items in frozen E100 order',
            supplied_vector_mode=True,baseline_mode='unpatched',behaviour_mode='frozen_continuation',new_text=False,
            frozen_scorer_sha256=f['scorer_sha256'],e101_source_seal_sha256=f['e101_source_seal_sha256'],
            candidate_recipe_sha256=f['candidate_recipe_sha256'],tokenizer_sha256=f['tokenizer_sha256'],
            e100_vector_seal_sha256=E100_VECTOR_SHA,e100_public_input_sha256=parent_sha,
            e100_h44_sha256=sha(pub/r['h44']),e100_T_pairings_sha256=sha(pairs_path),
            vector_policy='exact fp32 E100 donor residual; cast only to subject dtype, no scaling/normalisation')
        validate(xs,h,manifest,t_pairs,s_pairs)
        write(dest/'MANIFEST.json',manifest);write(dest/'items.json',xs);np.save(dest/'vectors.npy',h,allow_pickle=False)
        shutil.copyfile(pairs_path,dest/'T_PAIRINGS.json');write(dest/'S_PAIRINGS.json',s_pairs)
        write(dest/'INPUT_SEAL.json',dict(experiment='E105',labels_on_pod=False,files={n:sha(dest/n) for n in sorted(PUBLIC_FILES)}))
        load(dest,sha(dest/'INPUT_SEAL.json'));archive=out/(row+'.tar.gz')
        with tarfile.open(archive,'w:gz',compresslevel=1) as tar:tar.add(dest,arcname='inputs')
        if archive.stat().st_size>20*1024*1024:raise ValueError('20MiB input archive cap')
        packages.append(dict(row=row,items=N,condition_cells=N*3,input_root=str(dest.resolve()),
            input_sha256=sha(dest/'INPUT_SEAL.json'),archive=str(archive.resolve()),archive_sha256=sha(archive),bytes=archive.stat().st_size))
    if len(inventory)!=504:raise ValueError('six complete test rows')
    write(inventory_out/'INVENTORY.json',inventory);write(inventory_out/'CANDIDATE_AUDIT.json',audit)
    write(inventory_out/'CUSTODY.json',dict(e100_vector_seal_sha256=E100_VECTOR_SHA,e100_target_seal_sha256=E100_TARGET_SHA,
        original_sources=sources,scorer_binding=f,labels_cpu_only=True,GPU_calls=0))
    write(inventory_out/'INVENTORY_SEAL.json',dict(experiment='E105',block=44,same_value_seed=SEED,supplied_vector_mode=True,
        behaviour_mode='frozen_continuation',new_text=False,labels_cpu_only=True,files={p.name:sha(p) for p in inventory_out.iterdir()}))
    binding=dict(experiment='E105',status='SEALED_INPUTS_REQUIRES_INTEGRATOR_ADMISSION',rows=6,items=504,condition_cells=1512,
        packages=packages,inventory_seal=str((inventory_out/'INVENTORY_SEAL.json').resolve()),inventory_sha256=sha(inventory_out/'INVENTORY_SEAL.json'),
        labels_on_pod=False,GPU_calls=0,reader_calls=0,judge_calls=0,full_launch_allowed=False)
    write(out/'BINDING.json',binding);return binding


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in ('owner','model','out','inventory-out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();print(json.dumps(build(a.owner,a.model,a.out,a.inventory_out),indent=2))
