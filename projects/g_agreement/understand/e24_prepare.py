"""CPU-only preparation of §118 derivatives; no new items or continuations."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import numpy as np
from .core import load_w1, W1
from projects.g_agreement.blindspot import protocol as P

FROZEN = P.ROOT/'results/g_agreement/understand/e24'
PIN = 'a8e41f4a31d654ccc29e2d9105abb2aac38ad5eb'


def read(p):
    return json.loads(Path(p).read_text())


def prepare(a):
    import torch
    for name, digest in read(FROZEN/'PREGEN_FREEZE.json')['files'].items():
        if P.sha(P.ROOT/name) != digest:
            raise ValueError('pregen freeze changed: '+name)
    scope = read(FROZEN/'SCOPE.json')
    items, acts, specs = load_w1()
    idx = [i for i,x in enumerate(items) if x['feature'] in scope['rows_c1_c3_c4'] and x['split'] in ('dev','test')]
    subset = [items[i] for i in idx]
    if len(subset) != 4704 or sum(x['split']=='test' for x in subset) != 2352:
        raise ValueError('expanded scope evidence mismatch')
    donor_bank = P.ROOT/'cache/g_agreement/blindspot/w1-bank-v2'
    P.verify(donor_bank, 'INPUT_SEAL.json')
    donors = {x['id']:x['donor_id'] for x in P.rows(donor_bank/'items.input.jsonl')}
    lookup = {x['id']:x for x in subset}
    for x in subset:
        d = lookup[donors[x['id']]]
        if d['feature'] != x['feature'] or d['split'] != x['split'] or d['value'] == x['value']:
            raise ValueError('W1 opposite donor alignment')
        if x['meta']['read_position'] != len(x['ids'])-1:
            raise ValueError('W1 read position changed')
    P.verify(a.continuations, 'SCORE_SEAL.json')
    cont = {x['id']:x for x in P.rows(a.continuations/'continuations.jsonl')}
    c5 = [cont[x['id']] for x in subset if x['split']=='test' and x['feature'] in scope['rows_c5']]
    if len(c5)!=2100 or any(len(x['ids'])!=16 for x in c5):
        raise ValueError('exact frozen next16 continuation bank required')
    P.verify(a.e16, 'INPUT_SEAL.json')
    e16 = read(a.e16/'templates.json')
    if set(e16)!=set(scope['rows_c5']) or any(len(t['olens'])!=8 for t in e16.values()):
        raise ValueError('E16 frozen25 x8 required')
    e15root=P.ROOT/'results/g_agreement/understand/e15'
    P.verify(e15root/'analysis_7whn3a1dvi399p', 'ANALYSIS_SEAL.json')
    e15=read(e15root/'analysis_7whn3a1dvi399p/metrics.json')['rows']
    pairs=read(e15root/'CONTINUATION_PAIRS.json')['rows']
    c2={r['feature']:[[pairs[r['feature']]['pairs'][j][k] for k in ('A','B')]
                        for j in r['valid_pairs']] for r in e15 if r['valid_pairs']}
    if len(c2)!=7: raise ValueError('E15 seven dev-valid rows required')
    a.bank.mkdir(parents=True, exist_ok=False)
    evidence={}
    def pinned(name, starts=None, ends=None):
        data=subprocess.check_output(['git','-C',str(a.s14),'show',PIN+':'+name])
        import hashlib
        digest=hashlib.sha256(data).hexdigest()
        if (starts and not digest.startswith(starts)) or (ends and not digest.endswith(ends)):
            raise ValueError('S14 clarification hash mismatch: '+name)
        evidence[name]=digest
        dest=a.bank/'upstream'/name; dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
        return dest
    # Exact commit/path is authoritative for staging; launch separately blocks on the
    # clarification's mistyped abbreviated suffix, recorded in DERIVATION.
    pinned('experiments/14_ar_blindspot/modal14.py','339be5ba','51de8fc')
    pinned('experiments/14_ar_blindspot/ar_lib.py','83486f27','11006e6e6')
    templates={
        '13':read(pinned('experiments/13_new_rows/templates_frozen.json','d9046206','837d16')),
        '07':read(pinned('experiments/07_template_mining/templates_frozen.json','09156722','3e923b'))}
    c6items=[];c6labels=[];c6refs=[];c6pairs={};published={}
    for feature, exp, values in [('tb_tablecol','13',['first','late']),('tb_paren','13',['inside','outside']),('ij2_lang','07',['French','German'])]:
        directory='13_new_rows' if exp=='13' else '07_template_mining'
        bankname=f'experiments/{directory}/results/gen_ol_{feature}.json' if exp=='13' else f'experiments/handoff_inputs/{directory}/gen_ol_{feature}.json'
        bp=pinned(bankname, 'f8f9e2d3' if exp=='07' else None, 'a9e214f6' if exp=='07' else None)
        bank=read(bp)['items']
        ap=pinned(f'experiments/handoff_inputs/{directory}/acts_{feature}.pt', 'd557c3d4' if exp=='07' else None, '33486189' if exp=='07' else None)
        ref=torch.load(ap, map_location='cpu', weights_only=True)
        if len(bank)!=200 or ref['ids']!=[x['id'] for x in bank]: raise ValueError('S14 bank/order mismatch')
        c6refs.append(ref['acts'][44].float().numpy())
        for x in bank:
            uid=feature+':'+str(x['id'])
            c6items.append({'id':uid,'feature':feature,'ids':x['ids']})
            c6labels.append({'id':uid,'feature':feature,'label':int(x['value']==values[0])})
            if x['value'] not in values: raise ValueError('S14 value mismatch')
        t=templates[exp]['templates']['ol'][feature]
        c6pairs[feature]=[[r['id'],r['candidates'][values[0]],r['candidates'][values[1]]] for r in [t['fixed_label']]+t['selected']]
        published[feature]=read(pinned(f'experiments/14_ar_blindspot/results/analysis14_{feature}.json'))['ol']
    # Source banks contain labels: retained only in local provenance cache, never staged.
    shutil.rmtree(a.bank/'upstream')
    P.jsonl(a.bank/'items.input.jsonl',[{'id':x['id'],'feature':x['feature'],'split':x['split'],'ids':x['ids'],'donor_id':donors[x['id']]} for x in subset])
    P.jsonl(a.bank/'continuations.jsonl',c5)
    P.jsonl(a.bank/'c6.input.jsonl',c6items)
    np.save(a.bank/'reference44.npy',np.asarray(acts[44][idx]),allow_pickle=False)
    np.save(a.bank/'c6.reference44.npy',np.concatenate(c6refs),allow_pickle=False)
    P.dump(a.bank/'templates.json',{f:specs[f] for f in scope['rows_c1_c3_c4']})
    P.dump(a.bank/'c2.json',c2);P.dump(a.bank/'c6.pairs.json',c6pairs)
    P.dump(a.bank/'c7.json',{f:x['olens'] for f,x in e16.items()})
    private=a.bank.with_suffix('.labels.DO_NOT_STAGE.json')
    baseline=read(W1/'metrics.json')
    P.dump(private,{'w1':[ {k:x[k] for k in ('id','feature','split','value','cluster','class')} for x in subset],
                    'c6':c6labels,'c6_published':published,'w1_metrics':baseline,'e15_metrics':e15})
    P.dump(a.bank/'SCOPE.json',scope)
    P.dump(a.bank/'DERIVATION.json',{'s14_commit':PIN,'s14_files':evidence,'clarification_hash_discrepancy':{'path':'experiments/14_ar_blindspot/modal14.py','registered':'339be5ba…a8de8fc','actual':evidence['experiments/14_ar_blindspot/modal14.py'],'launch_blocked_pending_correction':True},'labels_sha256':P.sha(private),
        'e1b_continuations_sha256':P.sha(a.continuations/'continuations.jsonl'),
        'e1b_seal_sha256':P.sha(a.continuations/'SCORE_SEAL.json'),
        'e16_seal_sha256':P.sha(a.e16/'INPUT_SEAL.json'), 'e16_templates_sha256':P.sha(a.e16/'templates.json'),
        'w1_donors_sha256':P.sha(donor_bank/'items.input.jsonl'),
        'e15_analysis_seal_sha256':P.sha(e15root/'analysis_7whn3a1dvi399p/ANALYSIS_SEAL.json'),
        'pregen_freeze_sha256':P.sha(FROZEN/'PREGEN_FREEZE.json')})
    P.seal(a.bank,[str(p.relative_to(a.bank)) for p in a.bank.iterdir() if p.is_file()], 'E24_DERIVATIVES_BEFORE_CAPTURE')
    for name in ('INPUT_SEAL.json','DERIVATION.json'):
        shutil.copyfile(a.bank/name,FROZEN/name)
    print(json.dumps({'bank':str(a.bank),'items':len(subset),'c5':len(c5),'c6':len(c6items),'input_seal':P.sha(a.bank/'INPUT_SEAL.json')}))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('bank','continuations','e16','s14'):p.add_argument('--'+name,type=Path,required=True)
    prepare(p.parse_args())
