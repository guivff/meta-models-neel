"""CPU E133 template/intake for W-mechanism-C sealed v3 packet 3213b0875.

Candidate preparation is not screening or a native-output seal. Actual judging
units require a COMPLETE main output and the explicit frozen selected item IDs.
"""
import argparse
from pathlib import Path
from .banks import opaque
from .e133_judge import RUBRIC_SHA, naming_call
from .runner import CACHE
from .transport import ROOT
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

LAYERS=(44,52,60)
OTHER='__OTHER_EXPLICITLY_NAMED_VALUE__'


def unique(rows,key):
    out={r[key]:r for r in rows};require(len(out)==len(rows),'unique original source identity');return out


def templates(arm,items,roles,pairs,names,places):
    role=unique(roles,'id');pair=unique(pairs,'pair_id')
    require({r['id']for r in items}==set(role)and len(items)==2*len(pairs),'whole original source candidate grid')
    out=[]
    for item in items:
        r=role[item['id']];p=pair[r['pair_id']];member=r['member']
        require(member in (0,1)and item['pair_id']==r['pair_id']and item['member']==member and item['family']==r['family'], 'literal original item/pair/member join')
        require(item['candidate_ids']==[[[v]for v in r['ascending_candidate_ids']]]and r['ascending_candidate_ids']==sorted(r['recipient_token_ids']), 'original ascending recipient tokens')
        current=r['recipient_strings'][r['current_recipient_index']]
        if arm=='synthetic':
            original=p['members'][member]
            require(original['id']==item['id']and original['current_holder']==current and p['previous_holder']==r['previous'],'original source roles unchanged')
            relation=p['relation'];pool=places if relation=='object_location'else names
            label={'object_holder':'holder of','object_location':'location of','token_owner':'owner of'}[relation]
        else:
            require(arm=='babi'and p['member_ids'][member]==item['id']and r['previous']==p['previous']and current==[p['original_current'],p['twin_current']][member],'original QA2 twin roles unchanged')
            pool=places;label='location of';relation='object_location'
        require(current in pool and r['previous']in pool and current!=r['previous'],'frozen source current/previous in complete literal value pool')
        values={chr(65+i):[v]for i,v in enumerate(pool)};value_map={k:v[0]for k,v in values.items()};value_map['OTHER']=OTHER
        out.append(dict(item_id=item['id'],pair_id=r['pair_id'],member=member,family=r['family'],arm=arm,
            property=label+' the '+p['object'],values=values,value_map=value_map,current=current,previous=r['previous'],
            relation=relation,original_pair_order=r['original_pair_order']))
    return out


def native_units(template_rows,index,read_member,selected_ids):
    by=unique(template_rows,'item_id');selected=set(selected_ids)
    require(len(selected)==len(selected_ids)and selected<=set(by),'explicit frozen selected original IDs')
    require(all({x['item_id']for x in template_rows if x['pair_id']==by[i]['pair_id']}<=selected for i in selected),'both original pair members selected')
    rows=[r for r in index if r.get('kind')=='oracle'];seen=set();units=[];pointers=[]
    for r in rows:
        require(r['id']in selected and r['block']in LAYERS and r['member'].startswith('oracle/'),'original native INDEX Oracle identity')
        key=r['id'],r['block'];require(key not in seen,'one original Oracle cell per item/block');seen.add(key)
        source=read_member(r['member']);require(type(r['record'])is int and 0<=r['record']<len(source),'literal native member/index')
        raw=source[r['record']];require(type(raw.get('text'))is str,'missing native text is not synthesized empty/zero')
        t=by[r['id']];uid=opaque('E133',t['arm'],r['id'],str(r['block']))
        data=dict(id=uid,property=t['property'],values=t['values'],readout=raw['text']);naming_call(data)
        units.append(dict(id=uid,kind='e133_naming',data=data))
        pointers.append(dict(id=uid,item_id=r['id'],pair_id=t['pair_id'],member=t['member'],family=t['family'],arm=t['arm'],block=r['block'],value_map=t['value_map'],current=t['current'],previous=t['previous'],native_member=r['member'],native_keys=[r['record'],'text']))
    require(seen=={(i,l)for i in selected for l in LAYERS},'complete selected Oracle grid; no partial stitching/refill')
    return units,pointers


def prepare_candidates():
    receipt=ROOT/'results/g_agreement/understand/e133/ADAPTED_SCREEN_INPUTS.json';meta=read(receipt)
    main=ROOT.parent/'wt-wtext/results/g_agreement/understand/e133/cache/bank_2026-10-30_v1'
    require(sha(main/'PAIRS.PRIVATE.json')=='ca87f20e749011d458b9a0c4b213ab9fece7c340cd8a4c2271352212a4315dc2','original W-text frozen main pair source')
    manifest=read(ROOT/'results/g_agreement/understand/e133/BANK_MANIFEST.json')
    babi=ROOT.parent/'outputs/e133-babi-v1/packet/cpu_only';verify(babi/'LABEL_SEAL.json','9364a8644a4222e769043cd217c0f67f14ff1cc349401cbc70c816289f89d390')
    source=read(ROOT/'results/g_agreement/understand/e133/DELIVERY.json')
    require(source['source_sha256']=='ea13b7b11a6ad3a5cf5438a663adcc3eb5289fbe737736bcca24778062aee130'and sha(source['source_archive'])=='cc199f384bfb6a8593ca4718e689baeccfd48f5dca9237c706f1bf6c553c5301','actual sealed3213b0875 v3 source archive')
    all_rows=[];bindings={str(receipt):sha(receipt)}
    for arm,expected,role_hash in [('synthetic','d610761951d1739292450199acbac9a4267bc38a60e846c094a449231146272f','9f1fb864d1f9e574e65b869cb1acf85e904e9623de36cfd6a7bdd0b542ce55eb'),('babi','0d2bd3968b0f4eb6981d960d3054ebc87d2e2ae52e150395d82a894ec56e2ec1','d95c5e0bf19806ed82f4c8d06db34a0936cf1c947f0aedf1967ac47cb8ea2501')]:
        m=meta[arm];inp=Path(m['public_root']);cpu=Path(m['CPU_only_root']);verify(inp/'INPUT_SEAL.json',expected);verify(cpu/'ROLE_SEAL.json',role_hash)
        require(read(cpu/'ROLE_SEAL.json')['input_sha256']==expected,'original input/CPU role binding')
        items=read(inp/'items.json');roles=read(cpu/'ROLES.PRIVATE.json')
        pairs=read(main/'PAIRS.PRIVATE.json')['pairs']if arm=='synthetic'else read(babi/'LABELS.PRIVATE.json')
        pool=manifest['places']if arm=='synthetic'else sorted({s for r in roles for s in r['recipient_strings']+[r['previous']]})
        require(len(items)==(900 if arm=='synthetic'else 988)and len(pool)==(5 if arm=='synthetic'else 6),'complete actual candidate packets/frozen value pools')
        rows=templates(arm,items,roles,pairs,manifest['names'],pool);all_rows.extend(rows)
        for p in [inp/'INPUT_SEAL.json',cpu/'ROLE_SEAL.json',cpu/'ROLES.PRIVATE.json']:
            bindings[str(p)]=sha(p)
    for p in [main/'PAIRS.PRIVATE.json',babi/'LABEL_SEAL.json',babi/'LABELS.PRIVATE.json',ROOT/'results/g_agreement/understand/e133/BANK_MANIFEST.json']:
        bindings[str(p)]=sha(p)
    dest=CACHE/'E133/candidate_judge_templates';dest.mkdir(parents=True,exist_ok=True,mode=0o700)
    if(dest/'SOURCE_SEAL.json').exists():
        verify(dest/'SOURCE_SEAL.json',sha(dest/'SOURCE_SEAL.json'));require(read(dest/'TEMPLATES.PRIVATE.json')==all_rows,'immutable candidate templates');return dest
    write(dest/'TEMPLATES.PRIVATE.json',all_rows);(dest/'TEMPLATES.PRIVATE.json').chmod(0o600)
    write(dest/'SOURCE_BINDINGS.PRIVATE.json',bindings);(dest/'SOURCE_BINDINGS.PRIVATE.json').chmod(0o600)
    write(dest/'SOURCE_SEAL.json',dict(experiment='E133',status='CANDIDATE_SOURCE_ONLY_NOT_SCREENED_OR_JUDGED',candidate_templates=1888,main_templates=900,babi_templates=988,rubric_sha256=RUBRIC_SHA,screen_or_native_output_opened=False,allocation_created=False,files={n:sha(dest/n)for n in ('TEMPLATES.PRIVATE.json','SOURCE_BINDINGS.PRIVATE.json')}))
    return dest


def prepare_complete(spec):
    """Owner supplies literal COMPLETE output/main-input/screened-ID bindings."""
    from .e133_channel import source_gate,worker
    from . import registered
    from ..privacy79 import redact
    source_gate();template_root=prepare_candidates();all_templates=read(template_root/'TEMPLATES.PRIVATE.json')
    native=Path(spec['native_seal']);ns=verify(native,spec['native_sha256']);inp=Path(spec['main_input_seal']);ins=verify(inp,spec['main_input_sha256']);selection=Path(spec['screened_inventory_seal']);ss=verify(selection,spec['screened_inventory_sha256'])
    require(spec['arm']in ('synthetic','babi')and ns['experiment']=='E133'and ns['status']=='COMPLETE'and ns['stage']=='main'and ns['arm']==spec['arm'],'complete original main output, never screening/NOFIT')
    require(ins['experiment']=='E133'and ins['stage']=='main'and ins['arm']==spec['arm']and ins['labels_on_pod']is False,'same original staged main input')
    require(ss['experiment']=='E133'and ss['status']=='SCREENED_COHORT_FROZEN'and ss['labels_cpu_only']is True and ss['main_input_sha256']==spec['main_input_sha256'],'frozen screened cohort binds exact staged input')
    selected=[r['id']for r in read(inp.parent/'items.json')];require('SELECTED_ITEM_IDS.PRIVATE.json'in ss['files']and set(selected)==set(read(selection.parent/'SELECTED_ITEM_IDS.PRIVATE.json')),'literal owner selected-ID crosswalk')
    rows=[r for r in all_templates if r['arm']==spec['arm']];by=unique(rows,'item_id');require(len(selected)==len(set(selected))and set(selected)<=set(by),'original selected source IDs only')
    from collections import Counter
    count=Counter(by[i]['family']for i in selected);limits={'multi_hop':168,'one_hop':84,'babi':84};require(all(n<=limits[k]for k,n in count.items()),'original registered selected pair maxima')
    units,pointers=native_units(rows,read(native.parent/'INDEX.json'),lambda m:read(native.parent/m),selected)
    copied,audit=redact([u['data']for u in units],'E133',addresses=True);changed={r['id']:r for r in copied};affected={r['id']for r in audit['affected']};original={u['id']:u['data']['readout']for u in units if u['id']in affected};units=[dict(u,data=changed[u['id']])for u in units]
    d=CACHE/'E133'/(spec['arm']+'_units');d.mkdir(exist_ok=True,mode=0o700)
    sources=[dict(seal=str(p),sha256=sha(p))for p in (native,inp,selection,template_root/'SOURCE_SEAL.json')]
    custody=dict(issuer='W-internals-C',experiment='E133',verified=True,complete_eligible_native_grid=True,labels_cpu_only=True,arm=spec['arm'],rubric_sha256=RUBRIC_SHA,selected_items=len(selected),native_status='COMPLETE',screened_cohort_bound=True,source_seals=sources)
    payloads={'UNITS.json':units,'SOURCE_POINTERS.PRIVATE.json':pointers,'PATH_REDACTION_AUDIT.json':audit,'ORIGINAL_EVIDENCE.PRIVATE.json':original,'CUSTODY.json':custody}
    if(d/'UNIT_SEAL.json').exists():
        verify(d/'UNIT_SEAL.json',sha(d/'UNIT_SEAL.json'));require(all(read(d/n)==v for n,v in payloads.items()),'immutable actual native unit seal')
    else:
        for n,v in payloads.items():write(d/n,v);(d/n).chmod(0o600)
        write(d/'UNIT_SEAL.json',dict(experiment='E133',n=len(units),files={n:sha(d/n)for n in payloads}))
    prepare_spec=d/'PREPARE_SPEC.json';write(prepare_spec,dict(bank='E133',unit_seal=str(d/'UNIT_SEAL.json'),unit_sha256=sha(d/'UNIT_SEAL.json'),phase_name=spec['arm']+'_naming'))
    with worker():return registered.prepare(prepare_spec)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--native-spec',type=Path);args=parser.parse_args()
    if args.native_spec:print(prepare_complete(read(args.native_spec)))
    else:print('E133 actual v3 candidate source '+sha(prepare_candidates()/'SOURCE_SEAL.json')+'; no selection/output/model calls')
