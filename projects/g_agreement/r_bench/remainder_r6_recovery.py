"""Explicit R5 replay for frozen R6 cases; isolated output, no source-array writes."""
from __future__ import annotations
import argparse
from collections import defaultdict
import copy
import hashlib
import json
from pathlib import Path
import time
import numpy as np
from projects.g_agreement.r_bench import remainder_r6 as R

LAYERS=(42,44,56)
LO_TOL=.10
STATE_COS_MIN=.999
ZERO_TOL=.001
BASE=R.CACHE/'remainder/r6/recovery'


def plan(manifest,root=R.ROOT):
    R.available_cohort(manifest)  # exact frozen identity, before any replay
    bank_path=root/'projects/g_agreement/dataset/items_r.json'
    bank={r['item_id']:r for r in json.loads(bank_path.read_text())['items']}
    if any(r.get('source_bank_sha')!=R.sha(bank_path) for r in manifest): raise ValueError('frozen source bank hash changed')
    select_path=root/'results/g_agreement/r/r5_selection.json'
    selections=json.loads(select_path.read_text())['datasets']
    steer_path=root/'cache/g_agreement/r/r5/steer.jsonl'
    models={r['key']:r for r in R.read_rows(steer_path)}
    hashes={str(p.relative_to(root)):R.sha(p) for p in (bank_path,select_path,steer_path)}
    for rel in ('projects/g_agreement/r_bench/steer.py','projects/g_agreement/r_bench/collect.py','projects/g_agreement/core/config.py','projects/g_agreement/core/model.py','projects/g_agreement/core/readers.py','projects/g_agreement/core/scoring_lo.py'):
        hashes[rel]=R.sha(root/rel)
    groups={}
    for row in [r for r in manifest if r['case']=='C4']:
        source=row['r5_source'] if row['arm']=='focal' else row['r5_natural_source']
        ds=row['dataset'];direction=source['direction'];alpha=float(source['alpha']);iid=row['item_id']
        key=f'{ds}|{iid}|{direction}|{alpha}'
        if key not in models: raise ValueError('original model row absent '+key)
        mr=models[key]; item=bank[iid]
        if mr['label']!=item['label'] or mr['candidates']!=item['primary']['candidates'] or mr['edit_layer']!=38 or mr['read_layer']!=42:
            raise ValueError('original model identity/carrier mismatch '+key)
        if mr['sign']!=(-1. if item['label']==1 else 1.): raise ValueError('original direction sign mismatch')
        selection=selections[ds]
        if iid not in selection['item_ids'] or len(selection['item_ids'])!=32 or float(selection['scale'])!=float(mr['scale']):
            raise ValueError('original selection order/scale mismatch')
        dp=root/f'cache/g_agreement/r/r5/directions/{ds}.npz';hashes[str(dp.relative_to(root))]=R.sha(dp)
        z=np.load(dp,allow_pickle=False)
        if direction!='natural' and (direction not in z or not np.isfinite(z[direction]).all() or abs(float(np.linalg.norm(z[direction]))-1)>.001):
            raise ValueError('original Oracle direction absent/invalid')
        gid=f'{ds}|{direction}|{alpha}'
        group=groups.setdefault(gid,{'group':gid,'dataset':ds,'direction':direction,'alpha':alpha,'edit_layer':38,
            'scale':float(mr['scale']),'order':selection['item_ids'],'direction_path':str(dp.relative_to(root)),'selected':[]})
        group['selected'].append({'pair_id':row['pair_id'],'arm':row['arm'],'item_id':iid,'boundary':row['boundary'],
            'source_model':mr,'source_oracle':source,'original42':row['states']['42']})
    if sum(len(g['selected']) for g in groups.values())!=40: raise ValueError('recovery requires all20 C4 pairs')
    from projects.g_agreement.core import config as C
    return {'identity_sha':R.cohort_identity(manifest),'source_hashes':hashes,'groups':list(groups.values()),
        'target_model':C.TARGET_MODEL_ID,'target_revision':C.TARGET_MODEL_SHA,'layers':list(LAYERS),'edit_layer':38,
        'selected_pairs':20,'selected_arms':40,'expected_state_cells':120,'original_target_pairs_per_case':20,
        'lo_tolerance':LO_TOL,'restored_state_cos_min':STATE_COS_MIN,'zero_delta_tolerance':ZERO_TOL,
        'capture_kind':'r5_replay','preserve_original_batch_order':True}


def plan_sha(p): return hashlib.sha256(json.dumps(p,sort_keys=True).encode()).hexdigest()


def validate_numeric(rows,require_full=True):
    if require_full and (len(rows)!=40 or len({(r['pair_id'],r['arm']) for r in rows})!=40): raise ValueError('recovery audit requires40 unique selected arms')
    errors=[]
    for r in rows:
        for name in ('model_lo_error','oracle42_lo_error'):
            if not np.isfinite(r[name]) or abs(r[name])>LO_TOL: errors.append(f"{r['pair_id']}/{r['arm']} {name}")
        if r['oracle42_positive']!=r['original_oracle42_positive']: errors.append(f"{r['pair_id']}/{r['arm']} original Oracle boundary sign changed")
        if r.get('original42_cos') is not None and (not np.isfinite(r['original42_cos']) or r['original42_cos']<STATE_COS_MIN): errors.append(f"{r['pair_id']}/{r['arm']} original42 cosine")
    pairs=defaultdict(dict)
    for r in rows:pairs[r['pair_id']][r['arm']]=r
    if any((require_full and set(v)!={'focal','control'}) or (set(v)=={'focal','control'} and v['focal']['oracle42_positive']==v['control']['oracle42_positive']) for v in pairs.values()):errors.append('missing pair or original report flip not retained')
    return errors


def validate_smoke_receipt(rec,expected_conditions=None):
    if rec.get('smoke') is not True or rec.get('numerical_errors')!=[] or rec.get('coverage_cells')!=6:
        raise RuntimeError('recovery live smoke did not pass numeric/arm coverage audit')
    if expected_conditions is not None:
        expected={(d,float(a),L) for d,a in expected_conditions for L in LAYERS}
        actual={tuple(x) for x in rec.get('condition_site_cells',[])}
        if actual!=expected:raise RuntimeError('recovery live smoke missing registered condition/site')
    zero=rec.get('zero_delta_max_abs',{})
    if set(zero)!={str(L) for L in LAYERS} or any(not isinstance(v,(int,float)) or not np.isfinite(v) or v<0 or v>=ZERO_TOL for v in zero.values()):
        raise RuntimeError('recovery live smoke zero-delta audit missing/invalid')
    for name in ('seconds_per_group','load_seconds'):
        value=rec.get(name)
        if not isinstance(value,(int,float)) or not np.isfinite(value) or value<0:
            raise RuntimeError('recovery live smoke timing missing/invalid')
    if rec['seconds_per_group']<=0 or rec.get('state_cells',0)<6:raise RuntimeError('recovery live smoke incomplete')


def smoke_groups(frozen):
    groups=frozen['groups'];selected=set()
    conditions=sorted({(g['direction'],float(g['alpha'])) for g in groups if g['direction']!='natural'})
    for direction,alpha in conditions:
        candidates=[x['pair_id'] for g in groups if (g['direction'],float(g['alpha']))==(direction,alpha) for x in g['selected'] if x['arm']=='focal']
        if not candidates:raise ValueError('recovery smoke has no frozen representative for condition')
        selected.add(min(candidates))
    result=[g for g in groups if any(x['pair_id'] in selected for x in g['selected'])]
    if {(g['direction'],float(g['alpha'])) for g in result}!={(g['direction'],float(g['alpha'])) for g in groups}:raise ValueError('recovery smoke missing direction/dose')
    for pair in selected:
        if {x['arm'] for g in result for x in g['selected'] if x['pair_id']==pair}!={'focal','control'}:raise ValueError('recovery smoke missing paired natural group')
    return result


def capture_multi(model,rows,spans,delta,pad):
    """Same R5 L38 span hook; record all three sites in one adapter-disabled forward."""
    from projects.g_agreement.core import model as M
    from projects.g_agreement.r_bench import steer as S
    import torch
    captures={};fires={L:0 for L in (44,56)};handles=[]
    def hook(layer):
        def save(_m,_i,out):
            h=out[0] if isinstance(out,tuple) else out;fires[layer]+=1
            captures[layer]=h[torch.arange(len(rows),device=h.device),torch.tensor([len(r)-1 for r in rows],device=h.device)].detach().float().cpu()
        return save
    try:
        for L in (44,56):handles.append(M.blocks(model)[L].register_forward_hook(hook(L)))
        _,captures[42]=S.edited_forward_batch(model,rows,spans,38,delta,pad,read_layer=42)
    finally:
        for h in handles:h.remove()
    if any(n!=1 for n in fires.values()):raise RuntimeError('recovery multi-site hook did not fire exactly once')
    if any(not np.isfinite(captures[L].numpy()).all() for L in LAYERS):raise RuntimeError('nonfinite recovery state')
    return captures


def run(manifest,pod,guard_dir,budget,smoke=False,mock=False,joint_run=False):
    reserve=300 if joint_run else 120
    cap=5400 if joint_run else 1200
    if not mock and (isinstance(budget,bool) or not reserve<budget<=cap):
        raise RuntimeError(f'recovery shares original cap{cap}s; reserve{reserve}s for pull')
    frozen=plan(manifest);ph=plan_sha(frozen);meta={**R.provenance(pod),'recovery_code_sha':R.sha(__file__)}
    out=BASE/('mock_smoke' if mock else 'live_smoke' if smoke else 'full')
    if out.exists() and not mock:raise RuntimeError('recovery output exists; no overwrite permitted')
    out.mkdir(parents=True,exist_ok=True)
    (out/'plan.json').write_text(json.dumps({**frozen,**meta,'plan_sha':ph},indent=2)+'\n')
    groups=frozen['groups']
    expected_conditions=sorted({(g['direction'],float(g['alpha'])) for g in groups})
    if smoke:groups=smoke_groups(frozen)
    if mock:
        rows=[{**meta,'pair_id':s['pair_id'],'arm':s['arm'],'direction':g['direction'],'alpha':g['alpha'],'layer':L,'mock':True} for g in groups for s in g['selected'] for L in LAYERS]
        if {(r['arm'],r['layer']) for r in rows}!={(a,L) for a in ('focal','control') for L in LAYERS}:raise RuntimeError('recovery mock missing arm/site')
        condition_cells=sorted({(r['direction'],float(r['alpha']),r['layer']) for r in rows})
        if set(condition_cells)!={(d,a,L) for d,a in expected_conditions for L in LAYERS}:raise RuntimeError('recovery mock missing condition/site')
        R.write_rows(out/'coverage.jsonl',rows);return {'mock':True,'coverage_cells':6,'condition_site_cells':len(condition_cells),'groups':len(groups),'rows':len(rows),'plan_sha':ph}
    R.check_pod(pod);guard=R.verify_guards(pod,'r6',guard_dir,joint_run=joint_run)
    deadline=guard['deadline_epoch'] if joint_run else min(time.time()+budget,guard['deadline_epoch'])
    receipt_path=BASE/'live_smoke/receipt.json'
    if not smoke:
        if not receipt_path.is_file():raise RuntimeError('recovery live all-arm/site smoke required')
        rec=json.loads(receipt_path.read_text())
        validate_smoke_receipt(rec,expected_conditions)
        if any(rec.get(k)!=v for k,v in {'plan_sha':ph,'pod':pod,'code_sha':meta['code_sha'],'recovery_code_sha':meta['recovery_code_sha'],'guard_sha':guard['receipt_sha']}.items()):raise RuntimeError('recovery smoke receipt mismatch')
        projected=rec['seconds_per_group']*len(groups)*1.5+rec['load_seconds']+reserve
        if projected>deadline-time.time():raise RuntimeError(f'recovery throughput gate: projected{projected:.1f}s exceeds immutable remainder')
    def checktime():
        current=R.verify_guards(pod,'r6',guard_dir,joint_run=joint_run)
        if current['receipt_sha']!=guard['receipt_sha']:raise RuntimeError('immutable shared guard changed')
        if time.time()>=deadline-reserve:raise RuntimeError('recovery deadline reached; partial evidence retained for pull')
    import torch
    from projects.g_agreement.core import model as M,readers as Readers,scoring_lo as LO
    from projects.g_agreement.r_bench import steer as S,collect as RC
    bank={r['item_id']:r for r in json.loads((R.ROOT/'projects/g_agreement/dataset/items_r.json').read_text())['items']}
    checktime();t0=time.monotonic();target=M.load_target();oracle=Readers.OLensReader().bind(target);load_seconds=time.monotonic()-t0
    references={};audits=[];coverage=[];zero=None;tgroups=time.monotonic()
    try:
        tok=target.tokenizer;pad=tok.pad_token_id if tok.pad_token_id is not None else tok.eos_token_id
        for g in groups:
            checktime();order=g['order'];renders=S.item_renders(tok,bank,order);vectors=np.load(R.ROOT/g['direction_path'],allow_pickle=False)
            direction=None if g['direction']=='natural' else vectors[g['direction']].astype(np.float32)
            deltas=np.zeros((32,len(vectors['d_cm_L38'])),dtype=np.float32) if direction is None else np.stack([sign*g['alpha']*g['scale']*direction for sign in renders['signs']]).astype(np.float32)
            for s in g['selected']:
                i=order.index(s['item_id']);mr=s['source_model']
                if list(renders['span_po'][i])!=mr['span_prompt_only'] or list(renders['span_ch'][i])!=mr['span_chat']:raise RuntimeError('original token span changed')
            if zero is None:
                rows=renders['ch_ids'][:1];spans=renders['span_ch'][:1]
                hz=capture_multi(target.model,rows,spans,torch.zeros_like(torch.from_numpy(deltas[:1])),pad)
                hn=capture_multi(target.model,rows,spans,None,pad)
                zero={str(L):float((hz[L]-hn[L]).abs().max()) for L in LAYERS}
                if any(v>=ZERO_TOL for v in zero.values()):raise RuntimeError('zero-delta smoke disagrees with unhooked forward')
            captured={L:[] for L in LAYERS};model_los=[];cands=bank[order[0]]['primary']['candidates']
            for start in range(0,32,16):
                checktime();inds=list(range(start,start+16));delta=torch.from_numpy(deltas[inds])
                h=capture_multi(target.model,[renders['ch_ids'][i] for i in inds],[renders['span_ch'][i] for i in inds],delta,pad)
                for L in LAYERS:captured[L].append(h[L].numpy().astype(np.float16))
                rows=[renders['po_ids'][i]+LO.encode(tok,c) for i in inds for c in cands]
                spans=[renders['span_po'][i] for i in inds for _ in cands];heads=[len(renders['po_ids'][i]) for i in inds for _ in cands]
                lps,_=S.edited_forward_batch(target.model,rows,spans,38,delta.repeat_interleave(2,0),pad,head_lens=heads)
                model_los.extend(lps[i]-lps[i+1] for i in range(0,len(lps),2))
            captured={L:np.concatenate(v) for L,v in captured.items()}
            pri=bank[order[0]]['primary'];fam=RC.register_templates(pri);pos,neg=RC.reader_candidates('olens',pri)
            checktime();scores=LO.score_lo(oracle,torch.from_numpy(captured[42].astype(np.float32)),[(pos,neg)]*32,fam,layer=42,batch=32)
            folder=out/hashlib.sha256(g['group'].encode()).hexdigest()[:16];folder.mkdir()
            for L in LAYERS:
                p=folder/f'L{L}.npy';ip=folder/f'L{L}.index.json';np.save(p,captured[L])
                ip.write_text(json.dumps({**meta,'item_ids':order,'read_layer':L,'edit_layer':38,'kind':'r5_replay','original_group':g['group'],'plan_sha':ph},indent=2)+'\n')
                for s in g['selected']:
                    ref={'kind':'r5_replay','path':str(p.relative_to(R.ROOT)),'index_path':str(ip.relative_to(R.ROOT)),'item_id':s['item_id'],'layer':L,'state_sha':R.sha(p),'index_sha':R.sha(ip),'original_ref':s['original42'] if L==42 else None}
                    references[(s['pair_id'],s['arm'],L)]=ref;coverage.append({**meta,'pair_id':s['pair_id'],'arm':s['arm'],'direction':g['direction'],'alpha':g['alpha'],'layer':L,'kind':'r5_replay','state_ref':ref})
            for s in g['selected']:
                i=order.index(s['item_id']);old=s['source_oracle'];old42=s['original42'];cos=None
                if R.state_status(old42)['ok']:
                    a=R.load_vector(old42);b=captured[42][i].astype(np.float32);cos=float(a@b/(np.linalg.norm(a)*np.linalg.norm(b)))
                row={**meta,'pair_id':s['pair_id'],'arm':s['arm'],'item_id':s['item_id'],'dataset':g['dataset'],'direction':g['direction'],'alpha':g['alpha'],
                    'model_lo':model_los[i],'model_lo_error':model_los[i]-s['source_model']['lo'],'original_model_lo':s['source_model']['lo'],
                    'oracle42_lo':scores[i]['lo'],'oracle42_lo_error':scores[i]['lo']-old['lo'],'original_oracle42_lo':old['lo'],
                    'oracle42_positive':scores[i]['lo']>s['boundary'],'original_oracle42_positive':old['lo']>s['boundary'],'original42_cos':cos}
                audits.append(row)
            R.write_rows(out/'numeric_audit.jsonl',audits);R.write_rows(out/'coverage.jsonl',coverage)
    finally:M.unload(target)
    errors=validate_numeric(audits,require_full=not smoke)
    if {(r['arm'],r['layer']) for r in coverage}!={(a,L) for a in ('focal','control') for L in LAYERS}:errors.append('missing recovery arm/site')
    if not smoke and len(coverage)!=120:errors.append('incomplete recovery120 state cells')
    condition_cells=sorted({(r['direction'],float(r['alpha']),r['layer']) for r in coverage})
    if set(condition_cells)!={(d,a,L) for d,a in expected_conditions for L in LAYERS}:errors.append('missing recovery direction/dose/site')
    for path,digest in frozen['source_hashes'].items():
        if R.sha(R.ROOT/path)!=digest:errors.append('source changed during recovery '+path)
    receipt={**meta,'plan_sha':ph,'guard_sha':guard['receipt_sha'],'guard_deadline_epoch':guard['deadline_epoch'],
        'source_identity_sha':frozen['identity_sha'],'groups':len(groups),'seconds_per_group':(time.monotonic()-tgroups)/len(groups),'load_seconds':load_seconds,
        'zero_delta_max_abs':zero,'coverage_cells':6,'condition_site_cells':condition_cells,'state_cells':len(coverage),'numerical_errors':errors,'complete_pass':not errors and not smoke,'smoke':smoke}
    rp=out/'receipt.json';rp.write_text(json.dumps(receipt,indent=2)+'\n')
    if errors:raise RuntimeError('recovery numeric/coverage audit failed: '+'; '.join(errors[:8]))
    if not smoke:
        recovered=copy.deepcopy(manifest)
        for row in recovered:
            if row['case']!='C4':continue
            for L in LAYERS:
                original=row['states'][str(L)]
                if R.state_status(original)['ok']:
                    original.update(state_sha=R.sha(R.ROOT/original['path']),index_sha=R.sha(R.ROOT/original['index_path']))
                    continue  # always prefer restored original
                ref=references[row['pair_id'],row['arm'],L]
                ref.update(recovery_receipt=str(rp.relative_to(R.ROOT)),recovery_receipt_sha=R.sha(rp))
                row['states'][str(L)]=ref
        R.write_rows(out/'selection_recovered.jsonl',recovered)
    return receipt


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=('preflight','smoke','recover'),required=True)
    p.add_argument('--manifest',type=Path,default=R.CACHE/'remainder/r6/selection.jsonl');p.add_argument('--pod');p.add_argument('--guard-dir',type=Path,default=R.ROOT.parent)
    p.add_argument('--budget-seconds',type=float,default=1200);p.add_argument('--mock',action='store_true');p.add_argument('--joint-run',action='store_true');a=p.parse_args(argv)
    manifest=list(R.read_rows(a.manifest))
    if a.phase=='preflight':
        result={**plan(manifest),**R.provenance(),'recovery_code_sha':R.sha(__file__)}
        R.OUT.mkdir(parents=True,exist_ok=True);(R.OUT/'recovery_preflight.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'ready_inputs':True,'selected_arms':40,'state_cells':120,'groups':len(result['groups'])}));return 0
    if a.mock and a.phase!='smoke':raise ValueError('--mock is smoke-only')
    result=run(manifest,a.pod,a.guard_dir,a.budget_seconds,smoke=a.phase=='smoke',mock=a.mock,joint_run=a.joint_run)
    print(json.dumps(result,indent=2));return 0

if __name__=='__main__':raise SystemExit(main())
