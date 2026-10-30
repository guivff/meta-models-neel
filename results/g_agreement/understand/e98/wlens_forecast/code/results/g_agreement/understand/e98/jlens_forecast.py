"""E98 operational port of frozen E57/E59 R3b CPU kernels; no native readers.

Only model width/layer, Qwen3 final norm, tied head and tokenizer bindings differ.
Pursuit/G3/label/token-variant kernels are imported unchanged from sealed sources.
"""
from pathlib import Path
import json,hashlib,sys,subprocess,time,os
import numpy as np
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CACHE=ROOT/'cache/g_agreement/understand/e98/jlens'
I5=ROOT.parent/'wt-i5'
SOURCE=I5/'cache/g_agreement/understand/e98'
PUBLIC=I5/'results/g_agreement/sealed/E98_CAPTURE'
PLAN=HERE/'JLENS_INPUT_PLAN.json'
sys.path.insert(0,str(ROOT/'results/g_agreement/understand/e52'))
sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
from build_basis import sha,read,dump
from sparse_primary import fraction,primary_label
from core import g3
from mats.readers.jlens import token_variants

CARD_SHA='0586f016b42c2dfb1a2c6db52fc826e54e0d163788b5215a4744a47c80d2683c'
CAPTURE_SHA='08001b2633927151c109dd9e00226b87e5a1a409295711e9591304d2617b4d2a'
J_SHA='9c94a43ac2db2debbab36acb74480f49a3ac411fb3d7fa8e5461377028e74606'


def custody(receipt):
    if receipt.get('status')!='COMPLETE' or receipt.get('R3b_readers_opened') is not False:
        raise ValueError('complete unopened capture-only receipt required')
    if receipt.get('capture_seal_sha256')!=CAPTURE_SHA or receipt.get('card_sha256')!=CARD_SHA:
        raise ValueError('exact original capture/card required')


def mean_direction(h,y):
    if h.ndim!=2 or y.shape!=(len(h),) or set(y)!={0,1} or not np.isfinite(h).all():
        raise ValueError('finite binary capture required')
    means=np.stack([h[y==k].mean(0,dtype=np.float64) for k in (1,0)])
    d=means[0]-means[1];norm=float(np.linalg.norm(d))
    if not norm>0:raise ValueError('zero class-mean direction; stop, never retry')
    return means,d/norm,norm


def logits(h,j,wu,norm):
    # Exact model-specific Qwen3 RMSNorm, BF16 input/weight then float32 head.
    import torch
    z=norm((h@j.T).to(torch.bfloat16)).float()
    return z@wu.T


def prepare():
    from transformers import AutoTokenizer
    CACHE.mkdir(parents=True,exist_ok=True)
    if PLAN.exists():raise ValueError('plan already frozen; do not overwrite')
    pins={}
    def pin(p,expected=None):
        p=Path(p).resolve();h=sha(p)
        if expected is not None and h!=expected:raise ValueError('hash mismatch: '+str(p))
        pins[str(p)]=h;return p
    card=read(pin(I5/'results/g_agreement/understand/e98/ASSET_CARD.json',CARD_SHA))
    assert card['model']['hidden_size']==2560 and card['jlens']['layer']==18
    cfg=read(pin(HERE/'assets/base_config'));assert cfg['tie_word_embeddings'] is True and cfg['hidden_size']==2560 and cfg['rms_norm_eps']==1e-6
    receipt=read(pin(PUBLIC/'CAPTURE_RECEIPT.json'));custody(receipt)
    cap=read(pin(PUBLIC/'CAPTURE_SEAL.json',CAPTURE_SHA));raw=SOURCE/'capture_v1/out'
    for n,h in cap['files'].items():pin(raw/n,h)
    for name in ['SEAL.json','CLOSEOUT.json']:pin(PUBLIC/name)
    port=read(pin(HERE/'PORT_RECEIPT.json'))
    keypath=pin(SOURCE/'ported_v1/KEY.PRIVATE.json',port['private_key_sha256']);records=read(keypath)
    dropped=read(pin(SOURCE/'ported_v1/DROPPED.PRIVATE.json'));assert dropped==[] or dropped=={}
    podseal=read(pin(SOURCE/'ported_v1/pod_inputs/INPUT_SEAL.json',port['pod_seal_sha256'])) if (SOURCE/'ported_v1/pod_inputs/INPUT_SEAL.json').exists() else read(pin(SOURCE/'ported_v1/pod_inputs/SEAL.json',port['pod_seal_sha256']))
    items=read(pin(SOURCE/'ported_v1/pod_inputs/items.json',podseal['files']['items.json']))
    assert len(records)==len(items)==4368 and len({r['id'] for r in records})==4368
    assert [r['id'] for r in records]==[r['id'] for r in items]
    for a,b in zip(records,items):
        assert a['ids']==b['ids'] and b.get('read_index',b.get('read_position',len(b['ids'])-1))==len(a['ids'])-1
        p=raw/'records'/(a['id']+'.npy');assert 'records/'+p.name in cap['files']
        v=np.load(p,allow_pickle=False);assert v.shape==(2560,) and v.dtype==np.float32 and np.isfinite(v).all()
    tokdir=SOURCE/'tokenizer'
    for n,h in port['tokenizer_files'].items():pin(tokdir/n,h)
    tok=AutoTokenizer.from_pretrained(tokdir,local_files_only=True)
    units=[]
    for bank in ['E57','E59']:
        oldplan=read(pin(ROOT/f'results/g_agreement/understand/e57/jlens/{bank}_INPUT_PLAN.json'))
        original=read(pin(oldplan['records']['path'],oldplan['records']['sha256']));by={r['id']:r for r in original}
        if 'word_audit_path' in oldplan:audit=read(pin(oldplan['word_audit_path'],oldplan['word_audit_sha256']))
        else:audit=oldplan['word_audit']
        for a in [r for r in records if r['source_bank']==bank]:
            b=by[a['source_id']]
            assert a['text']==b['text'] and a['label']==b['label'] and a['split']==b['split'] and a['feature']==b['feature']
            assert tok.encode(a['text'],add_special_tokens=False)==a['ids']
        for old in oldplan['units']:
            rr=sorted([r for r in records if r['source_bank']==bank and r['feature']==old['source_row'] and r['split']=='test'],key=lambda r:r['id'])
            assert len(rr)==84
            frozen=[]
            for r in rr:
                words=audit[old['id']][r['source_id']]['words'] if bank=='E57' else audit[old['id']]['words']
                pair=[token_variants(tok,w) for w in words] if old['binary'] else [[],[]]
                frozen.append(dict(id=r['id'],source_id=r['source_id'],label=r['label'],tokens=pair,words=words))
            if old['binary']:assert sum(r['label'] for r in rr)==42 and set(r['label'] for r in rr)=={0,1}
            units.append(dict(bank=bank,row=old['id'],binary=old['binary'],items=frozen))
    assert len(units)==26 and sum(u['binary'] for u in units)==23 and sum(len(u['items']) for u in units)==2184
    private=CACHE/'TOKEN_PLAN.PRIVATE.json';dump(private,dict(units=units));os.chmod(private,0o600);pin(private)
    weights=read(pin(CACHE/'assets/WEIGHT_RANGES.json'))
    for n,s in weights.items():pin(s['path'],s['sha256'])
    jpath=pin(SOURCE/'assets/Qwen3-4B_jacobian_lens.pt',J_SHA)
    for f in (CACHE/'assets').glob('*.header.json'):pin(f)
    pin(CACHE/'assets/model.safetensors.index.json')
    import inspect
    from transformers.models.qwen3.modeling_qwen3 import Qwen3RMSNorm
    code=[Path(__file__),ROOT/'external/mats-nla-workspace/src/mats/jspace.py',ROOT/'external/mats-nla-workspace/src/mats/readers/jlens.py',ROOT/'results/g_agreement/understand/e52/core.py',ROOT/'results/g_agreement/understand/e52/sparse_primary.py',ROOT/'results/g_agreement/understand/e52/build_basis.py',Path(inspect.getfile(Qwen3RMSNorm)),HERE/'test_jlens_forecast.py']
    for p in code:pin(p)
    plan=dict(experiment='E98',status='FROZEN_BEFORE_SCIENTIFIC_COMPUTE',model=card['model'],layer=18,width=2560,k=16,null_directions=200,seed=20261027,refine_steps=6,rank_secondary=[384,1536],source_pins=pins,private_token_plan=str(private),jlens_path=str(jpath),weights=weights,rms_norm_eps=cfg['rms_norm_eps'],basis_map='W_U @ diag(Qwen3 final norm.weight) @ J18',atoms_map='W_U @ J18, unit bf16 rows, no final-norm gain',readout='Qwen3RMSNorm((h@J18.T).bf16).float @ tied_embedding.float.T',word_policy='Reuse exact sealed E57/E59 pre-tokenization word audits, retokenise with pinned 4B tokenizer; no synonyms/backfill',units=[dict(bank=u['bank'],row=u['row'],binary=u['binary'],n_test=len(u['items']),empty_token_items=sum(not all(r['tokens']) for r in u['items'])) for u in units],claim=str(CACHE/'ONCE.json'),command='python results/g_agreement/understand/e98/jlens_forecast.py run',custody='after completed capture, before Oracle outputs/GO; direct Guiv authorization I5-E98-R3B-20261029',gpu_hours=0)
    dump(PLAN,plan);print('E98 validated/frozen:4368 captures,2184 tests,23 binary rows,3 nonbinary exclusions; NO compute claim',flush=True)


def run():
    import torch
    from transformers.models.qwen3.modeling_qwen3 import Qwen3RMSNorm
    from mats.jspace import load_jlens_layers,jspace_basis,jlens_atoms,nn_pursuit
    torch.set_num_threads(8)
    rel=str(PLAN.relative_to(ROOT));assert subprocess.check_output(['git','show','HEAD:'+rel],cwd=ROOT)==PLAN.read_bytes()
    plan=read(PLAN)
    for p,h in plan['source_pins'].items():
        if sha(p)!=h:raise ValueError('frozen source/input drift '+p)
    custody(read(PUBLIC/'CAPTURE_RECEIPT.json'))
    units=read(plan['private_token_plan'])['units']
    with (CACHE/'ONCE.json').open('x') as f:json.dump(dict(status='CLAIMED_NEVER_RESET',plan_sha256=sha(PLAN),epoch=time.time()),f)
    out=CACHE/'raw';out.mkdir(exist_ok=False);started=time.time()
    j=load_jlens_layers(plan['jlens_path'],[18])[18];assert j.shape==(2560,2560) and torch.isfinite(j).all()
    weights=plan['weights'];wu=torch.from_file(weights['unembedding.bf16']['path'],shared=False,size=151936*2560,dtype=torch.bfloat16).reshape(151936,2560).float()
    w=torch.from_file(weights['norm.bf16']['path'],shared=False,size=2560,dtype=torch.bfloat16).clone()
    assert torch.isfinite(wu).all() and torch.isfinite(w).all()
    norm=Qwen3RMSNorm(2560,eps=1e-6).to(dtype=torch.bfloat16)
    with torch.no_grad():norm.weight.copy_(w)
    norm.requires_grad_(False)
    print('E98 build4B J18 basis and atom dictionary once; CPU',flush=True)
    basis=jspace_basis(j,wu,w.float(),r_max=1536,chunk=4096,layer=18)
    q=basis.vecs.numpy();assert np.max(np.abs(q.T@q-np.eye(1536)))<1e-5
    np.save(out/'basis_L18_r1536.npy',q,allow_pickle=False);np.save(out/'eigenvalues.npy',basis.evals.numpy(),allow_pickle=False)
    atoms,norms=jlens_atoms(j,wu,torch.ones(2560),chunk=4096)
    torch.save(dict(atoms=atoms,norms=norms,layer=18),out/'atoms.pt')
    rng=np.random.default_rng(20261027);random=rng.normal(size=(200,2560));random/=np.linalg.norm(random,axis=1,keepdims=True);random=random.astype(np.float32)
    print('E98 200-direction null once k16',flush=True)
    idx,coef,recon=nn_pursuit(torch.from_numpy(random),atoms,k=16)
    nf=fraction(random,recon.numpy());median,upper=np.quantile(nf,[.5,.975]);np.savez_compressed(out/'null.npz',directions=random,idx=idx.numpy(),coef=coef.numpy(),reconstruction=recon.numpy(),fractions=nf)
    dump(out/'BASIS_ATOM_NULL_SEAL.json',dict(model='Qwen3-4B',layer=18,k=16,n=200,seed=20261027,median=float(median),percentile97_5=float(upper),files={n:sha(out/n) for n in ['basis_L18_r1536.npy','eigenvalues.npy','atoms.pt','null.npz']},plan_sha256=sha(PLAN)))
    rows=[];exclusions=[]
    for u in units:
        bank,row=u['bank'],u['row'];key=bank+'__'+row
        if not u['binary']:
            exclusions.append(dict(bank=bank,row=row,n_test=84,reason='Inherited E57 nonbinary descriptive unit; no registered A/B J direction'))
        hh=np.stack([np.load(SOURCE/'capture_v1/out/records'/(r['id']+'.npy'),allow_pickle=False) for r in u['items']]);ranks=[];tops=[]
        with torch.no_grad():
            for start in range(0,len(hh),16):
                z=logits(torch.from_numpy(hh[start:start+16]),j,wu,norm);assert torch.isfinite(z).all()
                tops.extend(z.topk(50,dim=1).indices.tolist())
                for i,r in enumerate(u['items'][start:start+16]):ranks.append([int((z[i]>z[i,ids].max()).sum()) if ids else None for ids in r['tokens']])
        dump(out/(key+'.readout.json'),dict(items=[dict(id=r['id'],best_full_vocab_ranks=a,top10_token_ids=t[:10],top50_token_ids=t) for r,a,t in zip(u['items'],ranks,tops)]))
        result=dict(bank=bank,row=row,n_test=84)
        if u['binary']:
            y=np.array([r['label'] for r in u['items']]);means,d,dnorm=mean_direction(hh,y)
            readable=g3(np.asarray(ranks,dtype=np.int64),y) if all(all(x is not None for x in rr) for rr in ranks) else dict(status='NOT EVALUABLE',readable=None,reason='empty frozen value-token set; no backfill')
            h=d.astype(np.float32)[None,:];ix,c,rec=nn_pursuit(torch.from_numpy(h),atoms,k=16);value=float(fraction(h,rec.numpy())[0]);label=primary_label(value,float(median),float(upper),readable)
            np.savez_compressed(out/(key+'.direction.npz'),class_means=means,direction=d,idx=ix.numpy(),coef=c.numpy(),reconstruction=rec.numpy())
            result.update(label=label,J_fraction=value,J_readability=readable,class_mean_difference_norm=dnorm,oracle_prediction='REPORTED' if label=='IN-J' else 'MISSED')
            rows.append(result)
        print(key,result.get('label','NONBINARY_EXCLUDED'),flush=True)
    dump(HERE/'E98_JFORECAST.json',dict(experiment='E98',status='SEALED_PROSPECTIVE_TO_ORACLE_OUTPUTS',model='Qwen3-4B',layer=18,rows=rows,exclusions=exclusions,dropped_rows=[],total_test_items=2184,binary_test_items=1932,excluded_test_items=252,plan_sha256=sha(PLAN),capture_seal_sha256=CAPTURE_SHA,asset_card_sha256=CARD_SHA,jlens_sha256=J_SHA,basis_atom_null_seal_sha256=sha(out/'BASIS_ATOM_NULL_SEAL.json'),null_median=float(median),null_percentile97_5=float(upper),k=16,null_directions=200,created_epoch=time.time(),elapsed_seconds=time.time()-started,gpu_hours=0,reader_outcomes_accessed=False,chronology='capture complete before forecast; forecast must be committed before GO/readers'))
    dump(out/'RAW_SEAL.json',dict(files={p.name:sha(p) for p in out.iterdir() if p.is_file()}))
    dump(HERE/'JLENS_COMPLETION_SEAL.json',dict(status='COMPLETE',forecast_sha256=sha(HERE/'E98_JFORECAST.json'),plan_sha256=sha(PLAN),raw_seal_sha256=sha(out/'RAW_SEAL.json'),raw_root=str(out),claim_sha256=sha(CACHE/'ONCE.json'),elapsed_seconds=time.time()-started,gpu_hours=0))
    print('E98 forecast COMPLETE, awaiting actual Git commitment before I5 GO',flush=True)

if __name__=='__main__':
    if sys.argv[1:] == ['prepare']:prepare()
    elif sys.argv[1:]==['run']:run()
    else:raise SystemExit('prepare or run only; never rerun run')
