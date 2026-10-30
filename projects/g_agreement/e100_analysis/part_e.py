"""§226 E100e descriptive extension; independent guard, never replay parts a/b."""
import argparse,hashlib,subprocess
from pathlib import Path
import numpy as np
from projects.g_agreement.understand.wmech2 import core
from projects.g_agreement.e100_analysis.rules import Bootstrap,DRAWS,SEED
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
ROWS=('container_after_move','holder_after_handovers')
GUARD=ROOT.parent/'wt-wmech/cache/g_agreement/understand/e100/part_e/ANALYSIS_ONCE.json'
REQ=core.require

class PartEBootstrap(Bootstrap):
    # Identical original E100 joint-item sampling; only registered row names extend.
    def __init__(self,cells):
        self.cells,self.indices=cells,{};rng=np.random.default_rng(SEED)
        for row in ROWS:
            selected=[v for (r,_,_),v in cells.items() if r==row]
            if not selected:raise ValueError('both tracked rows')
            ids=sorted(selected[0])
            if len(ids)!=84 or any(set(v)!=set(ids) for v in selected):raise ValueError('84 paired items per row')
            self.indices[row]=(ids,rng.integers(0,len(ids),(DRAWS,len(ids))))

def analyze(cells,gates=None,custody_caveat=None):
    REQ(set(cells)=={(r,s,'transplant') for r in ROWS for s in ('oracle','nla')},'exact two-row two-reader transplant grid')
    gates={r:1.0 for r in ROWS} if gates is None else gates
    REQ(set(gates)==set(ROWS),'both original E87 gates')
    b=PartEBootstrap(cells);out={}
    for row in ROWS:
        out[row]={}
        if gates[row]<.90:
            out[row]=dict(status='EXCLUDED BY E87 GATE',gate=gates[row],readouts={reader:sorted(cells[(row,reader,'transplant')]) for reader in ('oracle','nla')})
            continue
        for reader in ('oracle','nla'):
            z=b.stat(row,'transplant',reader=reader);p=z['estimate']
            z['pre_stated_reading']='NOT EVALUABLE' if p is None else 'bookkeeping-specific; use case survives at read site' if p>=.30 else 'blind spot covers tracked state too' if p<=.10 else 'intermediate'
            z['role']='descriptive' if reader=='oracle' else 'descriptive check';out[row][reader]=z
    return dict(experiment='E100e',authority='§226',status='DESCRIPTIVE',custody_caveat=custody_caveat,rows=out,bootstrap=dict(draws=DRAWS,seed=SEED,unit='paired source item'),decision_rules='No confirmatory rule; pre-stated point readings only')

def committed():
    for f,h in core.read(HERE/'PART_E_DEPENDENCIES.json').items():REQ(core.sha(ROOT/f)==h,'E100e dependency pin')
    for name in ('part_e.py','test_part_e.py','PART_E_README.md','PART_E_DEPENDENCIES.json'):
        p=HERE/name;blob=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT)
        REQ(hashlib.sha256(blob).hexdigest()==core.sha(p),'pre-output committed extension')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def amendment(inv,o):
    fields=o.get('amendment_fields',{})
    intervention=fields.get('intervention',{}).get('value',inv['intervention'])
    if intervention=='h′ = h_donor at the read site':intervention='h_prime=h_donor'
    committed=fields.get('pre_gpu_pairing_committed',{}).get('value',inv['pre_gpu_pairing_committed'])
    REQ(type(committed) is bool,'explicit pairing custody boolean')
    caveat=None if committed else 'pairing sealed before attempt 2 first output (R-Q verified) but not committed before the first GPU run; custody caveat, not a missing value'
    return intervention,caveat

def inputs(s):
    ip=Path(s['inventory_seal']).resolve();commit=s['inventory_commit'];REQ(len(commit)==40,'full pre-output inventory commit')
    inventory_root=Path(subprocess.check_output(['git','rev-parse','--show-toplevel'],cwd=ip.parent,text=True).strip())
    blob=subprocess.check_output(['git','show',commit+':'+str(ip.relative_to(inventory_root))],cwd=ROOT)
    REQ(hashlib.sha256(blob).hexdigest()==s['inventory_sha256'],'committed inventory seal')
    inv=core.verify(ip,s['inventory_sha256']);REQ('INVENTORY.json' in inv['files'],'sealed private item census')
    REQ(inv['experiment']=='E100e' and inv['pairing_seed']==20261029 and amendment(inv,core.verify(s['output_seal'],s['output_sha256']))[0]=='h_prime=h_donor','registered transplant')
    REQ(inv['reader_blocks']=={'oracle':44,'nla':42},'frozen pair/site custody')
    meta=core.unique(core.read(ip.parent/'INVENTORY.json'));REQ(len(meta)==168,'all168 items')
    for row in ROWS:REQ(sum(x['row']==row for x in meta.values())==84,'two exact rows')
    for x in meta.values():
        donor=meta[x['donor_id']]
        REQ(x['split']=='test' and donor['row']==x['row'] and x['original_value']!=donor['original_value'] and x['target_value']==donor['original_value'],'original same-row different-value donor')
    op=Path(s['output_seal']);o=core.verify(op,s['output_sha256'])
    REQ(o['experiment']=='E100e' and o['status']=='COMPLETE' and o['inventory_sha256']==s['inventory_sha256'],'complete E100e bank')
    for k in ('route_verified','privacy_verified','labels_cpu_only','one_greedy_readout_per_cell','donor_vector_binding_verified'):
        REQ(o[k] is True,k)
    REQ(o['rubric']=='E82','registered two-candidate E82 rubric')
    sources=o['source_seals'];seals=[core.verify(x['seal'],x['sha256']) for x in sources];cache={}
    def ref(x):
        i=x['seal_index'];REQ(type(i) is int and 0<=i<len(seals) and x['member'] in seals[i]['files'],'original sealed pointer')
        p=Path(sources[i]['seal']).parent/x['member']
        if p not in cache:cache[p]=core.read(p)
        v=cache[p]
        for k in x['keys']:v=v[k]
        return v
    gate_refs=dict(o['e87_gates']);excluded=[]
    if o.get('excluded_by_gate'):
        REQ(set(o['excluded_by_gate'])=={'holder_after_handovers'} and 'HOLDER_DESCRIPTIVE.json' in o['files'],'sealed excluded holder readouts')
        holder=core.read(op.parent/'HOLDER_DESCRIPTIVE.json')
        REQ(holder['row']=='holder_after_handovers','excluded row identity')
        gate_refs[holder['row']]=holder['e87_gate'];excluded=holder['items']
        REQ(ref(holder['e87_gate'])<.90,'excluded original gate must fail')
    gates={row:ref(x) for row,x in gate_refs.items()}
    for row,value in gates.items():
        REQ(row in ROWS and isinstance(value,(int,float)) and 0<=value<=1,'original E87 gate')
    REQ(set(gate_refs)==set(ROWS),'both E87 gates')
    REQ('MEASUREMENTS.json' in o['files'],'sealed measurements')
    ms=core.unique(core.read(op.parent/'MEASUREMENTS.json')+excluded);REQ(set(ms)==set(meta),'complete original item grid')
    cells={(r,reader,'transplant'):{} for r in ROWS for reader in ('oracle','nla')}
    for ident,m in ms.items():
        x=meta[ident];REQ(set(m['systems'])=={'oracle','nla'},'both readers')
        for reader,z in m['systems'].items():
            REQ(ref(z['target_value'])==x['target_value'],'original donor target value')
            letter=ref(z['target_letter']);REQ(letter in ('A','B'),'original two candidate letter')
            code=ref(z['code']);text=ref(z['text']);REQ(code is None or code['id']==z['judgment_id'],'original judgment identity')
            cells[(x['row'],reader,'transplant')][ident]=None if code is None else core.score(code,letter,text)
    return cells,gates,amendment(inv,o)[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);a=p.parse_args();commit=committed();s=core.read(a.spec);cells,gates,caveat=inputs(s)
    out=core.claim(dict(analysis=s['analysis'],guard=str(GUARD),output_sha256=s['output_sha256']),commit)
    core.write(out/'RESULTS.json',analyze(cells,gates,caveat));core.write(out/'BINDING.json',s)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E100e',status='COMPLETE_ONCE',code_commit=commit,output_sha256=s['output_sha256'])
if __name__=='__main__':main()
