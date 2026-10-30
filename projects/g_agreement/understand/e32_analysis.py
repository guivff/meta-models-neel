"""Once-only E32 CPU report on a complete sealed acquisition; no inference."""
import argparse,json
from pathlib import Path
from . import e32 as E
from .e24_analysis import draws,metric
from .e24_worker import seal
from projects.g_agreement.blindspot import protocol as P


def analyse(bank,plan,source,out):
    P.verify(bank,'INPUT_SEAL.json');P.verify(source,'SCORE_SEAL.json');p=E.E.read(plan)
    b=E.E.read(source/'BINDING.json')
    if b['plan_sha256']!=P.sha(plan) or b['input_seal_sha256']!=P.sha(bank/'INPUT_SEAL.json') or p['input_seal_sha256']!=b['input_seal_sha256']:raise ValueError('binding')
    for n,h in p['source_files'].items():
        if P.sha(P.ROOT/n)!=h:raise ValueError('analysis source binding')
    items=P.rows(bank/'items.jsonl');records=P.rows(source/'scores.jsonl');refs=E.E.read(bank/'references.json')
    if len(records)!=25200 or len({(r['id'],r['set'],r['arm']) for r in records})!=25200:raise ValueError('complete unique grid required')
    with (source/'ANALYSIS_ONCE.lock').open('x') as f:f.write(P.sha(plan))
    out.mkdir(parents=True,exist_ok=False);rows={}
    for feature in sorted(refs):
        group=sorted((x for x in items if x['feature']==feature),key=lambda x:x['id']);ids=[x['id'] for x in group];y=[x['label'] for x in group];boot=draws([x['cluster'] for x in group]);cell={}
        for cs in ('w1','e30'):
            cell[cs]={}
            for arm in E.ARMS:
                scores={r['id']:r['score'] for r in records if r['feature']==feature and r['set']==cs and r['arm']==arm}
                if set(scores)!=set(ids):raise ValueError('row coverage')
                cell[cs][arm]=metric(y,[scores[i] for i in ids],boot)[0]
        rows[feature]=cell
    verdict=E.rules(E.summarise(records,items,refs),refs,p['high_D_rows'])
    P.dump(out/'metrics.json',{'rows':rows,'rules':verdict,'controls':'Report same/opposite/random AUROC and CI per row; no unregistered control thresholds. Bprime descriptive.', 'high_D_rows':p['high_D_rows']})
    lines=['# E32 registered analysis','',f"A reproduces E25: {verdict['A_reproduces_E25']}",'']
    for cs,r in verdict['candidate_sets'].items():lines.append(f"- {cs}: {r['verdict']}; content gate {r['content_pass']}/9; low {r['low_rows']}/8, high {r['high_rows']}/8.")
    lines+=['','| Row | Candidates | A | B | B′ | Same | Opposite | Random |','|---|---|---:|---:|---:|---:|---:|---:|']
    for f in rows:
        for cs in rows[f]:lines.append('| '+f+' | '+cs+' | '+' | '.join(f"{rows[f][cs][a]['auroc']:.3f}" for a in E.ARMS)+' |')
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n');seal(out,['metrics.json','RESULTS.md'],'ANALYSIS_SEAL.json','COMPLETE')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('bank','plan','source','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();analyse(a.bank,a.plan,a.source,a.out)
