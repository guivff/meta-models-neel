"""Read-only JSON pointer intake; no prior analysis, model, fit or once guard."""
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class SealedJSON:
    """Verify exact seals and each referenced JSON member before parsing.

    Unreferenced activation arrays are never opened or rehashed for E134.
    The final plan records every JSON/seal actually consumed by this reader.
    """
    def __init__(self):
        self.pins={}
        self.cache={}

    def read(self,path,expected):
        path=Path(path).resolve()
        if path.suffix!='.json':raise ValueError('JSON source only')
        raw=path.read_bytes()
        actual=hashlib.sha256(raw).hexdigest()
        if actual!=expected:raise ValueError('original JSON hash mismatch')
        previous=self.pins.setdefault(str(path),actual)
        if previous!=actual:raise ValueError('source changed during intake')
        if str(path) not in self.cache:self.cache[str(path)]=json.loads(raw)
        return self.cache[str(path)]

    def seal(self,path,expected):
        seal=self.read(path,expected)
        if not isinstance(seal.get('files'),dict):raise ValueError('sealed member hashes required')
        return seal

    def member(self,path,expected,member):
        path=Path(path).resolve();seal=self.seal(path,expected)
        relative=Path(member)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('original relative member required')
        return self.read(path.parent/relative,seal['files'][member])

    def pointer(self,sources,ref):
        i=ref['seal_index']
        if type(i) is not int or not 0<=i<len(sources):raise ValueError('original source index')
        source=sources[i]
        value=self.member(source['seal'],source['sha256'],ref['member'])
        for key in ref['keys']:value=value[key]
        return value


def join_cue_rows(labels,at44,late):
    """Join already validated original cue flags; never infer silence as not-told."""
    from .normalize import cue_value
    test={r['public_id']:r for r in labels if r['split']=='test'}
    if len(test)!=400 or len(at44)!=400 or set(at44)!=set(test):raise ValueError('exact original400 T6 test identities')
    if set(late)!={(i,b) for i in test for b in (52,60)}:raise ValueError('exact400 by52/60 cue grid')
    out=[]
    for item,meta in test.items():
        if type(meta['addressed']) is not int or meta['addressed'] not in (0,1):raise ValueError('original told factor')
        cells={44:at44[item],52:late[item,52],60:late[item,60]}
        if any(not x.get('source_ref') for x in cells.values()):raise ValueError('original cue source lineage')
        out.append(dict(id='T6:'+item,item_id=item,truth='told' if meta['addressed'] else 'not_told',accuracy_eligible=bool(meta['addressed']),readings={b:cue_value(x['mention']) for b,x in cells.items()},source_refs={b:x['source_ref'] for b,x in cells.items()},truth_ref=dict(public_id=item,field='addressed')))
    return out


def bind_cue(io, original, timing, config_path, config_sha):
    """E85 Oracle44 plus E120a52/60, original judge205 validation only.

    original/timing are exact original analysis binding specifications. This
    function validates sealed readouts and joins labels, without computing any
    E85/E120/E134 statistic or invoking their runners.
    """
    from projects.g_agreement.e85_analysis.adapter import codes,inventory,JUDGE
    from projects.g_agreement.e120_analysis.adapter import judgment,validate_plan
    cfg=io.read(config_path,config_sha)
    if original['private']!=timing['private']:raise ValueError('same original E85 labels required')
    labels=io.read(original['private'],cfg['private_sha256'])
    test={k:v for k,v in inventory(labels).items() if v['split']=='test'}
    validate_plan(timing,cfg,test)
    at44={};late={}
    for spec,is_late in ((original,False),(timing,True)):
        path=spec['binding_seal' if is_late else 'output_seal']
        expected=spec['binding_sha256' if is_late else 'output_sha256']
        seal=io.seal(path,expected)
        if seal['experiment']!=('E120' if is_late else 'E85') or seal['status']!='COMPLETE':raise ValueError('complete original cue bank')
        if is_late and seal['part']!='a':raise ValueError('E120a only')
        if seal['private_sha256']!=cfg['private_sha256'] or seal['input_seal_sha256']!=cfg['input_seal_sha256'] or seal['judge205_sha256']!=digest(JUDGE):raise ValueError('frozen cue source identity')
        if any(seal[k] is not True for k in ('route_verified','redaction_audit_complete')):raise ValueError('original cue custody')
        sources=seal['source_seals'];ref=lambda r:io.pointer(sources,r)
        rows=io.member(path,expected,'MEASUREMENTS.json')
        if len(rows)!=800 or len({m['id'] for m in rows})!=800:raise ValueError('exact unique800 cue source cells')
        for m in rows:
            if m['item_id'] not in test:raise ValueError('cue test identity')
            f=m['fields']
            if is_late:
                b=m['block']
                if b not in (52,60) or ref(f['item_id'])!=m['item_id'] or ref(f['block'])!=b:raise ValueError('cue source identity/block')
                value=judgment(m,ref)['a'];key=(m['item_id'],b);dest=late
            else:
                if m['reader'] not in ('oracle','nla'):raise ValueError('original cue reader')
                if m['reader']!='oracle':continue
                value=codes(ref(f['code']),ref(f['text']))['a'];key=m['item_id'];dest=at44
            if key in dest:raise ValueError('duplicate cue cell')
            dest[key]=dict(mention=value,source_ref=dict(seal=path,sha256=expected,measurement_id=m['id'],fields=f))
    out=join_cue_rows(labels,at44,late)
    for x in out:x['truth_ref'].update(path=original['private'],sha256=cfg['private_sha256'])
    return out


def bind_context(io,spec):
    """T5 primary context_update condition, all84 originals, pair-logit truth.

    Controls remain original E127 controls; no flipped-subset selection. Strict
    pair ties/terminal missing truth are retained in a private exclusion audit.
    """
    from projects.g_agreement.e127_analysis.deviation1 import pair_answer
    from projects.g_agreement.understand.wmech2.core import score as validate_code
    from .normalize import binary_value
    ip=spec['inventory_seal'];ih=spec['inventory_sha256'];inv=io.seal(ip,ih)
    if inv['experiment']!='E127' or inv['status']!='SOURCE_ONLY_COHORT_BOUND' or inv['labels_cpu_only'] is not True:raise ValueError('original E127 cohort')
    items=io.member(ip,ih,'INVENTORY.json')
    if len(items)!=84 or len({x['item_id'] for x in items})!=84:raise ValueError('all84 original context items')
    op=spec['output_seal'];oh=spec['output_sha256'];seal=io.seal(op,oh)
    if seal['experiment']!='E127' or seal['status']!='COMPLETE' or seal['inventory_sha256']!=ih or seal['layers']!=[44,52,60]:raise ValueError('complete original E127 source')
    if any(seal[k] is not True for k in ('route_verified','labels_cpu_only','redaction_audit_complete','no_hooks')):raise ValueError('E127 custody')
    sources=seal['source_seals'];ref=lambda r:io.pointer(sources,r)
    ms=io.member(op,oh,'MEASUREMENTS.json');by={m['item_id']:m for m in ms}
    if len(by)!=84 or len(ms)!=84 or set(by)!={x['item_id'] for x in items}:raise ValueError('exact context measurement IDs')
    rows=[];excluded=[]
    for item in items:
        i=item['item_id'];z=by[i]['conditions']['context_update'];cell=z['behaviour']
        identity=ref(cell['identity']);record=ref(cell['record'])
        if identity['item_id']!=i or identity['condition']!='context_update' or identity['raw_id']!=record['id']:raise ValueError('context behaviour identity')
        value=pair_answer(record,item['new_value'])
        truth=item['new_value'] if value=='new' else item['old_value'] if value=='old' else None
        if truth is None:
            excluded.append(dict(item_id=i,reason='PAIR_TIE_OR_MISSING_TRUTH',truth_ref=cell));continue
        readings={};refs={}
        for b in (44,52,60):
            oc=z['oracle'][str(b)];ident=ref(oc['identity']);code=ref(oc['code']);text=ref(oc['text'])
            if any(ident[k]!=v for k,v in dict(item_id=i,row='fact_recall',condition='context_update',layer=b,reader='oracle').items()):raise ValueError('context readout identity')
            if code is None:
                cp=oc['code']
                if not cp['keys'] or cp['keys'][-1]!='code':raise ValueError('original terminal code pointer')
                terminal=ref(dict(cp,keys=cp['keys'][:-1]))
                if terminal['id']!=ident['judgment_id'] or terminal['status']!='UNPARSEABLE':raise ValueError('original terminal missing disposition')
                code=dict(id=ident['judgment_id'],category='UNPARSEABLE',values=[],evidence='')
            if code['id']!=ident['judgment_id']:raise ValueError('context judgment identity')
            validate_code(code,item['new_value'],text)
            readings[b]=binary_value(code);refs[b]=oc
        rows.append(dict(id='T5:'+i,item_id=i,truth=truth,readings=readings,source_refs=dict(seal=op,sha256=oh,cells=refs),truth_ref=dict(seal=op,sha256=oh,cell=cell,measure='E127 deviation1 original mean first-token pair logits')))
    return rows,excluded


def bind_steered(io,spec):
    """Original E109 44/52/60 readings; saved E104 pair contrast is truth.

    Retain all84 original test items per row before truth-missing audit. Never
    use a readout code, target sign or flipped subset to assign actual truth.
    """
    import math
    from projects.g_agreement.understand.wmech2.core import score as validate_code
    from .normalize import binary_value
    private=io.read(spec['e104_private'],'495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4')
    ip=spec['inventory_seal'];ih=spec['inventory_sha256'];inv=io.seal(ip,ih)
    if inv['experiment']!='E109':raise ValueError('original E109 inventory')
    inventory=io.member(ip,ih,'INVENTORY.json')
    op=spec['output_seal'];oh=spec['output_sha256'];seal=io.seal(op,oh)
    if seal['experiment']!='E109' or seal['status']!='COMPLETE' or seal['inventory_sha256']!=ih:raise ValueError('complete original E109 source')
    if any(seal[k] is not True for k in ('route_verified','privacy_verified','labels_cpu_only')):raise ValueError('original E109 custody')
    ms=io.member(op,oh,'MEASUREMENTS.json');sources=seal['source_seals'];ref=lambda r:io.pointer(sources,r)
    out={};excluded={}
    for row,typ in [('fact_recall','T1'),('language_plan','T3')]:
        prior={x['item_id']:x for x in private if x['row']==row and x['arm']=='U' and x['condition']=='steered'}
        ids=inventory[row]['test_ids']
        if len(ids)!=84 or len(set(ids))!=84 or set(ids)!=set(prior):raise ValueError('all84 original steered identities')
        cells={}
        for b in (44,52,60):
            xs=ms[row][str(b)]['oracle']['steered']
            if [x['item_id'] for x in xs]!=ids:raise ValueError('original steered source order')
            cells[b]={x['item_id']:x for x in xs}
        out[typ]=[];excluded[typ]=[]
        for i in ids:
            contrast=prior[i]['contrast']
            if type(contrast) not in (int,float) or not math.isfinite(contrast):raise ValueError('original finite pair contrast')
            if contrast==0:
                excluded[typ].append(dict(item_id=i,reason='PAIR_LOGIT_TIE',truth_ref=dict(path=spec['e104_private'],item_id=i,field='contrast')));continue
            truth='A' if contrast>0 else 'B';readings={};refs={}
            for b in (44,52,60):
                cell=cells[b][i];code=ref(cell['code']);text=ref(cell['text'])
                validate_code(code,prior[i]['target'],text)
                readings[b]=binary_value(code);refs[b]=cell
            out[typ].append(dict(id=typ+':steered:'+i,item_id=i,condition='steered',truth=truth,readings=readings,source_refs=dict(seal=op,sha256=oh,cells=refs),truth_ref=dict(path=spec['e104_private'],sha256='495bbb19179f507869779d611c737ac82181f8c404054fcffd6963b7615fd0e4',row=row,arm='U',condition='steered',item_id=i,field='contrast',measure='saved original E104 mean first-token A-minus-B logits')))
    return out,excluded


def classified_unhooked_truth(classifications,labels,mapping,inventory):
    """Join the sealed E131 owner's classifications, never replay its analysis.

    E131 text_value/pair_value are original old/new orientations, while E123
    old_value supplies the original A/B orientation. No E131 metrics are read.
    """
    from .truth import BEHAVIOUR
    labs={x['base_id']:x for x in labels}
    inv={x['item_id']:x for x in inventory}
    cells=[x for x in classifications if x['condition']=='unhooked']
    if len(cells)!=84 or len({x['base_id'] for x in cells})!=84 or len(inv)!=84:raise ValueError('original84 unhooked identities')
    out={}
    for cell in cells:
        base=cell['base_id']
        if cell['id']!=base+':unhooked':raise ValueError('original E131 unhooked id')
        lab=labs[mapping[base]];item=lab['original_base_id']
        if item not in inv or item in out:raise ValueError('original E131 to E123 identity')
        old=inv[item]['old_value']
        if old not in ('A','B') or lab['old_value']==lab['new_value']:raise ValueError('original old/new orientation')
        text,pair=cell['text_value'],cell['pair_value']
        if text not in ('old','new','neither') or pair not in ('old','new','tie'):raise ValueError('original classifier schema')
        selected=text if text!='neither' else pair
        value=old if selected=='old' else ('B' if old=='A' else 'A') if selected=='new' else None
        out[item]=dict(truth=value,truth_basis=BEHAVIOUR,truth_method='E131 greedy parse_target_answer' if text!='neither' else 'E131 same-pass pair-logit fallback',e131_id=cell['id'])
    if set(out)!=set(inv):raise ValueError('lossless original84 truth join')
    return out


def open_choice_rows(cohort,categories,catalog,texts,refs):
    """All original376 choices; match every registered member in its category."""
    from .matcher import match_candidates,stated_value
    ids={x['id'] for x in cohort}
    if len(cohort)!=376 or len(ids)!=376 or set(texts)!={(i,b) for i in ids for b in (44,52,60)}:raise ValueError('original376 by44/52/60 open-choice grid')
    out=[]
    for x in cohort:
        i=x['id'];candidates={x['member']:x['registered_aliases'] for x in catalog[categories[i]]}
        if not candidates or any(not isinstance(a,list) for a in candidates.values()):raise ValueError('original category member/alias catalog')
        matches={b:match_candidates(texts[i,b],candidates) for b in (44,52,60)}
        out.append(dict(id='T4:'+i,item_id=i,truth=x['choice'],readings={b:stated_value(v) for b,v in matches.items()},matcher_matches=matches,source_refs={b:refs[i,b] for b in (44,52,60)},truth_ref=x['ground_truth_ref'],category=categories[i],arm=x['arm']))
    return out


def bind_unhooked(io,spec,*,as_of,fact_truth=None,e131_sealed_at=None,rows=('fact_recall','language_plan')):
    """Original E123 unhooked44/52, ff005a9c7 truth provenance, no invented60."""
    from .truth import unhooked_value
    from .normalize import binary_value
    from projects.g_agreement.understand.wmech2.core import score as validate_code
    ip=spec['inventory_seal'];ih=spec['inventory_sha256'];inv=io.seal(ip,ih)
    inventory=io.member(ip,ih,'INVENTORY.json')
    if inv['experiment']!='E123' or inv['labels_cpu_only'] is not True:raise ValueError('original E123 inventory')
    op=spec['output_seal'];oh=spec['output_sha256'];seal=io.seal(op,oh)
    if seal['experiment']!='E123' or seal['status']!='COMPLETE' or seal['inventory_sha256']!=ih or seal['layers']!=[44,52]:raise ValueError('complete original unhooked44/52')
    if any(seal[k] is not True for k in ('route_verified','redaction_audit_complete','labels_cpu_only')):raise ValueError('original unhooked custody')
    sources=seal['source_seals'];ref=lambda r:io.pointer(sources,r)
    ms=io.member(op,oh,'MEASUREMENTS.json');out={}
    for row in rows:
        if row not in ('fact_recall','language_plan'):raise ValueError('registered unhooked rows only')
        typ='T2' if row=='fact_recall' else 'T3';items=inventory[row];by={x['item_id']:x for x in ms[row]}
        n=84 if row=='fact_recall' else 50
        if len(items)!=n or len(by)!=n or set(by)!={x['item_id'] for x in items}:raise ValueError('original84/50 unhooked identities')
        out[typ]=[]
        for item in items:
            i=item['item_id'];truth=unhooked_value(row,item['old_value'],e131=None if fact_truth is None or row!='fact_recall' else fact_truth[i],e131_sealed_at=e131_sealed_at,as_of=as_of)
            if truth['truth'] is None:raise ValueError('E131 pair tie/missing truth requires explicit private exclusion audit')
            readings={};refs={}
            for b in (44,52):
                cell=by[i]['conditions']['unhooked'][str(b)];identity=ref(cell['identity']);code=ref(cell['code']);text=ref(cell['text'])
                expected=dict(item_id=i,row=row,condition='unhooked',layer=b,reader='oracle')
                if any(cell[k]!=v or identity[k]!=v for k,v in expected.items()):raise ValueError('unhooked original cell identity')
                if code is None:
                    cp=cell['code']
                    if not cp['keys'] or cp['keys'][-1]!='code':raise ValueError('original terminal code pointer')
                    terminal=ref(dict(cp,keys=cp['keys'][:-1]))
                    if terminal['status']!='UNPARSEABLE' or terminal['id']!=identity['judgment_id']:raise ValueError('original unhooked missing disposition')
                    code=dict(id=identity['judgment_id'],category='UNPARSEABLE',values=[],evidence='')
                if code['id']!=identity['judgment_id']:raise ValueError('unhooked judgment identity')
                validate_code(code,item['old_value'],text);readings[b]=binary_value(code);refs[b]=cell
            out[typ].append(dict(id=typ+':unhooked:'+i,item_id=i,condition='unhooked',**truth,readings=readings,source_refs=dict(seal=op,sha256=oh,cells=refs),truth_ref=dict(inventory_seal=ip,inventory_sha256=ih,item_id=i,field='old_value',E131=None if fact_truth is None or row!='fact_recall' else fact_truth[i])))
    return out
