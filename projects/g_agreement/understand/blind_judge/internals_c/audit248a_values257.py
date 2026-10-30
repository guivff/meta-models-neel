"""Read-only F07 whole-source-value audit. No renderer, API, score or once-guard."""
import json,hashlib
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from .transport import ROOT,HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

FIELDS=('belief','belief_aliases','truth','truth_aliases')

def union_atoms(main,aliases):
    require(type(main)is list and type(aliases)is list,'F07 scalar candidate/alias input is not a whole-string array')
    require(all(type(s)is str and bool(s)for s in main+aliases),'original atomic candidate strings')
    out=[]
    for s in main+aliases:
        if s not in out:out.append(s)
    return out

def expected_values(source,letters,prefix=''):
    belief=union_atoms(source[prefix+'belief'],source[prefix+'belief_aliases']);truth=union_atoms([]if source[prefix+'truth']is None else source[prefix+'truth'],source[prefix+'truth_aliases'])
    require(bool(belief),'nonempty original belief')
    if not truth:
        require(letters=={'belief':'A'},'original no-truth disposition');return {'A':belief,'B':[]}
    require(set(letters)=={'belief','truth'}and set(letters.values())=={'A','B'},'original opposing letters')
    return {letters['belief']:belief,letters['truth']:truth}

def check_values(actual,expected):
    require(type(actual)is dict and set(actual)=={'A','B'},'binary value map')
    require(actual==expected,'value arrays differ from original whole source strings')
    return sum(len(v)for v in expected.values())

def suffix(property_text,values):
    return '\n\nProperty: '+property_text+'\nA: '+' / '.join(values['A'])+'\nB: '+' / '.join(values['B'])+'\n'

def check_header(rubric,property_text,values):
    require(type(rubric)is str and rubric.endswith(suffix(property_text,values)),'actual judge header must contain exact whole original strings, not characters')

def unique(rows):
    out={r['id']:r for r in rows};require(len(out)==len(rows),'unique original identity');return out

def audit():
    evidence={};bound={};verified=set();unit_rows=[];physical=[];cohort_bindings=[]
    def bind(p,want=None,seal=False):
        p=Path(p);key=str(p)
        if key not in bound:
            evidence[key]=sha(p);bound[key]=read(p)
        h=evidence[key];require(want is None or h==want,'original evidence hash mismatch')
        if seal and key not in verified:verify(p,h);verified.add(key)
        return bound[key]
    # Follow the actual §248A private binding to its original E107b/Oracle graph.
    A=ROOT.parent/'wt-wmech/cache/g_agreement/understand/companions248/A_analysis_once/ANALYSIS_SEAL.json';bind(A,seal=True);ab=bind(A.parent/'BINDING.PRIVATE.json')
    bp=Path(ab['e107b_seal']);bind(bp,'f62ef3aaf4d51cba3f2319bff90a78a1179a3c086e95bae598c4a692496bae28',True);bs=bind(bp.parent/'BINDING.json')
    primary=Path(bs['primary_seal']);bind(primary,'f2da69a4f0e7acb560552cb9bee8c56ea8012a926a9508303113a2d3ccdd93b8',True);ps=bind(primary.parent/'BINDING.json')
    ip=Path(ps['inventory_seal']);bind(ip,ps['inventory_sha256'],True);inventory=bind(ip.parent/'INVENTORY.json');maps=unique(bind(ip.parent/'TARGET_MAPS.PRIVATE.json'))
    cohort={r['id']:r for r in inventory if r['bank']=='E82'and r['cohort']=='belief_wrong'};require(len(cohort)==199,'all original §248A199 items')
    old_output=Path(ps['output_seal']);os=bind(old_output,ps['output_sha256'],True);oldmeasure=unique(bind(old_output.parent/'MEASUREMENTS.json'))
    forecast_output=Path(bs['output_seal']);fs=bind(forecast_output,bs['output_sha256'],True);newmeasure=unique(bind(forecast_output.parent/'MEASUREMENTS.json'));require(set(newmeasure)==set(cohort),'complete exact forecast cohort')
    cache={}
    def member(sources,r):
        ix=r['seal_index'];ref=sources[ix];sp=Path(ref['seal']);ss=bind(sp,ref['sha256'],True)
        require(r['member']in ss['files'],'literal sealed source member');p=sp.parent/r['member'];key=str(p)
        if key not in cache:cache[key]=bind(p,ss['files'][r['member']])
        value=cache[key]
        for k in r['keys']:value=value[k]
        return value
    # Original source atoms: every E82 item and both reader joins, not only schema types.
    e82=ROOT.parent/'wt-i2/cache/g_agreement/i2/e82_judge_cpu_v1';sb=bind(e82/'SOURCE_BINDINGS.PRIVATE.json');source=unique(bind(sb['targets'],sb['targets_sha256']));require(len(source)==209,'original209 source items')
    inv=bind(e82/'INVENTORY_RECEIPT.json');joins=unique(bind(e82/'JOIN_MAP.PRIVATE.json',inv['private_join_sha256']));require(len(joins)==418,'original both-reader418 groups')
    container_types=Counter()
    for raw in source.values():
        for k in FIELDS:container_types[k+':'+type(raw[k]).__name__]+=1
    for j in joins.values():
        raw=source[j['source_public_id']]
        for k in FIELDS:
            require((k=='truth'and raw[k]is None and raw['truth_aliases']==[])or(type(raw[k])is list and all(type(x)is str and x for x in raw[k])),'whole original E82 target/alias arrays; explicit absent truth only')
            require(j[k]==raw[k],'original join preserves whole source atoms')
    pre=bind(e82/'grouped_adapter_v1/PREFLIGHT.json',seal=True);require(pre['source_inventory_sha256']==sha(e82/'INVENTORY_RECEIPT.json'),'original grouped preflight inventory binding')
    packet=unique(bind(e82/'grouped_adapter_v1/GROUPED_PACKET.json'));tm=bind(e82/'grouped_adapter_v1/TARGET_MAP.PRIVATE.json');require(len(packet)==len(tm)==816,'full primary E82 target grid')
    group_letters={}
    for t in tm:group_letters.setdefault(t['group_id'],{})[t['target']]=t['target_letter']
    e82_expected={};tm_by=unique(tm)
    for t in tm:
        j=joins[t['group_id']];v=expected_values(source[j['source_public_id']],group_letters[t['group_id']]);check_header(packet[t['id']]['rubric'],j['target_kind'],v)
        e82_expected[t['id']]=(j['target_kind'],v);unit_rows.append(dict(channel='E82_primary',id=t['id'],source_public_id=j['source_public_id'],target=t['target'],values=v,original_source_fields={k:source[j['source_public_id']][k]for k in FIELDS}))
    original_ids=bind(e82/'grouped_adapter_v1/ORIGINAL_IDS.json');require(len(original_ids)==204 and set(original_ids)<=set(packet),'all original-rubric shadow IDs')
    # Inspect every saved request in both channels/all retry attempts, without sending anything.
    historical=bind(e82/'SECTION217_SAVED_REQUESTS_MANIFEST.json');seen_primary=set();seen_shadow=set();e82_counts=Counter()
    for p in sorted((e82/'judging').glob('E82*/*.request.json')):
        wire=read(p)['wire'];users=[m for m in wire['messages']if m['role']=='user'];require(len(users)==1,'one original user payload');rows=json.loads(users[0]['content'])
        for r in rows:
            require(r['id']in e82_expected,'no unknown grouped target');prop,v=e82_expected[r['id']];check_header(r['rubric'],prop,v)
            (seen_shadow if 'original' in p.parent.name else seen_primary).add(r['id'])
        rel=str(p.relative_to(e82));historical_bound=rel in historical
        if historical_bound:require(sha(p)==historical[rel],'original pre217 saved request hash')
        physical.append(dict(channel='E82',path=str(p),sha256=sha(p),pre217_manifest_hash_bound=historical_bound,response_present=p.with_name(p.name.replace('.request.json','.response.json')).exists(),ids=[r['id']for r in rows]));e82_counts['shadow'if'original'in p.parent.name else'primary']+=1
    require(seen_primary==set(packet)and seen_shadow==set(original_ids),'all primary and shadow logical IDs represented by saved requests')
    # Check original outside plan fields independently of the vulnerable production helper.
    plan_root=CACHE/'E107/frozen_judge_plan';bind(plan_root/'PLAN_SEAL.json',seal=True);oldplans=bind(plan_root/'PLANS.PRIVATE.json');checked_original_plans=0
    for p in oldplans:
        if p['bank']!='E82':continue
        m=maps[p['inventory_id']];lineage=m['source_lineage'];raw=source[lineage['original_source_public_id']]
        for k in FIELDS:require(lineage['source_'+k]==raw[k]and(type(lineage['source_'+k])is list or(k=='truth'and raw[k]is None)),'frozen outside lineage preserves whole source arrays')
        v=expected_values(raw,m['target_letters_by_system']['outside']);check_values(p['values'],v);checked_original_plans+=1
    # Exact selected Oracle packet references used in §248A, no order/text matching.
    selected_oracle=set()
    for ident,meta in cohort.items():
        require(set(oldmeasure[ident]['systems']['oracle'])=={'belief','truth'},'both original Oracle targets')
        for target,fields in oldmeasure[ident]['systems']['oracle'].items():
            ref=fields['text'];require(ref['keys'][-1]=='positions','literal original grouped text pointer');r=member(os['source_seals'],dict(ref,keys=ref['keys'][:-1]));require(r['id']in tm_by,'original target ID')
            t=tm_by[r['id']];require(t['reader']=='oracle'and t['target']==target and t['source_public_id']==maps[ident]['source_lineage']['original_source_public_id'],'exact cohort/source/target/reader join')
            require(member(os['source_seals'],fields['target_letter'])==t['target_letter'],'original Oracle letters');prop,v=e82_expected[r['id']];check_header(r['rubric'],prop,v);selected_oracle.add(r['id'])
            rowref=fields['code'];require(rowref['keys'][-1]=='code','literal original code pointer');row=member(os['source_seals'],dict(rowref,keys=rowref['keys'][:-1]));require(row['id']==r['id'],'judgment row and whole-value packet identity');cohort_bindings.append(dict(inventory_id=ident,system='oracle',target=target,judgment_id=r['id'],packet_ref=ref,code_ref=fields['code']))
    require(len(selected_oracle)==398,'all398 §248A Oracle target units')
    froot=CACHE/'E107b';source_seal=froot/'forecast_source/SOURCE_SEAL.json';bind(source_seal,'95bb773c2e0c0af00a2daa0d45ce03371923809fa1b82398a22ba3a700ca16ee',True)
    d=froot/'forecast_judging';bind(d/'INPUT_SEAL.json','0fa7a1a5ee5d44160b1f79fee7d2b98724627d78644ff587010a30ef232e63de',True);plans=bind(d/'TARGET_PLAN.PRIVATE.json');units=unique(bind(d/'UNITS.PRIVATE.json'));calls=unique(bind(d/'CALLS.json'));validation=bind(d/'VALIDATION.json');cid_by={p['unit']['id']:p['calls'][0]for p in validation};require(len(plans)==len(units)==len(calls)==398,'all398 forecast targets')
    outside_expected={};outside_by_source={}
    for p in plans:
        ident=p['inventory_id'];require(ident in cohort,'only registered199 forecast items');m=maps[ident];lineage=m['source_lineage'];raw=source[lineage['original_source_public_id']];v=expected_values(raw,m['target_letters_by_system']['outside']);u=units[p['judgment_id']];check_values(p['values'],v);check_values(u['data']['values'],v)
        c=calls[cid_by[u['id']]];rows=json.loads(c['rendered']['user']);require(len(rows)==1 and rows[0]['id']==u['id'],'exact frozen single forecast unit');check_header(rows[0]['rubric'],p['property'],v)
        outside_expected[u['id']]=(p['property'],v);outside_by_source[ident,p['target']]=u['id'];unit_rows.append(dict(channel='E107b_forecast',id=u['id'],inventory_id=ident,target=p['target'],values=v,original_source_fields={k:raw[k]for k in FIELDS}))
    for ident in cohort:
        for target in('belief','truth'):
            r=newmeasure[ident]['targets'][target]['code'];require(r['keys'][-1]=='code','literal forecast code ref');row=member(fs['source_seals'],dict(r,keys=r['keys'][:-1]));require(row['id']==outside_by_source[ident,target],'§248A consumed exact whole-value forecast judgment ID');cohort_bindings.append(dict(inventory_id=ident,system='outside',target=target,judgment_id=row['id'],code_ref=r))
    terminal=bind(d/'outputs/JUDGMENT_SEAL.json','0505d1d5e564af93a6a492f5291a42365d18baf25aebb5c782d61c7574f9c21a',True);raws=bind(d/'outputs/RAW_RESPONSE_BINDINGS.json');seen=set()
    for r in raws:
        response=Path(r['path']);require(sha(response)==r['sha256'],'original sealed physical response binding');p=response.with_name(response.name.replace('.response.json','.request.json'));wire=read(p)['wire'];users=[m for m in wire['messages']if m['role']=='user'];require(len(users)==1,'one actual forecast payload');rows=json.loads(users[0]['content'])
        for u in rows:
            require(u['id']in outside_expected,'actual frozen forecast target ID');prop,v=outside_expected[u['id']];check_header(u['rubric'],prop,v);seen.add(u['id'])
        physical.append(dict(channel='E107b',path=str(p),sha256=sha(p),sealed_response_sha256=r['sha256'],ids=[u['id']for u in rows]))
    require(seen==set(units),'every forecast target actually represented by saved request')
    require(len(cohort_bindings)==796,'all796 exact cohort-target pointer bindings')
    for p,h in evidence.items():require(sha(p)==h,'original sealed evidence unchanged during audit')
    for r in physical:require(sha(r['path'])==r['sha256'],'saved requests unchanged during audit')
    dest=froot/'value_encoding_audit257';dest.mkdir(exist_ok=True)
    for name,value in [('UNIT_SOURCE_COMPARISONS.PRIVATE.json',unit_rows),('PHYSICAL_REQUEST_MANIFEST.PRIVATE.json',physical),('SOURCE_HASHES.PRIVATE.json',evidence),('S248A_TARGET_ID_BINDINGS.PRIVATE.json',cohort_bindings)]:write(dest/name,value);(dest/name).chmod(0o600)
    private_seal=dest/'AUDIT_SEAL.json';write(private_seal,dict(scope='F07/section248A source-value transport only',status='PASS_ALL_WHOLE_SOURCE_VALUES',files={p.name:sha(p)for p in dest.glob('*.PRIVATE.json')}))
    receipt=dict(source_seal_hashes=dict(section248A_analysis=sha(A),original_E107b_analysis=sha(bp),original_E107_primary_analysis=sha(primary),original_E107_inventory=sha(ip),original_E82_targets=sb['targets_sha256'],original_E82_join=inv['private_join_sha256'],original_E82_grouped_preflight=sha(e82/'grouped_adapter_v1/PREFLIGHT.json'),original_E107_frozen_plan=sha(plan_root/'PLAN_SEAL.json'),forecast_source=sha(source_seal),forecast_INPUT=sha(d/'INPUT_SEAL.json'),forecast_terminal=sha(d/'outputs/JUDGMENT_SEAL.json')),independent_audit_source_sha256=sha(ROOT.parent/'outputs/independent-audit-c4518374/AUDIT.md'),auditor_tests=6,Oracle_selected_primary_physical_requests=sum(r['channel']=='E82'and'original'not in Path(r['path']).parent.name and bool(set(r['ids'])&selected_oracle)for r in physical),absent_truth_source_items_retained=10,status='PASS_NO_PRODUCTION_CHARACTER_SPLIT_IN_AUDITED_SCOPE',audit='AUDIT.md F07',at_utc=datetime.now(timezone.utc).isoformat(),cohort_items=199,section248A_oracle_target_units=398,section248A_forecast_target_units=398,all_796_section248A_units_checked=True,extended_E82_source_items=209,extended_E82_reader_groups=418,extended_E82_primary_units=816,extended_E82_original_rubric_shadow_units=204,extended_E107_E82_outside_plans=checked_original_plans,E82_saved_primary_requests=e82_counts['primary'],E82_saved_shadow_requests=e82_counts['shadow'],forecast_saved_physical_requests=len(raws),source_container_type_counts=dict(container_types),split_units=0,mismatched_whole_values=0,method='Exact whole original TARGETS.PRIVATE candidate/alias arrays -> JOIN/TARGET_MAP lineage -> frozen plans/units -> sealed grouped/frozen CALLS suffix -> every saved request; exact §248A original code-pointer IDs, no row/text matching; no production builder invoked',scalar_input_hazard_in_production_functions_remains=True,synthetic_F07_risk_not_dismissed=True,all_original_artifacts_unchanged=True,new_model_calls=0,rejudging=False,scientific_analysis_or_guard_invoked=False,private_audit_seal=str(private_seal),private_audit_sha256=sha(private_seal),public_source_hashes={str(p.relative_to(ROOT)):sha(p)for p in [ROOT/'projects/g_agreement/understand/blind_judge/internals_c/e107_plan.py',ROOT/'results/g_agreement/i2/e82_grouped_judge.py',Path(__file__)]},raw_or_labels_exported=False)
    return receipt

if __name__=='__main__':
    result=audit();write(HERE/'S248A_WHOLE_VALUES_AUDIT257.json',result);print(json.dumps(result,sort_keys=True))
