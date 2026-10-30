"""2026-10-25: freeze E25 inputs from sealed W1/E12 sources, without model calls."""
from pathlib import Path
import argparse
import collections
import json
import shutil
from worker import sha, dump


def prepare(args):
    here = Path(__file__).resolve().parent
    source, bank, w1 = Path(args.e12), Path(args.w1_bank), Path(args.w1_analysis)
    seal_path = Path(args.e12_seal)
    seal = json.loads(seal_path.read_text())
    for name in ('items.input.jsonl','templates.json'):
        if sha(source/name) != seal['files'][name]:
            raise ValueError('E12 source seal mismatch')
    analysis_seal = json.loads((w1/'ANALYSIS_SEAL.json').read_text())
    if sha(w1/'metrics.json') != analysis_seal['files']['metrics.json']:
        raise ValueError('W1 metrics seal mismatch')
    manifest = json.loads((bank/'manifest.json').read_text())
    for name in ('items.DO_NOT_STAGE.jsonl','templates.json'):
        if sha(bank/name) != manifest['files'][name]:
            raise ValueError('W1 bank hash mismatch')
    original={x['id']:x for x in map(json.loads,(bank/'items.DO_NOT_STAGE.jsonl').read_text().splitlines())}
    full_templates=json.loads((bank/'templates.json').read_text())
    items=list(map(json.loads,(source/'items.input.jsonl').read_text().splitlines()))
    specs=json.loads((source/'templates.json').read_text())
    counts=collections.Counter(x['feature'] for x in items)
    if len(items)!=2100 or len({x['id'] for x in items})!=2100 or len(counts)!=25 or set(counts.values())!={84}:
        raise ValueError('must have exactly 25 rows x84 distinct test items')
    for item in items:
        orig=original[item['id']]
        if orig['split']!='test' or any(orig[k]!=item[k] for k in ('text','ids','feature')):
            raise ValueError('not the unchanged W1 test item')
        if orig['value'] not in specs[item['feature']]['values']:
            raise ValueError('unknown W1 value, cannot silently map to B')
    if any(specs[f]!=full_templates[f] for f in counts):
        raise ValueError('frozen W1 phrasing changed')
    classes=collections.Counter('semantic' if specs[f]['class']=='semantic' else 'structure' for f in counts)
    if classes!={'semantic':9,'structure':16}:
        raise ValueError('wrong class counts')
    for feature in counts:
        balance=collections.Counter(original[x['id']]['value'] for x in items if x['feature']==feature)
        if len(balance)!=2 or set(balance.values())!={42}:
            raise ValueError('expected 42 A and42 B per row')
    cache=here/'cache'; cache.mkdir(exist_ok=True)
    stage=cache/'stage'; stage.mkdir(exist_ok=False)
    private=cache/'private'; private.mkdir(exist_ok=False)
    with (stage/'items.jsonl').open('x') as stream:
        for item in items:
            stream.write(json.dumps({k:item[k] for k in ('id','feature','text')},sort_keys=True)+'\n')
    dump(stage/'candidates.json',{f:specs[f]['olens'] for f in sorted(counts)})
    dump(stage/'INPUT_SEAL.json',{'date':'2026-10-25','files':{n:sha(stage/n) for n in ('items.jsonl','candidates.json')}})
    dump(private/'labels.json',{'items':[{'id':x['id'],'feature':x['feature'],
        'label':int(original[x['id']]['value']==specs[x['feature']]['values'][0])} for x in items]})
    metrics=json.loads((w1/'metrics.json').read_text())['rows']
    refs=[]
    for feature in sorted(counts):
        ref={'feature':feature,'class':'semantic' if specs[feature]['class']=='semantic' else 'structure'}
        for reader,layer in (('olens',44),('nla',42),('probe',44)):
            cells=[r for r in metrics if r['feature']==feature and r['reader']==reader and r['layer']==layer]
            if len(cells)!=1:
                raise ValueError('nonunique W1 outcome')
            ref[reader]=cells[0]['true']['auroc']
        refs.append(ref)
    dump(here/'REFERENCES.json',{'date':'2026-10-25','rows':refs,'source_metrics_sha256':sha(w1/'metrics.json')})
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(args.tokenizer,local_files_only=True)
    from worker import encode_frame, TOKENIZER_SHA
    if sha(Path(args.tokenizer)/'tokenizer.json')!=TOKENIZER_SHA:
        raise ValueError('wrong tokenizer')
    frames=[encode_frame(tokenizer,x['text'],c) for x in items for pair in specs[x['feature']]['olens'] for c in pair]
    audit={'date':'2026-10-25','frames':len(frames),'boundary_crossings':0,
           'max_frame_tokens':max(len(f['ids']) for f in frames),
           'candidate_tokens_min':min(f['token_count'] for f in frames),
           'candidate_tokens_max':max(f['token_count'] for f in frames),'tokenizer_sha256':TOKENIZER_SHA,
           'model_forwards':0,'all_items_exact_original_W1_test':True,'all_phrasings_exact_W1_olens':True}
    dump(here/'TOKENIZER_AUDIT.json',audit)
    dump(here/'INPUT_PROVENANCE.json',{'date':'2026-10-25','e12_seal_sha256':sha(seal_path),
        'e12_items_sha256':sha(source/'items.input.jsonl'),'e12_templates_sha256':sha(source/'templates.json'),
        'w1_manifest_sha256':sha(bank/'manifest.json'),'w1_labelled_items_sha256':sha(bank/'items.DO_NOT_STAGE.jsonl'),
        'w1_analysis_seal_sha256':sha(w1/'ANALYSIS_SEAL.json'),'w1_metrics_sha256':sha(w1/'metrics.json'),
        'input_seal_sha256':sha(stage/'INPUT_SEAL.json'),'labels_sha256':sha(private/'labels.json'),
        'items':2100,'rows':25,'class_counts':dict(classes)})
    dump(here/'RUN_PLAN.json',{'date':'2026-10-25','experiment':'E25','registration_commit':'97cfc5dd',
        'rows':sorted(counts),'items':[{'id':x['id'],'feature':x['feature']} for x in items],
        'input_seal_sha256':sha(stage/'INPUT_SEAL.json'),'labels_sha256':sha(private/'labels.json'),
        'references_sha256':sha(here/'REFERENCES.json'),'batch_size':4,
        'analysis_inputs':{'labels_sha256':sha(private/'labels.json'),'references_sha256':sha(here/'REFERENCES.json')},
        'frame':'item text + one newline + verbatim W1 Oracle candidate',
        'score':'mean candidate token log probability, nats; no prefix tokens',
        'analysis':{'seed':20261025,'bootstrap':2000},
        'clarifications':{'D_definition':'AUROC(s_A-s_B,value_is_A)','clarification_commit':'e4225a1e',
                          'phrasing_aggregation':'mean_of_two_W1_pairs','integrator_acknowledged':True},
        'source_files':{str(p.relative_to(here.parents[3])):sha(p) for p in sorted(here.glob('*.py'))}})
    print(json.dumps(audit,sort_keys=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('e12','e12-seal','w1-bank','w1-analysis','tokenizer'):
        p.add_argument('--'+key,required=True)
    prepare(p.parse_args())
