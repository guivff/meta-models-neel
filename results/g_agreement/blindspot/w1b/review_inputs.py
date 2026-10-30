"""Read-only audit of existing W1b bank; never build or score items."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from projects.g_agreement.blindspot import protocol as P
from projects.g_agreement.blindspot import w1b_items as W
from transformers import AutoTokenizer

bank = ROOT/'cache/g_agreement/blindspot/w1b-bank-v1'
stage = ROOT/'cache/g_agreement/blindspot/w1b-stage-v1'
freeze = ROOT/'results/g_agreement/blindspot/w1b/freeze'
read = lambda path: json.loads(path.read_text())
git = lambda *args: subprocess.check_output(['git', *args], cwd=ROOT)
digest = lambda data: hashlib.sha256(data).hexdigest()
m = read(bank/'manifest.json')
for directory in (bank, stage):
    P.verify(directory, 'INPUT_SEAL.json')
for name, expected in m['files'].items():
    assert P.sha(bank/name) == expected, name
for path in freeze.iterdir():
    assert path.read_bytes() == (bank/path.name).read_bytes(), path.name
    assert path.read_bytes() == git('show', '328bc63c:'+str(path.relative_to(ROOT)))
for name, expected in m['source_files'].items():
    assert P.sha(ROOT/name) == expected, name
    assert digest(git('show', '328bc63c:'+name)) == expected, name
for name in ('projects/g_agreement/blindspot/w1b_items.py',
             'projects/g_agreement/blindspot/w1b/registry_features.py'):
    assert git('show', '9f39b528:'+name) == (ROOT/name).read_bytes(), name
receipt = m['selection_receipt']
selected_bytes = git('show', receipt['source_commit']+':'+receipt['selection_file'])
assert digest(selected_bytes) == receipt['selection_sha256']
selection = json.loads(selected_bytes)
if isinstance(selection, dict):
    options = [selection[k] for k in ('section79_features','features','selected_features','top10','top_10','candidates') if k in selection]
    assert len(options) == 1
    selection = options[0]
selected = [x if isinstance(x,str) else x.get('feature',x.get('id')) for x in selection]
assert selected == receipt['section79_features'] and not receipt['section81_features']
assert len(selected) == len(set(selected)) == 10
assert set(m['rows']) == set(selected)
assert git('show', receipt['source_commit']+':projects/g_agreement/blindspot/screens/features.py') == Path(W.S.__file__).read_bytes()
assert set(p.name for p in stage.iterdir()) == set(read(bank/'INPUT_SEAL.json')['files']) | {'INPUT_SEAL.json'}
assert all('DO_NOT_STAGE' not in p.name for p in stage.iterdir())
tokenizer = Path(m['tokenizer'])
assert P.sha(tokenizer/'tokenizer.json') == W.TOKENIZER_SHA256 == m['tokenizer_sha256']
tok = AutoTokenizer.from_pretrained(tokenizer, local_files_only=True)
items = P.rows(bank/'items.DO_NOT_STAGE.jsonl')
inputs = P.rows(stage/'items.input.jsonl')
labels = P.rows(bank/'labels.DO_NOT_STAGE.jsonl')
assert len(items) == len(inputs) == len(labels) == 1680
assert len({it['id'] for it in items}) == len({it['text'] for it in items}) == 1680
checks = W.verify_lengths(tok, items)  # Validation only; no build/matched_pair/main call.
assert checks == read(freeze/'lengths.json')
templates = read(bank/'templates.json')
pair_groups = defaultdict(list)
tails = defaultdict(lambda: defaultdict(set))
pad_counts = defaultdict(lambda: defaultdict(set))
pad_deltas = defaultdict(set)
prepositions = set('at between by for from in on over to under with without'.split())
auxiliaries = set('am are be been being can could did do does had has have is may might must shall should was were will would'.split())

def independent_value(text, feature):
    # These authored rows end in simple decimal integers, ASCII words or punctuation.
    # Parse the terminal content directly, independently of the frozen extractor.
    terminal = text.rsplit(None, 1)[-1]
    if feature == 'current_colon':
        return text.rstrip().endswith(':')
    if feature == 'current_number':
        return terminal.isascii() and terminal.isdecimal()
    if feature.startswith('number_'):
        assert terminal.isascii() and terminal.isdecimal()
        threshold = int(feature.rsplit('_',1)[-1])
        return (len(terminal) if 'digits' in feature else int(terminal)) >= threshold
    if feature == 'word_allcaps':
        assert terminal.isascii() and terminal.isalpha()
        return len(terminal) >= 2 and terminal == terminal.upper()
    if feature in ('wordlist_preposition','wordlist_auxiliary'):
        return terminal.lower() in (prepositions if feature.endswith('preposition') else auxiliaries)
    raise AssertionError(feature)

for it, inp, lab in zip(items, inputs, labels):
    feature = it['feature']
    side = it['value'] == 'present'
    assert inp['id'] == lab['id'] == it['id']
    assert inp['feature'] == lab['feature'] == feature and inp['ids'] == it['ids']
    assert lab == {key: it[key] for key in lab}
    assert set(inp) == {'id','feature','ids','donor_id'}
    assert it['meta']['read_position'] == len(it['ids']) - 1
    assert it['meta']['token_length'] == len(it['ids'])
    assert tok.decode(it['ids'], clean_up_tokenization_spaces=False) == it['text']
    padding = re.match(r'^(?:pad )*', it['text']).group()
    unpadded = it['text'][len(padding):]
    assert independent_value(it['text'],feature) == independent_value(unpadded,feature) == side
    assert W.S.extract(unpadded,it['domain'])[feature] is side
    assert it['split'] == ('dev' if it['meta']['template_index'] % 2 == 0 else 'test')
    assert it['class'] == W.S.BY_ID[feature].kind and it['domain'] == W.domain(feature)
    assert it['meta']['registry_definition'] == W.S.BY_ID[feature].definition
    pair_groups[(feature,it['meta']['pair_id'])].append((it, inp))
    tails[feature][it['value']].add(it['text'].rsplit(None,1)[-1])
    pad_counts[feature][it['value']].add(len(padding)//4)

per_row = []
for feature in selected:
    subset = [it for it in items if it['feature'] == feature]
    dev = {it['cluster'] for it in subset if it['split'] == 'dev'}
    test = {it['cluster'] for it in subset if it['split'] == 'test'}
    assert len(dev) == len(test) == 6 and not dev & test
    assert Counter((it['split'],it['value']) for it in subset) == Counter({(s,v):42 for s in ('dev','test') for v in ('present','absent')})
    assert len({it['meta']['template_index'] for it in subset}) == 12
    spec = W.StatementFeature(W.domain(feature),W.S.BY_ID[feature].kind,('present','absent'),
                              (W.S.BY_ID[feature].positive,W.S.BY_ID[feature].negative),('true','false'))
    assert templates[feature]['olens'] == [list(x) for x in spec.pairs('olens')]
    assert templates[feature]['nla'] == [list(x) for x in spec.pairs('nla')]
    assert templates[feature]['jlens'] == templates[feature]['logit'] == W.NATIVE_PAIRS
    per_row.append({'feature':feature,'n':len(subset),'dev_clusters':6,'test_clusters':6,
                    'labels_checked_before_and_after_padding':len(subset),
                    'terminal_values':{v:sorted(x) for v,x in tails[feature].items()}})
for (feature,_), pair in pair_groups.items():
    assert len(pair) == 2 and {it['value'] for it,inp in pair} == {'present','absent'}
    (a,ai),(b,bi) = pair
    assert len(a['ids']) == len(b['ids'])
    assert a['cluster'] == b['cluster'] and a['split'] == b['split']
    assert ai['donor_id'] == b['id'] and bi['donor_id'] == a['id']
    byvalue = {it['value']:len(re.match(r'^(?:pad )*',it['text']).group())//4 for it,inp in pair}
    pad_deltas[feature].add(byvalue['present']-byvalue['absent'])
assert len(pair_groups) == 840
for row in per_row:
    row['pad_count_present_minus_absent'] = sorted(pad_deltas[row['feature']])

result = {'at_utc':datetime.now(timezone.utc).isoformat(),'status':'checked OK',
          'scope':'Pre-capture input/seal/label/length review only; no generation or model forwards',
          'generator_commit':'9f39b528','freeze_commit':'328bc63c',
          'selection_receipt':receipt,'input_seal_sha256':P.sha(bank/'INPUT_SEAL.json'),
          'manifest_sha256':P.sha(bank/'manifest.json'),'tokenizer_sha256':m['tokenizer_sha256'],
          'items_verified':1680,'pairs_verified':840,'length_groups_verified':20,
          'all_ks_p':1.0,'all_mean_token_difference':0.0,
          'committed_freeze_matches_bank':True,'stage_label_free':True,
          'generator_and_registry_match_preselection_commit':True,
          'selection_registry_matches_snapshot':True,'source_file_hashes_verified':len(m['source_files']),
          'rows':per_row,
          'interpretation_caveats':[
              'Templates are held out; terminal lexemes are reused across splits. This tests the registered operational predicates, not generalization to unseen words or numeric forms.',
              'Numeric magnitude and digit rows use positive decimal integers near thresholds; signed values, decimals and scientific notation are outside this bank.',
              'Prepositions and auxiliaries mean exact frozen lexical-list membership, not contextual part of speech.',
              'Exact token matching can require different amounts of leading pad text by value; the required label and length checks pass, but padding is not identical and is not proven cue-free.'
          ]}
out = ROOT/'results/g_agreement/blindspot/w1b/PRECAPTURE_REVIEW.json'
out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({'status':result['status'],'items':len(items),'pairs':len(pair_groups),'length_groups':len(checks['checks']),
                  'rows':per_row,'report':str(out)},indent=2))
