"""T7 JSON-only join from the existing E133 normalized source contract.

Caller must establish committed E134 selection/custody before invoking this
reader. No E133 analysis/probe runner or activation array is opened here.
"""


def other_literal(evidence,fixed_names):
    """Direct user: exactly one fixed literal, whole word/case-insensitive; no aliases."""
    from .matcher import match_candidates,stated_value
    if len(set(fixed_names))!=len(fixed_names):raise ValueError("unique original fixed name list")
    return stated_value(match_candidates(evidence,{name:[] for name in fixed_names}))


def stated(code,text,value_map,current,previous,fixed_names=None):
    from projects.g_agreement.e133_analysis.rules import readout
    readout(code,text,value_map,current,previous) # Original evidence/schema validation.
    if code is None or code['category']=='UNPARSEABLE':return None
    values=code['values']
    if values==['OTHER']:
        if fixed_names is None:raise ValueError('OTHER is not a scalar identity; original stated-value binding required')
        return other_literal(code['evidence'],fixed_names)
    return value_map[values[0]] if len(values)==1 else None


def bind(io,spec):
    from projects.g_agreement.e133_analysis import screen
    ip=spec['inventory_seal'];ih=spec['inventory_sha256'];inv=io.seal(ip,ih)
    if inv['experiment']!='E133' or inv['status']!='SCREENED_COHORT_FROZEN' or inv['labels_cpu_only']is not True:raise ValueError('original frozen screened E133 inventory')
    if inv['classifier_sha256']!=screen.MATCHER_SHA256 or inv['greedy_max_new_tokens']!=32:raise ValueError('original32-token classifier')
    pairs=io.member(ip,ih,'PAIRS.PRIVATE.json')
    op=spec['output_seal'];oh=spec['output_sha256'];seal=io.seal(op,oh)
    if seal['experiment']!='E133' or seal['status']!='COMPLETE' or seal['inventory_sha256']!=ih or seal['reader_layers']!=[44,52,60] or seal['no_steer']is not True:raise ValueError('complete same-inventory E133 source')
    if seal['judging_bank']!='E133' or not 0<seal['judging_cap_usd']<=5 or seal['rubric_sha256']!=spec['rubric_sha256']:raise ValueError('registered original E133 judgments')
    if any(seal[k]is not True for k in ('route_verified','redaction_audit_complete','labels_cpu_only')):raise ValueError('original E133 custody')
    sources=seal['source_seals'];ref=lambda p:io.pointer(sources,p)
    ms=io.member(op,oh,'MEASUREMENTS.json');grid={x['pair_id']:x for x in ms}
    if len(grid)!=len(ms) or set(grid)!={p['pair_id']for p in pairs}:raise ValueError('complete original pair grid')
    out=[]
    for p in pairs:
        if p['kind']!='multi_hop':continue
        m=grid[p['pair_id']]
        if len(p['members'])!=2 or len(m['members'])!=2:raise ValueError('both original matched members')
        for j,(lab,cell)in enumerate(zip(p['members'],m['members'])):
            def identity(c,mode,block=None):
                i=ref(c['identity'])
                if any(i[k]!=v for k,v in dict(pair_id=p['pair_id'],item_id=lab['item_id'],kind='multi_hop',member=j,mode=mode).items())or i.get('block')!=block:raise ValueError('original T7 identity/site')
                return i
            ni=identity(cell['greedy'],'greedy');native=ref(cell['greedy']['record'])
            if native['id']!=ni['raw_id']:raise ValueError('original greedy record identity')
            truth=screen.classify(native,[p['members'][0]['current'],p['members'][1]['current'],lab['previous']])
            if truth is None:raise ValueError('no unique T7 greedy truth; do not claim or infer a value')
            readings={};lineage={}
            for block in (44,52,60):
                c=cell['readouts'][str(block)];i=identity(c,'readout',block);code=ref(c['code']);text=ref(c['text'])
                if code is None:
                    ptr=c['code']
                    if not ptr['keys']or ptr['keys'][-1]!='code':raise ValueError('terminal source pointer')
                    terminal=ref(dict(ptr,keys=ptr['keys'][:-1]))
                    if terminal['id']!=i['judgment_id']or terminal['status']!='UNPARSEABLE':raise ValueError('original terminal missing')
                elif code['id']!=i['judgment_id']:raise ValueError('original judgment id')
                readings[block]=stated(code,text,p['value_map'],lab['current'],lab['previous']);lineage[block]=c
            out.append(dict(id='T7:'+lab['item_id'],item_id=lab['item_id'],pair_id=p['pair_id'],truth=truth,truth_basis='behaviour-verified',readings=readings,source_refs=dict(seal=op,sha256=oh,readouts=lineage),truth_ref=dict(seal=op,sha256=oh,greedy=cell['greedy'],classifier_sha256=screen.MATCHER_SHA256)))
    if not out or len({x['id']for x in out})!=len(out):raise ValueError('nonempty unique original T7 cohort')
    return out


def bind_c(io,spec):
    """Join C's original terminal source directly; never run B normalization.

    Same stated-value/greedy classifier as bind(), retaining all 100 selected
    multi-hop members. Exact C unit pointers supply the original site crosswalk.
    """
    from projects.g_agreement.e133_analysis import screen
    ip=spec['inventory_seal'];ih=spec['inventory_sha256'];inv=io.seal(ip,ih)
    if inv['status']!='SCREENED_COHORT_FROZEN' or inv['experiment']!='E133' or inv['labels_cpu_only']is not True or inv['classifier_sha256']!=screen.MATCHER_SHA256 or inv['greedy_max_new_tokens']!=32:raise ValueError('original E133 screened inventory')
    pairs=io.member(ip,ih,'PAIRS.PRIVATE.json');selected=io.member(ip,ih,'SELECTED_ITEM_IDS.PRIVATE.json')
    fixed_names=io.member(ip,ih,'FIXED_NAMES.PRIVATE.json')
    labs={m['item_id']:(p,m)for p in pairs for m in p['members']}
    if len(labs)!=180 or set(labs)!=set(selected):raise ValueError('exact180 selected native identities')
    jp=spec['judgment_seal'];jh=spec['judgment_sha256'];js=io.seal(jp,jh)
    if js['experiment']!='E133' or js['status']!='COMPLETE' or any(js[k]is not True for k in ('route_verified','redaction_audit_complete','labels_cpu_only')):raise ValueError('complete original terminal judgments')
    inp=spec['judging_input'];ins=io.seal(inp,js['input_sha256']);ss=ins['source_seals']
    if ins['frozen_before_calls']is not True or ins['labels_cpu_only']is not True:raise ValueError('original pre-call input')
    up=ss[0]['seal'];uh=ss[0]['sha256'];us=io.seal(up,uh);cust=io.member(up,uh,'CUSTODY.json')
    if us['n']!=540 or cust['selected_items']!=180 or cust['arm']!='synthetic' or any(cust[k]is not True for k in ('verified','complete_eligible_native_grid','labels_cpu_only','screened_cohort_bound')):raise ValueError('original C whole native grid custody')
    if cust['source_seals'][2]!={'seal':ip,'sha256':ih}:raise ValueError('same inventory source')
    np=ss[1]['seal'];nh=ss[1]['sha256'];ns=io.seal(np,nh)
    if cust['source_seals'][0]!={'seal':np,'sha256':nh} or ns['status']!='COMPLETE' or ns['arm']!='synthetic' or ns['stage']!='main':raise ValueError('same original native COMPLETE source')
    if ss[2]['sha256']!=inv['main_input_sha256']:raise ValueError('same original input')
    ptrs=io.member(up,uh,'SOURCE_POINTERS.PRIVATE.json');units=io.member(up,uh,'UNITS.json');judgments=io.member(jp,jh,'JUDGMENTS.json')
    def indexed(xs):
        out={x['id']:x for x in xs}
        if len(out)!=len(xs):raise ValueError('unique source identities')
        return out
    pb=indexed(ptrs);ub=indexed(units);jb=indexed(judgments)
    if len(pb)!=540 or set(pb)!=set(ub) or set(pb)!=set(jb):raise ValueError('whole540 terminal grid')
    grid={}
    for uid,ptr in pb.items():
        item=ptr['item_id'];block=ptr['block'];key=(item,block)
        if key in grid or item not in labs or block not in (44,52,60):raise ValueError('exact item/layer crosswalk')
        p,m=labs[item]
        if (ptr['pair_id'],ptr['member'],ptr['family'],ptr['arm'],ptr['current'],ptr['previous'])!=(p['pair_id'],m['member'],p['kind'],'synthetic',m['current'],m['previous']):raise ValueError('literal original source roles')
        unit=ub[uid];j=jb[uid];text=unit['data']['readout']
        if unit['kind']!='e133_naming' or unit['data']['id']!=uid or j['kind']!='e133_naming' or j['status']not in ('KEPT','UNPARSEABLE'):raise ValueError('terminal naming source identity')
        code=j['code']
        if code is None and j['status']!='UNPARSEABLE' or code is not None and code['id']!=uid:raise ValueError('terminal code identity')
        raw=io.member(np,nh,ptr['native_member'])
        for k in ptr['native_keys']:raw=raw[k]
        # Original C evidence is the judged text, including any sealed redaction.
        if raw!=text:
            original=io.member(up,uh,'ORIGINAL_EVIDENCE.PRIVATE.json')
            if original.get(uid)!=raw:raise ValueError('original/readout redaction binding')
        grid[key]=(stated(code,text,ptr['value_map'],m['current'],m['previous'],fixed_names) if p['kind']=='multi_hop' else None,uid,ptr)
    if set(grid)!={(i,b)for i in labs for b in (44,52,60)}:raise ValueError('complete original layer grid')
    ix=io.member(np,nh,'INDEX.json');answers={x['id']:x for x in ix if x.get('kind')=='capture_answer'}
    if set(answers)!=set(labs):raise ValueError('whole original greedy grid')
    out=[]
    for item,(p,m)in labs.items():
        if p['kind']!='multi_hop':continue
        a=answers[item];record=io.member(np,nh,a['member'])[a['record']]
        if record['id']!=item or record['pair_id']!=p['pair_id'] or record['member']!=m['member']:raise ValueError('greedy original identity')
        truth=screen.classify(record,[z['current']for z in p['members']]+[m['previous']])
        if truth is None:raise ValueError('no unique original greedy T7 truth')
        refs={str(b):dict(judgment_id=grid[item,b][1],pointer=grid[item,b][2])for b in (44,52,60)}
        out.append(dict(id='T7:'+item,item_id=item,pair_id=p['pair_id'],truth=truth,truth_basis='behaviour-verified',readings={b:grid[item,b][0]for b in (44,52,60)},source_refs=dict(judgment_seal=jp,sha256=jh,unit_seal=up,unit_sha256=uh,readouts=refs),truth_ref=dict(native_seal=np,native_sha256=nh,member=a['member'],record=a['record'],classifier_sha256=screen.MATCHER_SHA256)))
    if len(out)!=100:raise ValueError('exact100 original multi-hop members')
    return out
