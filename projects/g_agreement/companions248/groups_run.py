"""Amendment1 parts1/2 once; source decoding only, never original analyses."""
import argparse,hashlib,json,subprocess
from pathlib import Path
from .run import source_check
from .amendment1 import groups
from projects.g_agreement.e127_analysis import transport as t,deviation1 as d
from projects.g_agreement.e127_analysis.common import state,require
from projects.g_agreement.e135_analysis import adapter as e135
from projects.g_agreement.e131_analysis import adapter as e131
E104_SEAL='ce564237b9951502478d26ab9c5bdcca3a8e3a7c90c0579660c76e4149cbf85b'
ROOT=Path(__file__).resolve().parents[3]
E135_SEAL='717df78053b3fa77342ded7166535fd8d3a878e7cba2e33fa5f78289cb6dc5f4'
E127_SEAL='3025b76adfd74ee194e62a69e3b57044eb92a99298b64232f47172e3fbf93f5c'
E131_SEAL='88f4252d7c45e9ffa93fd79c5bca1248dfec3e36dab7dd2003b86fcb122d5b9f'

def e131_crosswalk(path,ids):
    require(t.core.sha(path)=='f03acd297f0cca855167fea022a118199791062b8632afad7f0333d996e3f1f6','original W-text246 crosswalk')
    rows=t.core.read(path)['records'];by=t.core.unique(rows,'e131_base_id')
    require(len(by)==84 and {r['e104_item_id'] for r in rows}==ids and all(r['e104_item_id']==r['e127_original_base_id'] for r in rows),'exact original84 crosswalk')
    return {b:r['e104_item_id'] for b,r in by.items()}

def source_rows(spec):
    c=t.core
    for key,digest in [('e135',E135_SEAL),('e127',E127_SEAL),('e131',E131_SEAL)]:c.verify(spec[key+'_seal'],digest)
    s135=c.read(Path(spec['e135_seal']).parent/'BINDING.json')
    s127=c.read(Path(spec['e127_seal']).parent/'BINDING.json')
    s128=c.read(s135['e128_spec'])
    require(c.sha(s135['e128_spec'])==e135.SPEC_SHA,'original E128 SPEC')
    decoded={};originals={}
    for name,s in [('E127',s127),('E128',s128),('E135',s135)]:
        items,original,meta=t.cohort(s,name)
        fn=e135.inputs if name=='E135' else t.inputs
        decoded[name]=c.unique(fn(s,name,items,original,meta,pair_answer_fn=d.pair_answer),'item_id')
        originals[name]=original
    ids=set(decoded['E135']);require(len(ids)==84 and all(set(v)==ids for v in decoded.values()),'exact source census')
    fixed=e135.fixed_cohort(s135,ids)
    c.verify(spec['e104_judgment_seal'],E104_SEAL)
    codes104=c.unique(c.read(Path(spec['e104_judgment_seal']).parent/'JUDGMENTS.json'),'id')
    # Original E131 input binding supplies exact candidate orientation and identity.
    binding,bound,tok=e131.bind()
    crosswalk=e131_crosswalk(spec['e131_crosswalk'],ids)
    meta=c.verify(spec['e131_output_seal'],spec['e131_output_sha256'])
    require(meta['experiment']=='E131' and meta['status']=='COMPLETE','complete E131 source')
    am=c.read(spec['e131_seal']);require(am['output_sha256']==spec['e131_output_sha256'],'original E131 author output binding')
    root=Path(spec['e131_output_seal']).parent;index=c.read(root/'INDEX.json');cache={};margins={}
    require(len(index)==840 and len({z['id'] for z in index})==840,'complete E131 indexed grid')
    for entry in index:
        b=bound[entry['id']]
        if b['item']['condition']!='unhooked':continue
        member=entry['member'];require(member in meta['files'],'sealed E131 indexed member')
        if member not in cache:cache[member]=c.read(root/member)
        raw=cache[member][entry['record']]
        margin=e131.validate_record(raw,b['item'],tok)
        i=crosswalk[raw['base_id']]
        require(i not in margins,'one unhooked margin per original item')
        margins[i]=margin if b['a_value']=='old' else -margin
    require(set(margins)==ids,'exact E131 original84 mapping')
    rows=[]
    for i in sorted(ids):
        a,b,z=decoded['E127'][i],decoded['E128'][i],decoded['E135'][i]
        require(a['old_value']==b['old_value']==z['old_value'] and a['new_value']==b['new_value']==z['new_value'],'same source orientation')
        f={str(k):b['doses'][k]['steered']['pair_preference_flip_descriptive'] for k in (2,4,8)}
        f['6']=z['doses'][6]['steered']['pair_preference_flip_descriptive']
        require((f['4'] is True)==(i in fixed),'E135 fixed cohort agreement')
        lab=originals['E128']['random'][i];code=codes104[lab['opaque_id']];c.score(code,b['new_value'],lab['text'])
        rows.append(dict(id=i,flips=f,clean_old44=state(a['conditions']['no_prefix']['oracle'][44],a['old_value']),answer_margin=margins[i],
            random_old44_4=state(b['doses'][4]['random']['oracle'][44],b['old_value']),
            random_old44_6=None if z['doses'][6]['random']['oracle'][44] is None else state(z['doses'][6]['random']['oracle'][44],z['old_value']),
            random_old44_8=state(code,b['old_value'])))
    return rows

def main(specfile):
    source_check();s=t.core.read(specfile)
    require(ROOT.name=='wt-wmech2' and s['status']=='COMPLETE' and s['reviewer_source_delivered'] is True,'canonical complete binding and prospective delivery')
    guard=ROOT.parent/'wt-wmech/cache/g_agreement/understand/companions248/C_GROUPS_AMENDMENT1_ONCE.json'
    require(not guard.exists(),'parts1/2 consumed; reuse sealed output, never replay')
    out=Path(s['analysis']);require(not out.exists(),'fresh output required')
    rows=source_rows(s)  # custody validation before claim; no group quantities computed
    guard.parent.mkdir(parents=True,exist_ok=True)
    with guard.open('x') as f:json.dump(dict(spec_sha256=t.core.sha(specfile),source_receipt=t.core.sha(Path(__file__).with_name('SOURCE_RECEIPT.json'))),f)
    out.mkdir(parents=True)
    t.core.write(out/'ROWS.PRIVATE.json',rows);t.core.write(out/'BINDING.PRIVATE.json',s)
    t.core.write(out/'RESULTS.json',groups(rows))
    t.core.seal(out,'ANALYSIS_SEAL.json',section='248 C amendment1 parts1-2',status='COMPLETE_ONCE',new_calls=0)
    print(t.core.sha(out/'ANALYSIS_SEAL.json'))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);main(p.parse_args().spec)
