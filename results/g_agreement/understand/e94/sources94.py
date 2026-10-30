"""Frozen local source bindings and read-only adapters; actual maps stay in cache."""
import hashlib,json,os
from pathlib import Path
from score94 import require,value_class,claim_class
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];WT=ROOT.parent
CACHE=ROOT/'cache/g_agreement/understand/e94'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,x):Path(p).write_text(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')
class Ledger:
    def __init__(self):self.files={}
    def bind(self,p,expected=None):
        p=Path(p).resolve();h=sha(p);require(expected is None or h==expected,'source hash mismatch: '+str(p));self.files[str(p)]=h;return read(p)
    def seal(self,p,expected=None):
        p=Path(p);s=self.bind(p,expected)
        for name,h in s['files'].items():
            h=h['sha256'] if isinstance(h,dict) else h
            member=p.parent/name;require(sha(member)==h,'seal member mismatch: '+str(member));self.files[str(member.resolve())]=h
        return s

def prepare():
    CACHE.mkdir(parents=True,exist_ok=True,mode=0o700);l=Ledger();banks=[]
    for e in ('E56','E57','E62','E59'):
        family='analysis5968' if e=='E59' else 'analysis402'
        s=l.bind(WT/f'wt-wmech/results/g_agreement/understand/{family}/{e}_SPEC.json')
        l.seal(Path(s['analysis_out'])/'ANALYSIS_SEAL.json')
        bs=l.seal(Path(s['blind_out'])/'BLIND_SEAL.json')
        l.bind(s['private_key'],bs['private_key_sha256']);l.bind(s['private_items'],s['private_items_sha256'])
        js=Path(s.get('judgment_seal',str(Path(s['judgments']).parent/'JUDGMENT_SEAL.json')));j=l.seal(js)
        require(j['blind_seal_sha256']==sha(Path(s['blind_out'])/'BLIND_SEAL.json'),'judge source binding')
        if e=='E56':l.bind(Path(s['inputs'])/'injection/ITEMS.json')
        banks.append({'type':'value','bank':e,'spec':s})
    plan=l.bind(ROOT/'results/g_agreement/sealed/E73/E73_ONCE_ANALYSIS_INPUT_PLAN.json')
    l.seal(ROOT/'results/g_agreement/sealed/E73/judged/ANALYSIS_SEAL.json')
    for b in plan['banks']:
        l.bind(b['builder_spec'],plan['input_bindings'][b['builder_spec']]);s=read(b['builder_spec'])
        l.bind(s['private_key'],plan['input_bindings'][s['private_key']])
        jdir=ROOT/f"results/g_agreement/sealed/E73/judged/{b['name']}/adapted"
        l.seal(jdir/'JUDGMENT_SEAL.json')
        banks.append({'type':'E73','bank':'E73','stratum':b['name'],'key':s['private_key'],'judgments':str(jdir/'JUDGMENTS.json')})
    for wave in (1,2):
        s=l.bind(ROOT/f'results/g_agreement/r/e67_analysis/ANALYSIS_SPEC.wave{wave}.json')
        l.seal(ROOT/f'results/g_agreement/r/e67_analysis/wave{wave}_once/ANALYSIS_SEAL.json')
        # Frozen seal is public; actual maps were moved to ignored cache without changing bytes.
        ps=l.bind(s['private_seal'],s['private_seal_sha256'])
        private=CACHE.parent/f'e67/wave{wave}/integrator_wave{wave}/PAIRING_CONDITION_MAP.PRIVATE.json'
        l.bind(private,ps['files']['PAIRING_CONDITION_MAP.PRIVATE.json'])
        for g in s['terminal_grids'].values():l.seal(Path(g['dir'])/'RESULT_SEAL.json',g['result_seal_sha256'])
        banks.append({'type':'E67','bank':'E67','wave':wave,'map':str(private),'grids':s['terminal_grids']})
    # E76 is available only if its once-only judged analysis has sealed; no regex substitute.
    e76=ROOT/'results/g_agreement/understand/e76/judged/analysis_once_20261028/ANALYSIS_SEAL.json'
    require(not e76.exists(),'E76 judged seal arrived: bind before freezing rather than omit')
    unavailable={'E76':'No sealed judged analysis/terminal delivered at source freeze; registered placebo agreement NOT EVALUABLE.', 'E62':'Oracle-only native acquisition; no shared Oracle/NLA judged item grid.'}
    data={'banks':banks,'files':l.files,'unavailable':unavailable}
    private=CACHE/'SOURCES.PRIVATE.json';require(not private.exists(),'source bindings already frozen');write(private,data);os.chmod(private,0o600)
    write(HERE/'INPUT_PLAN.json',{'experiment':'E94','authority':'BRIEF_UNDERSTAND §203','private_sources':str(private),'private_sources_sha256':sha(private),'bound_file_count':len(l.files),'unavailable':unavailable,'analysis_runs':1,'E67':'ratified §203 clarification 1: separate wave tables, excluded from pooled H-A1 and pooled ensemble','no_readouts_or_judging':True})
    print(json.dumps({'source_files':len(l.files),'banks':[b['bank'] for b in banks],'outcomes_scored':False}))

def index(rows,field):
    require(len({x[field] for x in rows})==len(rows),'duplicate '+field);return {x[field]:x for x in rows}
def load(data):
    rows=[];audit={}
    for b in data['banks']:
        e=b['bank']
        if b['type']=='value':
            s=b['spec'];private=index(read(s['private_items']),'id');keys=read(s['private_key']);codes=index(read(s['judgments']),'id')
            require(set(codes)=={k['opaque_id'] for k in keys},'exact source key/judgment grid')
            inj=index(read(Path(s['inputs'])/'injection/ITEMS.json')['items'],'id') if e=='E56' else {}
            for k in keys:
                unit,reader,repeat=k['source_id'].rsplit(':',2);require(repeat=='0','single repeat')
                if k.get('eval'):continue
                code=codes[k['opaque_id']]
                if unit in private:
                    p=private[unit];truth='A' if p['label']==1 else 'B';stratum=p['feature'];cluster=e+'|'+str(p.get('base_item_id',p['id']))
                else:
                    require(e=='E56' and unit in inj,'unknown private unit');p=inj[unit];truth=p['variant'];stratum='injection|'+p['row']+'|'+p['arm'];cluster=e+'|injection|'+p['row']+'|'+p['variant']
                rows.append(dict(bank=e,unit=unit,reader=reader,cluster=cluster,stratum=stratum,raw_category=code['category'],both_values=len(code.get('values',[]))==2,**{'class':value_class(code,truth)}))
        elif b['type']=='E73':
            keys=read(b['key']);codes=index(read(b['judgments']),'id');require(set(codes)=={k['opaque_id'] for k in keys},'E73 exact grid')
            for k in keys:
                code=codes[k['opaque_id']];unit=b['stratum']+'|'+k['source_id']
                rows.append(dict(bank=e,unit=unit,reader=k['reader'],cluster=e+'|'+unit,stratum=b['stratum']+'|'+k['state'],raw_category=code['category'],both_values=len(code['values'])==2,**{'class':value_class(code,'AB'[k['label']])}))
        else:
            codes={}
            for packet,g in b['grids'].items():
                xs=read(Path(g['dir'])/'JUDGMENTS.json');cs=index(xs,'id');codes[int(packet)]=cs
                for t in xs:require(t['status'] in ('KEPT','UNPARSEABLE') and ((t['code'] is None)==(t['status']=='UNPARSEABLE')),'terminal status')
            seen=set()
            for p in read(b['map'])['pairs']:
                for r in p['records']:
                    require((r['packet'],r['id']) not in seen,'E67 duplicated record');seen.add((r['packet'],r['id']))
                    t=codes[r['packet']][r['id']];c=claim_class(t['code']);unit=f"wave{b['wave']}|{p['bank']}|{p['arm']}|{p['item_id']}|{r['condition']}|{r['prompt_arm']}|{r['prompt_item_id']}|{r['prompt_sha256']}"
                    rows.append(dict(bank=f"E67_wave{b['wave']}",unit=unit,reader=p['reader'],cluster=p['bank']+'|'+p['item_id'],stratum=f"wave{b['wave']}|{p['bank']}|{r['condition']}|{r['prompt_arm']}|{r['prompt_item_id']}|{r['prompt_sha256']}",raw_category=t['status'],both_values=False,**{'class':c}))
            require(seen=={(packet,i) for packet,cs in codes.items() for i in cs},'complete E67 terminal join')
    return rows
if __name__=='__main__':prepare()
