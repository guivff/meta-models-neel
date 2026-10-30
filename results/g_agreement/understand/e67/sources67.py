"""Read only E67-eligible sealed native readouts; never imports reader runtimes."""
from pathlib import Path
from packet67 import *

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
WORKTREES=ROOT.parent
MECH=WORKTREES/'wt-wmech'
INTERNALS=WORKTREES/'wt-blindspot-internals'


class Ledger:
    def __init__(self):self.files={};self.analyses={}
    def bind(self,path,expected=None):
        path=Path(path).resolve();actual=sha(path)
        require(expected is None or actual==expected,'Source hash mismatch')
        require(str(path) not in self.files or self.files[str(path)]==actual,'Source changed during assembly')
        self.files[str(path)]=actual;return actual
    def verify(self,folder,name,expected=None):
        folder=Path(folder).resolve();self.bind(folder/name,expected);record=read(folder/name)
        require(isinstance(record.get('files'),dict) and record['files'],'Nonempty sealed source required')
        for name,digest in record['files'].items():
            path=(folder/name).resolve();require(path.is_relative_to(folder),'Unsafe source seal path');self.bind(path,digest)
        return record


def lines(path):return [json.loads(x) for x in Path(path).read_text().splitlines()]


def normalized(bank,reader,item,record,path,index):
    require(item['split']=='test' and isinstance(item['text'],str) and isinstance(record['text'],str),'Frozen test prompt and native text required')
    return {'bank':bank,'reader':reader,'row':item['feature'],'item_id':item['id'],'prompt_text':item['text'],
        'readout':record['text'],'arm':item.get('arm'),
        'source':{'path':str(path),'record_index_zero_based':index,'field':'text','native_record_id':record.get('id')},
        'truncation_cohort':'NLA_128_TOKEN_LIMIT_REPORTED_SEPARATELY' if reader=='nla' and bank in ('E49','E54') else 'NOT_THE_128_TOKEN_NLA_COHORT',
        'native_max_new_tokens':(128 if bank in ('E49','E54') else 512) if reader=='nla' else None}


def load_e49(ledger):
    job=MECH/'results/g_agreement/understand/e49/job'
    analysis=ledger.verify(job/'analysis','ANALYSIS_SEAL.json')
    require(analysis.get('status')=='COMPLETE_ONCE','E49 once-only analysis must seal first')
    ledger.analyses['E49']={'path':str(job/'analysis/ANALYSIS_SEAL.json'),'sha256':sha(job/'analysis/ANALYSIS_SEAL.json')}
    ledger.bind(job/'ANALYSIS_SPEC.json');spec=read(job/'ANALYSIS_SPEC.json');root=Path(spec['verified_output'])
    output=ledger.verify(root,'OUTPUT_SEAL.json',analysis['output_seal_sha256']);require(output['status']=='COMPLETE','Incomplete E49 output')
    ledger.bind(spec['verified_receipt']);receipt=read(spec['verified_receipt'])
    require(receipt['verified'] is True and receipt['output_seal_sha256']==sha(root/'OUTPUT_SEAL.json'),'E49 verified receipt mismatch')
    ledger.bind(job/'INPUT_BINDING.json');binding=read(job/'INPUT_BINDING.json')
    ledger.verify(binding['bank_path'],'BANK_SEAL.json',analysis['bank_seal_sha256'])
    ledger.bind(binding['private_items_path'],binding['private_items_sha256'])
    items={x['id']:x for x in read(binding['private_items_path']) if x['split']=='test'}
    seal=ledger.verify(root/'readers','READER_OUTPUT_SEAL.json')
    pools={('E49',r):[] for r in ('oracle','nla')}
    for reader in ('oracle','nla'):
        files=sorted(name for name in seal['files'] if name.endswith('/'+reader+'_native.jsonl'))
        require(files,'Sealed native file set missing')
        for name in files:
            path=root/'readers'/name
            for index,x in enumerate(lines(path)):
                require(x['id'] in items and x['block']==(44 if reader=='oracle' else 42),'E49 native/test identity')
                item=items[x['id']];require(x['feature']==item['feature']==Path(name).parts[0],'E49 row identity')
                pools['E49',reader].append(normalized('E49',reader,item,x,path,index))
        require(len(pools['E49',reader])==len(items)==1344 and {x['item_id'] for x in pools['E49',reader]}==set(items),'Complete E49 native grid required')
    return pools


def load_e54(ledger):
    job=INTERNALS/'results/g_agreement/understand/e5354';analysis_dir=job/'analysis_c9076571_541b23b1'
    analysis=ledger.verify(analysis_dir,'ANALYSIS_SEAL.json')
    require('E54_RESULTS.json' in analysis['files'] and (INTERNALS/'cache/g_agreement/understand/e5354/ANALYSIS_ONCE.json').is_file(),
            'E54 once-only analysis must seal first')
    ledger.analyses['E54']={'path':str(analysis_dir/'ANALYSIS_SEAL.json'),'sha256':sha(analysis_dir/'ANALYSIS_SEAL.json')}
    root=INTERNALS/'cache/g_agreement/understand/e5354/verified_output_d8z2quqdxth285'
    output=ledger.verify(root,'OUTPUT_SEAL.json',analysis['output_seal_sha256']);require(output['status']=='COMPLETE','Incomplete E54 output')
    inp=INTERNALS/'cache/g_agreement/understand/e5354/bound_inputs_21a39c48'
    ledger.verify(inp,'INPUT_SEAL.json',output['input_seal_sha256'])
    items={x['id']:x for x in read(inp/'e54_items.json') if x['split']=='test'}
    pools={('E54',r):[] for r in ('oracle','nla')};path=root/'scores.jsonl'
    for index,x in enumerate(lines(path)):
        if x['bank']!='E54':continue
        require(x['arm']=='native' and x['reader'] in ('olens','nla') and x['id'] in items,'E54 native identity')
        reader='oracle' if x['reader']=='olens' else 'nla';item=items[x['id']]
        require(item['feature']==x['row'],'E54 row mismatch')
        pools['E54',reader].append(normalized('E54',reader,item,x,path,index))
    require(len(items)==168,'Exact E54 test bank required')
    for pool in pools.values():require(len(pool)==168 and {x['item_id'] for x in pool}==set(items),'Complete E54 native grid required')
    return pools


def load_d4(ledger):
    analysis_dir=MECH/'results/g_agreement/understand/e61/d4_stage_analysis'
    analysis=ledger.verify(analysis_dir,'ANALYSIS_SEAL.json');require(analysis['status']=='COMPLETE' and analysis['stage']=='D4','D4 analysis must seal first')
    ledger.analyses['D4']={'path':str(analysis_dir/'ANALYSIS_SEAL.json'),'sha256':sha(analysis_dir/'ANALYSIS_SEAL.json')}
    manifest=MECH/'cache/g_agreement/understand/replan402_verified/E61_D4_MANIFEST.json'
    ledger.bind(manifest,analysis['manifest_sha256']);m=read(manifest);require(m['verified'] is True,'D4 verified manifest required')
    job=MECH/'results/g_agreement/understand/e61/job';ledger.bind(job/'INPUT_BINDING.json');binding=read(job/'INPUT_BINDING.json')
    inp=Path(binding['inputs']);ledger.verify(inp,'INPUT_SEAL.json',binding['input_seal_sha256'])
    items={x['id']:x for x in read(inp/'items.json') if x['display']=='D4'}
    require(len(items)==252 and all(x['text']==x['read_prefix'] and x['ids']==x['read_ids'] for x in items.values()),'D4 read-prefix prompt required')
    pools={('D4',r):[] for r in ('oracle','nla')};seen=set()
    for shard in m['shards']:
        n=shard['shard'];require(n not in seen,'Duplicate D4 shard');seen.add(n)
        path=MECH/f'results/g_agreement/understand/replan402/E61_{n}_BINDING.json';ledger.bind(path);binding=read(path)
        plan_path=Path(binding['inputs'])/'PLAN.json';ledger.bind(plan_path,binding['plan_sha256']);plan=read(plan_path)
        root=Path(shard['stage_path']);seal=ledger.verify(root,'STAGE_SEAL.json',shard['stage_seal_sha256'])
        require(seal['stage']=='D4' and seal['status']=='COMPLETE' and seal['plan_sha256']==binding['plan_sha256'],'D4 stage/source mismatch')
        # The retained D4 pilots are base-probability jobs only. Never open a
        # shared pilot readout file, which could contain unsealed E56/E57 data.
        require(all(j['kind']=='base' for j in plan['retained_pilots'] if j['stage']=='D4'),'Unexpected retained D4 native pilot; hold for a sealed D4-only export')
        for j in plan['jobs']:
            if j['stage']!='D4' or j['kind']=='base':continue
            path=root/'jobs'/f'{j["number"]:06d}.json'
            require(str(path.relative_to(root)) in seal['files'],'Unsealed D4 native job')
            for index,x in enumerate(read(path)):
                reader=x['reader'];require(reader==j['reader'] and reader in ('oracle','nla') and x['item_id'] in items
                    and x['display']=='D4' and x['repeat']==0 and x['relative_position']==0,'D4 native identity')
                item=items[x['item_id']];require(x['arm']==item['arm'],'D4 arm mismatch')
                pools['D4',reader].append(normalized('D4',reader,item,x,path,index))
    require(seen=={0,1,2},'All D4 stage shards required')
    for pool in pools.values():require(len(pool)==252 and {x['item_id'] for x in pool}==set(items),'Complete D4 native grid required')
    return pools


def pending_banks():
    states={}
    for bank in ('E56','E57'):
        seal=MECH/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1'/bank.lower()/'analysis_once/ANALYSIS_SEAL.json'
        states[bank]={'once_analysis_seal':str(seal),'exists':seal.is_file(),
            'status':'AWAITING_SEALED_ONCE_ONLY_ANALYSIS' if not seal.is_file() else 'SEALED_AFTER_WAVE1_SCOPE_CHECK_REQUIRES_SEPARATE_WAVE',
            'readouts_opened_for_E67':False}
    return states
