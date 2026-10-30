"""§209 CPU-only E101 directions; reuse §208 a/b pairings and projectors."""
import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
ROWS=(('E59','language_plan'),('E59','format_plan'),('E56','fact_recall'),('E56','language_continuation'),
      ('E57','nesting_depth'),('E57','indent_level'),('E57','page_range_digit'))
SEED=20261028

def require(ok,why):
    if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text())
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def verify(p,expected):
    p=Path(p);require(sha(p)==expected,'source seal identity: '+str(p));s=read(p)
    for n,h in s['files'].items():
        member=(p.parent/n).resolve();require(member.is_relative_to(p.parent.resolve()),'seal path containment')
        require(sha(member)==h,'sealed member: '+n)
    return s

def dev_direction(records,acts,row):
    groups={y:sorted(x['id'] for x in records if x['feature']==row and x['split']=='dev' and x['label']==y) for y in (1,0)}
    require(all(len(ids)==42 for ids in groups.values()),'42 dev items per class')
    require(set(groups[1]).isdisjoint(groups[0]),'disjoint dev classes')
    means=np.stack([np.stack([acts[i] for i in groups[y]]).mean(0,dtype=np.float64) for y in (1,0)])
    d=means[0]-means[1]
    require(d.shape==(5120,) and np.isfinite(d).all() and np.linalg.norm(d)>1e-12,'finite dev difference')
    return d,groups

def unit(d):
    d=np.asarray(d,np.float64);norm=float(np.linalg.norm(d))
    require(np.isfinite(d).all() and norm>1e-12,'nonzero finite direction')
    return d/norm

def random_direction(block):
    require(block in (42,44),'registered blocks')
    return unit(np.random.default_rng(np.random.SeedSequence([SEED,block])).standard_normal(5120))

def seal(root,name,metadata):
    write(root/name,dict(metadata,files={str(p.relative_to(root)):sha(p) for p in sorted(root.rglob('*')) if p.is_file() and p!=root/name and '__pycache__' not in p.parts and not any(part.startswith('.') for part in p.relative_to(root).parts)}))

def run():
    started=time.monotonic();spec=read(HERE/'INPUTS.json')
    for name in ('build.py','test_build.py','PLAN.md','INPUTS.json'):
        require(subprocess.check_output(['git','show','HEAD:'+str((HERE/name).relative_to(ROOT))],cwd=ROOT)==(HERE/name).read_bytes(),'commit recipe before build')
    e100=ROOT/spec['e100_root'];verify(e100/'BUNDLE_SEAL.json',spec['e100_bundle_sha256'])
    prov=read(e100/'artifacts/cpu_only/SOURCES.json')
    old=Path(spec['e79_directions']);require(sha(old)==prov['e79_directions_sha256'],'sealed original E79 directions')
    old=np.load(old,allow_pickle=False)
    q=np.load(e100/'artifacts/public/Q_J.npy',allow_pickle=False);qr=np.load(e100/'artifacts/public/Q_R.npy',allow_pickle=False)
    require(q.shape==qr.shape==(5120,384),'rank384 projectors')
    jerr=float(np.max(np.abs(q.T@q-np.eye(384))));rerr=float(np.max(np.abs(qr.T@qr-np.eye(384))))
    require(jerr<1e-4 and rerr<1e-10,'orthonormal projectors')
    # Verify bank/capture membership before loading activations. Only dev activations are used below.
    data={};source_evidence={}
    for bank,source in prov['banks'].items():
        mp=Path(source['metadata_path']);verify(mp.parent/'BANK_SEAL.json',source['bank_seal_sha256'])
        require(sha(mp)==source['metadata_sha256'],'metadata binding');records=read(mp);by={x['id']:x for x in records}
        require(len(by)==len(records),'unique bank IDs')
        acts={42:{},44:{}};evidence=[]
        for capture in source['captures']:
            sp=Path(capture['seal_path']);cs=verify(sp,capture['seal_sha256'])
            require({'acts42.npy','acts44.npy','items.order.json'}<=set(cs['files']),'both layers sealed')
            order=read(sp.parent/'items.order.json');require(len(order)==len(set(order)),'unique capture IDs')
            for block in (42,44):
                a=np.load(sp.parent/f'acts{block}.npy',mmap_mode='r',allow_pickle=False)
                require(a.shape==(len(order),5120),'capture shape')
                for i,ident in enumerate(order):
                    require(ident in by,'capture/bank membership')
                    m=by[ident]
                    if m['split']=='dev' and (bank,m['feature']) in ROWS:
                        require(ident not in acts[block],'duplicate dev capture')
                        acts[block][ident]=np.asarray(a[i],np.float64)
            evidence.append(dict(path=str(sp),sha256=sha(sp),files={n:cs['files'][n] for n in ('acts42.npy','acts44.npy','items.order.json')}))
        data[bank]=(records,acts);source_evidence[bank]=dict(metadata_path=str(mp),metadata_sha256=sha(mp),bank_seal_sha256=source['bank_seal_sha256'],captures=evidence)
    public=HERE/'public';cpu=HERE/'cpu_only';require(not public.exists() and not cpu.exists(),'build once; no overwrite')
    public.mkdir();cpu.mkdir();report=[];private=[];manifest=[]
    for block in (42,44):np.save(public/f'r{block}.npy',random_direction(block),allow_pickle=False)
    for bank,row in ROWS:
        records,acts=data[bank];by={x['id']:x for x in records}
        for block in (44,42):
            computed,groups=dev_direction(records,acts[block],row)
            reused=block==44 and bank in ('E57','E59')
            raw=old[row+'__d'].copy() if reused else computed
            require(np.array_equal(raw,computed),'reused E79 direction exactly matches original dev means')
            direction=unit(raw);norm=float(np.linalg.norm(raw));np.save(public/f'{row}.d{block}.npy',direction,allow_pickle=False)
            np.save(cpu/f'{row}.raw_d{block}.npy',raw,allow_pickle=False)
            require(abs(np.linalg.norm(direction)-1)<1e-12,'unit saved direction')
            jf=float(np.linalg.norm(q@(q.T@raw))/norm) if block==44 else None
            report.append(dict(bank=bank,row=row,block=block,n_dev=84,n_dev_per_class=42,raw_norm=norm,J_fraction=jf,
                chance_display=0.27,chance_exact=float(np.sqrt(384/5120)),reused_E79_raw_bytes=reused,
                fit='original E79 Arm '+('A' if bank=='E57' else 'B') if reused else 'dev class1 mean minus class0 mean',
                raw_sha256=sha(cpu/f'{row}.raw_d{block}.npy'),unit_sha256=sha(public/f'{row}.d{block}.npy')))
            private.append(dict(bank=bank,row=row,block=block,positive_label=1,negative_label=0,
                dev_ids={str(y):ids for y,ids in groups.items()},values={str(y):sorted({by[i]['value'] for i in ids}) for y,ids in groups.items()},
                target_label_formula='1 - true_label',sigma_formula='1 - 2 * true_label',raw_norm=norm))
            manifest.append(dict(row=row,block=block,d=f'{row}.d{block}.npy',r=f'r{block}.npy',raw_norm=norm,dimension=5120,dtype='float64'))
    # Existing E100 pairing grid checked against CPU-only bank labels; do not build another sample.
    join=read(e100/'artifacts/cpu_only/JOIN.DO_NOT_STAGE.json');join_by={x['id']:x for x in join}
    pm=read(e100/'artifacts/public/MANIFEST.json');pair_checks=[]
    for row in pm['rows']:
        pairs=read(e100/'artifacts/public'/row['pairings']);require(len(pairs)==84,'all84 E100 test items')
        labels=[join_by[p['id']]['true_label'] for p in pairs];rng=np.random.default_rng(SEED)
        for i,p in enumerate(pairs):
            a,b=join_by[p['id']],join_by[p['donor_id']]
            eligible=[j for j,v in enumerate(labels) if v!=labels[i]];chosen=int(rng.choice(eligible))
            require(p['slot']==i and p['donor_slot']==chosen and p['donor_id']==pairs[chosen]['id'],'original seeded pairing')
            require(a['row']==b['row']==row['row'] and a['true_label']!=b['true_label'],'opposite-value same-row pair')
            records,_=data[a['bank']];by={v['id']:v for v in records}
            require(by[a['source_item_id']]['split']==by[b['source_item_id']]['split']=='test','test/test pairing')
        pair_checks.append(dict(row=row['row'],items=84,opposite_value_verified=84,pairings_sha256=sha(e100/'artifacts/public'/row['pairings'])))
    require(len(pair_checks)==8 and sum(x['items'] for x in pair_checks)==672,'E100 all eight rows retained')
    write(public/'MANIFEST.json',dict(experiment='E101',status='DIRECTIONS_ONLY_DOSE_SELECTION_PENDING',rows=manifest,
        random_seed=SEED,random_recipe='unit Gaussian from default_rng(SeedSequence([20261028, block])); one shared direction per block, not row-orthogonal',
        formula='h_prime = h + alpha * raw_norm * sigma * unit_direction',dose_grid=[0.5,1,2,4],labels_in_package=False))
    seal(public,'INPUT_SEAL.json',dict(experiment='E101',status='SEALED_DIRECTIONS_NO_CALLS',input_spec_sha256=sha(HERE/'INPUTS.json')))
    write(cpu/'DEV_JOINS.DO_NOT_STAGE.json',private);write(cpu/'SOURCES.json',source_evidence)
    write(HERE/'E100_AB_REUSE.json',dict(status='REUSE_EXISTING_AB_ONLY',root=spec['e100_root'],bundle_sha256=spec['e100_bundle_sha256'],
        public_input_seal_sha256=sha(e100/'artifacts/public/INPUT_SEAL.json'),handoff_request_sha256=sha(e100/'HANDOFF_REQUEST.json'),
        Q_J_sha256=sha(e100/'artifacts/public/Q_J.npy'),Q_R_sha256=sha(e100/'artifacts/public/Q_R.npy'),projector_formula='P = Q @ Q.T',
        basis_shape=[5120,384],J_orthogonality_max_error=jerr,R_orthogonality_max_error=rerr,pairings=pair_checks,
        withdrawn=['u_tok','d_J injection','d_perp injection','all E100 injection','upstream28','upstream36']))
    write(HERE/'BUILD_REPORT.json',dict(rows=report,seed=SEED,CPU_only=True,GPU_calls=0,judge_calls=0,
        original_E79_reused_count=5,new_directions=9,unit_directions=14,random_directions=2,
        alpha_star_selected=False,behavioural_flip_not_measured=True,wall_seconds=time.monotonic()-started,
        public_input_seal_sha256=sha(public/'INPUT_SEAL.json')))
    seal(HERE,'VECTOR_SEAL.json',dict(experiment='E101',authority='69f8c08e',status='CPU_VECTORS_READY_DOSE_SELECTION_PENDING',
        build_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),GPU_calls=0,judge_calls=0))
    print(json.dumps(dict(unit_directions=14,random_directions=2,E100_pairings=672,seal_sha256=sha(HERE/'VECTOR_SEAL.json'))))

if __name__=='__main__':run()
