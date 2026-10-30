"""§113 / 6a2b114e: frozen E21 texts and split checks, without model inference."""
import argparse
from pathlib import Path
import numpy as np
from .cpu import ROOT, read, rows, dump, sha, verify, seal
from .e18 import pair_donors
from .followup_packed import jsonl

SEED = 20261025
BATCH = 8
PATHS = ('dev_real', 'description', 'exhibit_e15', 'exhibit_real')
BRIEF = 'results/g_agreement/understand/e21/BRIEF_UNDERSTAND.6a2b114e.md'
PLAN = 'results/g_agreement/understand/e21/PLAN.json'


def check_splits(items, features, count=84):
    if len({r['id'] for r in items}) != len(items):
        raise ValueError('duplicate item IDs')
    if {r['feature'] for r in items} != set(features):
        raise ValueError('exact frozen feature set required')
    if any(r['split'] not in ('dev', 'test') for r in items):
        raise ValueError('only dev/test permitted')
    for f in features:
        groups = {}
        for split in ('dev', 'test'):
            rr = [r for r in items if r['feature'] == f and r['split'] == split]
            if len(rr) != count or len({r['value'] for r in rr}) != 2:
                raise ValueError('complete binary dev/test row required')
            if sorted(sum(r['value'] == v for r in rr) for v in {r['value'] for r in rr}) != [count//2]*2:
                raise ValueError('balanced frozen values required')
            groups[split] = {r['cluster'] for r in rr}
        if groups['dev'] & groups['test']:
            raise ValueError('template-cluster leakage across probe train and test')


def assemble(items, templates, continuations, e15, donors):
    """Both W1 Oracle strings verbatim, including '- '; both E15 strings verbatim.

    Each arm variant is reconstructed separately, without text deduplication.
    No prefix, chat wrapper, stripping, concatenation, or dev-valid-pair selection.
    """
    records = []
    for item in items:
        key, f, split = item['id'], item['feature'], item['split']
        spec = templates[f]
        side = spec['values'].index(item['value'])
        if len(spec['olens']) != 2 or any(len(p) != 2 for p in spec['olens']):
            raise ValueError('two frozen W1 pairs required')
        if key not in continuations or len(continuations[key]['ids']) != 16:
            raise ValueError('sealed E1b sixteen-token continuation required')
        def put(path, arm, variant, text):
            if not isinstance(text, str) or not text:
                raise ValueError('nonempty, unmodified reconstructor text required')
            records.append({'id': key+'|'+arm+'|'+str(variant), 'item': key,
                            'feature': f, 'split': split, 'path': path,
                            'arm': arm, 'variant': variant, 'text': text})
        if split == 'dev':
            put('dev_real', 'dev_real', 0, continuations[key]['text'])
            continue
        for variant, pair in enumerate(spec['olens']):
            put('description', 'describe_true', variant, pair[side])
            put('description', 'describe_opposite', variant, pair[1-side])
        if f in e15['rows']:
            pairs = e15['rows'][f]['pairs']
            if len(pairs) != 2:
                raise ValueError('both frozen E15 variants required')
            for variant, pair in enumerate(pairs):
                put('exhibit_e15', 'exhibit_true', variant, pair['AB'[side]])
                put('exhibit_e15', 'exhibit_opposite', variant, pair['AB'[1-side]])
        else:
            put('exhibit_real', 'exhibit_true', 0, continuations[key]['text'])
            put('exhibit_real', 'exhibit_opposite', 0, continuations[donors[key]]['text'])
    return records


def unit_plan(records):
    return {path: [ix[j:j+BATCH] for j in range(0, len(ix), BATCH)]
            for path in PATHS
            for ix in [[i for i, r in enumerate(records) if r['path'] == path]]}


def prepare(a):
    from transformers import AutoTokenizer
    bank, target = a.w1/'w1-bank-v2', a.w1/'w1-assembled/target'
    verify(bank, 'INPUT_SEAL.json'); verify(target)
    verify(a.e1b); verify(a.e1b/'continuations')
    verify(a.w1_analysis, 'ANALYSIS_SEAL.json')
    private = bank/'items.DO_NOT_STAGE.jsonl'
    if sha(private) != read(bank/'manifest.json')['files'][private.name]:
        raise ValueError('W1 private label hash mismatch')
    e15_plan = read(a.e15.parent/'plan.json')
    if sha(a.e15) != e15_plan['source_files'][str(a.e15.relative_to(a.e15.parents[4]))]:
        raise ValueError('E15 continuation pair pin mismatch')
    previous = read(ROOT/'results/g_agreement/understand/e1b/PACKED_INPUT_RECEIPT.json')
    if previous['private_items_sha256'] != sha(private):
        raise ValueError('E1b/W1 bank mismatch')
    verify(Path(previous['path']), 'INPUT_SEAL.json')
    cp = read(a.e1b/'continuations/provenance.json')
    if cp['input_seal_sha256'] != previous['seal_sha256']:
        raise ValueError('E1b continuation/input lineage mismatch')
    cont_rows = rows(a.e1b/'continuations/continuations.jsonl')
    if len(cont_rows) != 4200 or len({r['id'] for r in cont_rows}) != 4200:
        raise ValueError('all sealed 2100 dev +2100 test continuations required')
    cont = {r['id']: r for r in cont_rows}
    features = sorted({r['feature'] for r in cont_rows})
    if len(features) != 25:
        raise ValueError('all25 W1 rows required')
    full = rows(private)
    items = sorted([r for r in full if r['feature'] in features and r['split'] in ('dev','test')],
                   key=lambda r: (r['split'], r['feature'], r['id']))
    check_splits(items, features)
    if set(cont) != {r['id'] for r in items}:
        raise ValueError('continuation IDs differ from frozen dev/test population')
    templates = {f: read(bank/'templates.json')[f] for f in features}
    e15 = read(a.e15)
    if any(e15_plan['values'][f] != templates[f]['values'] for f in e15['rows']):
        raise ValueError('E15/W1 value orientation mismatch')
    test = [r for r in items if r['split'] == 'test']
    dev = [r for r in items if r['split'] == 'dev']
    donors = pair_donors(test, SEED)
    records = assemble(items, templates, cont, e15, donors)
    # Only dev items provide pilot inputs, including the same fixed text variants.
    pseudo = [{**r, 'split': 'test'} for r in dev]
    dev_donors = pair_donors(dev, SEED)
    pilot_pool = [r for r in records if r['split'] == 'dev'] + [
        {**r, 'split': 'dev'} for r in assemble(pseudo, templates, cont, e15, dev_donors)]
    tok = AutoTokenizer.from_pretrained(a.tokenizer, local_files_only=True)
    if sha(a.tokenizer/'tokenizer.json') != read(ROOT/'projects/g_agreement/manifest/assets.json')['target']['files_needed']['tokenizer.json_sha256']:
        raise ValueError('native tokenizer pin mismatch')
    lengths = [len(tok.encode(r['text'], add_special_tokens=False)) for r in records]
    pilot_lengths = [len(tok.encode(r['text'], add_special_tokens=False)) for r in pilot_pool]
    plans, pilots, pilot_selected = unit_plan(records), {}, []
    for path, us in unit_plan(pilot_pool).items():
        # Three full dev batches with largest padded work; repeated setup first batch.
        full_units = [u for u in us if len(u) == BATCH]
        chosen = sorted(full_units, key=lambda u: (-max(pilot_lengths[i] for i in u), u))[:3]
        if len(chosen) != 3:
            raise ValueError('three full dev pilot batches required for every path')
        required = max(lengths[i] for u in plans[path] for i in u)
        pilots[path] = []
        for unit in chosen:
            selected = []
            for i in unit:
                # Discarded timing-only copies cover the longest production text.
                # Never modify any retained dev continuation or test text.
                r = dict(pilot_pool[i]); original = r['text']
                while len(tok.encode(r['text'], add_special_tokens=False)) < required:
                    r['text'] += ' neutral'
                r['timing_only_padding'] = r['text'] != original
                selected.append(len(pilot_selected)); pilot_selected.append(r)
            pilots[path].append(selected)
    capture = read(target/'provenance.target.json')
    if capture['input_seal_sha256'] != sha(bank/'INPUT_SEAL.json'):
        raise ValueError('native capture belongs to another bank')
    order = read(target/'items.order.json'); index = {key:i for i,key in enumerate(order)}
    h = np.load(target/'acts44.npy', allow_pickle=False, mmap_mode='r')
    a.out.mkdir(parents=True, exist_ok=False)
    jsonl(a.out/'texts.input.jsonl', records); jsonl(a.out/'pilot.input.jsonl', pilot_selected)
    public = [{k:r[k] for k in ('id','feature','split')} for r in items]
    jsonl(a.out/'items.input.jsonl', public)
    dump(a.out/'test_ids.json', [r['id'] for r in test]); dump(a.out/'dev_ids.json', [r['id'] for r in dev])
    np.save(a.out/'acts44.npy', np.asarray(h[[index[r['id']] for r in test]]), allow_pickle=False)
    for name, value in [('templates',templates),('E15_CONTINUATION_PAIRS',e15),('donors',donors),('units',plans),('pilot_units',pilots)]:
        dump(a.out/(name+'.json'),value)
    w1rows=read(a.w1_analysis/'metrics.json')['rows']
    reference={f:next(r['true']['auroc'] for r in w1rows if r['feature']==f and r['reader']=='olens' and r['layer']==44) for f in features}
    dump(a.out/'W1_ORACLE_REFERENCE.json',reference)
    dump(a.out/'provenance.json',{'authority':'6a2b114e','private_items_sha256':sha(private),
        'W1_bank_seal_sha256':sha(bank/'INPUT_SEAL.json'),'W1_target_seal_sha256':sha(target/'SCORE_SEAL.json'),
        'E1b_continuation_seal_sha256':sha(a.e1b/'continuations/SCORE_SEAL.json'),
        'E15_pairs_sha256':sha(a.e15),'W1_analysis_seal_sha256':sha(a.w1_analysis/'ANALYSIS_SEAL.json'),
        'tokenizer_sha256':sha(a.tokenizer/'tokenizer.json'),'new_generation':False,
        'real_next_16':'exact sealed E1b target greedy continuations, no prefix or new generation',
        'donors':'numpy default_rng20261025; sorted feature/id; opposite test value, replacement',
        'W1_descriptions':'both olens phrasing pairs verbatim including bullet prefix',
        'E15_exhibits':'both frozen variants, including all eight rows; no E15 validity filtering',
        'cosine_order':'cosine each variant with recipient h, then mean; never cosine of averaged vectors',
        'counts':{p:sum(r['path']==p for r in records) for p in PATHS},
        'units':{p:len(u) for p,u in plans.items()},'dev_pilot_lengths_cover_production':True,
        'pilot':'discarded dev-derived copies; append neutral text only in pilot to cover longest production token length per path; never used to fit or score'})
    seal(a.out,[p.name for p in a.out.iterdir() if p.is_file()],'E21_INPUTS_FROZEN_BEFORE_AR')
    (a.out/'SCORE_SEAL.json').rename(a.out/'INPUT_SEAL.json')


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','w1','w1-analysis','e1b','e15','tokenizer'):
        p.add_argument('--'+name,type=Path,required=True)
    prepare(p.parse_args())
