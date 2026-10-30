"""§249 scope/schema envelope; ORIGINAL E133 synthetic acquisition code objects."""
from pathlib import Path
from types import FunctionType
from projects.g_agreement.e133 import runner as v3
from projects.g_agreement.e100.contract import read,verify,sha
# Literal aliases preserve all generation, capture, pair, swap and control maths.
generation_batch=v3.generation_batch
capture_batch=v3.capture_batch
patch_batch=v3.patch_batch
batches=v3.batches
CAPTURE=v3.CAPTURE
READ=v3.READ
PATCH=v3.PATCH


def count_disposition(d1,d2):
    if any(type(n)is not int or not 0<=n<=150 for n in (d1,d2)):
        raise ValueError('original150candidatepairs per design')
    return dict(action='SCREEN_RESULTS_ONLY'if d1<20 and d2<20 else 'MAIN',
                D1_kept=min(42,d1),D2_kept=min(42,d2),
                D1_counts=d1>=30,D2_counts=d2>=30)


def validate_items(items,stage):
    if stage not in ('screen','main')or not items or len({x['id']for x in items})!=len(items):
        raise ValueError('unique nonempty stage items')
    groups={}
    for x in items:
        if set(x)!={'id','pair_id','family','member','ids','read_index','candidate_ids'}or x['family']not in ('multi_hop','one_hop')or x['member']not in (0,1):
            raise ValueError('original label-free E133 synthetic structure only')
        if x['read_index']!=len(x['ids'])-1 or x['read_index']<=8:
            raise ValueError('original final read token, no truncation')
        p=x['candidate_ids']
        if len(p)!=1 or len(p[0])!=2 or any(len(c)!=1 for c in p[0])or p[0][0][0]>=p[0][1][0]:
            raise ValueError('one ascending unordered recipient contrast only')
        groups.setdefault(x['pair_id'],[]).append(x)
    counts=dict(multi_hop=0,one_hop=0)
    for pair in groups.values():
        if len(pair)!=2 or {x['member']for x in pair}!={0,1}or pair[0]['family']!=pair[1]['family']or pair[0]['candidate_ids']!=pair[1]['candidate_ids']:
            raise ValueError('both original twins/common recipient contrast')
        counts[pair[0]['family']]+=1
    if stage=='screen'and counts['multi_hop']!=300:
        raise ValueError('all original150D1+150D2 candidate pairs; no screen subset')
    if stage=='main'and(not 0<=counts['multi_hop']<=84 or not 0<=counts['one_hop']<=42 or 3*len(items)>600):
        raise ValueError('frozen main cohort/readout ceiling; no silent control truncation')
    return counts


# Same scientific orchestration code objects. Only the input census validator
# differs from the old450-pair bank; all globals doing acquisition stay original.
_screen=FunctionType(v3.screen.__code__,dict(v3.screen.__globals__,validate_items=validate_items))
_main=FunctionType(v3.main_job.__code__,dict(v3.main_job.__globals__,validate_items=validate_items))


def screen(model,tok,items,out,check_work,*,gpu_type,batch=8):
    return _screen(model,tok,items,out,check_work,gpu_type=gpu_type,batch=batch)


def main_job(runtime,items,out,check_work,*,gpu_type,batch=8):
    return _main(runtime,items,out,check_work,gpu_type=gpu_type,batch=batch)


def load(root,digest,stage):
    root=Path(root);s=verify(root,'INPUT_SEAL.json',digest)
    if s.get('experiment')!='E137'or s.get('stage')!=stage or s.get('labels_on_pod')is not False:
        raise ValueError('public stage-bound E137 seal')
    allowed={'items.json','MANIFEST.json'}|({'SCREEN_SELECTION_SEAL.json'}if stage=='main'else set())
    if set(s['files'])!=allowed:raise ValueError('public members only')
    items=read(root/'items.json');counts=validate_items(items,stage);m=read(root/'MANIFEST.json')
    if stage=='screen'and m.get('one_hop_candidate_pairs')!=counts['one_hop']:
        raise ValueError('exact frozen owner control census')
    if stage=='main':
        p=read(root/'SCREEN_SELECTION_SEAL.json')
        if p.get('selection_basis')!='behaviour_only_both_members_correct'or p.get('reader_calls_before_selection')!=0 or not p.get('screen_output_seal_sha256')or p.get('kept_item_ids')!=[x['id']for x in items]:
            raise ValueError('NEW complete screen/frozen exact roster before readers')
        # The one-hop main rule is an owner protocol, never guessed from capacity.
        if not p.get('one_hop_main_rule_authority'):
            raise ValueError('explicit registered one-hop main rule required')
    return items


def source_gate():
    root=Path(__file__).resolve().parents[3]
    for name,h in read(Path(__file__).with_name('SOURCE_SEAL.json'))['files'].items():
        if sha(root/name)!=h:raise ValueError('changed E137 sealed source '+name)


def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--input-sha',required=True);p.add_argument('--stage',choices=['screen','main'],required=True);p.add_argument('--validate-only',action='store_true');a=p.parse_args()
    source_gate();items=load(a.input,a.input_sha,a.stage)
    if a.validate_only:print('E137 VALIDATE_OK',a.stage,len(items),'no model loaded');return
    raise SystemExit('TrackQ original assignment/clock/custody only; no standalone production')

if __name__=='__main__':main()
