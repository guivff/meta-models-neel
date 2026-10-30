"""CPU E102 pair selection and strict post-acquisition dataset finalization.

The plan contains no activations; finalization cannot claim readiness without
sealed gate, acquisition vectors, and original-lens dev teacher outputs.
"""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import random
import numpy as np
from projects.g_agreement.e96.reconstructor_check import digest, write
from projects.g_agreement.e96.prepare_smoke_inputs import verify

TARGETS = ('nesting_depth', 'indent_level', 'page_range_digit')
REPLAY = {'e56': ('fact_recall', 'language_continuation', 'tense_implicit'),
          'e59': ('format_plan', 'language_plan', 'hedge_plan')}
SEED = 20261029


def dev_rows(items, rows):
    selected = [x for x in items if x['split'] == 'dev' and x['feature'] in rows]
    if Counter(x['feature'] for x in selected) != Counter({r:84 for r in rows}):
        raise ValueError('exactly84 dev items per registered row required')
    if len({x['id'] for x in selected}) != len(selected): raise ValueError('duplicate IDs')
    if any(not x['ids'] for x in selected): raise ValueError('empty token sequence')
    return selected


def positions(item, width):
    end = len(item['ids']) - 1
    return list(range(max(0, end-width+1), end+1))


def build(bank_root, templates, out, manifest):
    if out.exists(): raise FileExistsError(out)
    verify(templates, 'COMPLETE_TEMPLATES_SEAL.json')
    spec = importlib.util.spec_from_file_location('e102_page_renderer', templates/'page_range102.py')
    renderer = importlib.util.module_from_spec(spec); spec.loader.exec_module(renderer)
    frozen = json.loads((templates/'TEMPLATES.json').read_text())['rows']
    source = {}; selected = {}
    for bank, rows in [('e57', TARGETS), *REPLAY.items()]:
        root = bank_root/bank/'cache/bank_2026-10-27_v1'
        public = Path('results/g_agreement/understand')/bank/'BANK_SEAL.json'
        if digest(root/'BANK_SEAL.json') != digest(public): raise ValueError('bank seal identity')
        seal = json.loads((root/'BANK_SEAL.json').read_text())
        if digest(root/'items.PRIVATE.json') != seal['files']['items.PRIVATE.json']:
            raise ValueError('items changed')
        selected[bank] = dev_rows(json.loads((root/'items.PRIVATE.json').read_text()), rows)
        source[bank] = {'bank_seal_sha256':digest(public), 'items_sha256':seal['files']['items.PRIVATE.json']}
    rng = random.Random(SEED)
    pairs=[]; requests=[]
    for bank in ('e57','e56','e59'):
        for item in selected[bank]:
            role = 'target' if bank=='e57' else 'replay'
            pos = positions(item, 8 if role=='target' else 4)
            key=bank+':'+item['id']
            requests.append({'key':key,'bank':bank,'id':item['id'],'row':item['feature'],
                             'split':'dev','ids':item['ids'],'positions':pos,
                             'read_position':len(item['ids'])-1,'role':role})
            if role=='target':
                texts = renderer.render_dev(item) if item['feature']=='page_range_digit' else frozen[item['feature']][item['value']]
                if len(texts)!=5: raise ValueError('five frozen templates required')
            for p in pos:
                pair={'pair_id':key+':p'+str(p),'item_key':key,'row':item['feature'],
                      'bank':bank,'split':'dev','position':p,'role':role}
                if role=='target':
                    i=rng.randrange(5);pair.update(template_index=i,text=texts[i])
                else: pair['teacher_item_key']=key
                pairs.append(pair)
    counts=Counter(p['role'] for p in pairs)
    if counts!={'target':2016,'replay':2016}: raise ValueError('equal2016 pair counts')
    out.mkdir(parents=True)
    write(out/'PAIRS.CPU.json',pairs)
    write(out/'ACQUISITION_ITEMS.json',requests)
    write(out/'PLAN_SEAL.json',{'status':'DEV_SELECTION_FROZEN_AWAITING_ACQUISITION',
          'files':{p.name:digest(p) for p in sorted(out.iterdir())}})
    report={'experiment':'E102','status':'DEV_PAIR_PLAN_FROZEN_NOT_TRAINING_READY',
      'seed':SEED,'target_items':252,'replay_items':504,'target_pairs':2016,'replay_pairs':2016,
      'block':44,'capture_convention':'output of decoder block44; original frozen raw token IDs; no appended chat tokens',
      'target_positions':'last8 ending at read token',
      'target_template_selection':'Python Random(20261029).randrange(5) per position, frozen bank item order',
      'replay_selection':'all84 dev items per six rows; last4 positions per item,336pairs per row',
      'replay_teacher':'one sealed original-lens greedy readout at item read token, reused for its4 positions',
      'window_label_convention':'target describes item read-token state at each selected window position, per section210',
      'sources':source,'complete_templates_seal_sha256':digest(templates/'COMPLETE_TEMPLATES_SEAL.json'),
      'plan_seal_sha256':digest(out/'PLAN_SEAL.json'),
      'plan_files':json.loads((out/'PLAN_SEAL.json').read_text())['files'],
      'local_directory':str(out.resolve()),'first_output_utc':None,
      'excluded':{'test_items':0,'test_activations':0,'judge_outputs':0},
      'pending':['PASS_GPU_GATE','4032position_vectors','504sealed_original_greedy_dev_texts','CPU_finalize_and_seal']}
    write(manifest,report)
    return report


def finalize(plan, acquisition, gate, out, manifest):
    if out.exists(): raise FileExistsError(out)
    verify(plan,'PLAN_SEAL.json');verify(acquisition,'OUTPUT_SEAL.json');verify(gate,'OUTPUT_SEAL.json')
    passed=json.loads((gate/'REPORT.json').read_text())
    if passed.get('status')!='PASS' or passed.get('steps')!=10 or passed.get('parity_byte_equal')!=3:
        raise ValueError('GPU gate has not passed')
    if passed['base_before_sha256']!=passed['base_after_sha256'] or passed['adapter_tensors_changed']<=0:
        raise ValueError('frozen-base/update evidence')
    meta=json.loads((acquisition/'ACQUISITION.json').read_text())
    if meta['plan_seal_sha256']!=digest(plan/'PLAN_SEAL.json') or meta['gate_seal_sha256']!=digest(gate/'OUTPUT_SEAL.json'):
        raise ValueError('acquisition provenance')
    if (meta['adapter_sha256']!='7d4b301e002246af3c3f2bb6e768f8fa62f8aac2c231a0bd02a8d4f9ecafd9aa'
        or meta['base_revision']!='6a9e13bd6fc8f0983b9b99948120bc37f49c13e9'
        or meta['capture_adapter_enabled'] or meta['block']!=44 or meta['decoding']!={'do_sample':False,'max_new_tokens':128,'batch':1}
        or not meta['first_output_utc']): raise ValueError('original frozen model and greedy acquisition contract')
    pairs=json.loads((plan/'PAIRS.CPU.json').read_text())
    if any(p['split']!='dev' for p in pairs): raise ValueError('non-dev pair')
    if len(pairs)!=4032 or len({p['pair_id'] for p in pairs})!=4032:
        raise ValueError('exact unique pair inventory')
    if Counter(p['role'] for p in pairs)!=Counter(target=2016,replay=2016):
        raise ValueError('target/replay balance')
    expected = {r:672 for r in TARGETS}
    expected.update({r:336 for rows in REPLAY.values() for r in rows})
    if Counter(p['row'] for p in pairs)!=Counter(expected): raise ValueError('row inventory')
    order=json.loads((acquisition/'PAIR_ORDER.json').read_text())
    if order!=[p['pair_id'] for p in pairs]: raise ValueError('position vector order')
    a=np.load(acquisition/'acts44.npy',allow_pickle=False)
    if a.shape!=(4032,5120) or not np.isfinite(a).all(): raise ValueError('activation grid')
    teachers=json.loads((acquisition/'DEV_TEACHER.json').read_text())
    required={p['teacher_item_key'] for p in pairs if p['role']=='replay'}
    if len(teachers)!=504 or {t['item_key'] for t in teachers}!=required: raise ValueError('exact dev teacher membership')
    if any(t.get('split')!='dev' or not isinstance(t.get('text'),str) or not t['text'] for t in teachers):
        raise ValueError('invalid teacher record')
    lookup={t['item_key']:t['text'] for t in teachers}
    texts=[p['text'] if p['role']=='target' else lookup[p['teacher_item_key']] for p in pairs]
    out.mkdir(parents=True)
    np.save(out/'acts44.npy',a,allow_pickle=False)
    write(out/'TRAINING.json',[{'pair_id':p['pair_id'],'text':t} for p,t in zip(pairs,texts)])
    write(out/'DATASET_SEAL.json',{'status':'DEV_DATASET_READY','files':{p.name:digest(p) for p in sorted(out.iterdir())},
          'plan_seal_sha256':digest(plan/'PLAN_SEAL.json'),'gate_seal_sha256':digest(gate/'OUTPUT_SEAL.json'),
          'acquisition_seal_sha256':digest(acquisition/'OUTPUT_SEAL.json'),'first_output_utc':meta['first_output_utc']})
    write(manifest,{'status':'DEV_DATASET_READY','pairs':4032,'target_pairs':2016,'replay_pairs':2016,
          'dataset_seal_sha256':digest(out/'DATASET_SEAL.json'),'files':json.loads((out/'DATASET_SEAL.json').read_text())['files'],
          'local_directory':str(out.resolve()),'first_output_utc':meta['first_output_utc']})


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('plan')
    for k in ('bank-root','templates','out','manifest'): b.add_argument('--'+k,type=Path,required=True)
    f=sub.add_parser('finalize')
    for k in ('plan','acquisition','gate','out','manifest'): f.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();d=vars(a);command=d.pop('command');(build if command=='plan' else finalize)(**d)

if __name__=='__main__':main()
