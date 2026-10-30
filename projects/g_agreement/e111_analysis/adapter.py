"""E111 source-bound CPU adapter; no input opening until committed-source check."""
import argparse,hashlib,subprocess
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
from .analysis import analyze,figure,EXPERIMENTS as ORIGINAL_EXPERIMENTS
EXPERIMENTS=ORIGINAL_EXPERIMENTS
E100_USER_EXCLUSION="E100a excluded: complete donor/control binding not sealed in time (E111 deviation 1 fallback)"
E100_EXCLUSION="E100a excluded: E105 flip seal or probe lineage missing at 12:45 CET"
E100_DEADLINE=datetime(2026,10,29,11,45,tzinfo=timezone.utc)
from . import contrast
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wmech/cache/g_agreement/understand/e111/ANALYSIS_ONCE.json')
DEADLINE=datetime(2026,10,29,23,tzinfo=timezone.utc)
REQ=core.require

def committed():
    for f,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/f)==h,'changed scientific dependency')
    for p in HERE.iterdir():
        if p.suffix in ('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
            REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted adapter')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def admission(included,e109_sealed,now,e100_inputs=None,exclude_e100_by_user=False):
    wanted=set(EXPERIMENTS) if e109_sealed else set(EXPERIMENTS)-{'E109_44'}
    if exclude_e100_by_user:
        REQ(exclude_e100_by_user is True,'explicit user exclusion')
        REQ(set(included)==wanted-{'E100_a'},'exact scope under user exclusion')
        REQ(e109_sealed or now>=DEADLINE,'wait E109 seal or Fri00 CET')
        return
    REQ(isinstance(e100_inputs,dict) and set(e100_inputs)=={'flip_seal_available','probe_lineage_available'} and all(type(v) is bool for v in e100_inputs.values()),'explicit E100 input dispositions')
    ready=all(e100_inputs.values())
    if not ready:
        REQ(now>=E100_DEADLINE,'wait E100 inputs or 12:45 CET')
        wanted.remove('E100_a')
    REQ(set(included)==wanted,'full registered experiment scope')
    REQ(e109_sealed or now>=DEADLINE,'wait E109 seal or Fri00 CET')

def vector(h,mode,p):
    h=np.asarray(h,float)
    REQ(h.ndim==1 and np.isfinite(h).all(),'finite natural44 vector')
    if mode=='natural':v=h
    elif mode in ('persisted','donor'):v=np.asarray(p['vector'],float)
    elif mode=='E101_reconstructed':
        u=np.asarray(p['unit'],float);alpha=p['alpha'];norm=p['raw_norm'];sigma=p['sigma']
        REQ(u.shape==h.shape and np.isfinite(u).all() and np.isclose(np.linalg.norm(u),1,atol=1e-6),'sealed unit direction')
        REQ(sigma in (-1,1) and np.isfinite([alpha,norm]).all() and alpha>0 and norm>0,'sealed E101 dose/norm/sign')
        # Matches original materialize.py float64 sum, then float32 storage.
        v=(h+alpha*norm*sigma*u).astype(np.float32).astype(float)
    else:raise ValueError('unknown source vector mode')
    REQ(v.shape==h.shape and np.isfinite(v).all(),'finite aligned vector')
    return v

def effective_weights(w,preprocessing,scale=None):
    w=np.asarray(w,float)
    REQ(w.ndim==1 and np.isfinite(w).all(),'finite raw probe coefficients')
    if preprocessing=='none':
        REQ(scale is None,'unscaled probe has no feature scale')
        return w
    REQ(preprocessing=='standardized','declared original probe preprocessing')
    sd=np.asarray(scale,float)
    REQ(sd.shape==w.shape and np.isfinite(sd).all() and np.all(sd>0),'original positive feature scales')
    return w/sd

def target_shift(h,hp,w,target):
    w=np.asarray(w,float);REQ(w.shape==h.shape and np.isfinite(w).all() and target in (0,1),'probe and target orientation')
    return float((2*target-1)*np.dot(w,hp-h))

def target_statement(code,letter,text,ident):
    if code is None:return None
    REQ(code['id']==ident,'sealed judgment identity')
    valid=core.score(code,letter,text)
    if valid is None:return None
    return int(code['category']=='states_value' and letter in code['values'])

def inputs(s,now=None):
    now=now or datetime.now(timezone.utc)
    ip=Path(s['inventory_seal']).resolve();ic=s['inventory_commit']
    REQ(len(ic)==40,'full inventory commit')
    blob=subprocess.check_output(['git','show',ic+':'+str(ip.relative_to(ROOT))],cwd=ROOT)
    REQ(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'frozen census commitment')
    inv=core.verify(ip,s['inventory_sha256']);REQ(inv['experiment']=='E111' and inv['scope']=='§224','registered inventory')
    REQ({'INVENTORY.json','PROBES.json'}<=set(inv['files']),'sealed census/probe plan')
    admission(inv['included_experiments'],s['e109_sealed'],now,s.get('e100_inputs'),s.get('exclude_e100_by_user',False))
    if s['e109_sealed']:
        e=core.verify(s['e109_seal'],s['e109_sha256']);REQ(e['experiment']=='E109' and e['status'] in ('COMPLETE','COMPLETE_ONCE'),'terminal E109 seal')
        REQ(inv['adapter_committed_before_e109_seal'] is True,'pre-E109 source ordering receipt')
    op=Path(s['binding_seal']);o=core.verify(op,s['binding_sha256'])
    REQ(o['experiment']=='E111' and o['status']=='COMPLETE' and o['inventory_sha256']==s['inventory_sha256'],'complete bound source normalization')
    REQ({'MEASUREMENTS.json','CONTRAST.json'}<=set(o['files']),'sealed regression and independent full shared contrast census')
    for k in ('source_census_complete','private_join_verified','route_verified','privacy_verified','labels_cpu_only'):
        REQ(o[k] is True,'source/privacy completeness')
    sources=o['source_seals'];seals=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(seals) and x['member'] in seals[i]['files'],'original sealed pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=np.load(p,allow_pickle=False) if p.suffix in ('.npy','.npz') else core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    meta=core.unique(core.read(ip.parent/'INVENTORY.json'));probes=core.read(ip.parent/'PROBES.json')
    REQ(set(x['experiment'] for x in meta.values())==set(inv['included_experiments']),'full experiment census')
    included={k:x for k,x in meta.items() if x['disposition']=='INCLUDED'}
    REQ(all(x['disposition'] in ('INCLUDED','VECTOR_UNAVAILABLE') for x in meta.values()),'only availability exclusions')
    REQ(all(x['reason'] for x in meta.values() if x['disposition']!='INCLUDED'),'exclusion reasons')
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json'));REQ(set(ms)==set(included),'exact available observation grid')
    weights={}
    for row,p in probes.items():
        REQ(p['block']==44 and p['fit_split']=='unhooked_dev' and p['test_used_for_fit'] is False and p['positive_class']==1,'dev-only block44 probe')
        REQ(p['origin']=='E109' if p['e109_probe_available'] else p['origin'] in ('E49','E56','E57','E59'),'registered probe priority')
        REQ(set(p['dev_ids']).isdisjoint({x['source_item_id'] for x in meta.values() if x['row']==row}),'no test fitting')
        REQ(p['recipe_sha256'] and p['labels_order_sha256'] and p['training_source_sha256'],'original fit lineage')
        weights[row]=effective_weights(ref(p['coefficients']),p['preprocessing'],ref(p['feature_scale']) if p['preprocessing']=='standardized' else None)
    rows=[]
    for ident,m in ms.items():
        x=included[ident];REQ(x['split']=='test' and x['reader']=='oracle' and x['block']==44,'only Oracle block44 test')
        REQ(x['paired_control_id'] in included and included[x['paired_control_id']]['cluster_id']==x['cluster_id'],'matched control in census and shared item cluster')
        h=np.asarray(ref(m['natural']),float);params={k:ref(v) for k,v in m['vector_parameters'].items()}
        hp=vector(h,x['vector_mode'],params)
        if x['experiment']=='E101':REQ(x['vector_mode'] in ('E101_reconstructed','natural'),'label reconstructed E101')
        if x['experiment']=='E100_a':REQ(x['vector_mode'] in ('donor','natural'),'E100a whole donor only')
        if x['experiment'] in ('E104_U','E109_44'):REQ(x['vector_mode'] in ('persisted','natural'),'persisted read44 only')
        target=ref(m['target_class']);letter=ref(m['target_letter']);flip=ref(m['behaviour_flip'])
        REQ(letter in ('A','B') and type(flip) in (bool,int) and flip in (0,1),'sealed target/behaviour')
        if x['experiment']=='E100_a' and x['vector_mode']=='natural':REQ(flip==0,'E105 condition0 control flip must be zero')
        rows.append(dict(id=ident,cluster_id=x['cluster_id'],experiment=x['experiment'],row=x['row'],
                         y=target_statement(ref(m['code']),letter,ref(m['text']),x['judgment_id']),
                         x1=target_shift(h,hp,weights[x['row']],target),x2=int(flip),reconstructed=x['vector_mode']=='E101_reconstructed'))
    direct=[]
    for x in core.read(op.parent/'CONTRAST.json'):
        REQ(x['row'] in contrast.ROWS and x['site_source_item_id']==x['carried_source_item_id']==x['item_id'],'exact shared source identity')
        scores={}
        REQ(ref(x['site_target_value'])==ref(x['carried_target_value']),'same target orientation across experiments')
        REQ(set(x['cells'])==set(contrast.CELLS),'full original four-cell contrast')
        for cell,z in x['cells'].items():
            REQ(z['experiment']==('E101' if cell.startswith('site_') else 'E104_U'),'original experiment')
            code=ref(z['code']);text=ref(z['text']);letter=ref(z['target_letter'])
            REQ(code is None or code['id']==z['judgment_id'],'contrast original judgment')
            scores[cell]=None if code is None else core.score(code,letter,text)
        site=ref(x['site_flip']);carried=ref(x['carried_flip'])
        REQ(type(site) in (bool,int) and site in (0,1) and type(carried) in (bool,int) and carried in (0,1),'source behaviour flips')
        direct.append(dict(row=x['row'],item_id=x['item_id'],site_flip=bool(site),carried_flip=bool(carried),scores=scores))
    census=dict(total=len(meta),included=len(included),vector_unavailable=len(meta)-len(included),
                excluded_E109=not s['e109_sealed'],excluded_experiments=({'E100_a':E100_USER_EXCLUSION if s.get('exclude_e100_by_user') else E100_EXCLUSION} if 'E100_a' not in inv['included_experiments'] else {}),reconstructed=sum(x['reconstructed'] for x in rows))
    return rows,census,direct

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);p.add_argument('--exclude-e100-by-user',action='store_true');a=p.parse_args();commit=committed();s=core.read(a.spec)
    if a.exclude_e100_by_user:
        s=dict(s,exclude_e100_by_user=True,original_spec_sha256=core.sha(a.spec))
    records,census,direct=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    direct_result=contrast.analyze(direct)
    result=analyze(records);result['census']=census;result['R_SL0']=direct_result
    if 'E100_a' in census['excluded_experiments']:result['R_SL2']['E100_a'].update(status='EXCLUDED',reason=census['excluded_experiments']['E100_a'])
    contrast.figure(direct_result,out/'SITE_VS_CARRIED.png')
    core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',s);figure(result,out/'BINS.png')
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E111',status='COMPLETE_ONCE',code_commit=commit,binding_sha256=s['binding_sha256'])
if __name__=='__main__':main()
