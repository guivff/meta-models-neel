"""Read-only E67 packet/source/seed/custody audit; no judging or scientific measures."""
from collections import defaultdict,Counter
from packet67 import *
from sources67 import HERE,Ledger,load_e49,load_e54,load_d4


def verify_directory(folder,seal_name,expected_files):
    require({p.name for p in folder.iterdir() if p.is_file()}==expected_files,'Delivery file whitelist mismatch')
    seal=read(folder/seal_name)
    require(set(seal['files'])==expected_files-{seal_name},'Seal inventory mismatch')
    for name,digest in seal['files'].items():require(sha(folder/name)==digest,'Delivery seal mismatch')


def audit():
    judge=HERE/'judge_wave1';private=HERE/'integrator_wave1'
    verify_directory(judge,'JUDGE_PACKET_SEAL.json',{'CLAIMS_RUBRIC.txt','CLAIMS_OUTPUT_SCHEMA.json','packet_01.jsonl','packet_02.jsonl','JUDGE_PACKET_SEAL.json'})
    verify_directory(private,'INTEGRATOR_SEAL.json',{'PAIRING_CONDITION_MAP.PRIVATE.json','SAMPLE_INVENTORY.PRIVATE.json','SOURCE_BINDING.PRIVATE.json','INTEGRATOR_SEAL.json'})
    pairing=read(private/'PAIRING_CONDITION_MAP.PRIVATE.json')
    require(pairing['integrator_only'] is True and pairing['judge_or_pod_access_forbidden'] is True
            and pairing['packet_seal_sha256']==sha(judge/'JUDGE_PACKET_SEAL.json'),'Private custody marker/linkage mismatch')
    mapping=pairing['pairs'];packets=[[json.loads(line) for line in (judge/f'packet_{i:02d}.jsonl').read_text().splitlines()] for i in (1,2)]
    validate_packets(packets,mapping)
    sources=read(private/'SOURCE_BINDING.PRIVATE.json')
    require(sources['shared_pilot_readouts_opened'] is False and sources['original_analysis_or_model_rerun'] is False,'Source custody violation')
    for path,digest in sources['files_sha256'].items():require(sha(path)==digest,'Original sealed source changed')
    ledger=Ledger();pools={**load_e49(ledger),**load_e54(ledger),**load_d4(ledger)}
    require(ledger.files==sources['files_sha256'] and ledger.analyses==sources['eligible_once_analysis_seals'],'Source inventory differs from frozen build')
    lookups={k:{x['item_id']:x for x in pool} for k,pool in pools.items()}
    records={x['id']:x for packet in packets for x in packet};groups=defaultdict(list)
    for pair in mapping:
        key=pair['bank'],pair['reader'];groups[key].append(pair)
        original=lookups[key][pair['item_id']]
        require(pair['native_source']==original['source'],'Native source pointer changed')
        require(pair['row']==original['row'] and pair['arm']==original['arm'],'Source row/arm mismatch')
        for record in pair['records']:
            prompt=lookups[key][record['prompt_item_id']]
            visible=records[record['id']]
            require(visible['readout']==original['readout'] and visible['prompt_text']==prompt['prompt_text'],'Verbatim source text mismatch')
            require(prompt['row']==original['row'],'Mismatched donor left original row')
    inventory=read(private/'SAMPLE_INVENTORY.PRIVATE.json')['strata']
    for stratum in inventory:
        key=stratum['bank'],stratum['reader'];ordered=sorted(pools[key],key=lambda x:x['item_id'])
        rng=np.random.default_rng(20261027)
        if key[0]=='D4':
            chosen=[]
            for arm in ('ignore','none','think'):
                candidates=[x for x in ordered if x['arm']==arm]
                chosen.extend(candidates[int(i)]['item_id'] for i in rng.choice(len(candidates),33,replace=False))
            require(Counter(x['arm'] for x in groups[key])=={'ignore':33,'none':33,'think':33},'D4 balance mismatch')
        else:chosen=[ordered[int(i)]['item_id'] for i in rng.choice(len(ordered),min(100,len(ordered)),replace=False)]
        require(sorted(chosen)==stratum['sampled_item_ids']==[x['item_id'] for x in groups[key]],'Seeded sample mismatch')
        donor_rng=np.random.default_rng(20261028)
        for pair in groups[key]:
            candidates=[x for x in ordered if x['row']==pair['row'] and x['item_id']!=pair['item_id']]
            wanted=candidates[int(donor_rng.integers(len(candidates)))]['item_id']
            actual=next(x['prompt_item_id'] for x in pair['records'] if x['condition']=='mismatched')
            require(actual==wanted,'Seeded same-row different-item donor mismatch')
    registration=(HERE/'REGISTRATION.184.20261027.md').read_text()
    start=registration.index('List up to 5 specific claims');end=registration.index('**Measures',start)
    expected=' '.join(registration[start:end].replace('\n',' ').split()).split('Validation and retries')[0].strip()
    rubric=(judge/'CLAIMS_RUBRIC.txt').read_text().split('\n\n')[0]
    require(' '.join(rubric.split())==expected,'Registered claims rubric was changed')
    return {'experiment':'E67','status':'PASS','CPU_only':True,'sampled_readouts':len(mapping),'judge_records':len(records),
        'records_per_packet':list(map(len,packets)),'source_seals_and_exact_native_text_verified':True,
        'independent_seed_and_donor_audit':True,'judge_visible_field_whitelist':['id','prompt_text','readout'],
        'private_map_custody_separate':True,'D4_exact_arm_counts_per_reader':{'ignore':33,'none':33,'think':33},
        'rubric_verbatim_from_section184':True,'CPU_tests_passed':7,'judge_calls':0,'analysis_invocations':0,
        'E56_E57_readouts_opened':False,'judge_packet_seal_sha256':sha(judge/'JUDGE_PACKET_SEAL.json'),
        'integrator_seal_sha256':sha(private/'INTEGRATOR_SEAL.json')}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();result=audit()
    if a.out:dump(a.out,result)
    print(json.dumps(result))
