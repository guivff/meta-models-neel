"""Freeze metadata, paths and source hashes before feature extraction or statistics."""
import json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4];OUT=ROOT/'results/g_agreement/understand/e48'
C=ROOT.parent/'blindspot-worktree';T=ROOT.parent/'wt-wtext';P=T/'results/g_agreement/understand'
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in Path(p).read_text().splitlines()]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,x):
    with Path(p).open('x') as f:json.dump(x,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def main():
    pins={};seals=[]
    def pin(p,expected=None):
        p=Path(p).resolve();h=sha(p)
        if expected is not None and h!=expected:raise ValueError('source hash '+str(p))
        pins[str(p)]=h;return str(p)
    def member(folder,seal,name):
        folder=Path(folder);pin(folder/seal);d=read(folder/seal);seals.append(str((folder/seal).resolve()))
        return pin(folder/name,d['files'][name])
    bank=C/'cache/g_agreement/blindspot/w1-bank-v2';manifest=read(bank/'manifest.json');pin(bank/'manifest.json')
    w1items=member(bank,'manifest.json','items.DO_NOT_STAGE.jsonl');w1spec=member(bank,'manifest.json','templates.json')
    scope={k:v for k,v in manifest['rows'].items() if v['kind']=='binary'}
    config={'W1':{'items':w1items,'spec':w1spec,'rows':sorted(scope),'structure':sorted(k for k,v in scope.items() if v['class']!='semantic'),'scores':member(C/'cache/g_agreement/blindspot/w1-assembled/target','SCORE_SEAL.json','scores.target.jsonl')}}
    b=P/'e36/cache/v2_25_2026-10-25';o=P/'e36/cache/verified_pull_149/out';plan=read(o/'plan.json');member(o,'OUTPUT_SEAL.json','plan.json')
    config['E36']={'items':member(b,'PREPARED_SEAL.json','items.input.jsonl'),'labels':member(b,'PREPARED_SEAL.json','labels.DO_NOT_STAGE.jsonl'),'spec':pin(P/'e36/ROW_DEFINITIONS.json'),'rows':plan['scope']['rows'],'structure':plan['scope']['structure_rows'],'scores':member(o,'OUTPUT_SEAL.json','scores.jsonl')}
    b=T/'cache/g_agreement/blindspot/w12-freeze-2833a200';spec=read(b/'templates.json')
    config['W12']={'items':member(b,'FREEZE.json','items.jsonl'),'spec':member(b,'FREEZE.json','templates.json'),'rows':sorted(spec),'structure':sorted(spec),'scores':member(C/'cache/g_agreement/blindspot/w12/gxzcklh33qpr8h/final/out/W12_RUN','SCORE_SEAL.json','scores.jsonl')}
    b=C/'cache/g_agreement/understand/e24-stage-v1';items=rows(b/'items.input.jsonl');spec=read(b/'templates.json')
    layer=next((C/'cache/g_agreement/understand/e24g').glob('*/inc/E24G_S0/L44/SCORE_SEAL.json')).parent
    # Canonical slot0, exactly as the sealed E24 analysis; other anchor is not pooled.
    config['E24@44']={'items':member(b,'INPUT_SEAL.json','items.input.jsonl'),'spec':member(b,'INPUT_SEAL.json','templates.json'),'rows':sorted({r['feature'] for r in items}),'structure':sorted(r for r in {x['feature'] for x in items} if manifest['rows'][r]['class']!='semantic'),'scores':member(layer,'SCORE_SEAL.json','readouts.jsonl'),'canonical':'mode-G slot0 L44, section159 analysis; not original attempt1'}
    config['E24@44']['labels']=config['W1']['items']
    for bank,c in config.items():
        rr=rows(c['items']);c['item_ids']={r: {split:sorted(x['id'] for x in rr if x['feature']==r and x['split']==split) for split in ['dev','test']} for r in c['rows']}
        for r,sp in c['item_ids'].items():
            if any(len(v)!=84 for v in sp.values()):raise ValueError('84 dev/test metadata: '+bank+':'+r)
    e43=member(P/'e43','COVERAGE_SEAL.json','cache/READOUTS.json')
    # Pin E43's already verified source manifest without re-running its detector.
    sourcepins=read(P/'e43/cache/SOURCE_PINS.json')
    for name,h in sourcepins.items():pin(name,h)
    pin(P/'e43/cache/SOURCE_PINS.json')
    pool=read(e43);shownscope=sorted({(r['bank'],r['row'],r['reader'],r['layer']) for r in pool if r['arm']=='native' and r['split']=='test' and r['layer']==({'oracle':44,'nla':42}[r['reader']])})
    token=Path('/Users/guivff/Documents/Neel_Exploration/mats-minis/cache/g_assets/Qwen__Qwen3.6-27B/tokenizer.json');pin(token,'5f9e4d4901a92b997e463c1f46055088b6cca5ca61a6522d1b9f64c4bb81cb42')
    mirror='/Users/guivff/Documents/Neel_Exploration/activation-readers'
    for rev,name,dest in [('b5ff6b5a','BRIEF_UNDERSTAND.md','REGISTRATION.md'),('34976db5','REVIEW_HYPOTHESES_2026-10-26.md','REVIEW_HYPOTHESES_2026-10-26.md')]:
        text=subprocess.check_output(['git','-C',mirror,'show',rev+':projects/g_agreement/'+name],text=True)
        if dest=='REGISTRATION.md':text=text[text.index('## §162'):]
        (OUT/dest).write_text(text);pin(OUT/dest)
    plan={'experiment':'E48','authority':'§162 b5ff6b5a','review_commit':'34976db5','seed':20261026,'CPU_only':True,'banks':config,'score_orientation':'first frozen value A positive; mean across original asked phrasings; true arm, Oracle block44','scope_policy':'All binary W1 rows, all25 E36 rows, all6 W12 rows; no probe-performance eligibility filter. Ordinal W1 rows excluded from binary AUROC. No score-dependent exclusions. E24 canonical slot0. Parts2 correlations: all structure bank-rows W1/E36/W12, including below-chance clause_embedding.','features':{'presence':'last32 stored target token IDs, binary presence, punctuation retained','counts':'same token-ID vocabulary, counts','words':'decode last32 tokens; remove entire backslash alphabetic command names; lowercase Unicode alphabetic word runs, excluding digits/underscore/punctuation; word counts','fit':'separate per bank-row; dev-only vocabulary and LogisticRegression L2 C1 liblinear tol1e-8 max_iter10000 seed20261026; no tuning, standardization or test vocabulary; empty vocabulary constant0','shown':['close_minus_open_paren','double_quote_parity','single_quote_parity','leading_space_runs','pipe_count'],'shown_aggregation':'E43 exact dedup retained; native test only, Oracle44/NLA42 separately, arithmetic mean of each fixed feature over readouts per item; first value positive; no direction flip or feature selection','shown_correlation':'each fixed feature separately across matched bank-row-reader groups; Oracle asked reference. W1b has no matching asked bank: report feature AUROCs only.'},'bootstrap':{'item_draws':2000,'row_draws':10000,'CI':'percentile95','item_sampling':'unstratified resampling items, discard one-class draws','row_sampling':'bank-row units with replacement; common resamples for words-minus-presence rho','pooled':'equal weight structure bank-row mean; W1/E36/E24 primary, W12 supplementary, also each bank'},'H3_pattern':'asked>=.8 implies presence>=.8; presence<=.6 implies asked<=.65; <=2 violations','H3_falsifier':'rho<.3 OR both paren and string have presence>=.8 and asked<=.65 in at least one bank each','H5_rule':'rho_words>=.6 and rho_words-rho_presence>=.15; paired CI reported with no added veto; falsified if >=3 structure bank-rows words>=.75 and asked<=.65','reliability':'Spearman W1/E36 common rows, all and structure separately, row bootstrap; empirical bank stability, not an identified strict mathematical ceiling','shown_pool':e43,'shown_scope':shownscope,'tokenizer':str(token),'reward':{'status':'NOT AVAILABLE','searched_roots':['/Users/guivff/Documents/Neel_Exploration','/Users/guivff/Documents/ChatGPT/Activation_Readers'],'search':'recursive filenames matching grpo/GRPO/reward; found reward source/audit code only, no sealed within-group GRPO reward logs','reference_FVE':.015},'pins':pins}
    dump(OUT/'PLAN.json',plan)
    print({k:{'rows':len(c['rows']),'structure':len(c['structure'])} for k,c in config.items()})
if __name__=='__main__':main()
