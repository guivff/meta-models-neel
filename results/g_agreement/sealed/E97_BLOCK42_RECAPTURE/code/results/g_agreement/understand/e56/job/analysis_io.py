"""Verified-pull and blind-judgment validation shared by E56/E57."""
import json
from pathlib import Path
from contract56 import read,verify,require,sha,auc,validate_judgment,BANK_SHA

def lines(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]

def collect(spec,experiment):
    inp=Path(spec['inputs']);verify(inp,'INPUT_SEAL.json',spec['input_seal_sha256'])
    require(sha(spec['private_items'])==spec['private_items_sha256'],'private item binding')
    private={x['id']:x for x in read(spec['private_items'])};items=read(inp/'items.json');receipt=read(spec['receipt'])
    require(receipt['verified'] is True and receipt['experiment']==experiment and set(receipt['slots'])=={'0','1','2'},'verified pull receipt')
    plan=read(inp/('RUN_PLAN.json' if experiment=='E57' else 'SHARDS.json'));native=[];probes=[];continuation=[];caps={};pods=set();counts=[]
    for slot,path in enumerate(spec['outputs']):
        root=Path(path);r=receipt['slots'][str(slot)];s=verify(root,'OUTPUT_SEAL.json',r['output_seal_sha256']);a=read(root/'ASSIGNMENT.json')
        require(s['experiment']==experiment and s['slot']==slot and s['pod_id']==a['pod_id']==r['pod_id'],'collection identity')
        require(s['pod_id'] not in pods,'pod reused');pods.add(s['pod_id'])
        require(s['input_seal_sha256']==spec['input_seal_sha256'] and s['source_seal_sha256']==spec['source_seal_sha256'],'sealed identity')
        created=a['pod_created_epoch'];done=read(root/'TIMING.json')['completed_epoch']
        allocation=a['allocation_by_slot'];prior=a['prior_custody_seconds'];registered={'E56':9000,'E57':5400,'E61':1800}
        require(all(sum(v.values())+prior[e]<=2*registered[e] for e,v in allocation.items()),'cumulative twice-registered custody')
        end=created+sum(v.get(str(slot),0) for v in allocation.values());require(end==a['absolute_deadline_epoch'] and created<=done<end,'creation custody cap')
        require(read(root/'ADMISSION.json')['status']=='ADMIT','self admission required')
        go=read(root/'GO_RECEIPT.json');require(go['reader_launch_authorized'] is True and go['pod_id']==a['pod_id'] and go['capture_seals'][experiment]==sha(root/'capture/CAPTURE_SEAL.json'),'R3b GO capture binding')
        if experiment=='E56':require(read(root/'parity/PARITY_RESULT.json')['status']=='PASS','parity')
        else:
            reuse=read(root/'PARITY_REUSE.json');sibling=root.parent/'e56'
            require(reuse['status']=='PASS' and reuse['pod_id']==a['pod_id'] and reuse['e56_output_seal_sha256']==sha(sibling/'OUTPUT_SEAL.json') and reuse['parity_result_sha256']==sha(sibling/'parity/PARITY_RESULT.json'),'parity reuse')
            verify(sibling,'OUTPUT_SEAL.json');require(read(sibling/'parity/PARITY_RESULT.json')['status']=='PASS','reused parity failed')
        verify(root/'capture','CAPTURE_SEAL.json');caps[str(slot)]=sha(root/'capture/CAPTURE_SEAL.json')
        rows=plan['shards' if experiment=='E57' else 'rows'][str(slot)]
        order=read(root/'capture/items.order.json');require(order==[x['id'] for x in items if x['feature'] in rows],'capture order')
        cpu=Path(spec['cpu_outputs'][str(slot)]);cs=verify(cpu,'CPU_SEAL.json')
        require(cs['capture_seal_sha256']==caps[str(slot)] and cs['private_items_sha256']==spec['private_items_sha256'] and cs['source_seal_sha256']==spec['source_seal_sha256'],'CPU probe/class-mean binding')
        probe=read(cpu/'PROBE.json');expected={x['id'] for x in items if x['feature'] in rows and x['split']=='test' and (experiment=='E56' or plan['rows'][x['feature']]['probe_applicable'])}
        require(len(probe)==len(expected) and {x['id'] for x in probe}==expected,'probe grid');probes+=probe
        for reader in ('oracle','nla'):
            data=lines(root/(reader+'.native.jsonl')) if experiment=='E57' else lines(root/'native'/(reader+'.jsonl'))
            if experiment=='E57':units={k for row in rows for k in plan['native_ids'][row]};injection={}
            else:
                sample=read(inp/'SAMPLING.json')['native_ids'];units={k for row in rows for k in sample[row]};injection={x['id']:x for x in read(inp/'injection/ITEMS.json')['items'] if x['row'] in plan['injection_rows'][str(slot)]};units|=set(injection)
            require(len(data)==len(units) and {x['id'] for x in data}=={k+':'+reader+':'+str(i) for k in units for i in range(1)},'native grid')
            for x in data:
                require(x['id']==x['unit_id']+':'+reader+':'+str(x['repeat']) and x['reader']==reader and x['reader_native_layer']==(44 if reader=='oracle' else 42),'native identity')
                if x['unit_id'] in injection:
                    u=injection[x['unit_id']];require(x['direction_id']==u['row']+':'+u['variant'] and x['arm']==u['arm'] and x['vector_index']==u['index'],'direction identity')
                else:require(x['feature']==private[x['unit_id']]['feature'],'text row identity')
            native+=data
            c=lines(root/(reader+'.continuation.jsonl')) if experiment=='E57' else lines(root/'continuation'/(reader+'.jsonl'))
            eligible={row for row in rows if (plan['rows'][row]['continuation_pairs'] if experiment=='E57' else read(inp/'CONTINUATIONS.json')[row]['pairs']) is not None}
            expected={(x['id'],arm) for x in items if x['feature'] in eligible and x['split']=='test' for arm in ('own','swap')}
            require(len(c)==len(expected) and {(x['id'],x['arm']) for x in c}==expected,'continuation grid')
            require(all(x['reader']==reader and x['feature']==private[x['id']]['feature'] for x in c),'continuation identity');continuation+=c
        if experiment=='E57':counts+=read(root/'COUNTS.json')
    from native_nla512 import truncation_summary
    truncation=truncation_summary([x for x in native if x['reader']=='nla'])
    return dict(truncation=truncation,lineage={'authority':'8c66b004','native_readouts_per_item':1,'cpu_outputs':spec['cpu_outputs']},private=private,native=native,probes=probes,continuation=continuation,capture_seals=caps,counts=counts,plan=plan)

def judgments(spec,data):
    root=Path(spec['blind_out']);b=verify(root,'BLIND_SEAL.json')
    require(b['source_seal_sha256']==spec['source_seal_sha256'] and b['input_seal_sha256']==spec['input_seal_sha256'] and b['receipt_sha256']==sha(spec['receipt']),'blind binding')
    require(b['rubric_sha256']==sha(Path(__file__).parent/'JUDGE_RUBRIC.md'),'same frozen rubric')
    require(sha(spec['private_key'])==b['private_key_sha256'],'blind key')
    key=read(spec['private_key']);packet={x['id']:x for x in read(root/'JUDGE_PACKET.json')};native={x['id']:x for x in data['native']}
    require(len(key)==len(native) and {x['source_id'] for x in key}==set(native) and len(packet)==len(key),'blind source grid')
    js=Path(spec['judgments']);sealed=verify(js.parent,Path(spec['judgment_seal']).name)
    require(sealed['blind_seal_sha256']==sha(root/'BLIND_SEAL.json') and sealed['rubric_sha256']==b['rubric_sha256'],'judge seal')
    jj=read(js);require(len(jj)==len(key) and {x['id'] for x in jj}==set(packet),'judge grid');byid={x['id']:x for x in jj};out={}
    for x in key:
        n=native[x['source_id']];p=packet[x['opaque_id']];j=byid[x['opaque_id']]
        require(p['readout']==n['text'],'blind text altered');validate_judgment(j,n['text']);out[x['source_id']]=j
    return out

def j_inputs(spec,data):
    root=Path(spec['j_input']);s=verify(root,'J_SEAL.json')
    require(s['bank_seal_sha256']==spec['bank_seal_sha256'] and s['capture_seals']==data['capture_seals'],'J input binding')
    for name in ('reader','labels'):
        source=root/name/'INPUT_SEAL.json'
        verify(source.parent,source.name,s['source_seals'][name])
    rows=read(root/'J_ROWS.json')
    for row,value in rows.items():
        g=value['G3_AUROC'];require(g is None or 0<=g<=1,'J G3 range')
        require(value['J_label'] in ('IN-J','OUT-J','DIFFUSE','NOT APPLICABLE'),'J label')
        require('J_fraction' in value and 'top10' in value,'complete J reader and label inputs')
    return rows

def probe_aucs(data):
    rows={x['feature'] for x in data['probes']};return {r:auc([data['private'][x['id']]['label'] for x in data['probes'] if x['feature']==r],[x['score'] for x in data['probes'] if x['feature']==r]) for r in rows}

def continuation_aucs(data):
    out={}
    for reader in ('oracle','nla'):
        out[reader]={}
        for row in sorted({x['feature'] for x in data['continuation']}):
            out[reader][row]={}
            for arm in ('own','swap'):
                c=[x for x in data['continuation'] if x['reader']==reader and x['feature']==row and x['arm']==arm]
                out[reader][row][arm]=auc([data['private'][x['id']]['label'] for x in c],[sum(x['scores'])/len(x['scores']) for x in c])
    return out


def claim_once(path,experiment,spec_sha):
    from contract56 import dump
    out=Path(path);out.mkdir(parents=True,exist_ok=False)
    dump(out/'ONCE.json',{'experiment':experiment,'invocation':1,'spec_sha256':spec_sha})
    return out
