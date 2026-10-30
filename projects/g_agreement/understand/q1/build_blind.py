"""Export Q1's sealed full grid into E13's blind three-field schema."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from projects.g_agreement.understand.e13 import io as I

OUT=I.ROOT/'results/g_agreement/understand/q1'
CACHE=I.ROOT/'cache/g_agreement/understand/q1'
SOURCE=I.ROOT/'cache/g_agreement/understand/q1-readonly-voveudjvl0ph34/free'
EXPECTED_SEAL='dca8bc44466b6051817c9b6049ee8248aa58c9c76869ff4fbd09502429577e32'


def build():
    if I.sha(SOURCE/'FREE_SEAL.json')!=EXPECTED_SEAL:
        raise ValueError('unexpected producer seal')
    seal=I.read(SOURCE/'FREE_SEAL.json')
    if seal['status']!='Q1_ALL_480_RAW_READOUTS_SEALED_BEFORE_CODING':
        raise ValueError('free phase incomplete')
    for name,sha in seal['files'].items():
        if Path(name).is_absolute() or '..' in Path(name).parts or I.sha(SOURCE/name)!=sha:
            raise ValueError('source seal mismatch')
    sample_receipt=I.read(OUT/'SAMPLE_RECEIPT.json')
    keypath=Path(sample_receipt['key_cache_only'])
    if I.sha(keypath)!=sample_receipt['key_sha256']:
        raise ValueError('original sixty-item key changed')
    request_hash=I.sha(OUT/'E16_ITEM_REQUEST.json')
    if request_hash!=sample_receipt['item_request_sha256'] or I.sha(SOURCE/'E16_ITEM_REQUEST.json')!=request_hash or seal['q1_request_sha256']!=request_hash:
        raise ValueError('not original Q1 request')
    provenance=I.read(SOURCE/'provenance.json')
    if provenance['q1_request_sha256']!=request_hash or provenance['sealed_before_any_coding'] is not True or provenance['Q1_keys_accessed'] is not False:
        raise ValueError('provenance does not bind blind original request')
    plan=I.read(OUT/'SAMPLING_PLAN.json')
    for bank,ref in plan['bank_refs'].items():
        if provenance['source_banks'][bank]['bank_input_seal_sha256']!=ref['files']['INPUT_SEAL.json']:
            raise ValueError('source bank lineage changed')
    if provenance['decoding']['temperature']!=[0,.7,.7,.7] or provenance['decoding']['samples']!=4:
        raise ValueError('wrong decoding modes')
    items=I.rows(keypath);keys={r['id']:r for r in items}
    if len(items)!=60 or len(keys)!=60:
        raise ValueError('sample size')
    raw=I.rows(SOURCE/'raw.jsonl')
    expected={(item,reader,sample) for item in keys for reader in ['olens','nla'] for sample in range(4)}
    actual=[(r['id'],r['reader'],r['sample']) for r in raw]
    if len(raw)!=480 or len(set(actual))!=480 or set(actual)!=expected:
        raise ValueError('missing/extra/duplicate native cells')
    paired=[]
    for r in raw:
        item=keys[r['id']];native=44 if r['reader']=='olens' else 42
        if r['layer']!=native or not isinstance(r['raw'],str):
            raise ValueError('invalid site/raw')
        opaque=I.rank('q1-opaque',r['id'],r['reader'],r['sample'])
        blind={'id':opaque,'question':item['question'],'readout':r['raw']}
        private={'id':opaque,'item':r['id'],'feature':item['feature'],'tier':item['tier'],'bank':item['bank'],
                 'reader':'oracle' if r['reader']=='olens' else 'nla','layer':r['layer'],'sample':r['sample'],
                 'value':item['value'],'truth_AB':item['truth_AB'],'readout_sha256':I.digest(r['raw'])}
        paired.append((blind,private))
    paired.sort(key=lambda x:I.rank('q1-order',x[0]['id']))
    blind=[r[0] for r in paired];private=[r[1] for r in paired]
    if len({r['id'] for r in blind})!=480 or any(set(r)!={'id','question','readout'} for r in blind):
        raise ValueError('blind identity/schema')
    I.jsonl(CACHE/'blind_sample.jsonl',blind)
    I.jsonl(CACHE/'KEY.DO_NOT_SHARE.jsonl',private)
    I.save(OUT/'BLIND_SAMPLE_RECEIPT.json',dict(status='ALL480_NATIVE_Q1_READOUTS_READY_FOR_BLIND_CODING',at=datetime.now(timezone.utc).isoformat(),seed=I.SEED,
        sample=str(CACHE/'blind_sample.jsonl'),sample_sha256=I.sha(CACHE/'blind_sample.jsonl'),key_cache_only=str(CACHE/'KEY.DO_NOT_SHARE.jsonl'),key_sha256=I.sha(CACHE/'KEY.DO_NOT_SHARE.jsonl'),
        n=480,n_items=60,readers=dict(Counter(r['reader'] for r in private)),tiers=dict(Counter(r['tier'] for r in private)),
        empty_raw=sum(not r['readout'].strip() for r in blind),all_raw_preserved=True,exact_schema=['id','question','readout'],
        source_free_seal_sha256=EXPECTED_SEAL,source_raw_sha256=I.sha(SOURCE/'raw.jsonl'),source_provenance_sha256=I.sha(SOURCE/'provenance.json'),source_directory=str(SOURCE),
        original_item_request_sha256=request_hash,original_item_key_sha256=I.sha(keypath),amendment='39f7bd78',human_subset_exported=False,unblinded_pass=False,
        question_scope='Frozen question with exact source prefix and both alternatives; no reader, true value, tier, sample index, score or path metadata.',
        api_calls=0,gpu_hours=0,code_sha256=I.sha(Path(__file__))))
    print('480 Q1 native readouts exported; exact schema; no human subset')

if __name__=='__main__':build()
