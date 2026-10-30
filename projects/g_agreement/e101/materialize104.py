"""§213 CPU composition; Arm N reuses E101 dev directions, U binds a sealed d40."""
import argparse,hashlib,json,tarfile
from pathlib import Path
import numpy as np
from .contract104 import ROWS,DOSES,SEED,validate,validate_doses,read,write,sha,verify,committed_dose
from .intervention104 import WRITE_BLOCK,write_positions,NORM_CONVENTION
from .bind_owner import BANKS,PAIRS,TOKENIZER_SHA,member
ROOT=Path(__file__).resolve().parents[3]


def compose(records,directions,raw_norms,arm,stage,selected=None,*,random_unit=None):
    if arm not in DOSES or stage not in ('dev','test'):raise ValueError('registered arm/stage')
    if stage=='test':validate_doses(selected)
    rng=np.random.default_rng(np.random.SeedSequence([SEED,WRITE_BLOCK[arm]]))
    dimension=len(np.asarray(directions[ROWS[0]]));random=rng.standard_normal(dimension);random/=np.linalg.norm(random)
    if random_unit is not None:
        supplied=np.asarray(random_unit,np.float64)
        if not np.array_equal(supplied,random):raise ValueError('owner random direction must match registered seed recipe')
        random=supplied
    items=[];deltas=[];key={}
    for row in ROWS:
        xs=[x for x in records if x['row']==row and x['split']==stage]
        if len(xs)!=84 or len({x['id'] for x in xs})!=84:raise ValueError('84 frozen items per row/split')
        unit=np.asarray(directions[row],np.float64);norm=raw_norms[row]
        if unit.shape!=(dimension,) or not np.isfinite(unit).all() or not np.isclose(np.linalg.norm(unit),1.,atol=1e-6) or not np.isfinite(norm) or norm<=0:raise ValueError('finite dev unit direction and raw norm')
        alphas=DOSES[arm] if stage=='dev' else [selected[f'{arm}:{row}']['alpha']]
        if alphas==[None]:continue
        for x in xs:
            if x['label'] not in (0,1) or x['contrast_target_sign']!=1-2*x['label']:raise ValueError('CPU opposite-value orientation')
            key[x['id']]={k:x[k] for k in ('row','split','label','contrast_target_sign')}
            for alpha in alphas:
                for condition in ('steered','random'):
                    delta=(alpha*norm*(1-2*x['label'])*(unit if condition=='steered' else random)).astype(np.float32)
                    identity=hashlib.sha256(f'E104:{stage}:{arm}:{row}:{x["id"]}:{alpha}:{condition}'.encode()).hexdigest()
                    pos=len(x['ids'])-1
                    items.append(dict(id=identity,base_id=x['id'],row=row,arm=arm,block=WRITE_BLOCK[arm],alpha=alpha,condition=condition,delta_index=len(deltas),ids=x['ids'],read_index=pos,write_positions=write_positions(arm,[pos])[0],candidate_ids=x['candidate_ids']))
                    deltas.append(delta)
    return items,np.asarray(deltas,np.float32).reshape(-1,dimension),key


def scorer_document():
    return dict(experiment='E104',score_field='pair_logits',aggregation='mean(A-B)',tie='not_flipped',candidate_requirement='all_single_token',
        continuation_relation='Retain E101 pair_logprobs. Every frozen E104 candidate is one token, so pairwise logit and token-sum logprob contrasts are identical up to roundoff.',
        implementation=dict(path='projects/g_agreement/e101/acquisition.py',sha256=sha(ROOT/'projects/g_agreement/e101/acquisition.py')))


def scorer_digest():
    return hashlib.sha256((json.dumps(scorer_document(),indent=2,allow_nan=False)+'\n').encode()).hexdigest()


def save(out,items,deltas,stage,provenance,selected=None,dose_commit=None,dose_sha=None):
    if not items:raise ValueError('No eligible cells: record disposition on CPU, do not create a pod input')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    scorer=scorer_document()
    write(out/'SCORER.json',scorer);write(out/'items.json',items);np.save(out/'deltas.npy',deltas,allow_pickle=False)
    cells=[dict(arm=a,row=r) for a,r in sorted({(x['arm'],x['row']) for x in items})]
    m=dict(experiment='E104',status='FROZEN_READY',authority='5e075c6af',stage=stage,seed=SEED,dev_count=84,dose_grids={a:list(v) for a,v in DOSES.items()},cells=cells,
        scoring_mode='continuation',dose_score_field='pair_logits',behaviour_scorer_sha256=sha(out/'SCORER.json'),read_block=44,
        selected_doses=selected,dose_commit=dose_commit,dose_sha256=dose_sha,provenance=provenance,
        norm_convention=NORM_CONVENTION,
        U_hook=dict(block=40,positions='eight_before_read',read_token_untouched=True),N_hook=dict(block=44,positions='read_token',renormalized=True,random_renormalized=True))
    validate(items,deltas,m);write(out/'MANIFEST.json',m)
    write(out/'INPUT_SEAL.json',dict(experiment='E104',labels_on_pod=False,files={p.name:sha(p) for p in out.iterdir()}))


def load_u_directions(root,digest):
    """Accept W-internals-B's published E104 vector fitter output, unchanged."""
    seal=verify(root,'VECTOR_SEAL.json',digest)
    request=read(ROOT/'results/g_agreement/understand/e104/vectors/REQUEST.json')
    if (seal['experiment']!='E104' or seal['status']!='COMPLETE' or seal['block']!=40 or seal['fit_split']!='dev'
        or seal['class_count']!=42 or seal['orientation']!='mean(label1)-mean(label0)'
        or seal['input_sha256']!=request['public_input_sha256'] or seal['random_seed']!=SEED
        or len(seal['capture_sha256'])!=64):raise ValueError('same frozen dev40 capture and owner fit')
    required={'NORMS.json','random40.npy'}|{r+s for r in ROWS for s in ('.unit_d40.npy','.d40.npy')}
    if not required<=set(seal['files']):raise ValueError('complete owner d40/norm/random files')
    directions={};norms=read(root/'NORMS.json');pins=[]
    for row in ROWS:
        u=np.load(root/(row+'.unit_d40.npy'),allow_pickle=False);raw=np.load(root/(row+'.d40.npy'),allow_pickle=False);norm=norms[row]
        if (u.shape!=(5120,) or raw.shape!=(5120,) or not np.isfinite(u).all() or not np.isfinite(raw).all()
            or not np.isfinite(norm) or norm<=0 or not np.isclose(np.linalg.norm(raw),norm)
            or not np.allclose(u*norm,raw,rtol=1e-10,atol=1e-10)):raise ValueError('owner raw/unit/scale identity')
        directions[row]=u;pins.append(dict(row=row,block=40,unit_sha256=sha(root/(row+'.unit_d40.npy')),raw_norm=norm,capture_sha256=seal['capture_sha256'],input_sha256=seal['input_sha256']))
    return directions,norms,np.load(root/'random40.npy',allow_pickle=False),pins


def build(owner,owner_sha,model,out,arm,stage,direction_root=None,direction_sha=None,dose_path=None,dose_commit=None,dose_sha=None):
    selected=None
    if stage=='test':
        receipt=committed_dose(ROOT,dose_path,dose_commit,dose_sha)
        if receipt['experiment']!='E104' or receipt['dev_count']!=84 or receipt['seed']!=SEED:raise ValueError('committed E104 dev doses')
        selected=receipt['selected_doses'];validate_doses(selected)
        if receipt.get('behaviour_scorer_sha256')!=scorer_digest() or receipt.get('dose_score_field')!='pair_logits':raise ValueError('committed dose scorer must match test scorer')
    seal=verify(owner,'VECTOR_SEAL.json',owner_sha);pub=owner/'public';verify(pub,'INPUT_SEAL.json',seal['files']['public/INPUT_SEAL.json'])
    if sha(model/'tokenizer.json')!=TOKENIZER_SHA:raise ValueError('pinned tokenizer')
    from transformers import AutoTokenizer
    tok=AutoTokenizer.from_pretrained(model,local_files_only=True)
    sources=read(owner/'cpu_only/SOURCES.json');records=[];dev_ids={};source_pins=[]
    for bank in ('E56','E59'):
        src=sources[bank];meta=Path(src['metadata_path']);member(meta.parent,'BANK_SEAL.json',src['bank_seal_sha256'],[meta.name])
        if sha(meta)!=src['metadata_sha256']:raise ValueError('metadata identity')
        source_pins.append(dict(bank=bank,bank_seal_sha256=src['bank_seal_sha256'],metadata_sha256=src['metadata_sha256']))
        for x in read(meta):
            if x['feature'] not in ROWS or BANKS[x['feature']]!=bank:continue
            ident=hashlib.sha256(f'E101:{bank}:{x["id"]}'.encode()).hexdigest()
            if x['split']=='dev':dev_ids.setdefault(x['feature'],[]).append(ident)
            if x['split']!=stage:continue
            cands=[[tok.encode(s,add_special_tokens=False) for s in p] for p in PAIRS[x['feature']]]
            records.append(dict(id=ident,row=x['feature'],split=stage,ids=x['ids'],label=x['label'],contrast_target_sign=1-2*x['label'],candidate_ids=cands))
    directions={};norms={};direction_pins=[];owner_random=None
    if arm=='N':
        manifest=read(pub/'MANIFEST.json')
        for row in ROWS:
            d=next(x for x in manifest['rows'] if x['row']==row and x['block']==44)
            directions[row]=np.load(pub/d['d'],allow_pickle=False);norms[row]=d['raw_norm'];direction_pins.append(dict(row=row,block=44,unit_sha256=sha(pub/d['d']),raw_norm=d['raw_norm']))
    elif arm=='U':
        if direction_root is None or direction_sha is None:raise ValueError('U requires sealed dev-only block40 directions; no substitution')
        directions,norms,owner_random,direction_pins=load_u_directions(direction_root,direction_sha)
    else:raise ValueError('registered arm')
    items,deltas,key=compose(records,directions,norms,arm,stage,selected,random_unit=owner_random)
    out.mkdir(parents=True,exist_ok=False);cpu=out/'cpu_only';cpu.mkdir();write(cpu/'KEY.json',key)
    provenance=dict(E101_vector_seal_sha256=owner_sha,source_pins=source_pins,direction_pins=direction_pins,tokenizer_sha256=TOKENIZER_SHA,U_direction_seal_sha256=direction_sha,
        random_recipe='default_rng(SeedSequence([20261029,write_block])), normalized standard Gaussian; shared across rows at each block')
    packages=[]
    for row in ROWS:
        ix=[i for i,x in enumerate(items) if x['row']==row]
        if not ix:packages.append(dict(arm=arm,row=row,status='NOT_EVALUABLE'));continue
        xs=[dict(items[i],delta_index=j) for j,i in enumerate(ix)];dest=out/row
        save(dest,xs,deltas[ix],stage,provenance,selected,dose_commit,dose_sha)
        archive=out/(row+'.tar.gz')
        with tarfile.open(archive,'w:gz',compresslevel=1) as tar:tar.add(dest,arcname='inputs')
        packages.append(dict(arm=arm,row=row,input_root=str(dest),input_sha256=sha(dest/'INPUT_SEAL.json'),archive=str(archive),archive_sha256=sha(archive),bytes=archive.stat().st_size,cells=len(xs)))
    write(out/'BINDING.json',dict(experiment='E104',arm=arm,stage=stage,packages=packages,cpu_key_path=str(cpu/'KEY.json'),cpu_key_sha256=sha(cpu/'KEY.json'),provenance=provenance,GPU_calls=0))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('owner','model','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--owner-sha',required=True);p.add_argument('--arm',choices=tuple(DOSES),required=True);p.add_argument('--stage',choices=['dev','test'],required=True)
    p.add_argument('--direction-root',type=Path);p.add_argument('--direction-sha');p.add_argument('--dose-path',type=Path);p.add_argument('--dose-commit');p.add_argument('--dose-sha')
    a=p.parse_args();build(a.owner,a.owner_sha,a.model,a.out,a.arm,a.stage,a.direction_root,a.direction_sha,a.dose_path,a.dose_commit,a.dose_sha)
