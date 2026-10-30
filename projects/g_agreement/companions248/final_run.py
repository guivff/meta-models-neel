"""Final §248 C amendment1: reuse sealed group phase; single original C guard."""
import argparse,json
from pathlib import Path
import numpy as np
from .run import source_check
from . import amendment1 as a,predictors
from .groups_run import E135_SEAL
from projects.g_agreement.e127_analysis import transport as t,deviation1 as d
from projects.g_agreement.e127_analysis.common import require,state
from projects.g_agreement.e128_addenda.adapter import category
from projects.g_agreement.e135_analysis import adapter as e135
ROOT=Path(__file__).resolve().parents[3]
GROUP_SHA='013fd87cfeb4cf355a058d1af20c1ac6e81f55771ed14f298ea201f331997691'
DELIVERY_SHA='5793698784276ac806f6908b370928db444e3c4df6be14feebdae14bc5166914'


def delivered(spec,expected):
    c=t.core;p=Path(spec['margin_delivery_seal']);m=c.verify(p,DELIVERY_SHA);root=p.parent
    require(m['experiment']=='E109' and m['n_items']==84 and m['block']==44 and m['new_fits']==0,'original E109 delivery')
    identity=c.read(root/'IDENTITIES.PRIVATE.json');ids=identity['item_ids']
    require(len(ids)==len(set(ids))==84 and set(ids)==set(expected),'exact84 margin IDs')
    plan=c.read(root/'SOURCE_BINDING.PRIVATE.json')['plan']
    for k in ('e133_analysis','inventory','binding','probe'):c.verify(plan[k+'_seal'],plan[k+'_sha256'])
    require(plan['e133_analysis_sha256']=='e6f12addf1bdb63fb02deafffe7b602835ec5efd02e326470a7aaf9b5fe752d0','E133 main dependency')
    bm=c.read(plan['binding_seal']);sources=bm['source_seals'];seals=[c.verify(z['seal'],z['sha256']) for z in sources]
    cap=seals[0];caproot=Path(sources[0]['seal']).parent
    probe=c.read(Path(plan['probe_seal']).parent/'PROBE_MANIFEST.json');require(probe['capture_seal_sha256']==sources[0]['sha256'],'same original capture/probe lineage')
    arrays={};margins={};rawmeta={};cache={}
    for cond in ('unhooked','steered'):
        arrays[cond]=np.load(root/(cond+'_vectors44.PRIVATE.npy'),allow_pickle=False)
        margins[cond]=np.load(root/(cond+'_old_fact_margins44.PRIVATE.npy'),allow_pickle=False)
        require(arrays[cond].shape==(84,5120) and arrays[cond].dtype==np.float32 and margins[cond].shape==(84,) and np.isfinite(arrays[cond]).all() and np.isfinite(margins[cond]).all(),'finite original arrays')
        refs=c.unique(identity['source_refs'][cond],'item_id');require(set(refs)==set(ids),'exact source pointer census')
        for j,i in enumerate(ids):
            require(identity['original_fact_letters'][j]==expected[i]['old_value'] and identity['steered_target_letters'][j]==expected[i]['new_value'],'original fact orientation')
            r=refs[i];v=r['vector'];md=r['metadata']
            for name in (v['member'],md['member']):require(name in cap['files'],'original sealed capture pointers')
            if v['member'] not in cache:cache[v['member']]=np.load(caproot/v['member'],allow_pickle=False)
            if md['member'] not in cache:cache[md['member']]=c.read(caproot/md['member'])
            raw=cache[md['member']][md['record_index']]
            require(raw['id']==r['native_id'] and raw['base_id']==i and raw['condition']==cond and raw['read_index']==r['read_index'],'native same-item/read-token pointer')
            require(raw['alpha']==8 if cond=='steered' else raw['hook_installed'] is False,'alpha8 or truly clean')
            require(np.array_equal(arrays[cond][j],cache[v['member']][v['vector_index']]),'bit-identical original read-token vector')
            rawmeta[i,cond]=raw
    return ids,arrays,margins,rawmeta


def vectors6(s135,ids,clean_meta):
    c=t.core;cm=c.verify(s135['calibration_seal'],s135['calibration_sha256']);sources=cm['source_seals']
    checked=[c.verify(z['seal'],z['sha256']) for z in sources]
    native=next(j for j,z in enumerate(checked) if 'CAPTURE_INDEX.json' in z['files'])
    pi=next(j for j,z in enumerate(checked) if 'ORIGINAL_POINTERS.PRIVATE.json' in z['files'])
    ai=next(j for j,z in enumerate(checked) if 'items.json' in z['files'])
    require(sources[ai]['sha256']=='381b58bde8ab7031e7a1de07bec1afe05655010a815e61a1a84c3b689c1c8047','original alpha6 input')
    root=Path(sources[native]['seal']).parent;meta=checked[native]
    pointers=c.unique(c.read(Path(sources[pi]['seal']).parent/'ORIGINAL_POINTERS.PRIVATE.json'),'id')
    items=c.unique(c.read(Path(sources[ai]['seal']).parent/'items.json'),'id')
    index=c.read(root/'CAPTURE_INDEX.json');captures={(x['id'],x['source_layer']):x for x in index}
    require(len(captures)==len(index),'no duplicate vector slots')
    result={};cache={}
    for key,x in items.items():
        if x['condition']!='steered':continue
        p=pointers[key];i=p['original_base_id'];require(i in ids and i not in result and p['scale']==6/8 and x['alpha']==6,'literal original alpha6 mapping')
        clean=clean_meta[i,'unhooked'];require(x['ids']==clean['ids'] and x['read_index']==clean['read_index'],'identical clean/capture prompt and read token')
        if (key,44) not in captures:result[i]=None;continue
        r=captures[key,44];require(r['member'] in meta['files'],'original capture member')
        if r['member'] not in cache:cache[r['member']]=np.load(root/r['member'],allow_pickle=False)
        v=cache[r['member']][r['vector_index']];require(v.shape==(5120,) and np.isfinite(v).all(),'finite original alpha6 read-token vector')
        result[i]=v
    require(set(result)==set(ids),'all original84 dispositions')
    return result


def inputs(spec):
    c=t.core;gp=Path(spec['group_seal']);c.verify(gp,GROUP_SHA)
    prior=c.unique(c.read(gp.parent/'ROWS.PRIVATE.json'),'id');gs=c.read(gp.parent/'BINDING.PRIVATE.json')
    c.verify(gs['e135_seal'],E135_SEAL);s135=c.read(Path(gs['e135_seal']).parent/'BINDING.json');s128=c.read(s135['e128_spec'])
    require(c.sha(s135['e128_spec'])==e135.SPEC_SHA,'original E128 source')
    data={}
    for name,s in [('E128',s128),('E135',s135)]:
        items,original,meta=t.cohort(s,name);fn=e135.inputs if name=='E135' else t.inputs
        data[name]=c.unique(fn(s,name,items,original,meta,pair_answer_fn=d.pair_answer),'item_id')
    require(set(data['E128'])==set(data['E135'])==set(prior),'original84 census')
    ids,arrays,margins,rawmeta=delivered(spec,data['E128']);six=vectors6(s135,ids,rawmeta)
    rows=[]
    for j,i in enumerate(ids):
        x=dict(prior[i]);codes={}
        for dose in (2,4,6,8):
            item=data['E135' if dose==6 else 'E128'][i];z=item['doses'][dose]['steered'];code=z['oracle'][44]
            f=z['pair_preference_flip_descriptive'];require(f==x['flips'][str(dose)],'same sealed group flags')
            cc=None if code is None or code['category']=='UNPARSEABLE' else category(code,item['old_value'],item['new_value'])
            c52=z['oracle'][52]
            codes[str(dose)]={'44':'neither' if cc=='neither_or_unparseable' else cc,'52_new':None if c52 is None or state(c52,item['new_value']) is None else bool(state(c52,item['new_value']))}
        x.update(codes=codes,unhooked_margin=x['answer_margin'],probe_unhooked=float(margins['unhooked'][j]),probe_alpha8=float(margins['steered'][j]),
            displacement8=a.displacement(arrays['unhooked'][j],arrays['steered'][j]),displacement6=a.displacement(arrays['unhooked'][j],six[i]))
        x['old44_alpha8']=None if codes['8']['44'] is None else int(codes['8']['44'] in ('old','dual'))
        rows.append(x)
    return sorted(rows,key=lambda x:x['id'])


def summarize(rows):
    original=predictors.analyze(rows);original.pop('PRIVATE_TABLE');original.pop('deck_phrase_eligible')
    geometry={}
    for f in ('displacement8','displacement6'):
        geometry[f]={g:a.mean_stat([r[f] for r in rows if a.group(r)==g]) for g in ('easy','resistant')}
        geometry[f]['difference']=a.difference(rows,f)
    return dict(section='248 C amendment1 final',status='COMPLETE_ONCE',original_registered=original,displacement_by_group=geometry,amendment_models=a.models(rows),group_result_seal=GROUP_SHA,group_results_recomputed=False,bank='old44 alpha8 models use E109 reference; group random8 uses original E104',new_calls=0)


def main(specfile):
    source_check();s=t.core.read(specfile);require(ROOT.name=='wt-wmech2' and s['status']=='COMPLETE' and s['reviewer_source_delivered'] is True,'canonical complete binding')
    # Immutable published RQ item-join receipt must be bound in the spec.
    import subprocess,hashlib
    content=subprocess.check_output(['git','show',s['review_commit']+':results/g_agreement/reviews/R-Q/HANDOFF.md'],cwd=ROOT)
    require(s['review_commit']=='55583c4b3' and hashlib.sha256(content).hexdigest()==s['review_file_sha256'],'original published RQ item-join review')
    guard=ROOT.parent/'wt-wmech/cache/g_agreement/understand/companions248/C_ONCE.json';require(not guard.exists(),'C guard consumed; never replay')
    out=Path(s['analysis']);require(not out.exists(),'fresh C output')
    rows=inputs(s)
    guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:json.dump(dict(spec_sha256=t.core.sha(specfile),source_receipt=t.core.sha(Path(__file__).with_name('SOURCE_RECEIPT.json'))),f)
    out.mkdir(parents=True);t.core.write(out/'TABLE.PRIVATE.json',rows);t.core.write(out/'BINDING.PRIVATE.json',s)
    t.core.write(out/'RESULTS.json',summarize(rows));t.core.seal(out,'ANALYSIS_SEAL.json',section='248 C amendment1 final',status='COMPLETE_ONCE',new_calls=0)
    print(t.core.sha(out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);main(p.parse_args().spec)
