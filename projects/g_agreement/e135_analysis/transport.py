"""E135 source-bound transport: E128 original validation, dose list6 only."""
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e127_analysis.common import require
from projects.g_agreement.e127_analysis.classifier import classify,pair_preference
from projects.g_agreement.e127_analysis.transport import RUBRIC_SHA
def inputs(spec,experiment,items,original,inventory_meta,pair_answer_fn=None):
    op=Path(spec['output_seal']);meta=core.verify(op,spec['output_sha256'])
    require(meta['experiment']==experiment and meta['status']=='COMPLETE' and meta['inventory_sha256']==spec['inventory_sha256'],'complete bound original outputs')
    require(meta['judging_bank']==experiment and type(meta['judging_cap_usd'])in(int,float) and 0<meta['judging_cap_usd']<=1,'registered separate E135 bank cap at most USD1')
    require(meta['rubric_sha256']==RUBRIC_SHA and meta['route_verified'] is True and meta['labels_cpu_only'] is True and meta['redaction_audit_complete'] is True,'original E104/E109 rubric/route/privacy')
    if experiment=='E127':
        require(meta['no_hooks'] is True and meta['layers']==[44,52,60] and meta['greedy_answer_max_new_tokens']==3,'registered E127 acquisition')
    else:
        require(meta['layers']==[44,52] and meta['new_doses']==[6]
                and meta['steer']==dict(block=40,positions='eight_before_read',direction='class_mean'),'original E128 dose-only intervention')
    require(meta['redacted_count']==0,'redactions need prospective exact-map companion before opening')
    require(meta['behaviour_classifier_sha256']==inventory_meta['behaviour_classifier_sha256'],'frozen CPU answer/flip classifier; no interpretation from readouts')
    require(meta['judging_status'] in ('COMPLETE','PARTIAL','NOT RUN') and meta['unknown_charge_requests']==0 and 0<=meta['lifetime_booked_usd']<=meta['judging_cap_usd'],'terminal disposition and cap')
    sources=meta['source_seals'];seals=[core.verify(x['seal'],x['sha256'])for x in sources];cache={}
    def ref(p,complete=False):
        i=p['seal_index'];require(type(i)is int and 0<=i<len(seals) and p['member'] in seals[i]['files'],'sealed original pointer')
        if complete:require(seals[i]['status'] in ('COMPLETE','COMPLETE_ONCE'),'no partial pilots')
        key=(i,p['member'])
        if key not in cache:cache[key]=core.read(Path(sources[i]['seal']).parent/p['member'])
        x=cache[key];require(isinstance(p['keys'],list) and all(type(k)in(int,str)for k in p['keys']),'literal source keys')
        for k in p['keys']:x=x[k]
        return x
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json'),'item_id');require(set(ms)=={x['item_id']for x in items},'complete original item grid')
    records=[]
    for item in items:
        i=item['item_id'];m=ms[i]
        def oracle(cell,condition,layer,dose=None):
            if meta['judging_status']=='NOT RUN':
                require(cell is None,'no fabricated unrun judgments');return None
            identity=ref(cell['identity']);code=ref(cell['code'],True);text=ref(cell['text'],True)
            require(identity['item_id']==i and identity['row']=='fact_recall' and identity['condition']==condition
                    and identity['layer']==layer and identity['reader']=='oracle' and identity.get('dose')==dose,'original readout identity')
            if code is None and (experiment=='E127' or pair_answer_fn is not None):
                pointer=cell['code'];require(pointer['keys'] and pointer['keys'][-1]=='code','terminal code pointer')
                terminal=ref(dict(pointer,keys=pointer['keys'][:-1]),True)
                require(terminal['id']==identity['judgment_id'] and terminal['status']=='UNPARSEABLE',
                        'null code requires original UNPARSEABLE disposition and identity')
                code=dict(id=identity['judgment_id'],category='UNPARSEABLE',values=[],evidence='')
            require(code['id']==identity['judgment_id'],'original judgment/readout join')
            if dose==8:require(seals[cell['code']['seal_index']]['experiment'] in ('E104','E109'),'reuse original8 judgments, no new bank')
            else:require(seals[cell['code']['seal_index']]['experiment']==experiment,'correct new judgment bank')
            core.score(code,item['new_value'],text)  # exact frozen rubric/evidence validation
            return code
        def behaviour(cell,condition,dose=None):
            identity=ref(cell['identity']);record=ref(cell['record'],True)
            require(identity['item_id']==i and identity['condition']==condition and identity.get('dose')==dose
                    and identity['classifier_sha256']==inventory_meta['behaviour_classifier_sha256'] and identity['raw_id']==record['id'],'frozen answer classification/source identity')
            require(seals[cell['record']['seal_index']]['experiment']==experiment,'correct new greedy-answer source')
            answer=classify(record,item['candidate_strings'])
            return answer,pair_preference(record,item['new_value']),pair_answer_fn(record,item['new_value']) if pair_answer_fn is not None else None
        out=dict(item)
        if experiment=='E127':
            conditions={};require(set(m['conditions'])=={'context_update','neutral_prefix','no_prefix'},'all three E127 conditions')
            for c,z in m['conditions'].items():
                require(set(z['oracle'])=={'44','52','60'},'all E127 layers')
                answer,pair,pair_answer=behaviour(z['behaviour'],c)
                conditions[c]=dict(answer=answer,pair_answer_deviation1=pair_answer,pair_preference_flip_descriptive=pair,oracle={l:oracle(z['oracle'][str(l)],c,l)for l in (44,52,60)})
            out['conditions']=conditions
        else:
            doses={};require(set(m['doses'])=={'6'},'exact new6 only')
            for dose in (6,):
                ds=m['doses'][str(dose)];require(set(ds)=={'steered','random'},'same-dose random control');doses[dose]={}
                for c,z in ds.items():
                    require(set(z['oracle'])=={'44','52'},'both E128 layers')
                    if dose==8:
                        # Original alpha8 has pair preference only; do not invent greedy text.
                        answer=None;pair=original[c][i]['flipped'];flipped=None
                    else:
                        answer,pair,pair_answer=behaviour(z['behaviour'],c,dose)
                        flipped=None if answer is None else answer=='new'
                        if pair_answer_fn is not None:pair=None if pair_answer is None else pair_answer=='new'
                    doses[dose][c]=dict(flipped=flipped,answer=answer,pair_preference_flip_descriptive=pair,oracle={l:oracle(z['oracle'][str(l)],c,l,dose)for l in (44,52)})
            out['doses']=doses
        records.append(out)
    return records
