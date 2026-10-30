"""§249 once-only source-bound E137 analysis, after E133 main; no paid work."""
import argparse,hashlib,subprocess
from datetime import datetime,timezone
from pathlib import Path
from projects.g_agreement.understand.wmech2 import core
from . import screen,rules,transport
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
GUARD=ROOT/'cache/g_agreement/understand/e137/ANALYSIS_ONCE.json'
REQ=core.require
E133_MAIN_SHA='e6f12addf1bdb63fb02deafffe7b602835ec5efd02e326470a7aaf9b5fe752d0'

def committed():
    for n,h in core.read(HERE/'DEPENDENCIES.json').items():REQ(core.sha(ROOT/n)==h,'changed frozen dependency '+n)
    for p in HERE.iterdir():
        if p.suffix in('.py','.json','.md'):
            b=subprocess.check_output(['git','show','HEAD:'+str(p.relative_to(ROOT))],cwd=ROOT);REQ(hashlib.sha256(b).hexdigest()==core.sha(p),'uncommitted E137 source')
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()

def metadata(spec):
    core.verify(spec['e133_main_seal'],E133_MAIN_SHA)
    seal=core.verify(spec['inventory_seal'],spec['inventory_sha256']);REQ(seal['experiment']=='E137'and seal['status']=='SCREENED_COHORT_FROZEN'and seal['labels_cpu_only']is True,'original E137 frozen CPU cohort')
    REQ(seal['classifier_sha256']==screen.MATCHER_SHA256 and seal['greedy_max_new_tokens']==32,'unchanged32token classifier')
    core.verify(seal['screen_seal'],seal['screen_sha256']);proof=core.read(Path(seal['screen_seal']).parent/'SCREEN_SELECTION.PRIVATE.json')
    REQ(proof['classifier_sha256']==screen.MATCHER_SHA256 and set(proof['selected'])==set(screen.KINDS),'original per-design selection proof')
    pairs=core.read(Path(spec['inventory_seal']).parent/'PAIRS.PRIVATE.json');REQ(len({p['pair_id']for p in pairs})==len(pairs),'unique exact original pairs')
    for kind in screen.KINDS:
        rows=sorted([r for r in proof['screening']if r['kind']==kind],key=lambda r:r['generation_index']);REQ(len(rows)==(60 if kind=='one_hop'else 150),'full150/150/60 candidate proof')
        REQ(len({r['generation_index']for r in rows})==len(rows),'original frozen unique source order')
        first=[r['pair_id']for r in rows if r['correct_both']][:screen.LIMITS[kind]]
        REQ(first==proof['selected'][kind]==[p['pair_id']for p in pairs if p['kind']==kind],'first42/42/16 qualifying exact order; no reader selection')
    REQ(not all(sum(r['correct_both']for r in proof['screening']if r['kind']==k)<20 for k in('D1','D2')),'screen-only disposition; no main analysis')
    rows=core.unique(proof['screening'],'pair_id')
    for p in pairs:
        REQ(p['generation_index']==rows[p['pair_id']]['generation_index']and p['kind']in screen.KINDS,'original pair kind/order')
        ms=p['members'];REQ(len(ms)==2 and [m['member']for m in ms]==[0,1],'original matched members')
        current=[m['current']for m in ms];previous=[m['previous']for m in ms];REQ(len(set(current))==2 and previous[0]==previous[1]and previous[0]not in current,'original final recipients/common previous')
        REQ(len(set(p['value_map'].values()))==len(p['value_map'])and set(current+previous)<=set(p['value_map'].values()),'frozen opaque-name map')
        if p['kind']in('D1','D2'):REQ(all(m['latest_mention']!=m['current']for m in ms),'both designs answer not most-recent name')
    names=core.read(Path(spec['inventory_seal']).parent/'FIXED_NAMES.PRIVATE.json');REQ(len(names)==len(set(names))and len(names)>=3,'original fixed name list')
    REQ(all(m['current']in names and m['previous']in names for p in pairs for m in p['members']),'original labels in frozen list')
    return pairs,names

def run(spec,commit):
    REQ(not GUARD.exists(),'E137 once guard consumed; no replay')
    from . import probe_phase
    probe_phase.available()
    pairs,names=metadata(spec);seal=core.verify(spec['output_seal'],spec['output_sha256'])
    REQ(seal['experiment']=='E137'and seal['status']=='COMPLETE','complete E137 only')
    REQ(any(s['sha256']==spec['native_output_sha256']for s in seal['source_seals']),'same original native capture for one-fit probes')
    for s in seal['source_seals']:core.verify(s['seal'],s['sha256'])
    out=core.claim(dict(analysis=spec['analysis'],guard=str(GUARD),output_sha256=spec['output_sha256']),commit)
    core.write(out/'FIRST_OPENING.json',dict(utc=datetime.now(timezone.utc).isoformat(),source_commit=commit,output_sha256=spec['output_sha256']))
    data=transport.inputs(spec,pairs);saved=probe_phase.ensure(spec,commit,data,names);result,private=rules.analyze(data,names,probe_results=saved);core.write(out/'RESULTS.json',result);core.write(out/'BINDING.json',spec)
    f=out/'PER_PAIR.PRIVATE.json';core.write(f,private);f.chmod(0o600)
    core.seal(out,'ANALYSIS_SEAL.json',experiment='E137',status='COMPLETE_ONCE',source_commit=commit,private_sha256=core.sha(f),output_sha256=spec['output_sha256'],new_calls=0)
    return out/'ANALYSIS_SEAL.json'

def main():
    p=argparse.ArgumentParser();p.add_argument('--spec',required=True);args=p.parse_args();commit=committed();print(run(core.read(args.spec),commit))
if __name__=='__main__':main()
