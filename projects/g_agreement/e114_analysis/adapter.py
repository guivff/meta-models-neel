"""§226 E114 descriptive CPU adapter; no acquisition or earlier analysis replay."""
import argparse
import hashlib
import subprocess
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e100_analysis.rules import Bootstrap, MISSED, DRAWS, SEED

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
ROWS=MISSED
ARMS=('stated','opposite')
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e114/ANALYSIS_ONCE.json'
BANK='c0b5e68130354be082a92c88761024b1ca5e49dab9ddd4b4133d2c820c0058a9'
E100='76b156f055567cb168b2cfd40ec6bcc65aa21d2aa18fd1d97d533ad5fa86d2d1'
REQ=core.require

def reading(stated, transplant):
    if stated is None or transplant is None:return 'NOT EVALUABLE'
    return 'token-shaped state at the site, not tracked state' if stated>=.30 and transplant<=.10 else 'pre-stated descriptive conjunction not met'

def analyze(cells, comparison):
    REQ(set(cells)=={(r,'oracle',a) for r in ROWS for a in ARMS},'exact three-row two-arm Oracle grid')
    REQ(set(comparison)==set(ROWS),'all original E100 row dispositions')
    for row in ROWS:
        ids=set(cells[(row,'oracle','stated')])
        REQ(len(ids)==84 and ids==set(cells[(row,'oracle','opposite')]),'84 original paired test items')
    b=Bootstrap(cells)
    rows={}
    for row in ROWS:
        old=comparison[row]
        REQ(old is None or isinstance(old,dict) and 'estimate' in old,'original saved transplant statistic or explicit missing')
        s=b.stat(row,'stated');c=b.stat(row,'opposite')
        rows[row]=dict(stated=s,opposite=c,stated_minus_opposite=b.stat(row,'stated','opposite'),
                       E100_transplant=old,pre_stated_reading=reading(s['estimate'],None if old is None else old['estimate']))
    return dict(experiment='E114',authority='§226',status='DESCRIPTIVE',rows=rows,
                bootstrap=dict(draws=DRAWS,seed=SEED,unit='paired original item'),
                decision_rules='No new confirmatory rule; E100 saved estimates copied without replay')

def committed():
    receipt=core.read(ROOT/'results/g_agreement/understand/e114/analysis/SOURCE_RECEIPT.json')
    for f,h in receipt['files'].items():
        p=ROOT/f;REQ(core.sha(p)==h,'source receipt mismatch')
        blob=subprocess.check_output(['git','show','HEAD:'+f],cwd=ROOT)
        REQ(hashlib.sha256(blob).hexdigest()==h,'source must be committed before output')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def inputs(s):
    # All normalization is supplied by source owners, with exact sealed pointers.
    bp=Path(s['binding_seal']);binding=core.verify(bp,s['binding_sha256'])
    REQ(binding['experiment']=='E114' and binding['status']=='COMPLETE','complete E114 binding')
    REQ({'INVENTORY.json','MEASUREMENTS.json'}<=set(binding['files']),'sealed full census and measurements')
    REQ(binding['source_bank_sha256']==BANK,'frozen original E114 bank')
    core.verify(binding['source_bank_seal'],BANK)
    REQ(binding['reader_block']==44 and binding['rubric']=='E57' and binding['route']=='E56','registered reader/scorer/route')
    for k in ('privacy_verified','route_verified','labels_cpu_only','greedy','registered_read_token_verified','original_gold_unchanged'):
        REQ(binding[k] is True,k)
    sources=binding['source_seals'];seals=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(seals) and x['member'] in seals[i]['files'],'original sealed pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    inv=core.unique(core.read(bp.parent/'INVENTORY.json'))
    REQ(len(inv)==252,'252 original items')
    cells={(r,'oracle',a):{} for r in ROWS for a in ARMS}
    ms=core.unique(core.read(bp.parent/'MEASUREMENTS.json'));REQ(set(ms)==set(inv),'all original items measured')
    for ident,x in inv.items():
        REQ(x['row'] in ROWS and x['split']=='test','original row/split')
        REQ(ref(x['source_id'])==ident and ref(x['source_row'])==x['row'],'original E57 identity')
        gold=ref(x['target_letter']);REQ(gold in ('A','B'),'original frozen target letter')
        REQ(set(x['arms'])==set(ARMS) and set(ms[ident]['arms'])==set(ARMS),'exact matched arms')
        for arm in ARMS:
            a=x['arms'][arm];z=ms[ident]['arms'][arm]
            REQ(ref(a['original_target_letter'])==gold,'never retarget opposite control')
            REQ(ref(a['sentence'])+'\n'+ref(x['raw_prefix'])==ref(a['prompt']),'exact frozen prefix manipulation')
            REQ(ref(a['stated_letter'])==(gold if arm=='stated' else {'A':'B','B':'A'}[gold]),'original actual opposite value')
            REQ(ref(z['public_id'])==ref(a['public_id']),'exact source to readout binding')
            text=ref(z['text']);code=ref(z['code'])
            REQ(code is None or code['id']==z['judgment_id'],'original judgment identity')
            cells[(x['row'],'oracle',arm)][ident]=None if code is None else core.score(code,gold,text)
    ep=Path(s['e100_analysis_seal']);e=core.verify(ep,E100)
    REQ('RESULTS.json' in e['files'],'original sealed E100 result')
    old=core.read(ep.parent/'RESULTS.json')
    comparison={r:old.get('rows',{}).get(r,{}).get('oracle',{}).get('transplant') for r in ROWS}
    # Validate full grid before consuming the global guard.
    for row in ROWS:REQ(len(cells[(row,'oracle','stated')])==84,'84 per row')
    return cells,comparison

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args()
    commit=committed();s=core.read(a.spec);cells,old=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['binding_sha256']),commit)
    core.write(out/'RESULTS.json',analyze(cells,old));core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E114',status='COMPLETE_ONCE',code_commit=commit,
              binding_sha256=s['binding_sha256'],E100_analysis_sha256=E100)
if __name__=='__main__':main()
