"""E67 seed-fixed sampling and blind packets; no model or judge calls."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import numpy as np

SAMPLE_SEED = 20261027
DONOR_SEED = 20261028


def require(ok, message):
    if not ok: raise ValueError(message)


def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()


def read(p): return json.loads(Path(p).read_text())


def dump(p, obj):
    with Path(p).open('x') as f:
        f.write(json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)+'\n')


def validate_claims(record, expected_id):
    """Standard-library validation of the frozen claims wire schema."""
    require(isinstance(record,dict) and set(record)=={'id','claims','GENERIC'}, 'Exact claims output fields required')
    require(record['id']==expected_id and isinstance(record['id'],str) and len(record['id'])==32
            and all(c in '0123456789abcdef' for c in record['id']), 'Opaque claims identity mismatch')
    require(type(record['GENERIC']) is bool and isinstance(record['claims'],list)
            and len(record['claims'])<=5 and record['GENERIC']==(len(record['claims'])==0), 'Specific-claim/GENERIC schema mismatch')
    for claim in record['claims']:
        require(isinstance(claim,dict) and set(claim)=={'claim','status'} and isinstance(claim['claim'],str)
                and len(claim['claim'])>=1 and claim['status'] in ('SUPPORTED','CONTRADICTED','UNVERIFIABLE'),
                'Claim text/status schema mismatch')
    return record


def sample(pool, balanced=False):
    require(pool and len({x['item_id'] for x in pool}) == len(pool), 'One native test readout per item required')
    ordered = sorted(pool, key=lambda x:x['item_id'])
    rng = np.random.default_rng(SAMPLE_SEED)
    if not balanced:
        return sorted([ordered[int(i)] for i in rng.choice(len(ordered), min(100,len(ordered)), replace=False)], key=lambda x:x['item_id'])
    arms = sorted({x['arm'] for x in pool})
    require(arms == ['ignore', 'none', 'think'], 'Exact three frozen D4 arms required')
    groups = {a:[x for x in ordered if x['arm']==a] for a in arms}
    n = min(100//len(arms), *(len(v) for v in groups.values()))
    chosen = [groups[a][int(i)] for a in arms for i in rng.choice(len(groups[a]), n, replace=False)]
    return sorted(chosen, key=lambda x:x['item_id'])


def build_packets(pools):
    # Independent streams isolate donor selection from IDs, packet assignment and shuffling.
    assignment = np.random.default_rng(np.random.SeedSequence([DONOR_SEED,1]))
    ids = np.random.default_rng(np.random.SeedSequence([DONOR_SEED,2]))
    packets = [[],[]]; mapping = []; inventory = []; used_ids=set()
    def opaque():
        value=ids.bytes(16).hex(); require(value not in used_ids, 'Opaque ID collision'); used_ids.add(value); return value
    for (bank,reader),pool in sorted(pools.items()):
        require(all(x['bank']==bank and x['reader']==reader for x in pool), 'Mixed source stratum')
        selected=sample(pool, balanced=bank=='D4'); donor_rng=np.random.default_rng(DONOR_SEED)
        rows=defaultdict(list)
        for x in sorted(pool,key=lambda x:x['item_id']): rows[x['row']].append(x)
        item_ids=[]; equal_prompts=0
        for x in selected:
            candidates=[y for y in rows[x['row']] if y['item_id']!=x['item_id']]
            require(candidates, 'No different-item same-row donor')
            donor=candidates[int(donor_rng.integers(len(candidates)))]; first=int(assignment.integers(2)); pair_id=opaque()
            pair={'pair_id':pair_id,'bank':bank,'reader':reader,'row':x['row'],'item_id':x['item_id'], 'arm':x['arm'],
                  'native_source':x['source'],'readout_sha256':hashlib.sha256(x['readout'].encode()).hexdigest(),
                  'truncation_cohort':x['truncation_cohort'],'native_max_new_tokens':x['native_max_new_tokens'],'records':[]}
            for condition,prompt_item,packet_index in [('matched',x,first),('mismatched',donor,1-first)]:
                record={'id':opaque(),'prompt_text':prompt_item['prompt_text'],'readout':x['readout']}
                packets[packet_index].append(record)
                pair['records'].append({'id':record['id'],'packet':packet_index+1,'condition':condition,
                    'prompt_item_id':prompt_item['item_id'],'prompt_row':prompt_item['row'],'prompt_arm':prompt_item['arm'],
                    'prompt_sha256':hashlib.sha256(record['prompt_text'].encode()).hexdigest(),
                    'same_prompt_text_as_matched':prompt_item['prompt_text']==x['prompt_text']})
            equal_prompts += donor['prompt_text']==x['prompt_text']; mapping.append(pair); item_ids.append(x['item_id'])
        inventory.append({'bank':bank,'reader':reader,'eligible_items':len(pool),'sampled_items':len(selected),
            'sampled_item_ids':item_ids,'arm_counts':dict(Counter(x['arm'] for x in selected)) if bank=='D4' else None,
            'mismatched_equal_prompt_text_count':int(equal_prompts),
            'truncation_cohort':selected[0]['truncation_cohort'],'native_max_new_tokens':selected[0]['native_max_new_tokens']})
    for i,packet in enumerate(packets):
        rng=np.random.default_rng(np.random.SeedSequence([DONOR_SEED,3+i]));order=rng.permutation(len(packet));packets[i]=[packet[int(j)] for j in order]
    validate_packets(packets,mapping)
    return packets,mapping,inventory


def validate_packets(packets,mapping):
    require(len(packets)==2 and len(packets[0])==len(packets[1])==len(mapping), 'One record per readout in each packet required')
    records={x['id']:(i+1,x) for i,p in enumerate(packets) for x in p}
    require(len(records)==2*len(mapping), 'Unique independent opaque record IDs required')
    require(all(set(x)=={'id','prompt_text','readout'} and all(isinstance(v,str) for v in x.values())
                and len(x['id'])==32 and all(c in '0123456789abcdef' for c in x['id'])
                for p in packets for x in p), 'Exact judge-visible field whitelist required')
    seen=set()
    for pair in mapping:
        require(len(pair['records'])==2 and {x['condition'] for x in pair['records']}=={'matched','mismatched'}
                and {x['packet'] for x in pair['records']}=={1,2}, 'One condition per separate packet required')
        values=[]
        for key in pair['records']:
            require(key['id'] not in seen, 'Duplicate private mapping');seen.add(key['id'])
            packet,x=records[key['id']];require(packet==key['packet'],'Packet identity mismatch')
            require(hashlib.sha256(x['readout'].encode()).hexdigest()==pair['readout_sha256']
                    and hashlib.sha256(x['prompt_text'].encode()).hexdigest()==key['prompt_sha256'], 'Verbatim record linkage mismatch')
            require(key['prompt_row']==pair['row'],'Donor must have same frozen row')
            require((key['prompt_item_id']==pair['item_id'])==(key['condition']=='matched'), 'Own/different item condition mismatch')
            values.append(x['readout'])
        require(values[0]==values[1],'Readout changed across conditions')
    require(seen==set(records),'Unmapped judge record')
