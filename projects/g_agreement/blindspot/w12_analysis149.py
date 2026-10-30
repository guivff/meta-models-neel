"""§100 reader analysis, delegated by §149; W1 estimators and gates unchanged."""
import json
from pathlib import Path
import numpy as np
from . import protocol as P, analysis as A
from .w12_run import verify_release, READERS
from projects.g_agreement.understand.e24_worker import seal


def analyse(bank, source, freeze, plan, out):
    import torch
    torch.set_num_threads(4)
    plan_data=json.loads(plan.read_text());verify_release(bank,plan_data)
    for name in ('SCORE_SEAL.json','CAPTURE_SEAL.json','W1_PARITY_SEAL.json'):
        P.verify(source,name)
    if json.loads((source/'SCORE_SEAL.json').read_text())['status']!='W12_ASKED_ONLY_COMPLETE':raise ValueError('incomplete W12')
    if json.loads((source/'W1_PARITY_SEAL.json').read_text())['status']!='PASS':raise ValueError('W1 parity failed')
    binding=json.loads((source/'BINDING.json').read_text())
    for key in ('input_seal_sha256','freeze_sha256','values_seal_sha256','predictions_seal_sha256'):
        if binding[key]!=plan_data[key]:raise ValueError('release binding: '+key)
    if binding['plan_sha256']!=P.sha(plan):raise ValueError('plan binding')
    P.verify(freeze,'FREEZE.json')
    if P.sha(freeze/'FREEZE.json')!=plan_data['freeze_sha256']:raise ValueError('freeze identity')
    items=P.rows(bank/'items.input.jsonl');specs=json.loads((bank/'templates.json').read_text())
    if len(items)!=1008 or len(specs)!=6:raise ValueError('fixed scope')
    ids=[x['id'] for x in items]
    if json.loads((source/'ORDER.json').read_text())!=ids:raise ValueError('activation order')
    scoremap=A._grid(P.rows(source/'scores.jsonl'),items,specs,list(READERS.items()))
    # Labels are opened only after all input/score/capture seals and fixed grid pass.
    labels=P.rows(freeze/'items.jsonl');lookup={x['id']:x for x in labels}
    if len(lookup)!=1008 or set(lookup)!=set(ids):raise ValueError('label population')
    for f in specs:
        group=[x for x in labels if x['feature']==f]
        if {x['cluster'] for x in group if x['split']=='dev'} & {x['cluster'] for x in group if x['split']=='test'}:raise ValueError('split leakage')
        for split in ('dev','test'):
            g=[x for x in group if x['split']==split]
            if len(g)!=84 or len({x['cluster'] for x in g})!=6 or any(sum(x['value']==v for x in g)!=42 for v in specs[f]['values']):raise ValueError('frozen row balance')
    acts={l:np.load(source/f'acts{l}.npy',allow_pickle=False) for l in (42,44)}
    if any(h.ndim!=2 or len(h)!=1008 or not np.isfinite(h).all() for h in acts.values()):raise ValueError('invalid activation grid')
    out.mkdir(parents=True,exist_ok=False)
    cells,oof,_,_=A._analyse_cells(items,lookup,specs,scoremap,acts,list(READERS.items()),export_dev=False)
    result={'experiment':'W12','authority':'§100; §149 RUN-BY-INTEGRATOR','rows':cells,
            'source_score_seal_sha256':P.sha(source/'SCORE_SEAL.json'),'freeze_sha256':P.sha(freeze/'FREEZE.json'),
            'method':A.OPERATING_DETAILS,'E29_comparison':'Separate W-text §124 compare149 entry point; do not rerun D/P',
            'free_readouts':'NOT_REGISTERED','sealed_verdicts_changed':False}
    P.dump(out/'metrics.json',result);P.jsonl(out/'probe_oof.jsonl',oof)
    lines=['# W12 §100 reader analysis','', '§149 RUN-BY-INTEGRATOR. Gates and estimators are the unchanged W1 implementation.','', '| Row | Reader | Layer | True AUROC | Mismatch AUROC | Status |','|---|---|---:|---:|---:|---|']
    for c in cells:
        val=lambda k:'NA' if c.get(k) is None else f"{c[k]['auroc']:.6f}"
        lines.append(f"| {c['feature']} | {c['reader']} | {c['layer']} | {val('true')} | {val('mismatched')} | {c['status']} |")
    (out/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    seal(out,['metrics.json','probe_oof.jsonl','RESULTS.md'],'ANALYSIS_SEAL.json','W12_SECTION100_COMPLETE')
