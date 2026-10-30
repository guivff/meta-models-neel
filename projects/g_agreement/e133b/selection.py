"""CPU operator-only bAbI selection; original TrackQ parser/helpers and loop.

No actual screen is opened by the packet builder. No CPU labels ship to a pod.
"""
import hashlib,json,inspect,sys
from pathlib import Path
from projects.g_agreement.core.analysis_utils import parse_target_answer
from projects.g_agreement.e100.contract import verify
from projects.g_agreement.e133b.runner import load,main_disposition
PARSER_SHA='cf6bc5edc904a688b4c292064f230cbb6feec0b9a437ed80ac3b7993396fc390'
PUBLIC_SHA='0d2bd3968b0f4eb6981d960d3054ebc87d2e2ae52e150395d82a894ec56e2ec1'
CPU_SHA='9364a8644a4222e769043cd217c0f67f14ff1cc349401cbc70c816289f89d390'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())

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


def choose(labels,screen_answers):
    """Original bAbI loop, source order; no prefix/Oracle/logit selection."""
    bk=[]
    for pr in labels:
        mids=pr['member_ids']if isinstance(pr['member_ids'],list)else json.loads(pr['member_ids'].replace("'",'"'))
        cands=[pr['original_current'],pr['twin_current'],pr['previous']]
        req(len(set(cands))==3,'distinct bAbI roles')
        if correct(screen_answers.get(mids[0]),cands,cands[0]) and correct(screen_answers.get(mids[1]),cands,cands[1]):bk.append(mids)
    return bk[:42],len(bk)


def select(screen_root,screen_sha,public_root,cpu_root,out):
    req(sha(inspect.getfile(parse_target_answer))==PARSER_SHA,'unchanged original parser')
    req(sha(Path(screen_root)/'OUTPUT_SEAL.json')==screen_sha,'explicit NEW complete screen seal')
    seal=read(Path(screen_root)/'OUTPUT_SEAL.json')
    req(seal.get('experiment')=='E133'and seal.get('arm')=='babi','original E133/babi inner envelope')
    pub=load(public_root,PUBLIC_SHA,'screen');public={x['id']:x for x in pub}
    cpu=verify(Path(cpu_root),'LABEL_SEAL.json',CPU_SHA)
    req(cpu.get('public_input_sha256')=='a7bd943885497f10d62410c196dbed0f668fe770966c7fde7f8c6c58c0840c34','original public bank binding')
    labels=read(Path(cpu_root)/'LABELS.PRIVATE.json')
    ans,actual=answers(screen_root)
    req(actual==screen_sha and set(ans)==set(public),'NEW complete988 answers, no partial reuse')
    kept,n=choose(labels,ans);ids=[i for pair in kept for i in pair];disposition=main_disposition(n)
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    result=dict(experiment='E133b',arm='babi',qualifying_pairs=n,kept_pairs=len(kept),action=disposition['action'],
                screen_output_seal_sha256=screen_sha,screen_input_seal_sha256=PUBLIC_SHA,selector_sha256=sha(__file__))
    if result['action']=='MAIN':
        selection=dict(selection_basis='behaviour_only_both_members_correct',reader_calls_before_selection=0,
                       parser_sha256=PARSER_SHA,selector_sha256=sha(__file__),experiment='E133',arm='babi',
                       kept_item_ids=ids,babi_pairs=len(kept),screen_output_seal_sha256=screen_sha,
                       screen_input_seal_sha256=PUBLIC_SHA)
        result['input_sha256']=write_main(out/'main_babi',[public[i]for i in ids],'babi',selection)
    (out/'DISPOSITION.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    import argparse
    p=argparse.ArgumentParser()
    for name in ['screen-root','public-root','cpu-root','out']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--screen-sha',required=True);a=p.parse_args()
    print(json.dumps(select(a.screen_root,a.screen_sha,a.public_root,a.cpu_root,a.out)))

if __name__=='__main__':main()
