"""Freeze E129 candidate facts, donors and matched prefixes before any model output."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile
import numpy as np
from projects.g_agreement.e100.contract import read,write,sha
from projects.g_agreement.e127.build import prefix_pair
SEED=20261031
SOURCE_URL='https://download.geonames.org/export/dump/countryInfo.txt'
# Fixed sovereign-country catalog, authored before model output. Excludes original
# France/Peru and multi-capital/disputed/recent-transition cases (not performance).
ISO_CATALOG='AD AE AF AG AL AM AO AR AT AU AZ BA BB BD BE BF BG BH BI BJ BN BS BT BW BY BZ CA CD CF CG CI CL CM CN CO CR CU CV CY CZ DE DJ DK DM DO DZ EC EE ER ES ET FI FJ FM GA GB GD GE GH GM GN GT GW GY HN HR HT HU IE IN IQ IR IS IT JM JO JP KE KG KH KI KM KN KP KR KW KZ LA LB LC LI LR LS LT LU LV LY MA MC MD ME MG MH MK ML MM MN MR MT MU MV MW MX MY MZ NA NE NG NI NL NO NP NZ OM PA PG PH PK PL PT PW PY QA RO RS RU RW SA SB SC SE SG SI SK SL SM SN SO SR SS ST SV SY TD TG TH TJ TL TM TN TO TR TT TV TZ UA UG US UY UZ VC VE VN VU WS ZM ZW'.split()
TEMPLATE=('The clerk checked the dated record. The subject was the invoice. Only complete the current question.\n'
          'Archived question: The capital of {donor_entity} is\nEnd of archived question.\n'
          'Current question: The capital of {entity} is')


def facts_from_source(text):
    records={}
    for line in text.splitlines():
        if not line or line.startswith('#'):continue
        cells=line.split('\t')
        if len(cells)<6:raise ValueError('GeoNames countryInfo schema')
        iso,entity,value=cells[0],cells[4].strip(),cells[5].strip()
        if iso in ISO_CATALOG:
            if not entity or not value or iso in records:raise ValueError('unique source fact')
            records[iso]=dict(iso=iso,entity=entity,value=value,relation='capital')
    if set(records)!=set(ISO_CATALOG):raise ValueError('entire predeclared catalog must exist; no silent country dropping')
    return [records[i]for i in sorted(records)]


def compose(facts,tok):
    """All candidate items retained, seeded order; no behaviour/readout selection."""
    if len(facts)<84:raise ValueError('at least84 distinct fresh candidate facts')
    if len({x['iso']for x in facts})!=len(facts):raise ValueError('unique primary facts')
    rng=np.random.default_rng(SEED);facts=[facts[i]for i in rng.permutation(len(facts))]
    pool={x['entity']:x['value']for x in facts};public=[];labels=[]
    for rank,x in enumerate(facts):
        donors=[y for y in facts if y['iso']!=x['iso']and y['value']!=x['value']]
        # Fixed seeded first feasible donor: feasibility is exact neutral-template
        # token-length matching ONLY, before model calls; never remove a candidate.
        binding=None
        for attempt,k in enumerate(rng.permutation(len(donors))):
            donor=donors[k];text=TEMPLATE.format(entity=x['entity'],donor_entity=donor['entity'])
            ids=tok.encode(text,add_special_tokens=False)
            try:
                updated,neutral,b=prefix_pair(text,ids,donor['value'],pool,tok,rng)
            except ValueError as exc:
                if str(exc).startswith('no genuine unrelated fact'):continue
                raise
            binding=b;break
        if binding is None:raise ValueError('cannot bind neutral control for a candidate; no data-dependent drop or padding')
        base=f'E129-{rank:04d}';conditions={}
        for condition,tokens in [('context_update',updated),('neutral_prefix',neutral),('none',ids)]:
            ident=f'{base}:{condition}';conditions[condition]=ident
            public.append(dict(id=ident,base_id=base,row='fact_recall',condition=condition,ids=tokens,
                               read_index=len(tokens)-1,candidate_ids=[],input_index=len(public)))
        labels.append(dict(base_id=base,rank=rank,iso=x['iso'],relation='capital',old_value=x['value'],
                           donor_iso=donor['iso'],donor_entity=donor['entity'],
                           donor_matching_attempts=attempt+1,condition_ids=conditions,**binding))
    return public,labels


def build(source_file,out,tokenizer_root):
    from transformers import AutoTokenizer
    source_file,out,tokenizer_root=map(Path,(source_file,out,tokenizer_root))
    tokenizer_sha=sha(tokenizer_root/'tokenizer.json')
    if tokenizer_sha!='5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42':raise ValueError('original pinned Qwen tokenizer')
    tok=AutoTokenizer.from_pretrained(tokenizer_root,local_files_only=True,trust_remote_code=False)
    facts=facts_from_source(source_file.read_text());items,labels=compose(facts,tok)
    out.mkdir(parents=True,exist_ok=False);pub=out/'candidates';cpu=out/'cpu_only';pub.mkdir();cpu.mkdir()
    write(pub/'items.json',items)
    write(pub/'SCREEN_ORDER.json',[x['condition_ids']['none']for x in labels])
    write(pub/'MANIFEST.json',dict(experiment='E129',status='PRESELECTION_CANDIDATES_ONLY_NOT_LAUNCH_INPUT',seed=SEED,
       candidate_items=len(labels),candidate_cells=len(items),required_selected_n=84,selected_n=None,selection_executed=False,
       selection='first84 in frozen seeded order whose unprefixed3-token answer classifies OLD=true by unchanged parse_target_answer',
       new_value='seeded other candidate capital value; first donor with exact matched unrelated neutral prefix; no candidate removed',
       source_url=SOURCE_URL,source_sha256=sha(source_file),tokenizer_sha256=tokenizer_sha,hook_enabled=False,
       greedy_max_new_tokens=3,oracle_layers=[44,52,60],candidate_pair_logits='not a registered E129 measure; empty lists, greedy text only',
       model_calls=0,labels_on_pod=False,unused_original_bank_items=0))
    write(pub/'INPUT_SEAL.json',dict(experiment='E129',status='CANDIDATE_POOL_SEALED_SELECTION_PENDING',labels_on_pod=False,
       sealed_at_utc=datetime.now(timezone.utc).isoformat(),files={p.name:sha(p)for p in pub.iterdir()}))
    write(cpu/'LABELS.PRIVATE.json',labels)
    write(cpu/'LABEL_SEAL.json',dict(experiment='E129',input_sha256=sha(pub/'INPUT_SEAL.json'),source_sha256=sha(source_file),
       files={'LABELS.PRIVATE.json':sha(cpu/'LABELS.PRIVATE.json')}))
    with tarfile.open(out/'candidates.tar.gz','w:gz',compresslevel=1)as t:
        for p in pub.iterdir():t.add(p,arcname=p.name)
    return dict(experiment='E129',status='CANDIDATE_POOL_SEALED_SELECTION_PENDING_NOT_LAUNCHED',candidate_items=len(labels),
       candidate_cells=len(items),selected_n=None,selection_executed=False,seed=SEED,model_calls=0,GPU_calls=0,
       public_root=str(pub.resolve()),input_sha256=sha(pub/'INPUT_SEAL.json'),public_archive=str((out/'candidates.tar.gz').resolve()),
       public_archive_sha256=sha(out/'candidates.tar.gz'),cpu_label_seal=str((cpu/'LABEL_SEAL.json').resolve()),
       cpu_label_seal_sha256=sha(cpu/'LABEL_SEAL.json'),labels_stage_to_pod=False,source_url=SOURCE_URL,source_sha256=sha(source_file))
