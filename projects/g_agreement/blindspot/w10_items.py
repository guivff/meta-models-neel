"""§86: distal-mode carrier with an identical teacher-forced assistant prefix.

CPU authoring only. Does not run the §84 generator or any model forward.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil

from . import protocol as P
from .items import Feature, load_pinned_tokenizer, TOKENIZER_REVISION, TOKENIZER_SHA256

SECTION = 'results/g_agreement/blindspot/w10/REGISTERED_SECTION.md'
SEED = 20261023
READ_TOKEN = 15  # zero-based position in the assistant's copied passage
FILLER_TOKENS = {'near': 50, 'far': 420}
COPY = 'Copy the following passage exactly:\n'
MODES = {
    'language': (('English', 'French'), ('For every reply, answer in English.', 'For every reply, answer in French.'),
                 ('an instruction to answer in English', 'an instruction to answer in French'),
                 [('English', 'French'), ('english', 'french')]),
    'register': (('formal', 'casual'), ('For every reply, use a formal register.', 'For every reply, use a casual register.'),
                 ('an instruction to use a formal register', 'an instruction to use a casual register'),
                 [('formal', 'casual'), ('professional', 'informal')]),
    'audience': (('child', 'expert'), ('For every reply, write for a child.', 'For every reply, write for an expert.'),
                 ('an instruction to write for a child', 'an instruction to write for an expert'),
                 [('child', 'expert'), ('children', 'specialist')]),
    'format': (('JSON', 'prose'), ('For every reply, use JSON output.', 'For every reply, use prose output.'),
                 ('an instruction to output JSON', 'an instruction to output prose'),
                 [('JSON', 'prose'), ('json', 'paragraph')]),
    'length': (('terse', 'detailed'), ('For every reply, be terse.', 'For every reply, be detailed.'),
                 ('an instruction to give a terse answer', 'an instruction to give a detailed answer'),
                 [('terse', 'detailed'), ('brief', 'thorough')]),
    'persona': (('pirate', 'neutral'), ('For every reply, speak as a pirate.', 'For every reply, speak as a neutral assistant.'),
                 ('an instruction to speak as a pirate', 'an instruction to speak as a neutral assistant'),
                 [('pirate', 'neutral'), ('pirate', 'assistant')]),
    'topic': (('no_animals', 'unconstrained'), ('For every reply, never mention animals.', 'For every reply, there is no topic constraint.'),
                 ('an instruction never to mention animals', 'no constraint on which topics may be mentioned'),
                 [('forbidden', 'unrestricted'), ('restricted', 'free')]),
}

# Twelve genuinely different passage grammars; each contributes five passages.
# The same passage family stays in the same split across every mode and distance.
PASSAGES = (
    'The clerk placed the {object} on the wide desk beside the window. A small label recorded the date and the room number. The next task was to check the inventory and close the drawer.',
    'At the station, a notice described a change to the {object} delivery schedule. The morning service would arrive after the platform inspection. Staff checked the list and prepared a clear announcement for visitors.',
    'To prepare the work area, first move the {object} to a clean shelf. Then arrange the remaining tools in a straight line. Check the surface before starting the next stage of the routine procedure.',
    'The archive entry describes a {object} found during the survey of the old building. Its location was marked on a simple plan. A short note explained how the team measured the room and stored the record.',
    'During the meeting, the group discussed where to keep the {object} after the repair. One person suggested the cupboard near the door. The group agreed to check the available space before making the final arrangement.',
    'A visitor asked whether the {object} belonged on the lower shelf or beside the counter. The attendant pointed to a printed diagram. After comparing the markings, they moved it to the place shown on the plan.',
    'The field notebook lists a {object}, two storage boxes, and a roll of plain paper. Below the list is a sketch of the work site. The final line gives the date when the materials were returned.',
    'Before opening the workshop, the supervisor checked the {object} and counted the chairs. A delivery note lay beside the entrance. The team reviewed the schedule and left enough space for the afternoon inspection.',
    'The caretaker watched a dog rest beside the {object} near the garden wall. The path was quiet in the morning light. A neighbour arrived with a parcel and asked where the new notice should be placed.',
    'A short report compared the {object} with an earlier version kept in storage. Both used the same basic arrangement, although the newer version occupied less space. The report recommended another measurement before the next purchase.',
    'In the courtyard, a bird landed near the {object} while the gate was being repaired. The workers set their tools on a cloth. When the work was finished, they checked that the entrance could open freely.',
    'The instruction card shows the {object} in the centre of a square outline. A dotted line marks the edge of the working area. Readers are asked to compare the diagram with the actual position before moving anything.',
)
OBJECTS = ('wooden box', 'metal tray', 'folding screen', 'small cabinet', 'paper folder')


def opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def encode(tok, text):
    return list(tok(text, add_special_tokens=False)['input_ids'])


class ModeFeature(Feature):
    def pairs(self, reader):
        a, b = self.descriptions
        wrappers = ('- The model is following {x}.', '- The current operating mode reflects {x}.') if reader == 'olens' else (
            'The model is following {x}.', 'The current operating mode reflects {x}.')
        return [(w.format(x=a), w.format(x=b)) for w in wrappers]


def specs():
    out = {}
    for mode, (values, _, descriptions, native) in MODES.items():
        for distance in FILLER_TOKENS:
            f = ModeFeature('assistant', 'mode', values, descriptions, tuple(native[0]))
            out[f'{mode}_{distance}'] = {r: f.pairs(r) for r in ('olens', 'nla')}
            out[f'{mode}_{distance}'].update(jlens=native, values=list(values), mode=mode,
                distance=distance, kind='binary', **{'class': 'mode', 'domain': 'assistant'})
    for domain in ('prose', 'python'):
        out['surprisal_'+domain] = {'values': ['high', 'low'], 'class': 'surprisal', 'domain': domain,
            'kind': 'deferred_binary', 'jlens': [('surprising', 'predictable'), ('unexpected', 'expected')],
            'olens': [('- The current token is surprising to the model.', '- The current token is predictable to the model.'),
                      ('- The model assigned low probability to this token.', '- The model assigned high probability to this token.')],
            'nla': [('The current token is surprising to the model.', 'The current token is predictable to the model.'),
                    ('The model assigned low probability to this token.', 'The model assigned high probability to this token.')]}
    return out


def instruction_pair(tok, mode):
    """All padding is inside the instruction span; the carrier is never padded by value."""
    bases = MODES[mode][1]
    def render(base, n):
        return base+'\nInstruction record:'+' noted'*n+'.'
    sizes = [len(encode(tok, render(b, 0))) for b in bases]
    for target in range(max(sizes)+2, max(sizes)+40):
        result = []
        for base in bases:
            found = next((render(base, n) for n in range(45) if len(encode(tok, render(base, n))) == target), None)
            if found is None:
                break
            result.append(found)
        if len(result) == 2:
            return result
    raise ValueError('cannot match instruction pair: '+mode)


def filler(tok, distance):
    target = FILLER_TOKENS[distance]
    # No truncation of an arbitrary word or instructions; repeated neutral single-token material.
    for n in range(target+30):
        text = 'Neutral archive record:'+' paper'*n+'.'
        if len(encode(tok, text)) == target:
            return text
    raise ValueError('cannot construct exact neutral filler')


def carrier(tok, instruction, neutral, passage):
    head = 'Operating instruction:\n'
    tail = '\nEnd instruction.\n\n'+neutral+'\n\n'+COPY+passage
    user = head+instruction+tail
    rendered = tok.apply_chat_template([{'role': 'user', 'content': user}], tokenize=False,
                                       add_generation_prompt=True, enable_thinking=False)
    enc = tok(rendered, add_special_tokens=False, return_offsets_mapping=True)
    ids = list(enc['input_ids'])
    lo = rendered.index(head)+len(head)
    hi = lo+len(instruction)
    touched = [i for i, (a, b) in enumerate(enc['offset_mapping']) if b > lo and a < hi]
    if not touched or touched != list(range(touched[0], touched[-1]+1)):
        raise ValueError('noncontiguous instruction span')
    start, end = touched[0], touched[-1]+1
    copied = encode(tok, passage)[:READ_TOKEN+1]
    if len(copied) != READ_TOKEN+1:
        raise ValueError('passage too short')
    return rendered+tok.decode(copied), ids+copied, {
        'instruction_token_span': [start, end], 'instruction_char_span': [lo, hi],
        'instruction_ids': encode(tok, instruction), 'prompt_ids': ids,
        'assistant_start': len(ids), 'assistant_prefix_ids': copied,
        'assistant_read_index': READ_TOKEN, 'read_position': len(ids)+READ_TOKEN,
        'filler_tokens': len(encode(tok, neutral)), 'passage': passage,
        'instruction_to_read_tokens': len(ids)+READ_TOKEN-end,
    }


def build(tok):
    items = []
    for mode, (values, _, _, _) in MODES.items():
        instructions = instruction_pair(tok, mode)
        for distance in FILLER_TOKENS:
            neutral = filler(tok, distance)
            feature = mode+'_'+distance
            for template, grammar in enumerate(PASSAGES):
                cluster = opaque(f'W10-passage-family-v1:{template}')
                for variant, obj in enumerate(OBJECTS):
                    passage = grammar.format(object=obj)
                    pair = opaque(f'W10-pair-v1:{feature}:{template}:{variant}')
                    for side, value in enumerate(values):
                        text, ids, meta = carrier(tok, instructions[side], neutral, passage)
                        items.append({'id': opaque(pair+':'+str(side)), 'feature': feature,
                            'class': 'mode', 'domain': 'assistant', 'split': 'dev' if template%2 == 0 else 'test',
                            'cluster': cluster, 'value': value, 'ids': ids, 'text': text,
                            'meta': {**meta, 'pair_id': pair, 'template_index': template,
                                     'variant': variant, 'mode': mode, 'distance': distance,
                                     'token_length': len(ids), 'kind': 'binary'}})
    return items


def verify(tok, items):
    from scipy.stats import ks_2samp
    pairs, groups = defaultdict(list), defaultdict(list)
    if len(items) != 1680 or len({x['id'] for x in items}) != 1680:
        raise ValueError('need 14 rows × 120 unique items')
    for it in items:
        meta = it['meta']
        pairs[meta['pair_id']].append(it)
        groups[it['feature']].append(it)
        if encode(tok, it['text']) != it['ids']:
            raise ValueError('full rendered text/token drift')
        if meta['read_position'] != len(it['ids'])-1 or meta['assistant_read_index'] != READ_TOKEN:
            raise ValueError('read position drift')
        if meta['filler_tokens'] != FILLER_TOKENS[meta['distance']]:
            raise ValueError('wrong filler distance')
    if set(groups) != {m+'_'+d for m in MODES for d in FILLER_TOKENS}:
        raise ValueError('wrong frozen row set')
    for pair in pairs.values():
        if len(pair) != 2:
            raise ValueError('each passage requires both values')
        a, b = pair
        sa, ea = a['meta']['instruction_token_span']
        sb, eb = b['meta']['instruction_token_span']
        if (sa, ea) != (sb, eb) or a['ids'][:sa] != b['ids'][:sb] or a['ids'][ea:] != b['ids'][eb:]:
            raise ValueError('tokens outside instruction differ')
        if len(a['meta']['instruction_ids']) != len(b['meta']['instruction_ids']):
            raise ValueError('instruction token lengths differ')
        if a['meta']['passage'] != b['meta']['passage'] or a['cluster'] != b['cluster'] or a['split'] != b['split']:
            raise ValueError('passage pair or split drift')
    checks = []
    for row, group in groups.items():
        if len(group) != 120 or len({x['cluster'] for x in group}) != 12:
            raise ValueError('wrong row size or passage-cluster count')
        if Counter(x['value'] for x in group) != dict.fromkeys(MODES[row.rsplit('_', 1)[0]][0], 60):
            raise ValueError('wrong value balance')
        for split in ('dev', 'test'):
            subset = [x for x in group if x['split'] == split]
            values = MODES[row.rsplit('_', 1)[0]][0]
            ls = [[len(x['ids']) for x in subset if x['value'] == v] for v in values]
            p = float(ks_2samp(*ls).pvalue)
            diff = abs(sum(ls[0])/len(ls[0])-sum(ls[1])/len(ls[1]))
            if p <= .2 or diff > 1 or sorted(ls[0]) != sorted(ls[1]):
                raise ValueError('length check failed')
            checks.append({'feature': row, 'split': split, 'n_per_value': len(ls[0]),
                           'ks_p': p, 'mean_token_difference': diff})
        if {x['cluster'] for x in group if x['split'] == 'dev'} & {x['cluster'] for x in group if x['split'] == 'test'}:
            raise ValueError('passage cluster leakage')
    return {'status': 'PASS', 'items': len(items), 'pairs': len(pairs), 'checks': checks,
            'outside_instruction_identical': True, 'instruction_lengths_exact': True,
            'assistant_read_index': READ_TOKEN, 'filler_tokens': FILLER_TOKENS}


def random_donors(items):
    """Uniform hashed draw from the same row and passage cluster, independent of value.

    Self-donors are permitted: excluding the recipient would make the distribution
    depend slightly on its class. No balancing/selection using observed reader scores.
    """
    groups = defaultdict(list)
    for x in items:
        groups[x['feature'], x['cluster']].append(x['id'])
    out = {}
    for x in items:
        candidates = sorted(groups[x['feature'], x['cluster']])
        draw = int(hashlib.sha256(f'W10-random-donor:{SEED}:{x["id"]}'.encode()).hexdigest(), 16)
        out[x['id']] = candidates[draw % len(candidates)]
    return out


def mode_check_ids(items):
    """Ten passage pairs per row, round-robin over all six dev families."""
    out = []
    for feature in sorted({x['feature'] for x in items}):
        dev = [x for x in items if x['feature'] == feature and x['split'] == 'dev']
        chosen = []
        for variant in range(5):
            for template in range(0, 12, 2):
                if len(chosen) == 20:
                    break
                chosen.extend(x for x in dev if x['meta']['template_index'] == template and x['meta']['variant'] == variant)
            if len(chosen) == 20:
                break
        out.extend(x['id'] for x in chosen)
    return out


def surprisal_pool(w1):
    w1 = Path(w1)
    seal = P.verify(w1, 'INPUT_SEAL.json')
    source = w1/'items.DO_NOT_STAGE.jsonl'
    manifest = json.loads((w1/'manifest.json').read_text())
    if P.sha(source) != manifest['files']['items.DO_NOT_STAGE.jsonl']:
        raise ValueError('W1 source item hash changed')
    result = []
    for x in P.rows(source):
        if x['domain'] not in ('prose', 'python') or x['meta']['kind'] != 'binary':
            continue
        result.append({'id': opaque('W10-surprisal:'+x['id']), 'feature': 'surprisal_'+x['domain'],
            'class': 'surprisal', 'domain': x['domain'], 'cluster': x['cluster'], 'split': x['split'],
            'value': None, 'ids': x['ids'], 'text': x['text'],
            'meta': {'w1_id': x['id'], 'w1_feature': x['feature'], 'read_position': len(x['ids'])-1,
                     'token_length': len(x['ids']), 'kind': 'deferred_surprisal'}})
    return result, {'input_seal_sha256': P.sha(w1/'INPUT_SEAL.json'), 'manifest_sha256': P.sha(w1/'manifest.json'),
                    'source_items_sha256': P.sha(source), 'n': len(result)}


def source_hashes():
    paths = ['projects/g_agreement/blindspot/'+n for n in
             ('__init__.py', 'w10_items.py', 'w10_checks.py', 'w10_run.py', 'w10_request.py', 'run.py', 'protocol.py', 'items.py', 'w1_templates.py')]
    paths += [SECTION, 'results/g_agreement/blindspot/w10/REGISTRATION_ORIGIN.json',
              'projects/g_agreement/manifest/assets.json', 'common/__init__.py', 'common/stats.py', 'external/PINS.md']
    paths += [str(p.relative_to(P.ROOT)) for p in (P.ROOT/'external/mats-nla-workspace/src').rglob('*.py')]
    return {n: P.sha(P.ROOT/n) for n in paths}


def freeze(tok, tokenizer_path, w1, out, frozen, staged):
    from .w10_checks import JUDGE_PROMPT, SCRIPT_POLICY, SURPRISAL_POLICY
    items = build(tok)
    lengths = verify(tok, items)
    pool, lineage = surprisal_pool(w1)
    all_items = items+pool
    donors = random_donors(all_items)
    out, frozen, staged = map(Path, (out, frozen, staged))
    out.mkdir(parents=True, exist_ok=False)
    P.jsonl(out/'items.input.jsonl', [{'id': x['id'], 'feature': x['feature'], 'ids': x['ids'], 'donor_id': donors[x['id']]} for x in all_items])
    P.jsonl(out/'items.DO_NOT_STAGE.jsonl', all_items)
    P.jsonl(out/'labels.DO_NOT_STAGE.jsonl', [{k: x[k] for k in ('id', 'feature', 'class', 'domain', 'cluster', 'split', 'value')} for x in all_items])
    selected = set(mode_check_ids(items))
    P.jsonl(out/'mode_checks.input.jsonl', [{'id': x['id'], 'feature': x['feature'], 'prompt_ids': x['meta']['prompt_ids']} for x in items if x['id'] in selected])
    P.dump(out/'templates.json', specs())
    P.dump(out/'instruction_pairs.json', {mode: {'values': list(MODES[mode][0]),
        'instructions': instruction_pair(tok, mode),
        'token_lengths': [len(encode(tok, s)) for s in instruction_pair(tok, mode)]} for mode in MODES})
    P.dump(out/'lengths.json', lengths)
    P.dump(out/'mode_active_policy.json', {'n_dev_per_row': 20, 'threshold': .7,
        'generation': {'do_sample': False, 'max_new_tokens': 48}, 'teacher_forced_tokens': 0,
        'judge_prompt': JUDGE_PROMPT, 'scripts': SCRIPT_POLICY, 'judge_budget_usd': 3})
    P.dump(out/'surprisal_policy.json', SURPRISAL_POLICY)
    P.dump(out/'manifest.json', {'schema': 'blindspot-w10-v1', 'experiment': 'W10', 'section': 86,
        'registration_ref': '7b955281', 'registration_path': SECTION, 'registration_sha256': P.sha(P.ROOT/SECTION),
        'source_files': source_hashes(), 'tokenizer_revision': TOKENIZER_REVISION,
        'tokenizer_sha256': TOKENIZER_SHA256, 'chat_template_sha256': hashlib.sha256(tok.chat_template.encode()).hexdigest(),
        'seed': SEED, 'capture_sites': [42, 44], 'mode_rows': 14, 'mode_items': len(items),
        'mode_items_per_row': 120, 'passage_clusters_per_row': 12, 'passages_per_cluster': 5,
        'dev_clusters': [0, 2, 4, 6, 8, 10], 'test_clusters': [1, 3, 5, 7, 9, 11],
        'assistant_read_index': READ_TOKEN, 'filler_tokens': FILLER_TOKENS, 'mode_check_items': len(selected),
        'surprisal_pool': lineage, 'rows': specs(), 'random_donor_policy': 'same row and cluster, hash regardless of value; self allowed',
        'labels_sha256': P.sha(out/'labels.DO_NOT_STAGE.jsonl'), 'full_items_sha256': P.sha(out/'items.DO_NOT_STAGE.jsonl'),
        'science_cap_seconds': 3600, 'science_allocation': '1.5 * measured forecast + 360, NO_FIT if > 3600',
        'setup_allowance_seconds': 1500, 'bootstrap_replicates': 2000,
        'model_forwards_at_freeze': 0, 'reconstructor_text_window': 'OPEN_DEPENDENCY; ask Camila; no blind-by-construction claim until resolved'})
    names = ['items.input.jsonl', 'mode_checks.input.jsonl', 'templates.json', 'instruction_pairs.json', 'lengths.json',
             'mode_active_policy.json', 'surprisal_policy.json', 'manifest.json']
    P.seal(out, names, 'INPUTS_FROZEN_W10_BEFORE_CAPTURE')
    for destination, files in ((frozen, names[2:]+['INPUT_SEAL.json']), (staged, names+['INPUT_SEAL.json'])):
        destination.mkdir(parents=True, exist_ok=False)
        for name in files:
            shutil.copyfile(out/name, destination/name)
    P.verify(staged, 'INPUT_SEAL.json')
    return lengths


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('tokenizer', 'w1-bank', 'out', 'freeze-out', 'stage-out'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args()
    tok = load_pinned_tokenizer(a.tokenizer)
    with P.logged('w10_build_freeze', extra={'model_forwards': 0}):
        report = freeze(tok, a.tokenizer, a.w1_bank, a.out, a.freeze_out, a.stage_out)
    print(json.dumps({'status': report['status'], 'mode_items': report['items'], 'length_checks': len(report['checks'])}))


if __name__ == '__main__':
    main()
