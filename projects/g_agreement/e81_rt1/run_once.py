"""Freeze exact local inputs; then one committed-code, terminal-seal-gated analysis.

--freeze only hashes and validates input identity, never joins judgments to truth.
The analysis lock is consumed before any private truth join/effect computation.
Private joins remain local; public artifacts contain only aggregate rows/provenance.
"""
import argparse, datetime, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from collections import Counter
from analysis import analyze, normalize_source_polarity

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
HOME=ROOT/'cache/g_agreement/i2/e81_rt1_v2'
JUDGE=ROOT/'cache/g_agreement/i2/e81_judge_cpu_v3'
CPU=ROOT/'cache/g_agreement/i2/e81_cpu_analysis_v1'
MECH=ROOT.parent/'wt-wmech'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def dump(p,d):
    with Path(p).open('x') as f:json.dump(d,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()
def verify_member(root, seal, member):
    s=read(root/seal);v=s['files'][member];assert sha(root/member)==(v['sha256'] if isinstance(v,dict) else v),member

def paths():
    return dict(joins=JUDGE/'JOIN_MAP.PRIVATE.json',judgments=JUDGE/'judging/E81_judgments/JUDGMENTS.json',
        original=JUDGE/'judging/E81_judgments/ORIGINAL_JUDGMENTS.json',
        judgment_seal=JUDGE/'judging/E81_judgments/RESULT_SEAL.json',
        judge_source=JUDGE/'SOURCE_SEAL.json',terminal_validation=ROOT/'results/g_agreement/i2/E81_FULL_JUDGMENT_TERMINAL_VALIDATION.json',
        original_ids=JUDGE/'ORIGINAL_IDS.json',
        e49=MECH/'results/g_agreement/understand/e49/job/analysis/NATIVE_PRIMARY.json',
        e49_seal=MECH/'results/g_agreement/understand/e49/job/analysis/ANALYSIS_SEAL.json',
        e49_scorer=MECH/'results/g_agreement/understand/e49/job/statements49.py',
        e49_vendor=MECH/'results/g_agreement/understand/e49/job/vendor/e24_statements.py',
        e49_reader_seal=MECH/'cache/g_agreement/understand/e49/verified_section149/out/readers/READER_OUTPUT_SEAL.json',
        e57=MECH/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57/analysis_once/RESULTS.json',
        e57_seal=MECH/'cache/g_agreement/understand/e56_e57/verified_pull_single_v1/e57/analysis_once/ANALYSIS_SEAL.json',
        e59=MECH/'cache/g_agreement/understand/analysis5968_verified/E59/analysis_once/RESULTS.json',
        e59_seal=MECH/'cache/g_agreement/understand/analysis5968_verified/E59/analysis_once/ANALYSIS_SEAL.json',
        e73=ROOT/'cache/g_agreement/i2/e73_analysis_once_final/RESULTS.json',
        e73_seal=ROOT/'cache/g_agreement/i2/e73_analysis_once_final/ANALYSIS_SEAL.json',
        e73_structural_key=ROOT/'cache/g_agreement/i2/e73_judge_start_candidate/prepared/private/JOIN_MAP.json',
        e73_structural_blind_seal=ROOT/'cache/g_agreement/i2/e73_judge_start_candidate/prepared/packet/BLIND_SEAL.json',
        e73_controls_key=ROOT/'cache/g_agreement/i2/e73_controls_judging_candidate/private/JOIN_MAP.json',
        e73_controls_blind_seal=ROOT/'cache/g_agreement/i2/e73_controls_judging_candidate/packet/BLIND_SEAL.json',
        source_inventory=CPU/'ORACLE_SOURCES.PRIVATE.json',source_bindings=CPU/'SOURCE_BINDINGS_VERIFIED.private.json',
        brief=ROOT/'cache/g_agreement/i2/publication/projects/g_agreement/BRIEF_UNDERSTAND.md')

def source_keys(p):
    keys={}
    for kind in ('structural','controls'):
        k=p['e73_'+kind+'_key'];seal=read(p['e73_'+kind+'_blind_seal'])
        assert sha(k)==seal['private_key_sha256']
        for x in read(k):
            if x['reader']=='oracle':
                assert x['source_id'] not in keys
                keys[x['source_id']]=x
    return keys

def validate(p):
    for b in ('e49','e57','e59','e73'):
        verify_member(p[b].parent,p[b+'_seal'].name,p[b].name)
    verify_member(p['judgments'].parent,'RESULT_SEAL.json','JUDGMENTS.json')
    verify_member(p['original'].parent,'RESULT_SEAL.json','ORIGINAL_JUDGMENTS.json')
    s=read(p['judgment_seal']);assert s['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS'
    assert sha(p['e49_scorer'])==read(p['e49'])['regex_sha256']
    assert s['packet_seal_sha256']=='e3b091c5d1ffa9e500b7ce1b311e929d251204c2555e7c8b95b218f07a864ffe'
    assert sha(p['judgment_seal'])=='65030bffdf5b9b245c3afdbbfef371a3ddaa610f8a84199b0df2fe03e8ecd259'
    joins=read(p['joins']);normalize_source_polarity(joins,source_keys(p));assert len(joins)==7376 and len({x['id'] for x in joins})==7376
    assert len(read(p['original_ids']))==1844
    assert {x['id'] for x in read(p['original'])}==set(read(p['original_ids']))
    assert {x['id'] for x in read(p['judgments'])}=={x['id'] for x in joins}
    counts=Counter(x['bank']+'/'+x['row'] for x in joins if x['arm']=='generic')
    assert len(counts)==37 and sum(counts.values())==3688
    for bank,n in [('e49',14),('e57',13),('e59',5),('e73',5)]:
        assert sum(k.startswith(bank+'/') for k in counts)==n
    return counts

def freeze():
    p=paths();counts=validate(p);HOME.mkdir(exist_ok=False)
    refs={k:dict(path=str(v),sha256=sha(v)) for k,v in p.items()}
    # Pin the existing raw files for six probe-only E49 rows, not scored by the
    # old E49 analysis because its additional base-text gate excluded them.
    # §198 E81 explicitly selects by probe only: no rows may be dropped here.
    prior=read(p['e49'])['rows'];inventory=read(p['source_inventory'])['e49']
    extra=sorted(k.split('/',1)[1] for k in counts if k.startswith('e49/') and k.split('/',1)[1] not in prior)
    assert len(extra)==6
    raw={}
    for row in extra:
        records=[v for k,v in inventory.items() if k.startswith(row+':')]
        assert len(records)==84
        files={v['file']:v['sha256'] for v in records};assert len(files)==1
        file,digest=next(iter(files.items()));assert sha(file)==digest
        verify_member(p['e49_reader_seal'].parent,p['e49_reader_seal'].name,row+'/oracle_native.jsonl')
        raw[row]=dict(path=file,sha256=digest)
    manifest=dict(at_utc=now(),status='INPUTS_FROZEN_BEFORE_PRIVATE_JUDGMENT_JOIN',refs=refs,
        code={f.name:sha(f) for f in HERE.glob('*.py')},row_counts=dict(counts),e49_probe_only_supplement=raw,
        primary='generic',secondary='oracle_wording',seed=20261027,draws=2000,
        no_rule_change=True,private_source_paths_publish=False)
    dump(HOME/'INPUT_MANIFEST.private.json',manifest)
    dump(ROOT/'results/g_agreement/i2/E81_RT1_ANALYSIS_PREFLIGHT_V2.json',dict(at_utc=now(),status='CPU_ADAPTER_SYNTHETIC_TESTED_INPUTS_FROZEN',
        analysis_code_sha256=manifest['code'],input_manifest_sha256=sha(HOME/'INPUT_MANIFEST.private.json'),
        judgment_seal_sha256=sha(p['judgment_seal']),rows=37,items_per_arm=3688,
        primary='generic',secondary='oracle_wording',synthetic_tests=13,
        once_lock='cache/g_agreement/i2/e81_rt1_v2/ANALYSIS_ONCE_INTENT.json',
        note='Six probe-passing E49 rows absent from old base-text-gated analysis use unchanged source-sealed regex on already acquired native outputs as explicit E81 baseline supplement. Original E49/E73 analyses not rerun or mutated.',
        actual_outcome_analysis_run=False))
    print('FROZEN: 37 rows, 3688 items/arm; no private judgment join or outcome analysis')

def baselines(p,m,joins):
    out={};e49=read(p['e49'])['rows'];e57=read(p['e57']);e59=read(p['e59']);e73=read(p['e73'])['primary']['readers']['oracle']['states']
    for key in m['row_counts']:
        b,r=key.split('/',1)
        if b=='e49' and r in e49:
            x=e49[r]['oracle'];out[key]=dict(S=x['correct_only_minus_wrong_only'],missing=0,source_kind='E49_ORIGINAL_SEALED_NATIVE_REGEX',N=x['n'])
        elif b in ('e57','e59'):
            d=e57 if b=='e57' else e59;x=d['rates']['oracle|'+r]
            out[key]=dict(S=x['S'],N=x['readouts'],missing=m['row_counts'][key]-x['readouts'],CI95=x['CI95'],source_kind=b.upper()+'_ORIGINAL_SEALED_NATIVE_BLIND_JUDGE')
        elif b=='e73':
            x=e73[r];out[key]=dict(S=x['S'],N=x['kept'],missing=x['UNPARSEABLE'],CI95=x['CI95'],source_kind='E73_EXISTING_FINAL_ANALYSIS_NO_RERUN')
    # Only six already acquired E49 rows missing from old gate-limited result.
    spec=importlib.util.spec_from_file_location('frozen_statements49',p['e49_scorer']);scorer=importlib.util.module_from_spec(spec);spec.loader.exec_module(scorer)
    inv=read(p['source_inventory'])['e49'];supp={}
    for r,ref in m['e49_probe_only_supplement'].items():
        assert sha(ref['path'])==ref['sha256'];raw=[json.loads(l) for l in Path(ref['path']).read_text().splitlines()]
        selected={x['source_id']:x for x in joins if x['bank']=='e49' and x['row']==r and x['arm']=='generic'}
        assert len(raw)==84 and {x['id'] for x in raw}==set(selected)
        cs=Counter()
        for x in raw:
            assert x['text']==inv[x['id']]['text'] and x['block']==44
            cs[scorer.categorize(r,x['text'],selected[x['id']]['label'])]+=1
        supp[r]=dict(counts=dict(cs),N=84,S=(cs['correct_only']-cs['wrong_only'])/84,
            source_kind='E81_PROBE_ONLY_E49_BASELINE_SUPPLEMENT_UNCHANGED_E49_REGEX',missing=0)
        out['e49/'+r]=supp[r]
    assert set(out)==set(m['row_counts'])
    return out,supp

def run():
    m=read(HOME/'INPUT_MANIFEST.private.json')
    for name,digest in m['code'].items():
        f=HERE/name;assert sha(f)==digest
        committed=subprocess.check_output(['git','show','HEAD:'+str(f.relative_to(ROOT))],cwd=ROOT)
        assert hashlib.sha256(committed).hexdigest()==digest,'code not committed: '+name
    p={k:Path(v['path']) for k,v in m['refs'].items()}
    for k,v in m['refs'].items():assert sha(v['path'])==v['sha256'],k
    validate(p)
    with (HOME/'ANALYSIS_ONCE_INTENT.json').open('x') as f:json.dump(dict(started_utc=now(),status='CONSUMED',manifest_sha256=sha(HOME/'INPUT_MANIFEST.private.json'),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()),f)
    joins=normalize_source_polarity(read(p['joins']),source_keys(p));base,supp=baselines(p,m,joins)
    result=analyze(joins,read(p['judgments']),read(p['original']),base)
    out=ROOT/'results/g_agreement/sealed/E81_RT1_ANALYSIS_V2';out.mkdir(exist_ok=False)
    dump(out/'SUMMARY.json',result);dump(out/'ORACLE_BASELINES.json',base);dump(out/'E49_PROBE_ONLY_BASELINE_SUPPLEMENT.json',supp)
    dump(out/'PROVENANCE.json',dict(at_utc=now(),code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        code_sha256=m['code'],source_sha256={k:v['sha256'] for k,v in m['refs'].items()},input_manifest_sha256=sha(HOME/'INPUT_MANIFEST.private.json'),
        original_E73_analysis_reused_without_rerun=True,
        source_polarity='E73 source-sealed 0=A/1=B; otherbanks frozen 1=A/0=B; original private joins unchanged',
        invalid_prior_analysis_seal_sha256=sha(ROOT/'results/g_agreement/sealed/E81_RT1_ANALYSIS/ANALYSIS_SEAL.json'),
        correction='Implementation polarity error only, no rubric/row/threshold/data change; v1 retained INVALID, v2 one corrective recomputation.',scientific_rules_unchanged=True,raw_judgments_shared_commit='488330e3ca7933f22b53bc9693dd4699de47856f'))
    dump(out/'ANALYSIS_SEAL.json',dict(at_utc=now(),status='COMPLETE_ONCE_REVIEW_PENDING',files={f.name:sha(f) for f in out.iterdir()},analysis_intent_sha256=sha(HOME/'ANALYSIS_ONCE_INTENT.json')))
    print(json.dumps(dict(output=str(out),primary=result['primary_verdict'],primary_rule=result['arms']['generic']['rule'],secondary_rule=result['arms']['oracle_wording']['rule'])))

if __name__=='__main__':
    os.umask(0o077)
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--freeze',action='store_true');g.add_argument('--run-once',action='store_true');a=ap.parse_args()
    freeze() if a.freeze else run()
