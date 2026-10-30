"""E133 behaviour-only selection (Track Q, CPU; §241 + §242 addendum; Guiv one-pod ruling 23510d80d). No reader output exists or is read.
For each screened prompt: text = the 32-token greedy continuation (leading whitespace stripped, §238 clarification 3), classified with the unchanged
core.analysis_utils.parse_target_answer (pin cf6bc5ed) against [recipient0, recipient1, previous holder] (W-text parser_target_order; bAbI:
[original current, twin current, previous]). A pair is kept only if BOTH members answer their own current value. Kept: first 84 multi-hop and
first 42 one-hop pairs in generation order; first 42 bAbI pairs in source order (fewer if fewer qualify; no refill). Missing text = not correct.
v3 (§245 E133b): screen_synthetic may be "-" (bAbI-only pod); fewer than 20 qualifying bAbI pairs => no bAbI main root (screen results only).
v2 (W-mechanism-C v3 runner.load, 3213b0875): writes per arm a public main root = C's adapted runner-schema records of the kept pairs (original
order), MANIFEST.json and SCREEN_SELECTION_SEAL.json (literal kept IDs, basis, screen input/output seal references; no label, role or name),
under INPUT_SEAL stage main. Labels and role maps (W-text PAIRS.PRIVATE, bAbI LABELS.PRIVATE) never leave CPU."""
import hashlib, json, sys
from pathlib import Path
A = Path('/Users/guivff/Documents/ChatGPT/Activation_Readers')
sys.path.insert(0, str(A/'wt-internals-b'))
from projects.g_agreement.core.analysis_utils import parse_target_answer  # noqa: E402
MATCHER = A/'wt-internals-b/projects/g_agreement/core/analysis_utils.py'; MATCHER_SHA = 'cf6bc5edc904a688b4c292064f230cbb6feec0b9a437ed80ac3b7993396fc390'
SYN = A/'wt-wtext/results/g_agreement/understand/e133/cache/bank_2026-10-30_v1'; BABI = A/'outputs/e133-babi-v1/packet'; ADP = A/'outputs/e133-screen-adapted-v3'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_text())
def req(ok, m):
    if not ok: sys.exit('STOP: '+m)
def answers(screen_out):
    seal = read(Path(screen_out)/'OUTPUT_SEAL.json'); req(seal['status'] == 'COMPLETE' and seal['stage'] == 'screen', 'COMPLETE screen seal')
    for k, h in seal['files'].items(): req(sha(Path(screen_out)/k) == h, 'screen member '+k)
    out = {}
    for f in sorted(k for k in seal['files'] if k.startswith('jobs/')):
        for r in read(Path(screen_out)/f): req(r['id'] not in out, 'unique'); out[r['id']] = r.get('text')
    return out, sha(Path(screen_out)/'OUTPUT_SEAL.json')
def correct(text, cands, current):
    item = dict(primary=dict(candidates=cands, answer=current))
    return parse_target_answer(item, text.lstrip() if text else text) == current
def write_main(root, records, arm, selection):
    root.mkdir(parents=True, exist_ok=False)
    (root/'items.json').write_text(json.dumps(records, indent=1)+'\n')
    (root/'MANIFEST.json').write_text(json.dumps(dict(experiment='E133', arm=arm, stage='main', labels_on_pod=False, fields_on_pod=['id', 'pair_id', 'family', 'member', 'ids', 'read_index', 'candidate_ids'],
        order='original frozen source pair/member order of the kept pairs', selection='SCREEN_SELECTION_SEAL.json'), indent=1, sort_keys=True)+'\n')
    (root/'SCREEN_SELECTION_SEAL.json').write_text(json.dumps(selection, indent=1, sort_keys=True)+'\n')
    (root/'INPUT_SEAL.json').write_text(json.dumps(dict(experiment='E133', arm=arm, stage='main', labels_on_pod=False, files={f: sha(root/f) for f in ('items.json', 'MANIFEST.json', 'SCREEN_SELECTION_SEAL.json')}), indent=1, sort_keys=True)+'\n')
    return sha(root/'INPUT_SEAL.json')
def main(screen_syn, screen_babi, out):
    req(sha(MATCHER) == MATCHER_SHA, 'pinned parser'); out = Path(out); out.mkdir(parents=True, exist_ok=True); res = {}
    base = dict(selection_basis='behaviour_only_both_members_correct', reader_calls_before_selection=0, parser=dict(path='projects/g_agreement/core/analysis_utils.py', sha256=MATCHER_SHA),
                text_rule='32-token greedy text, leading whitespace stripped (§238 clarification 3)', selector_sha256=sha(__file__))
    if screen_syn:
        pub = {x['id']: x for x in read(ADP/'synthetic/inputs/items.json')}; P = read(SYN/'PAIRS.PRIVATE.json'); ans, ssh = answers(screen_syn); req(len(ans) == 900 and set(ans) == set(pub), '900 screened synthetic')
        keep = {'multi_hop': [], 'one_hop': []}
        for pr in sorted(P['pairs'], key=lambda q: (q['family'] != 'multi_hop', q['generation_order'])):
            ms = sorted(pr['members'], key=lambda m: m['member']); cands = [m['current_holder'] for m in ms]+[pr['previous_holder']]
            req(len(set(cands)) == 3 and all(m['previous_holder'] == pr['previous_holder'] for m in ms), 'distinct roles')
            if all(correct(ans[m['id']], cands, m['current_holder']) for m in ms): keep[pr['family']].append([m['id'] for m in ms])
        kept = keep['multi_hop'][:84]+keep['one_hop'][:42]; ids = [i for pq in kept for i in pq]
        res['synthetic'] = dict(qualifying=dict(multi_hop=len(keep['multi_hop']), one_hop=len(keep['one_hop'])), kept=dict(multi_hop=len(keep['multi_hop'][:84]), one_hop=len(keep['one_hop'][:42])))
        res['synthetic']['input_sha256'] = write_main(out/'main_synthetic', [pub[i] for i in ids], 'synthetic',
            dict(base, experiment='E133', arm='synthetic', kept_item_ids=ids, multi_pairs=len(keep['multi_hop'][:84]), one_hop_pairs=len(keep['one_hop'][:42]), screen_output_seal_sha256=ssh,
                 screen_input_seal_sha256=sha(ADP/'synthetic/inputs/INPUT_SEAL.json'), wtext_source_input_seal_sha256='ca4b738e02fd8fcad2e4f864a62c7f0cf1499b3832a20d019c41fb5b8c8b8b4949',
                 descriptive_only=len(keep['multi_hop'][:84]) < 50))
    if screen_babi:
        bpub = {x['id']: x for x in read(ADP/'babi/inputs/items.json')}; L = read(BABI/'cpu_only/LABELS.PRIVATE.json'); bans, bsh = answers(screen_babi); req(set(bans) == set(bpub), 'screened bAbI')
        bk = []
        for pr in L:
            mids = pr['member_ids'] if isinstance(pr['member_ids'], list) else json.loads(pr['member_ids'].replace("'", '"'))
            cands = [pr['original_current'], pr['twin_current'], pr['previous']]; req(len(set(cands)) == 3, 'distinct bAbI roles')
            if correct(bans[mids[0]], cands, cands[0]) and correct(bans[mids[1]], cands, cands[1]): bk.append(mids)
        ids = [i for pq in bk[:42] for i in pq]
        res['babi'] = dict(qualifying=len(bk), kept=len(bk[:42]) if len(bk) >= 20 else 0, screen_results_only=len(bk) < 20)
        if len(bk) < 20: ids = []
        if ids: res['babi']['input_sha256'] = write_main(out/'main_babi', [bpub[i] for i in ids], 'babi',
            dict(base, experiment='E133', arm='babi', kept_item_ids=ids, babi_pairs=len(bk[:42]), screen_output_seal_sha256=bsh, screen_input_seal_sha256=sha(ADP/'babi/inputs/INPUT_SEAL.json')))
    (out/'SELECTION_COUNTS.json').write_text(json.dumps(res, indent=1, sort_keys=True)+'\n'); print(json.dumps(res))
if __name__ == '__main__': main(None if sys.argv[1] == '-' else sys.argv[1], None if sys.argv[2] == '-' else sys.argv[2], sys.argv[3])  # select133.py <screen_synthetic_out> <screen_babi_out|-> <dest>
