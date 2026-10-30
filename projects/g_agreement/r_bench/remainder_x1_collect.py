"""X1 target capture/patching and downstream reader scoring; live phases require registered booking/guards."""
from __future__ import annotations
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import time
import numpy as np
from projects.g_agreement.r_bench import remainder_x1 as D


def forward(target, rows, positions, layers, *, patch_layer=None, patch_positions=None, values=None,
            mode='replace', heads=None):
    """Patch exact native-dtype values; read positions explicit, never candidate tokens. Hooks always removed."""
    import torch
    from projects.g_agreement.core import model as M
    if not rows or len(rows)!=len(positions):raise ValueError('Empty/misaligned forward')
    if any(not 0<=p<len(r) for p,r in zip(positions,rows)):raise ValueError('Read position outside row')
    if values is not None and (patch_layer is None or len(values)!=len(rows) or len(patch_positions)!=len(rows)):
        raise ValueError('Patch rows misaligned')
    if values is not None and any(not 0<=p<len(r) for p,r in zip(patch_positions,rows)):raise ValueError('Patch outside row')
    if mode not in ('replace','add'):raise ValueError('Unknown patch mode')
    model=target.model;dev=next(model.parameters()).device
    pad=target.tokenizer.pad_token_id
    if pad is None:pad=target.tokenizer.eos_token_id
    ids=torch.full((len(rows),max(map(len,rows))),pad,dtype=torch.long,device=dev);mask=torch.zeros_like(ids)
    for i,r in enumerate(rows):ids[i,:len(r)]=torch.tensor(r,device=dev);mask[i,:len(r)]=1
    blocks=M.blocks(model);saved={};counts={};handles=[]
    def patch(_m,_i,out):
        h=out[0] if isinstance(out,tuple) else out;h=h.clone();idx=torch.arange(len(rows),device=h.device)
        v=torch.as_tensor(np.asarray(values),device=h.device,dtype=h.dtype)
        if v.shape!=(len(rows),h.shape[-1]) or not torch.isfinite(v).all():raise ValueError('Invalid patch values')
        pos=torch.tensor(patch_positions,device=h.device)
        h[idx,pos]=v if mode=='replace' else h[idx,pos]+v
        counts['patch']=counts.get('patch',0)+1
        return (h,*out[1:]) if isinstance(out,tuple) else h
    def capture(layer):
        def hook(_m,_i,out):
            h=out[0] if isinstance(out,tuple) else out
            saved[layer]=h[torch.arange(len(rows),device=h.device),torch.tensor(positions,device=h.device)].detach().float().cpu().numpy()
            counts[layer]=counts.get(layer,0)+1
        return hook
    if values is not None:handles.append(blocks[patch_layer].register_forward_hook(patch))
    for L in layers:handles.append(blocks[L].register_forward_hook(capture(L)))
    lp=[]
    try:
        with torch.no_grad(),M.disable_adapter_ctx(model):
            if heads is None:
                try:model(input_ids=ids,attention_mask=mask,use_cache=False,logits_to_keep=1)
                except TypeError:model(input_ids=ids,attention_mask=mask,use_cache=False)
            else:
                output=model(input_ids=ids,attention_mask=mask,use_cache=False)
                for i,(r,head) in enumerate(zip(rows,heads)):
                    if not 0<head<len(r):raise ValueError('Invalid completion boundary')
                    logits=output.logits[i,head-1:len(r)-1].float().log_softmax(-1)
                    lp.append(float(logits.gather(1,ids[i,head:len(r),None]).sum()))
    finally:
        for h in handles:h.remove()
    if any(counts.get(L)!=1 for L in layers) or (values is not None and counts.get('patch')!=1):raise RuntimeError('Hook did not fire once')
    if any(not np.isfinite(x).all() for x in saved.values()):raise RuntimeError('Nonfinite readback')
    return lp,saved


def encode_bank(target,plan):
    from projects.g_agreement.r_bench import collect as C,swap as S
    encoded={};tok=target.tokenizer
    for r in plan['records']:
        ids=C.render_ids(tok,r['text'],'chat');p=r['position']
        span=S.char_span_tokens(tok,ids,r['text'],p['char_start'],p['char_end'],None)
        if span is None or span[1]-1>=len(ids)-1:raise ValueError('Unresolved or non-earlier bridge position: '+r['id'])
        encoded[r['id']]={'ids':ids,'bridge':span[1]-1,'answer':len(ids)-1}
    return encoded


def natural_capture(target,plan,out,check,batch=16,meta=None):
    meta={**D.provenance(),**(meta or {})}
    encoded=encode_bank(target,plan);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    identity={'plan_sha256':D.digest(plan),'code_sha':D.provenance()['code_sha']}
    identity_file=out/'identity.json'
    if identity_file.exists() and D.read(identity_file)!=identity:raise ValueError('Natural capture identity changed')
    D.save(identity_file,identity)
    bank=[r for r in plan['records'] if not (out/(r['id']+'.npz')).exists()]
    for start in range(0,len(bank),batch):
        check();chunk=bank[start:start+batch];rows=[encoded[r['id']]['ids'] for r in chunk]
        _,bridge=forward(target,rows,[encoded[r['id']]['bridge'] for r in chunk],D.LAYERS)
        _,answer=forward(target,rows,[len(x)-1 for x in rows],(24,28,42,44))
        for i,r in enumerate(chunk):
            arrays={f'L{L}_bridge':bridge[L][i] for L in D.LAYERS}
            arrays['provenance_json']=np.array(json.dumps(meta or D.provenance()))
            arrays.update({f'L{L}_answer':answer[L][i] for L in (24,28,42,44)})
            tmp=out/(r['id']+'.partial.npz');np.savez(tmp,**arrays);tmp.replace(out/(r['id']+'.npz'))
        print(json.dumps({'phase':'natural_capture','completed':start+len(chunk),'new_total':len(bank)}),flush=True)
    D.save(out/'encoded.json',encoded)
    D.save(out/'checksums.json',{p.name:D.sha(p) for p in sorted(out.glob('*.npz'))})
    return load_states(out,plan),encoded


def pilot_caliper_audit(plan,states,out,meta):
    frozen={}
    for layer in D.LAYERS:
        pairs,excluded=D.freeze_pairs(plan,states,layer,'pilot')
        frozen[str(layer)]={'pairs':pairs,'excluded':excluded}
    counts={layer:len(value['pairs']) for layer,value in frozen.items()}
    result={'counts':counts,'caliper':0.05,'uses_answer_outcomes':False,'layers':frozen,**meta}
    D.save(Path(out)/'pilot_caliper_audit.json',result)
    if any(n!=len(plan['pilot_ids']) for n in counts.values()):
        D.save(Path(out)/'pilot_shortfall.json',result)
        raise ValueError('Fewer than 20 norm-matched pool pilot pairs; stop without relaxing the 5% caliper: '+str(counts))
    return result


def load_states(path,plan):
    path=Path(path);checks=D.read(path/'checksums.json');states={}
    for r in plan['records']:
        p=path/(r['id']+'.npz')
        if D.sha(p)!=checks[p.name]:raise ValueError('Natural state checksum mismatch')
        with np.load(p,allow_pickle=False) as data:
            states[r['id']]={L:{pos:data[f'L{L}_{pos}'] for pos in ('bridge','answer') if f'L{L}_{pos}' in data} for L in (24,28,42,44)}
    return states


def write_rows(path,rows):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a') as f:
        for row in rows:f.write(json.dumps({**D.provenance(),**row},allow_nan=False)+'\n')


def load_rows(path):
    return [json.loads(s) for s in Path(path).read_text().splitlines() if s.strip()] if Path(path).exists() else []


def pair_meta(p,bank,split):
    rec=bank[p['recipient']];don=bank[p['donor']]
    return {'recipient':rec['id'],'donor':don['id'],'split':split,'layer':p['layer'],'bridge':rec['bridge'],
            'donor_bridge':don['bridge'],'answer':rec['answer'],'donor_answer':don['answer'],'template':rec['template'],
            'norm_a':p['norm'],'norm_c':p['answer_norm'],'random_bridge_donor':p['random_bridge']['donor'],
            'random_answer_donor':p['random_answer']['donor']}


def measure(target,plan,states,encoded,pairs,out,split,check,meta,batch=8):
    """Every arm writes one model row plus matching downstream state file per recipient/layer."""
    from projects.g_agreement.core import scoring_lo as LO
    meta={**D.provenance(),**meta}
    out=Path(out);out.mkdir(parents=True,exist_ok=True);bank={r['id']:r for r in plan['records']}
    # Freeze batch geometry and exact pair order, so changing a resume's chunking cannot skip recipients.
    identity={'plan_sha256':D.digest(plan),'code_sha':meta['code_sha'],'pairs_sha256':D.digest(pairs),'batch':batch,'split':split}
    identity_path=out/'measure_identity.json'
    if identity_path.exists() and D.read(identity_path)!=identity:raise ValueError('Measurement resume geometry changed')
    D.save(identity_path,identity)
    # Atomic per-batch bundles are the resume unit. Consolidation only after a complete sweep.
    for L in D.LAYERS:
      means=D.class_means(plan,states,L);pair_list=[p for p in pairs if p['layer']==L]
      for arm in D.ARMS:
       for start in range(0,len(pair_list),batch):
        check();chunk=pair_list[start:start+batch];bid=f'L{L}_{arm}_{start:05d}';folder=out/bid
        if (folder/'complete.json').exists():
            cert=D.read(folder/'complete.json')
            if cert.get('plan_sha256')!=D.digest(plan) or cert.get('code_sha')!=meta['code_sha']:raise ValueError('Resume identity changed')
            for name,h in cert['files'].items():
                if D.sha(folder/name)!=h:raise ValueError('Resume checksum mismatch')
            continue
        rows=[];heads=[];positions=[];values=[];kept=[];unavailable=[]
        for p in chunk:
            iid=p['recipient'];don=p['donor'];e=encoded[iid];site='answer' if arm in ('answer_patch','random_answer') else 'bridge'
            if arm=='class_mean':
                if bank[iid]['bridge'] not in means or bank[don]['bridge'] not in means:
                    unavailable.append({**pair_meta(p,bank,split),'arm':arm,'status':'UNAVAILABLE_CLASS_MEAN_SUPPORT',**meta});continue
                v=D.added_direction(p,bank,means)
            elif arm=='natural':v=None
            else:
                did=p[arm]['donor'] if arm.startswith('random_') else don
                v=states[did][L][site]
            for answer in (bank[iid]['answer'],bank[don]['answer']):
                tail=LO.encode(target.tokenizer,answer)
                if not tail:raise ValueError('Empty answer encoding')
                rows.append(e['ids']+tail);heads.append(len(e['ids']));positions.append(e[site]);values.append(v)
            kept.append((p,site,v))
        folder.mkdir(parents=True,exist_ok=True);output=list(unavailable)
        if kept:
            read_layers=[s for s in (28,42,44) if s>L]
            lps,readback=forward(target,rows,[h-1 for h in heads],read_layers,patch_layer=L,patch_positions=positions,
                                values=None if arm=='natural' else np.stack(values),mode='add' if arm=='class_mean' else 'replace',heads=heads)
            arrays={}
            for i,(p,site,v) in enumerate(kept):
                rec=p['recipient'];norm=0. if v is None else float(np.linalg.norm(v if arm=='class_mean' else v-states[rec][L][site]))
                for s in read_layers:
                    a,b=readback[s][2*i:2*i+2]
                    if not np.allclose(a,b,rtol=2e-3,atol=2e-3):raise RuntimeError('Candidate-dependent pre-answer readback')
                    arrays[f'{rec}_L{s}']=a.astype(np.float32)
                output.append({**pair_meta(p,bank,split),'arm':arm,'status':'OK','lo':lps[2*i]-lps[2*i+1],
                               'lp_original':lps[2*i],'lp_donor':lps[2*i+1],'delta_norm':norm,'patch_position':encoded[rec][site],
                               'read_position':encoded[rec]['answer'],'read_layers':read_layers,**meta})
            np.savez(folder/'states.npz',**arrays)
        D.save(folder/'rows.json',output)
        D.save(folder/'complete.json',{'plan_sha256':D.digest(plan),**meta,'files':{p.name:D.sha(p) for p in folder.iterdir() if p.name in ('rows.json','states.npz')}})
        print(json.dumps({'phase':split,'bundle':bid,'rows':len(output),'available':len(kept)}),flush=True)
    result=[]
    for folder in sorted(out.iterdir()):
        if folder.is_dir() and (folder/'complete.json').exists():
            result.extend({**r,'state_file':str((folder/'states.npz').relative_to(out))} for r in D.read(folder/'rows.json'))
    D.save(out/'model_rows.json',result);return result


def assert_model_coverage(rows):
    expected={(L,a) for L in D.LAYERS for a in D.ARMS}
    got={(r['layer'],r['arm']) for r in rows if r['status']=='OK'}
    if got-expected:raise ValueError('SMOKE FAILED: unexpected model cells '+repr(sorted(got-expected)))
    missing=expected-got
    if missing:raise ValueError('SMOKE FAILED: missing model cells '+repr(sorted(missing)))


def verify_measurement(root):
    root=Path(root);certs=sorted(root.glob('*/complete.json'));expected=[]
    if not certs:raise ValueError('No complete read-back bundles')
    for certpath in certs:
        cert=D.read(certpath)
        for name,h in cert['files'].items():
            if D.sha(certpath.parent/name)!=h:raise ValueError('Read-back bundle checksum mismatch: '+str(certpath.parent/name))
        expected.extend({**r,'state_file':str((certpath.parent/'states.npz').relative_to(root))} for r in D.read(certpath.parent/'rows.json'))
    if D.read(root/'model_rows.json')!=expected:raise ValueError('Consolidated model rows differ from bundles')


def assert_reader_completion(model_rows,reader_rows):
    expected={(r['recipient'],r['layer'],r['arm'],reader,site) for r in model_rows if r['status']=='OK'
              for reader,sites in D.READERS.items() for site in sites if site>r['layer']}
    got=[(r['recipient'],r['layer'],r['arm'],r['reader'],r['read_layer']) for r in reader_rows]
    if len(got)!=len(set(got)) or set(got)!=expected:raise ValueError('Reader output has missing/duplicate/orphan item cells: '+repr({'missing':sorted(expected-set(got)),'extra':sorted(set(got)-expected),'duplicates':[k for k in set(got) if got.count(k)>1]}))
    D.assert_coverage(reader_rows)
    return {'complete_item_cells':len(got)}


def score_reader(reader,plan,model_rows,root,output,check,meta,batch=16):
    import torch
    from projects.g_agreement.core import scoring_lo as LO
    verify_measurement(root)
    LO.NLA_TEMPLATES['x1_bridge']=['The country is {X}.']
    bank={r['id']:r for r in plan['records']};old=load_rows(output);done={(r['recipient'],r['layer'],r['arm'],r['reader'],r['read_layer']) for r in old}
    for site in D.READERS[reader.name]:
        todo=[r for r in model_rows if r['status']=='OK' and site>r['layer'] and (r['recipient'],r['layer'],r['arm'],reader.name,site) not in done]
        for start in range(0,len(todo),batch):
            check();chunk=todo[start:start+batch];xs=[];pairs=[]
            for r in chunk:
                with np.load(Path(root)/r['state_file'],allow_pickle=False) as blob:xs.append(blob[f"{r['recipient']}_L{site}"])
                a,b=bank[r['recipient']],bank[r['donor']]
                pairs.append((a['bridge_jlens'] or a['bridge'],b['bridge_jlens'] or b['bridge']) if reader.name=='jlens' else (a['bridge'],b['bridge']))
            scored=LO.score_lo(reader,torch.from_numpy(np.stack(xs)),pairs,'x1_bridge',layer=site,batch=batch)
            records=[]
            for row,res in zip(chunk,scored):
                value=res.get('lo');ok=value is not None and np.isfinite(value) and not res.get('unscorable')
                records.append({**row,**meta,'reader':reader.name,'read_layer':site,'status':'OK' if ok else 'UNSCORABLE',
                                'model_lo':row['lo'],'model_provenance':{k:row.get(k) for k in ('pod','git_sha','code_sha','code_sha256','run_id','run_kind')},'lo':float(value) if ok else None,'candidate_original':res['cand_A'],'candidate_donor':res['cand_B']})
            write_rows(output,records)
            print(json.dumps({'phase':'readers','reader':reader.name,'site':site,'new_rows':len(records)}),flush=True)


def zero_patch_precheck(target,states,encoded,pairs,plan,check,out,meta=None):
    from projects.g_agreement.core import scoring_lo as LO
    bank={r['id']:r for r in plan['records']};results=[]
    for pair in pairs:
        check();iid=pair['recipient'];L=pair['layer'];ids=encoded[iid]['ids']
        rows=[ids+LO.encode(target.tokenizer,a) for a in (bank[iid]['answer'],bank[pair['donor']]['answer'])]
        heads=[len(ids)]*2
        baseline,base_states=forward(target,rows,[len(ids)-1]*2,[42,44],heads=heads)
        for site in ('bridge','answer'):
            patched,h=forward(target,rows,[len(ids)-1]*2,[42,44],patch_layer=L,
                patch_positions=[encoded[iid][site]]*2,values=np.stack([states[iid][L][site]]*2),heads=heads)
            lo_error=abs((baseline[0]-baseline[1])-(patched[0]-patched[1]))
            max_relative=max(float(np.linalg.norm(h[s]-base_states[s])/max(1e-9,np.linalg.norm(base_states[s]))) for s in h)
            results.append({**(meta or D.provenance()),'recipient':iid,'layer':L,'site':site,'lo_error':lo_error,'state_relative_error':max_relative})
            if lo_error>.1 or max_relative>.01:raise ValueError('SMOKE FAILED: natural self-patch does not reproduce unpatched pass')
    D.save(out,{'status':'PASS','rows':results})


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=['capture','pilot','target','readers','nla','smoke'],required=True)
    parser.add_argument('--run-dir',type=Path,required=True);parser.add_argument('--pod',required=True)
    parser.add_argument('--plan',type=Path,default=D.OUT/'pilot_plan.json');parser.add_argument('--batch',type=int,default=8)
    args=parser.parse_args()
    D.RUN_KIND='smoke' if args.phase=='smoke' else 'real'
    plan=D.read(args.plan)
    (args.run_dir/'runtime_cache').mkdir(parents=True,exist_ok=True)
    import tempfile
    tempfile.tempdir=str(args.run_dir/'runtime_cache')
    with D.write_guard(D.output_paths(args.run_dir/D.DATA_REL,plan,args.batch),roots=[args.run_dir/'runtime_cache']):
        execute(args)


def execute(args):
    from projects.g_agreement.r_bench import remainder_x1_launch as G
    check=G.live_check(args.pod,args.run_dir);check();plan=D.read(args.plan);G.check_registration(args.run_dir,plan)
    if D.sha(D.ROOT/plan['bank'])!=plan['bank_sha256']:raise ValueError('Frozen bank changed')
    os.environ['HF_HUB_OFFLINE']='1';os.environ['TRANSFORMERS_OFFLINE']='1'
    root=args.run_dir/D.DATA_REL;root.mkdir(parents=True,exist_ok=True);meta={**D.provenance(args.pod),'plan_sha256':D.digest(plan)}
    if args.phase=='nla':
        from projects.g_agreement.core import readers as R
        reader=R.NLAReader().bind()
        for split in ('smoke','test'):
            path=root/split
            if (path/'model_rows.json').exists():
                model_rows=D.read(path/'model_rows.json')
                score_reader(reader,plan,model_rows,path,path/'reader_rows.jsonl',check,{**meta,'run_kind':'smoke' if split=='smoke' else 'real'},args.batch)
                assert_reader_completion(model_rows,load_rows(path/'reader_rows.jsonl'))
        return
    if args.phase in ('pilot','target'):
        assert_reader_completion(D.read(root/'smoke/model_rows.json'),load_rows(root/'smoke/reader_rows.jsonl'))
    if args.phase=='target':G.check_layer_release(args.run_dir,root/'layer_decision.json')
    from projects.g_agreement.r_bench.remainder_joint import warm_environment
    warm_environment()
    from projects.g_agreement.core import model as M
    started=time.time();target=M.load_target()
    write_rows(root/'model_load.jsonl',[{**meta,'phase':args.phase,'wall_seconds':time.time()-started}])
    if args.phase=='capture':
        states,_=natural_capture(target,plan,root/'natural',check,args.batch,meta)
        pilot_caliper_audit(plan,states,root,meta)
        return
    states=load_states(root/'natural',plan);encoded=D.read(root/'natural/encoded.json')
    frozen={};all_pairs=[]
    for L in D.LAYERS:
        split='pilot' if args.phase in ('pilot','smoke') else 'test'
        pairs,excluded=D.freeze_pairs(plan,states,L,split);all_pairs.extend(pairs);frozen[L]={'pairs':pairs,'excluded':excluded}
    if args.phase=='pilot':
        if any(len(v['pairs'])!=20 for v in frozen.values()):
            D.save(root/'pilot_shortfall.json',{'counts':{L:len(v['pairs']) for L,v in frozen.items()},'excluded':frozen,**meta})
            raise ValueError('Fewer than 20 norm-matched pool pilot pairs; no layer choice/test run')
        rows=measure(target,plan,states,encoded,all_pairs,root/'pilot','pilot',check,meta,args.batch)
        joined={(r['recipient'],r['layer'],r['arm']):r for r in rows if r['status']=='OK'}
        pilot=[{'recipient':p['recipient'],'split':'pilot','layer':p['layer'],
                'natural_lo':joined[p['recipient'],p['layer'],'natural']['lo'],
                'patched_lo':joined[p['recipient'],p['layer'],'bridge_patch']['lo']} for p in all_pairs]
        counts={L:len(D.freeze_pairs(plan,states,L,'test')[0]) for L in D.LAYERS}
        D.save(root/'layer_decision.json',{**D.select_layer(pilot,counts),'pilot_rows':pilot,'test_eligible_counts':counts,**meta})
        return
    if args.phase in ('target','smoke'):
        if args.phase=='target':
            G.check_layer_release(args.run_dir,root/'layer_decision.json')
            smoke=load_rows(root/'smoke/reader_rows.jsonl');D.assert_coverage(smoke)
        else:
            # Choose only pool pairs. Require a class-mean-supported pair at each layer.
            selected=[]
            for L in D.LAYERS:
                pp=[p for p in all_pairs if p['layer']==L];bank={r['id']:r for r in plan['records']};means=D.class_means(plan,states,L)
                supported=[p for p in pp if bank[p['recipient']]['bridge'] in means and bank[p['donor']]['bridge'] in means]
                if not supported:raise ValueError('SMOKE FAILED: no supported pool class-mean pair')
                selected.extend(supported[:2])
            all_pairs=selected
            zero_patch_precheck(target,states,encoded,selected,plan,check,root/'self_patch_precheck.json',meta)
        D.save(root/(args.phase+'_pairs.json'),{'layers':frozen,**meta})
        rows=measure(target,plan,states,encoded,all_pairs,root/('test' if args.phase=='target' else 'smoke'),args.phase,check,meta,args.batch)
        assert_model_coverage(rows)
        return
    if args.phase=='readers':
        from projects.g_agreement.core import readers as R
        # Mount Oracle before skip; J explicitly bound at both downstream sites.
        readers=[R.JLensReader().bind(target,layers_keep=[28,42]),R.OLensReader().bind(target),R.SKIPLENS_READERS['skip_a']().bind(target)]
        for split in ('smoke','test'):
            path=root/split
            if (path/'model_rows.json').exists():
                for reader in readers:score_reader(reader,plan,D.read(path/'model_rows.json'),path,path/'reader_rows.jsonl',check,{**meta,'run_kind':'smoke' if split=='smoke' else 'real'},args.batch)

if __name__=='__main__':main()
