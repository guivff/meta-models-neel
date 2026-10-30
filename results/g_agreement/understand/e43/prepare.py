"""Freeze source coverage and denominators without running any mention detector."""
import hashlib, json
from pathlib import Path
from collections import Counter, defaultdict
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
CORE=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/blindspot-worktree/cache/g_agreement')
SHARED=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_agreement')
OLD=Path('/Users/guivff/Documents/Neel_Exploration/wt-blindspot/cache/g_agreement/understand')
LENS=Path('/Users/guivff/Documents/ChatGPT/Activation_Readers/wt-wlens/cache/g_agreement/understand')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def lines(p): return [json.loads(x) for x in Path(p).read_text().splitlines() if x]
def save(p,x): Path(p).write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')

def prepare():
    if (HERE/'COVERAGE_SEAL.json').exists(): raise RuntimeError('coverage already frozen')
    refs={}; sources=[]; records={}; labels={}; definitions={}
    def pin(p, expected=None):
        p=Path(p); h=sha(p)
        if expected is not None and h!=expected: raise ValueError('hash mismatch: '+str(p))
        refs[str(p)]=h; return h
    def member(seal,name):
        pin(seal); s=read(seal); p=seal.parent/name; pin(p,s['files'][name]); return p
    def source(name,seal,file,scope):
        p=member(seal,file); sources.append(dict(name=name,seal_sha256=sha(seal),member=file,sha256=sha(p),scope=scope)); return p
    for bank,folder in [('w1','w1-bank-v2'),('w1b','w1b-bank-v1')]:
        mp=CORE/'blindspot'/folder/'manifest.json'; pin(mp); m=read(mp)
        ip=member(mp,'items.DO_NOT_STAGE.jsonl')
        definitions[bank]=m['rows']
        for r in lines(ip):
            d=m['rows'][r['feature']]
            if r['value'] not in d['values']: continue  # Non-binary ordinal rows have no A/B labels.
            labels[bank,r['id']]={'label': 'A' if r['value']==d['values'][0] else 'B','row':r['feature'],'class':d['class'],'split':r['split']}
            assert r['value'] in d['values']
    def add(bank,item,reader,layer,text,src,arm='native',code=None,truth=None):
        assert isinstance(text,str)
        meta=labels.get((bank,item))
        if meta is None: raise ValueError('missing label '+bank+':'+item)
        if truth is not None: assert truth==meta['label']
        key=(bank,meta['row'],reader,layer,arm,item,text)
        if key not in records: records[key]=dict(bank=bank,id=item,reader=reader,layer=layer,arm=arm,text=text,**meta,sources=[],codes=[])
        r=records[key]
        if src not in r['sources']: r['sources'].append(src)
        if code and code not in r['codes']:r['codes'].append(code)
    specs=[('W1 Oracle','w1','blindspot/w1-units/priority/target','unasked.target.jsonl'),('W1 NLA','w1','blindspot/w1-units/priority/nla','unasked.nla.jsonl'),('W1b NLA','w1b','blindspot/w1b-units/ybqkwg5zoc3vwg/w1b-out/nla','unasked.nla.jsonl'),('E13a Oracle','w1b','understand/e13a-units/jivab2a1xudpkk/e13a-out','unasked.target.jsonl')]
    for name,bank,rel,fn in specs:
        p=source(name,CORE/rel/'FREE_SEAL.json',fn,'primary native')
        for r in lines(p):
            if r['reader'] not in ['olens','nla']: continue
            add(bank,r['id'],'oracle' if r['reader']=='olens' else r['reader'],r['layer'],r['raw'],name)
    # Q1/Q2 are sealed sampled views; attach frozen code references, never recode.
    code_seal=SHARED/'understand/claude_codes_q/CLAUDE_CODES_SEAL.json';pin(code_seal); cs=read(code_seal)
    q1rec=ROOT/'results/g_agreement/understand/q1/BLIND_SAMPLE_RECEIPT.json';q2rec=ROOT/'results/g_agreement/understand/q2/SAMPLES_RECEIPT.json';pin(q1rec);pin(q2rec)
    for sample in ['q1','q2a','q2b']:
        rec=read(q1rec) if sample=='q1' else read(q2rec)[sample]
        sp=Path(rec['sample'] if sample=='q1' else rec['path']);kp=Path(rec['key_cache_only'])
        pin(sp,rec['sample_sha256'] if sample=='q1' else rec['sha256']);pin(kp,rec['key_sha256'])
        cname='q1_passA' if sample=='q1' else sample;cp=code_seal.parent/(cname+'.CLAUDE_CODES.jsonl');pin(cp,cs['samples'][cname]['sha256'])
        coding_input=OLD/'q1/pass_a.jsonl' if sample=='q1' else sp;pin(coding_input,cs['samples'][cname]['input_sha256'])
        sm={r['id']:r for r in lines(sp)}
        sources.append(dict(name=sample,seal_sha256=sha(q1rec if sample=='q1' else q2rec),member=sample,sha256=sha(sp),key_sha256=sha(kp),code_seal_sha256=sha(code_seal),code_sha256=sha(cp),scope='primary native; Q2b dose zero only'))
        for k in lines(kp):
            if sample=='q2b' and k['dose']!=0:continue
            text=sm[k['id']]['readout'];assert hashlib.sha256(text.encode()).hexdigest()==k['readout_sha256']
            add('w1b' if k.get('bank')=='s84' else k.get('bank','w1'),k['item'],k['reader'],k['layer'],text,sample,code={'path':str(cp),'id':k['id']},truth=k.get('truth_AB',k.get('source_truth_AB')))
    qseal=SHARED/'understand/q1-readonly-voveudjvl0ph34/free/FREE_SEAL.json'
    source('Q1 generation',qseal,'raw.jsonl','covered by Q1 sample and key')
    for seal in sorted((CORE/'understand/e24g').glob('*/inc/*/L*/SCORE_SEAL.json')):
        layer=int(seal.parent.name[1:]); name='E24/'+seal.parent.parent.name+'/'+seal.parent.name
        p=source(name,seal,'readouts.jsonl','primary' if layer==44 else 'descriptive other layer')
        for r in lines(p): add('w1',r['id'],'oracle',layer,r['C4'],name)
    for seal in sorted((LENS/'e28').glob('*/final/out/*/SCORE_SEAL.json')):
        if 'free.400.jsonl' not in read(seal)['files']:continue
        arm='E28/'+seal.parent.name; p=source(arm,seal,'free.400.jsonl','descriptive trained step 400; no step-0 free readouts')
        for r in lines(p):add('w1',r['id'],'oracle',44,r['raw'],arm,arm=arm)
    probe=ROOT/'results/g_agreement/blindspot/w1/analysis/probe.oof.jsonl'
    member(probe.parent/'ANALYSIS_SEAL.json',probe.name)
    # Probe availability only; no AUROC or mention calculation in preparation.
    probe_keys={(r['id'],r['layer']) for r in lines(probe)}
    data=sorted(records.values(),key=lambda r:(r['bank'],r['row'],r['reader'],r['layer'],r['arm'],r['id'],r['text']))
    groups=defaultdict(list)
    for r in data:groups[(r['bank'],r['row'],r['reader'],r['layer'],r['arm'])].append(r)
    # Detector row membership is fixed metadata, not a detector invocation.
    import sys
    sys.path.insert(0,str(ROOT))
    from projects.g_agreement.understand.e24_statements import PATTERNS
    detector=ROOT/'projects/g_agreement/understand/e24_statements.py';pin(detector)
    coverage=[]
    for key,rs in sorted(groups.items()):
        bank,row,reader,layer,arm=key;ids={r['id'] for r in rs};missing=[i for i in ids if bank!='w1' or (i,layer) not in probe_keys]
        coverage.append(dict(bank=bank,row=row,reader=reader,layer=layer,arm=arm,classification=rs[0]['class'],deduplicated_readouts=len(rs),unique_items=len(ids),label_counts=dict(Counter({i:next(r['label'] for r in rs if r['id']==i) for i in ids}.values())),missing_probe_items=len(missing),missing_detector_readouts=sum(row not in PATTERNS and not r['codes'] for r in rs),primary=arm=='native' and layer==({'oracle':44,'nla':42}[reader])))
    excluded=[{'set':'E36 / W12','reason':'sealed asked and continuation channels; no native free readout channel'}, {'set':'Q2c / E6','reason':'added continuation prompt; not native unprompted'}, {'set':'Q2b nonzero dose','reason':'edited activations; not primary native; edited truth unobserved'}, {'set':'Q2d GLM','reason':'different base model; no completed native Qwen pool'}, {'set':'old R / S-series free text','reason':'no matching sealed native item-label/probe package located; not silently imported'}, {'set':'E28 step 0','reason':'asked.0 exists; free.0 absent'}, {'set':'E39 step 800','reason':'adapted extension outside E28; no baseline free readout pool'}]
    protocol=dict(registration='§153; clarification 1 (69eaa384)',date='2026-10-26',dedup='within bank, row, reader, layer, arm: item id and exact raw text; no wrapper cleanup',primary_layers={'oracle':44,'nla':42},silent_primary='unique items with every deduplicated readout silent',silent_descriptive='unique items with at least one silent readout',minimum_silent_items=20,both_labels_required=True,missing_policy='no imputation; incomplete detector coverage or missing matching probes makes row NOT EVALUABLE for R1',detector='E24 statement for its 19 structure rows; otherwise existing §107 rater-1 pass-A codes only',R1='strict majority of evaluable primary Oracle structure bank-rows with full-pool probe >= .90 meet mention <= .05 and all-silent probe >= .85; zero eligible rows => NOT EVALUABLE',probe_orientation='value A positive; sealed true (not mismatched) probe predictions at reader block; no refit',value_correct='(correct-only minus wrong-only) / deduplicated readouts; both/unclear mentions contribute zero',no_new_judge=True,analysis_owner='integrator once only')
    save(HERE/'PROTOCOL.json',protocol);save(HERE/'INVENTORY.json',dict(sources=sources,excluded=excluded,rows=coverage))
    save(HERE/'cache/READOUTS.json',data);save(HERE/'cache/SOURCE_PINS.json',refs);save(HERE/'cache/PROBE_PATH.json',str(probe))
    files=['PROTOCOL.json','INVENTORY.json','cache/READOUTS.json','cache/SOURCE_PINS.json','cache/PROBE_PATH.json']
    save(HERE/'COVERAGE_SEAL.json',dict(status='COVERAGE_FROZEN_BEFORE_E43_MENTION_OR_AUROC_COMPUTATION',files={f:sha(HERE/f) for f in files},source_count=len(sources),deduplicated_readouts=len(data)))
    print('Frozen',len(sources),'source sets;',len(coverage),'bank-row-reader-arm groups;',len(data),'deduplicated readouts')
if __name__=='__main__':prepare()
