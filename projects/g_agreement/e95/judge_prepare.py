"""CPU packet/audit preparation using frozen E95 IDs and existing regex code.

No matching patterns, rubric, judgment parser, sample, or target is authored here.
The frozen scalar matcher is applied independently to every original position.
A complete group is regex-resolved only when every position is resolved, retaining
the first mention and union of stated values. Every unresolved position keeps the
whole preselected item/layer on the existing blind-judge channel.
"""
from collections import Counter
from pathlib import Path

from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require
from projects.g_agreement.ops.e98_frozen_regex620 import apply as frozen_regex
from projects.g_agreement.understand.blind_judge import e87
from projects.g_agreement.understand.blind_judge.validator221 import e87_classify
from .judge_admission import universe,group_id,unresolved_statement_ids
from .judging_stages import partition
from .stage_complete import admission as admit_stages

CATALOG_SHA='b0b82b3c0ec33fa1f7e03cfdf0f9cc67157d2401114eb724d3b54e55560b3e35'
MATCHER_SHA='620a763fbc270dc30c73ef353e7b68cb85fc765932573f32ed2e96bf356e5f6d'


def rendered(group):
    rubric=e87.render_record(dict(id=group['id'],property=group['property'],
                                 values=group['values'],readout=''),e87.RUBRIC.read_text())['rubric']
    return dict(id=group['id'],rubric=rubric,positions=group['positions'])


def regex_group(group,catalog_row):
    if catalog_row is None or catalog_row['status']!='AVAILABLE':return None
    values=[frozen_regex(p['readout'],group['values'],catalog_row)for p in group['positions']]
    if any(v is None for v in values):return None
    stated=sorted(set(v for vs in values for v in vs))
    require(bool(stated),'no missing-to-silent or missing-to-zero conversion')
    first=group['positions'][0]
    code=dict(id=group['id'],category='states_value',values=stated,
              evidence=first['readout'],first_position=first['offset'])
    result=e87_classify([rendered(group)],dict(records=[code]))[0]
    # Existing evidence validation is authoritative; no format repair.
    return result['code'] if result['status']=='KEPT'else None


def make_audit(rows,eligibility,groups,catalog,catalog_sha):
    expected=universe(rows);native={x['id']:x for x in groups}
    require(len(native)==len(groups)and set(native)<=set(expected),'unique original native IDs')
    by_row={r['row_index']:r for r in rows}
    score={r['row_index']:r['statement_score_registered']for r in eligibility['rows']}
    cat={(x['bank'].lower(),x['row']):x for x in catalog['rows']}
    records=[];resolved=[]
    for gid,(stratum,unit)in sorted(expected.items()):
        ri=int(stratum.split(':',1)[0]);row=by_row[ri]
        entry=cat.get((row['bank'],row['row']))
        record=dict(id=gid,regex_sha256=catalog_sha)
        if not score[ri]:record.update(status='NOT_EVALUABLE_NO_STATEMENT_SCORE')
        elif entry is None or entry['status']!='AVAILABLE':
            record.update(status='NO_REGEX',reason='ORIGINAL_CATALOG_UNAVAILABLE')
        elif gid not in native:
            record.update(status='UNRESOLVED',reason='NO_COMPLETE_ACQUIRED_STAGE; NO_REGEX_OUTCOME_ASSUMED')
        else:
            code=regex_group(native[gid],entry)
            record.update(status='UNRESOLVED'if code is None else'RESOLVED',
                          reason='ORIGINAL_POSITION_MATCHER_UNRESOLVED'if code is None else'ALL_ORIGINAL_POSITIONS_RESOLVED')
            if code is not None:resolved.append(dict(id=gid,status='CPU_REGEX',code=code,
                source='original E76 catalog / original frozen_regex620 / validator221'))
        records.append(record)
    unresolved_statement_ids(records,expected,eligibility)
    return records,resolved


def prepare(spec,out,audit_path):
    root=Path(__file__).resolve().parents[3]
    catalog_path=root/'results/g_agreement/understand/e76/REGEX_CATALOG.json'
    matcher_path=root/'projects/g_agreement/ops/e98_frozen_regex620.py'
    require(sha(catalog_path)==CATALOG_SHA and sha(matcher_path)==MATCHER_SHA,
            'unchanged existing catalog and matcher bytes')
    candidate=Path(spec['candidate_seal']);verify(candidate,spec['candidate_seal_sha256'])
    groups=read(candidate.parent/'ALL_GROUPS.PRIVATE.json')
    rows=read(spec['inventory'])['rows'];expected=universe(rows)
    eligible=admit_stages(spec,expected)
    require({x['id']for x in groups}==eligible,'exact closed complete-stage source grid')
    eligibility=read(spec['eligibility'])
    records,resolved=make_audit(rows,eligibility,groups,read(catalog_path),CATALOG_SHA)
    audit=dict(experiment='E95',inventory_sha256=sha(spec['inventory']),index_sha256=sha(spec['index']),
               candidate_seal_sha256=sha(candidate),catalog_sha256=CATALOG_SHA,matcher_sha256=MATCHER_SHA,
               stage_inventory_sha256=spec['stage_inventory_sha256'],records=records,
               counts=dict(Counter(x['status']for x in records)),labels_used=False,paid_calls=0)
    audit_path=Path(audit_path);require(not audit_path.exists(),'never overwrite an existing audit')
    write(audit_path,audit)
    out=Path(out);out.mkdir(parents=True,exist_ok=False);out.chmod(0o700)
    write(out/'REGEX_RESULTS.PRIVATE.json',resolved)
    index=read(spec['index']);chosen={group_id(k,x)for k,xs in index['selected'].items()for x in xs}
    original={group_id(k,x)for k,xs in index['old_rubric_selected'].items()for x in xs}
    unresolved=unresolved_statement_ids(records,expected,eligibility)
    wanted=chosen&unresolved&eligible
    require(len(chosen)==index['total_selected']and len(original)==index['total_old_rubric'],
            'existing fixed original selection and nested comparison, no resampling')
    joins={x['id']:x for x in read(candidate.parent/'SOURCE_POINTERS.PRIVATE.json')}
    summary={}
    for stage in (1,2,3):
        ids=partition(wanted,expected,stage);d=out/f'stage{stage}';d.mkdir();d.chmod(0o700)
        packet=[x for x in groups if x['id']in ids]
        write(d/'GROUPED_PACKET.json',packet)
        write(d/'ORIGINAL_IDS.json',sorted(original&ids))
        write(d/'PRIVATE_JOIN.json',[joins[x['id']]for x in packet])
        (d/'RUBRIC.txt').write_bytes(e87.RUBRIC.read_bytes())
        write(d/'PACKET_SEAL.json',dict(experiment='E95',judging_stage=stage,n=len(packet),
            n_readouts=sum(len(x['positions'])for x in packet),
            inventory_sha256=sha(spec['inventory']),index_sha256=sha(spec['index']),
            regex_audit_sha256=sha(audit_path),stage_inventory_sha256=spec['stage_inventory_sha256'],
            rubric_sha256=sha(e87.RUBRIC),candidate_seal_sha256=sha(candidate),
            files={n:sha(d/n)for n in('GROUPED_PACKET.json','ORIGINAL_IDS.json','PRIVATE_JOIN.json','RUBRIC.txt')}))
        for p in d.iterdir():p.chmod(0o600)
        summary[stage]=dict(primary_calls=len(packet),original_calls=len(original&ids),
                            packet=str(d.resolve()),packet_seal_sha256=sha(d/'PACKET_SEAL.json'))
    return dict(audit_sha256=sha(audit_path),audit_counts=audit['counts'],
                regex_resolved_native_groups=len(resolved),stages=summary)
