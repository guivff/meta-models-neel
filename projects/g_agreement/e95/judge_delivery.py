"""Seal original terminal codes and private provenance; never reparse or score."""
from collections import Counter
from pathlib import Path
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def reuse_lineage():
    root=Path(__file__).resolve().parents[3]
    p=root/'results/g_agreement/understand/blind_judge/validator221/E87_HANDOFF.json'
    r=read(p);verify(r['judgment_seal_path'],r['judgment_seal_sha256'])
    require(sha(r['private_join_local_path'])==r['private_join_sha256'],'original E87 join unchanged')
    return dict(handoff=str(p),handoff_sha256=sha(p),judgment_seal=r['judgment_seal_path'],
        judgment_seal_sha256=r['judgment_seal_sha256'],private_join=r['private_join_local_path'],
        private_join_sha256=r['private_join_sha256'],parser='validator221 corrected original codes',
        new_calls=0,reparse=False,resample=False,scope='separate original E87 Oracle lineage; no incomplete E95 NLA reuse introduced')


def normalized(terminal):
    """Exact existing funded_queue E87 flat-code representation."""
    require(len({x['id']for x in terminal})==len(terminal),'unique terminal IDs')
    require(all(x['status']in('KEPT','UNPARSEABLE')for x in terminal),'terminal records only')
    for x in terminal:
        require((x['code']is not None)==(x['status']=='KEPT'),'missing remains missing')
        if x['code']is not None:require(x['code']['id']==x['id'],'original code identity')
    return [x['code']if x['status']=='KEPT'else dict(id=x['id'],category='UNPARSEABLE',values=[],evidence='',first_position=None)for x in terminal]


def append_once(path,event,message):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists()and event in path.read_text():return
    with path.open('a')as f:f.write('\n\n## '+event+'\n\n'+message+'\n')


def deliver(spec_path,private_out,public_out):
    spec=read(spec_path);stage=spec['judging_stage'];job=Path(spec['out']);jp=job/'JUDGMENT_SEAL.json'
    s=verify(jp,sha(jp));require(s['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS'and s['judging_stage']==stage and s['route_verified']is True,'complete registered stage only')
    packet=Path(spec['packet']);verify(packet/'PACKET_SEAL.json',spec['packet_seal_sha256'])
    primary=read(job/'JUDGMENTS.json');old=read(job/'ORIGINAL_JUDGMENTS.json')
    groups=read(packet/'GROUPED_PACKET.json');joins=read(packet/'PRIVATE_JOIN.json')
    require({x['id']for x in primary}=={x['id']for x in groups}=={x['id']for x in joins},'entire admitted stage and original join')
    require({x['id']for x in old}==set(read(packet/'ORIGINAL_IDS.json')),'entire original comparison')
    dest=Path(private_out);pub=Path(public_out)
    if dest.exists():
        previous=verify(dest/'DELIVERY_SEAL.json',sha(dest/'DELIVERY_SEAL.json'))
        require(previous['original_judgment_seal_sha256']==sha(jp),'same once-only original stage delivery')
        receipt=read(pub/'RECEIPT.json')
        require(receipt['private_delivery_seal_sha256']==sha(dest/'DELIVERY_SEAL.json'),'same public/private delivery')
        return receipt
    dest.mkdir(parents=True,exist_ok=False);dest.chmod(0o700)
    flat=normalized(primary);old_flat=normalized(old)
    write(dest/'JUDGMENTS.json',flat);write(dest/'ORIGINAL_JUDGMENTS.json',old_flat)
    positions={x['id']:i for i,x in enumerate(primary)}
    linked=[dict(x,judge_source=dict(seal=str(jp),sha256=sha(jp),member='JUDGMENTS.json',keys=[positions[x['id']],'code']))for x in joins]
    write(dest/'JOIN.PRIVATE.json',linked)
    original_e87=reuse_lineage()
    write(dest/'SOURCE_BINDINGS.PRIVATE.json',dict(spec=str(Path(spec_path).resolve()),spec_sha256=sha(spec_path),judgment_seal=str(jp),judgment_seal_sha256=sha(jp),packet_seal_sha256=spec['packet_seal_sha256'],source_seal=spec['source_seal'],source_seal_sha256=spec['source_seal_sha256'],regex_audit=spec['regex_audit'],regex_audit_sha256=spec['regex_audit_sha256'],stage_inventory=spec['stage_inventory'],stage_inventory_sha256=spec['stage_inventory_sha256'],stage_sources=spec['stage_sources'],route=spec['route'],route_sha256=spec['route_sha256'],custody_receipt=spec['custody_receipt'],custody_receipt_sha256=spec['custody_receipt_sha256'],budget_receipt=spec['budget_receipt'],budget_receipt_sha256=spec['budget_receipt_sha256'],continuation=spec.get('continuation'),original_E87_reuse_lineage=original_e87))
    write(dest/'DELIVERY_SEAL.json',dict(experiment='E95',judging_stage=stage,status='COMPLETE_TERMINAL_STAGE_NO_ANALYSIS',parser_contract='E87 validator-corrected §221 item1',original_judgment_seal_sha256=sha(jp),route_verified=True,labels_cpu_only=True,raw_git_export=False,first_output_utc=s['first_output_utc'],files={p.name:sha(p)for p in dest.iterdir()if p.is_file()}))
    for p in dest.iterdir():p.chmod(0o600)
    pub.mkdir(parents=True,exist_ok=True)
    counts=read(job/'COUNTS.json')
    public_cost={k:v for k,v in counts['cost'].items()if k not in('upper_bound_provenance','legacy_ledger_summary')}
    receipt=dict(experiment='E95',judging_stage=stage,status='COMPLETE_TERMINAL_STAGE_NO_ANALYSIS',primary_groups=len(flat),original_comparison_groups=len(old_flat),primary_categories=dict(Counter(x['category']for x in flat)),original_categories=dict(Counter(x['category']for x in old_flat)),missing_remain_missing=True,private_delivery_seal=str(dest/'DELIVERY_SEAL.json'),private_delivery_seal_sha256=sha(dest/'DELIVERY_SEAL.json'),original_judgment_seal_sha256=sha(jp),packet_seal_sha256=spec['packet_seal_sha256'],source_seal_sha256=spec['source_seal_sha256'],route_sha256=spec['route_sha256'],regex_audit_sha256=spec['regex_audit_sha256'],stage_inventory_sha256=spec['stage_inventory_sha256'],parser_contract='E87 validator-corrected §221 item1',original_E87_reuse_seal_sha256=original_e87['judgment_seal_sha256'],original_E87_reparsed=False,cumulative_E95_bank_cost=public_cost,original_counts_sha256=sha(job/'COUNTS.json'),first_output_utc=s['first_output_utc'],raw_readouts_published=False,private_joins_published=False,labels_published=False,analysis_run=False,placebo_target_binding='original source join has no fabricated targets; analyst binds exact registered placebo truth lineage before scientific use')
    write(pub/'RECEIPT.json',receipt);write(pub/'PUBLIC_SEAL.json',dict(experiment='E95',judging_stage=stage,private_delivery_seal_sha256=sha(dest/'DELIVERY_SEAL.json'),files={'RECEIPT.json':sha(pub/'RECEIPT.json')}))
    return receipt
