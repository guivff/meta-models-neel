"""R-5 E140 prospective independent statistical/selection kernel.

Real CLI requires a pinned COMPLETE_ONCE seal; no owner entrypoint/guard.
Only pairs with two singleton X/Y sets enter tracking/prior denominators; other is never treated
as a shared value. Null terminal judgments stay missing; blocks remain separate.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from common.stats import wilson


def summary(values):
    known = [v for v in values if v is not None]
    count = sum(known)
    point, lo, hi = wilson(count, len(known)) if known else (None, None, None)
    return dict(k=count, n=len(known), planned_n=len(values), missing_n=len(values)-len(known),
                estimate=point, Wilson95=None if not known else [lo, hi],
                missing_over5percent=bool(values) and (len(values)-len(known))/len(values) > .05)


def selected_pairs(screen, pairs, original_pair_ids=None):
    planned = 600 if original_pair_ids is None else 300
    if len(screen) != planned or len({r['pair_id'] for r in screen}) != planned:
        raise ValueError('complete registered screen required')
    if original_pair_ids is not None:
        if (type(original_pair_ids) is not list or len(original_pair_ids) != 600 or
                len(set(original_pair_ids)) != 600 or
                [r['pair_id'] for r in screen] != original_pair_ids[:300]):
            raise ValueError('exact first300 of sealed original600 required')
    eligible = []
    for index, row in enumerate(screen):
        if row['generation_index'] != index or row['greedy_max_new_tokens'] != 32:
            raise ValueError('original order/screen window')
        a, b = row['answer_A'], row['answer_B']
        if type(a) is not str or type(b) is not str:
            raise ValueError('original parsed strings required')
        if a and b and a != b:
            eligible.append((row['pair_id'], a, b))
    if [(r['pair_id'], r['X'], r['Y']) for r in pairs] != eligible[:84]:
        raise ValueError('selection or original label drift')


def asserted_category(cell):
    if cell is None:
        return None
    values=cell['values']
    if (type(values) is not list or any(type(v) is not str or v not in ('X','Y','OTHER') for v in values) or
            len(values)!=len(set(values))):
        raise ValueError('original unique asserted set required')
    if len(values)>1:
        return 'multiple'
    return {'X':'X','Y':'Y','OTHER':'other'}[values[0]] if values else 'none'


def reproduce(rows):
    if not 40 <= len(rows) <= 84 or len({r['pair_id'] for r in rows}) != len(rows):
        raise ValueError('fixed40..84 pairs, otherwise screen-only')
    reports = {}
    for block in ('44', '52', '60'):
        categories, pair_coverage, tracking, prior = [], [], [], []
        multiple_pairs = 0
        for row in rows:
            if set(row['blocks']) != {'44', '52', '60'} or set(row['blocks'][block]) != {'A', 'B'}:
                raise ValueError('full source grid')
            pair = []
            for arm in ('A', 'B'):
                cell = row['blocks'][block][arm]
                value = asserted_category(cell)
                pair.append(value)
                categories.append(value)
            multiple_pairs += int('multiple' in pair)
            if None in pair:
                pair_coverage.append(None)
            else:
                both = all(v in ('X', 'Y') for v in pair)
                pair_coverage.append(int(both))
                if both:
                    tracking.append(int(tuple(pair) == ('X', 'Y')))
                    prior.append(int(pair[0] == pair[1]))
        def indicator(accepted):
            return summary([None if v is None else int(v in accepted) for v in categories])
        tr, pr = summary(tracking), summary(prior)
        reports[block] = dict(tracking=tr, prior=pr, coverage=indicator(('X', 'Y', 'other', 'multiple')),
            xy_coverage=indicator(('X', 'Y')), both_value_pair_coverage=summary(pair_coverage),
            planned_pairs=len(rows), eligible_pairs=len(tracking), unknown_pairs=pair_coverage.count(None),
            multiple_readouts=categories.count('multiple'), multiple_pairs=multiple_pairs,
            sensitivity=dict(tracking=summary(tracking+[0]*multiple_pairs), prior=summary(prior+[0]*multiple_pairs),
                             added_multiple_pairs=multiple_pairs, eligible_pairs=len(tracking)+multiple_pairs, used_for_verdict=False),
            categories={v: indicator((v,)) for v in ('X', 'Y', 'other', 'none', 'multiple')},
            tracking_reading=None if tr['estimate'] is None else bool(tr['estimate'] >= .60 and tr['Wilson95'][0] > .45),
            prior_reading=None if pr['estimate'] is None else bool(pr['estimate'] >= .50))
    return dict(experiment='E140', descriptive=True, blocks=reports, other_policy='xy_only',
        block60_readings=dict(follows_forward_pass=reports['60']['tracking_reading'],
                             prior_or_resolving_dominates=reports['60']['prior_reading']),
        ceiling=dict(value=1.0, construction_only=True, new_run=False),
        multiple_value_authority='252_clarification2_d1d15ccf2', new_calls=0)


def validate_native_index(pointer, identity, native, block, resolve):
    """Independent literal index-to-record transport; no invented embedded ID."""
    from pathlib import PurePosixPath
    if 'native_index' not in pointer:
        if native.get('id') != identity['native_id']:
            raise ValueError('native identity mismatch')
        return
    ip, np = pointer['native_index'], pointer['native']
    index = resolve(ip)
    valid = (PurePosixPath(ip['member']).name == 'INDEX.json' and
             ip['seal_index'] == np['seal_index'] and
             index['kind'] == 'oracle' and index['block'] == block and
             index['id'] == identity['native_id'] and type(index['record']) is int and index['record'] >= 0 and
             np['member'] == str(PurePosixPath(ip['member']).parent / index['member']) and
             np['keys'] == [index['record']] and ('id' not in native or native['id'] == index['id']))
    if not valid:
        raise ValueError('original index/member/record identity mismatch')


def original_record(judgment, text):
    """Validate literal producer data; never classify/reparse a readout."""
    if type(judgment) is not dict or type(text) is not str or not judgment.get('id'):
        raise ValueError('original terminal record')
    status, code = judgment.get('status'), judgment.get('code')
    if status == 'UNPARSEABLE' and code is None:
        return None
    if status != 'KEPT' or type(code) is not dict or set(code) != {'id','category','values','evidence'}:
        raise ValueError('original terminal disposition/code fields')
    if code['id'] != judgment['id'] or code['category'] not in ('states_value','names_property_without_value','exhibits','silent'):
        raise ValueError('original nested identity/category')
    asserted_category(code)
    if bool(code['values']) != (code['category']=='states_value'):
        raise ValueError('stating convention')
    evidence=code['evidence']
    if (type(evidence) is not str or evidence not in text or
            (evidence != '' if code['category']=='silent' else not evidence)):
        raise ValueError('original verbatim evidence')
    return dict(code,values=list(code['values']))


def main():
    import argparse
    import json
    from reproduce_e118b import read, sealed, sha, check, compare
    parser=argparse.ArgumentParser(description='Independent E140 final sealed reproduction; no owner adapter/guard')
    parser.add_argument('--analysis-seal',type=Path,required=True)
    parser.add_argument('--seal-sha256',required=True)
    args=parser.parse_args()
    pins=read(Path(__file__).with_name('E140_REPRODUCTION_SOURCE.json'))
    check(all(sha(ROOT/f)==h for f,h in pins['files'].items()),'prepared scientific source changed')
    final=sealed(args.analysis_seal,args.seal_sha256)
    check(final.get('experiment')=='E140' and final.get('status')=='COMPLETE_ONCE','final scientific seal required before real source opening')
    spec=read(args.analysis_seal.parent/'BINDING.PRIVATE.json')
    check(spec['experiment']=='E140' and spec['status']=='COMPLETE' and spec['other_policy']=='xy_only' and
          spec['other_policy_authority']=='direct_user_xy_only' and spec['multiple_value_authority']=='252_clarification2_d1d15ccf2','frozen explicit scientific authorities')
    inv=sealed(spec['inventory_seal'],spec['inventory_sha256'])
    screen=sealed(spec['screen_seal'],spec['screen_sha256'])
    check(inv['experiment']=='E140' and inv['seed']==20261030 and inv['screen_candidates'] in (300,600) and inv['category_count']>=8,'original screen inventory')
    check(inv['selection_frozen_before_reads'] is True and inv['labels_cpu_only'] is True and
          inv['selection']=='first_up_to84_nonempty_different_in_generation_order' and
          inv['parser']=='first_nonempty_line_lowercase_punctuation_stripped' and inv['other_policy']=='xy_only','frozen inventory selection/parser')
    check(screen['experiment']=='E140' and screen['status']=='COMPLETE' and
          all(screen[k] is True for k in ('parser_frozen_before_screen','selection_frozen_before_reads','no_answer_words_in_prompts_verified')) and
          inv['screen_sha256']==spec['screen_sha256'],'original complete screen provenance')
    for s in screen['source_seals']:sealed(s['seal'],s['sha256'])
    pairs=read(Path(spec['inventory_seal']).parent/'PAIRS.PRIVATE.json')
    check(40<=len(pairs)<=84 and len({p['pair_id']for p in pairs})==len(pairs) and
          all(p['X'] and p['Y'] and p['X']!=p['Y']for p in pairs),'fixed eligible pair roster')
    parent=None
    if inv['screen_candidates']==300:
        check(spec['screen_scope_authority']=='252_deviation2_b10b2694e' and screen['screen_candidates']==300,'authorized first300')
        ref=spec['original_pair_ids_ref'];pseal=sealed(ref['seal'],ref['sha256'])
        check(ref['member']in pseal['files']and inv['parent_identity_sha256']==ref['sha256'],'sealed full600 parent')
        parent=read(Path(ref['seal']).parent/ref['member'])
        for k in ref['keys']:parent=parent[k]
    selected_pairs(read(Path(spec['screen_seal']).parent/'SCREEN_PAIRS.PRIVATE.json'),pairs,parent)
    out=sealed(spec['output_seal'],spec['output_sha256'])
    check(out['experiment']=='E140' and out['status']=='COMPLETE' and out['inventory_sha256']==spec['inventory_sha256'] and
          out['layers']==[44,52,60] and out['read_position']=='final_prompt_token','complete same-inventory output source')
    check(out['judging_bank']=='E140' and 0<out['judging_cap_usd']<=1 and
          0<=out['lifetime_booked_usd']<=out['judging_cap_usd'] and out['unknown_charge_requests']==0,'original bank1')
    check(all(out[k] is True for k in ('route_verified','labels_cpu_only','redaction_audit_complete')) and out['redacted_count']==0,'source privacy')
    sources=out['source_seals'];seals=[sealed(s['seal'],s['sha256'])for s in sources];cache={}
    def resolve(ref):
        i=ref['seal_index']
        check(type(i)is int and 0<=i<len(sources)and ref['member']in seals[i]['files'],'sealed original reference')
        check(seals[i]['status']in ('COMPLETE','COMPLETE_ONCE'),'terminal original source')
        key=(i,ref['member'])
        if key not in cache:cache[key]=read(Path(sources[i]['seal']).parent/ref['member'])
        v=cache[key]
        for k in ref['keys']:v=v[k]
        return v
    measurements=read(Path(spec['output_seal']).parent/'MEASUREMENTS.PRIVATE.json')
    check([r['pair_id']for r in measurements]==[p['pair_id']for p in pairs],'exact selected order')
    rows=[];used=set()
    for r in measurements:
        check(set(r['blocks'])=={'44','52','60'},'full block grid')
        target=dict(pair_id=r['pair_id'],blocks={})
        for block in ('44','52','60'):
            arms=r['blocks'][block];check(set(arms)=={'A','B'},'both original paraphrases');target['blocks'][block]={}
            for arm,p in arms.items():
                identity,judgment,native=(resolve(p[k])for k in ('identity','judgment','native'))
                check(identity['pair_id']==r['pair_id']and identity['paraphrase']==arm and identity['block']==int(block)and
                      identity['judgment_id']==judgment['id'],'original literal identity/code join')
                validate_native_index(p,identity,native,int(block),resolve)
                check(judgment['id']not in used,'one original code per readout');used.add(judgment['id'])
                target['blocks'][block][arm]=original_record(judgment,native['text'])
        rows.append(target)
    check(len(used)==6*len(rows)<=504,'full original terminal census')
    actual=reproduce(rows);leaves=compare(actual,read(args.analysis_seal.parent/'RESULTS.json'))
    print(json.dumps(dict(status='VERIFIED',compared_leaves=leaves,analysis_sha256=args.seal_sha256,pairs=len(rows),readouts=len(used),
                         block60_readings=actual['block60_readings'],physical_and_chronology_custody='separate review required'),indent=2))


if __name__=='__main__':
    main()
