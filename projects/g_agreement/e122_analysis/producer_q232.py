"""Exact TrackQ worker122/E105 envelope binding, input metadata only.

No raw numerical job is read while building the index. The original E105 batch
recipe yields sealed member/record pointers directly from frozen public inputs.
"""
import argparse,hashlib,json
from pathlib import Path
from . import adapter as a

INPUT_SHA='3308228f0455c4b11e0c8ae9d52446172c86323f7b3aaa2d621ff0071f516089'
JOIN_SHA='80e9422c67f1a3c3a673c0b8751509c287b479b43aa1283721529c5249105439'
OUTPUT_SHA='d5d7f3700722d2699e6462463a94a847a6ec02467cd23e6f0d90fd6ca20fe4d6'
CAPTURE_SHA='d77cfa74a8bbc4a2787522e9f72d2594646f771a7f12dc437eddd18283a2a543'


def oid(*keys):return hashlib.sha256(json.dumps(['E122',*keys]).encode()).hexdigest()[:24]


def context(entry,output,frozen,cells,defs):
    a.require(entry['sha256']==OUTPUT_SHA and output['experiment']=='E122' and output['status']=='COMPLETE'
              and output['input_seals']=={'e122':INPUT_SHA} and output['evaluations']==1000,'exact completed TrackQ acquisition')
    ip=Path(entry['producer_input_seal']);inp=a.core.verify(ip,INPUT_SHA)
    jp=Path(entry['producer_join_seal']);join=a.core.verify(jp,JOIN_SHA)
    a.require(join['experiment']=='E122' and join['input_seal_sha256']==INPUT_SHA,'original CPU join/input binding')
    sources=join['sources']
    a.require(sources['contrasts_seal']==a.CONTRAST_SHA and sources['e85_labels']==a.E85_PRIVATE_SHA
              and sources['e85_capture_stage_seal']==CAPTURE_SHA and sources['donor_seed']==20261030,'original source lineage')
    a.require(inp['experiment']=='E122' and inp['labels_on_pod'] is False and inp['block']==44
              and inp['contrasts_seal_sha256']==a.CONTRAST_SHA and inp['candidate_order']=='[positive, negative]'
              and inp['contrast_order']==[x['id']for x in defs]
              and inp['parts']=={'a_unpatched':600,'b_T':200,'b_S':200},'original full candidate/source grid')
    items=a.read(ip.parent/'items.json');by=a.core.unique(items)
    records=a.read(jp.parent/'JOIN.PRIVATE.json');a.require(records['sources']==sources,'private source lineage')
    joins=a.core.unique(records['records']);a.require(set(by)==set(joins) and len(by)==1000,'exact public/CPU grid')
    original={x['id']:x for x in cells};donors={x['id']:x for x in a.read(frozen.parent/'S_PAIRINGS.json')};mapping={}
    candidates=[x['candidate_ids'][0] for x in defs]
    for key,x in by.items():
        j=joins[key];cond=x['condition'];carrier=j['public_id'] if j['part']=='a' else j['recipient_public_id']
        a.require(carrier in original and cond in ('0','T','S'),'original source carrier/condition')
        cell=original[carrier]
        a.require(x['base_id']==carrier and x['inventory_id']==oid('inv',carrier) and x['row']=='e122'
                  and x['block']==44 and x['read_index']==len(x['ids'])-1 and x['candidate_ids']==candidates,'frozen raw identity/prefix/token inputs')
        a.require(j['matched_set']==cell['quartet_id'] and j['genre']==cell['genre'] and j['split']==cell['split'],'original CPU quartet/genre/split')
        if cond=='0':
            a.require(j['part']=='a' and j['addressed']==cell['addressed'] and x['vector_index'] is None
                      and x['donor_id'] is None and key==oid(carrier,'0',None),'true unpatched native item')
        else:
            donor=donors[carrier][cond+'_donor_id']
            a.require(j['part']=='b' and j['condition']==cond and cell['split']=='test' and cell['addressed']==0
                      and j['donor_public_id']==donor and x['donor_id']==oid('donor',donor)
                      and key==oid(carrier,cond,donor) and type(x['vector_index'])is int,'original addressed twin/same-value donor')
        a.require((carrier,cond) not in mapping,'duplicate original measurement')
        mapping[carrier,cond]=x
    a.require(len(mapping)==1000,'full native and T/S mapping')
    return dict(mode='TrackQ',order=[x['id'] for x in defs],mapping=mapping,items=items)


def prepare(spec):
    frozen,cells,defs=a.frozen_inputs(spec)
    source=dict(seal=spec['raw_output_seal'],sha256=OUTPUT_SHA,format='trackq_e122_232',
                producer_input_seal=spec['producer_input_seal'],producer_join_seal=spec['producer_join_seal'])
    output=a.core.verify(source['seal'],OUTPUT_SHA);ctx=context(source,output,frozen,cells,defs)
    # Exact original worker122 plan: no job JSON/numerical arrays read here.
    from projects.g_agreement.e105.scoring import batches
    reverse={x['id']:k for k,x in ctx['mapping'].items()};native={};transplant={}
    for number,indices in enumerate(batches(ctx['items'])):
        member=f'jobs/{number:04d}_e122.json';a.require(member in output['files'],'original planned job member')
        for position,i in enumerate(indices):
            carrier,condition=reverse[ctx['items'][i]['id']]
            ref=dict(seal_index=0,member=member,keys=['records',position])
            if condition=='0':native[carrier]=ref
            else:transplant.setdefault(carrier,{})[condition]=ref
    a.require(len(native)==600 and len(transplant)==200 and all(set(x)=={'T','S'}for x in transplant.values()),'exact source-only index')
    out=a.CANONICAL/'trackq_index';out.mkdir(parents=True,exist_ok=False)
    a.write(out/'RAW_INDEX.json',dict(native=native,transplant=transplant))
    a.core.seal(out,'INDEX_SEAL.json',experiment='E122',status='SOURCE_POINTERS_ONLY',contrast_source_sha256=a.CONTRAST_SHA,source_e85_bank_sha256=a.E85_BANK_SHA,source_seals=[source])
    plan=dict(frozen_seal=str(frozen),frozen_sha256=spec['frozen_sha256'],raw_index_seal=str(out/'INDEX_SEAL.json'),raw_index_sha256=a.sha(out/'INDEX_SEAL.json'))
    a.write(a.CANONICAL/'PLAN.json',plan)
    return a.CANONICAL/'PLAN.json'


def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args()
    a.committed();print(prepare(a.read(args.spec)))

if __name__=='__main__':main()
