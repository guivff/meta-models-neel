"""Gate every sealed shard before reading science, then run registered analysis."""
import math
import argparse,json
from pathlib import Path
from projects.g_agreement.blindspot import protocol as P
from . import e32_analysis as A,e32_shard158 as S

class InvalidRun(ValueError):
    def __init__(self, gates):
        super().__init__('global validity failed; no shard science used')
        self.gates=gates


def global_validity(records,items,refs,high):
    gates=S.rules(S.summarise(records,items,refs),refs,high)
    gates={'A_reproduces_E25':gates['A_reproduces_E25'],'candidate_sets':{c:{k:v[k] for k in ('content_pass','interpretable')} for c,v in gates['candidate_sets'].items()}}
    # Item 6: any failed global validity gate invalidates the whole acquisition.
    if not gates['A_reproduces_E25'] or not all(v['interpretable'] for v in gates['candidate_sets'].values()):
        raise InvalidRun(gates)
    return gates


def merge(plan,bank,outputs,out):
    p=S.E.read(plan);rows=[];seen=set();validity=[]
    if len(outputs)!=len(p['row_shards']):raise ValueError('all shards required')
    items=P.rows(bank/'items.jsonl');refs=S.E.read(bank/'references.json')
    for slot,source in enumerate(outputs):
        P.verify(source,'SCORE_SEAL.json');P.verify(source,'SCORE_PARITY_SEAL.json')
        if S.E.read(source/'SCORE_PARITY_SEAL.json')['status']!='PASS':raise ValueError('score parity')
        b=S.E.read(source/'BINDING.json');stage=S.E.read(source/'STAGE_BINDING.json')
        if b['slot']!=slot or b['rows']!=p['row_shards'][slot] or b['plan_sha256']!=P.sha(plan) or b['input_seal_sha256']!=p['input_seal_sha256'] or stage['capture_seal_sha256']!=p['capture_seal_sha256']:raise ValueError('shard binding')
        required={'scores.jsonl','VALIDITY_INPUTS.jsonl','BINDING.json','STAGE_BINDING.json','SCORE_PARITY_SEAL.json'}
        if not required<=set(S.E.read(source/'SCORE_SEAL.json')['files']):raise ValueError('unsealed validity inputs')
        rr=P.rows(source/'VALIDITY_INPUTS.jsonl')
        expected={(x['id'],x['feature'],cs,arm) for x in items if x['feature'] in p['row_shards'][slot] for cs in ('w1','e30') for arm in ('A','B') if arm=='A' or refs[x['feature']]['class']=='semantic'}
        keys=[(r['id'],r['feature'],r['set'],r['arm']) for r in rr]
        if len(keys)!=len(set(keys)) or set(keys)!=expected or any(not math.isfinite(r['score']) for r in rr):raise ValueError('validity grid')
        validity.extend(rr)
    gates=global_validity(validity,items,refs,p['high_D_rows'])
    # No scores.jsonl is decoded until every global validity gate has passed.
    for slot,source in enumerate(outputs):
        rr=P.rows(source/'scores.jsonl');expected={(x['id'],cs,arm) for x in P.rows(bank/'items.jsonl') if x['feature'] in p['row_shards'][slot] for cs in ('w1','e30') for arm in S.ARMS}
        keys=[(x['id'],x['set'],x['arm']) for x in rr]
        if len(keys)!=len(set(keys)) or set(keys)!=expected or seen.intersection(keys):raise ValueError('shard grid')
        seen.update(keys);rows.extend(rr)
    if len(seen)!=25200:raise ValueError('global grid')
    score_map={(r['id'],r['set'],r['arm']):r for r in rows}
    if any(score_map[(r['id'],r['set'],r['arm'])]!=r for r in validity):raise ValueError('validity/science mismatch')
    out.mkdir(parents=True,exist_ok=False);P.jsonl(out/'scores.jsonl',rows)
    P.dump(out/'GLOBAL_VALIDITY.json',gates)
    P.dump(out/'BINDING.json',{'plan_sha256':P.sha(plan),'input_seal_sha256':p['input_seal_sha256']})
    P.dump(out/'SHARDS.json',[{'path':str(x),'seal_sha256':P.sha(x/'SCORE_SEAL.json')} for x in outputs])
    S.seal(out,['scores.jsonl','BINDING.json','SHARDS.json','GLOBAL_VALIDITY.json'],'SCORE_SEAL.json','COMPLETE_GATES_RECORDED')

def run(path,digest):
    if P.sha(path)!=digest:raise ValueError('spec hash')
    c=S.E.read(path);lock=Path(c['lock']);lock.parent.mkdir(parents=True,exist_ok=True)
    with lock.open('x') as f:f.write(digest)
    try:
        for n,h in c['pins'].items():
            if P.sha(n)!=h:raise ValueError('pin '+n)
        plan=Path(c['plan']);bank=Path(c['bank']);S.verify_capture(Path(c['capture']),bank,S.E.read(plan));outputs=[]
        for final in map(Path,c['pulls']):
            if not final.is_symlink():raise ValueError('link original verified final pull')
            for line in (final/'PULL_SUMS').read_text().splitlines():
                h,n=line.split(None,1);p=(final/n.lstrip('*')).resolve()
                if not p.is_relative_to(final.resolve()) or P.sha(p)!=h:raise ValueError('pull checksum')
            source=final/'out';b=S.E.read(source/'BINDING.json')
            if P.sha(final/'ASSIGNMENT.json')!=b['assignment_sha256']:raise ValueError('assignment binding')
            outputs.append(source)
        merged=Path(c['merged']);merge(plan,bank,outputs,merged)
        A.analyse(bank,plan,merged,Path(c['out']))
        P.dump(lock.with_suffix('.receipt.json'),{'status':'COMPLETE','label':'§149 RUN-BY-INTEGRATOR'})
    except InvalidRun as exc:
        out=Path(c['out']);out.mkdir(parents=True,exist_ok=False)
        P.dump(out/'INVALID.json',{'status':'INVALID','rules':exc.gates,'shard_science_read':False,'shard_results_used':False})
        (out/'RESULTS.md').write_text('# E32 INVALID\n\nGlobal validity failed. No shard science read or used; no scientific verdict.\n')
        S.seal(out,['INVALID.json','RESULTS.md'],'ANALYSIS_SEAL.json','INVALID')
        P.dump(lock.with_suffix('.receipt.json'),{'status':'INVALID','retry':False,'label':'§159 item 6'})
    except BaseException as exc:
        P.dump(lock.with_suffix('.receipt.json'),{'status':'STOP_OWNER_REQUIRED','error':str(exc),'retry':False});raise
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--spec',type=Path,required=True);a.add_argument('--spec-sha256',required=True);v=a.parse_args();run(v.spec,v.spec_sha256)
