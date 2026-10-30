"""§87 W11: no-padding minimal pairs, identical native-token carriers."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import shutil

from . import protocol as P
from .items import load_pinned_tokenizer, TOKENIZER_REVISION, TOKENIZER_SHA256
from .w1b import registry_features as S

SECTION = 'results/g_agreement/blindspot/w11/REGISTERED_SECTION.md'
ORIGIN = 'results/g_agreement/blindspot/w11/REGISTRATION_ORIGIN.json'
W84 = 'results/g_agreement/blindspot/w1b/freeze'
FRAMES = (
    'The clerk copied the {object} entry for {record}. The entry begins:\n',
    'A notice for {record} ended with this {object} notation:\n',
    'For the {object} inventory at {record}, the recorded fragment was:\n',
    'The archive at {record} preserves the following {object} mark:\n',
    'During the {record} inspection, the {object} label showed:\n',
    'A visitor at {record} copied a fragment from the {object} card:\n',
    'Below the {object} sketch, the {record} notebook contains:\n',
    'Before opening {record}, staff checked the {object} tag. It read:\n',
    'The {object} folder from {record} included a single entry:\n',
    'A report from {record} reproduced the {object} annotation:\n',
    'In the {record} workshop, the {object} slip carried this text:\n',
    'The instruction card at {record} displayed the {object} excerpt:\n',
)
OBJECTS = ('wooden', 'metal', 'paper', 'glass', 'stone')
RECORDS = ('Ashford','Briar','Cedar','Dover','Elm','Fern','Grove','Heath','Iris','Juniper')
NATURAL_PAIRS = {
    'current_number': [('2','red'),('4','home'),('6','about'),('7','blue'),('9','hot')],
    'number_magnitude_ge_10': [('12','.2'),('25','.5'),('38','.8'),('47','.7'),('64','.4')],
    'number_magnitude_ge_100': [('230','2.3'),('450','4.5'),('670','6.7'),('810','8.1'),('960','9.6')],
    'number_magnitude_ge_1000': [('2300','23.0'),('4500','45.0'),('6700','67.0'),('8100','81.0'),('9600','96.0')],
    'number_digits_ge_3': [('236','2.3'),('457','4.5'),('678','6.7'),('819','8.1'),('962','9.6')],
    'number_digits_ge_4': [('2367','23.6'),('4578','45.7'),('6789','67.8'),('8192','81.9'),('9623','96.2')],
    'wordlist_preposition': [('at','red'),('between','home'),('under','green'),('with','blue'),('on','hot')],
    'wordlist_auxiliary': [('am','red'),('are','hot'),('can','home'),('have','blue'),('might','black')],
    'word_allcaps': [('RED','red'),('BLUE','blue'),('GREEN','green'),('BLACK','black'),('WHITE','white')],
    'current_colon': [(':',',')]*5,
}


def opaque(text):
    return hashlib.sha256(text.encode()).hexdigest()[:24]


def encode(tok, text):
    return list(tok(text, add_special_tokens=False)['input_ids'])


def dependencies():
    """Read only the already committed §84 feature/phrasing freeze, never scores."""
    m = json.loads((P.ROOT/W84/'manifest.json').read_text())
    templates = json.loads((P.ROOT/W84/'templates.json').read_text())
    selected = m['selection_receipt']['section79_features']
    if len(selected) != 10 or set(selected) != set(NATURAL_PAIRS) or set(templates) != set(selected):
        raise ValueError('expected exact committed §79 top ten')
    if P.sha(P.ROOT/W84/'templates.json') != m['files']['templates.json']:
        raise ValueError('§84 phrasing freeze changed')
    return selected, templates, m


def build(tok):
    selected, _, _ = dependencies()
    items = []
    for row, feature in enumerate(selected):
        for context, grammar in enumerate(FRAMES):
            cluster = opaque(f'W11-context-v1:{feature}:{context}')
            for variant, obj in enumerate(OBJECTS):
                prefix = grammar.format(object=obj, record=RECORDS[row])
                prefix_ids = encode(tok, prefix)
                a, b = NATURAL_PAIRS[feature][(context+variant)%5]
                span_ids = [encode(tok,s) for s in (a,b)]
                if len(span_ids[0]) != len(span_ids[1]):
                    raise ValueError('target spans differ in native token count: '+feature)
                pair = opaque(f'W11-pair-v1:{feature}:{context}:{variant}')
                for side, span, ids in zip((True,False),(a,b),span_ids):
                    text = prefix+span
                    full_ids = encode(tok,text)
                    if full_ids != prefix_ids+ids:
                        raise ValueError('tokenization merges across target boundary: '+feature)
                    if S.extract(text,'prose')[feature] is not side:
                        raise ValueError('frozen §79 predicate does not match target span: '+feature)
                    items.append({'id':opaque(f'{pair}:{side}'),'feature':feature,
                        'class':S.BY_ID[feature].kind,'domain':'prose',
                        'split':'dev' if context%2==0 else 'test','cluster':cluster,
                        'value':'present' if side else 'absent','text':text,'ids':full_ids,
                        'meta':{'pair_id':pair,'template_index':context,'variant':variant,
                            'prefix':prefix,'span':span,'target_start':len(prefix_ids),
                            'target_span_tokens':len(ids),'target_char_start':len(prefix),
                            'pretarget_position':len(prefix_ids)-1,'read_position':len(full_ids)-1,
                            'token_length':len(full_ids),'kind':'binary'}})
    return items


def verify(tok, items):
    from scipy.stats import ks_2samp
    selected, _, _ = dependencies()
    if len(items)!=1200 or len({x['id'] for x in items})!=1200 or len({x['text'] for x in items})!=1200:
        raise ValueError('wrong item coverage or duplicate text')
    pairs=defaultdict(list)
    for x in items:
        m=x['meta'];start=m['target_start'];ids=encode(tok,x['text'])
        if (ids!=x['ids'] or x['text']!=m['prefix']+m['span'] or
                encode(tok,m['prefix'])!=ids[:start] or encode(tok,m['span'])!=ids[start:] or
                m['target_span_tokens']!=len(ids)-start or m['read_position']!=len(ids)-1 or
                m['pretarget_position']!=start-1 or not 0<start<len(ids) or
                m['target_char_start']!=len(m['prefix']) or m['token_length']!=len(ids)):
            raise ValueError('target boundary, no-suffix or token identity failed')
        if S.extract(x['text'],x['domain'])[x['feature']] is not (x['value']=='present'):
            raise ValueError('final text label failed')
        pairs[x['meta']['pair_id']].append(x)
    for pair in pairs.values():
        if len(pair)!=2 or {x['value'] for x in pair}!={'present','absent'}:
            raise ValueError('invalid binary pair')
        a,b=pair;sa,sb=(x['meta']['target_start'] for x in pair)
        if (sa!=sb or a['ids'][:sa]!=b['ids'][:sb] or a['meta']['prefix']!=b['meta']['prefix'] or
                len(a['ids'][sa:])!=len(b['ids'][sb:]) or a['ids'][sa:]==b['ids'][sb:] or
                any(a[k]!=b[k] for k in ('feature','cluster','split','domain'))):
            raise ValueError('nonminimal pair or unequal target span')
    if len(pairs)!=600:
        raise ValueError('wrong pair count')
    checks=[]
    for feature in selected:
        row=[x for x in items if x['feature']==feature]
        if len(row)!=120 or Counter(x['value'] for x in row)!={'present':60,'absent':60}:
            raise ValueError('row sample size or balance')
        clusters=[{x['cluster'] for x in row if x['split']==s} for s in ('dev','test')]
        if any(len(c)!=6 for c in clusters) or clusters[0]&clusters[1]:
            raise ValueError('context split leakage')
        for split in ('dev','test'):
            lengths=[[len(x['ids']) for x in row if x['split']==split and x['value']==v] for v in ('present','absent')]
            p=float(ks_2samp(*lengths).pvalue);diff=abs(sum(lengths[0])/30-sum(lengths[1])/30)
            if any(len(g)!=30 for g in lengths) or p!=1 or diff!=0:
                raise ValueError('minimal pair length distribution drift')
            checks.append({'feature':feature,'split':split,'n_per_value':30,'ks_p':p,'mean_token_difference':diff})
    return {'status':'PASS','items':1200,'pairs':600,'rows':10,'checks':checks,
        'identical_prefixes':True,'equal_span_token_counts':True,'no_padding':True,'no_suffix':True,
        'labels_rechecked_on_complete_prefix':True,'pretarget_probe_gate':'PENDING CAPTURE: both sites AUROC within [0.48,0.52]'}


def random_donors(items):
    """Hash each recipient independently into same row/context/native-length bin, ignoring value."""
    pools=defaultdict(list)
    for x in items:
        pools[x['feature'],x['cluster'],len(x['ids'])//16].append(x['id'])
    out={}
    for x in items:
        pool=sorted(pools[x['feature'],x['cluster'],len(x['ids'])//16])
        draw=int(hashlib.sha256(f'W11-random-donor:{P.SEED}:{x["id"]}'.encode()).hexdigest(),16)
        out[x['id']]=pool[draw%len(pool)]
    return out


def source_hashes():
    paths=['projects/g_agreement/blindspot/'+n for n in
        ('__init__.py','w11_items.py','w11_run.py','w11_analysis.py','w11_request.py',
         'run.py','protocol.py','items.py','w1_templates.py','analysis.py','w1b/__init__.py','w1b/registry_features.py')]
    paths += [SECTION,ORIGIN,'results/g_agreement/blindspot/w11/REGISTERED_BRIEF.md',
        W84+'/manifest.json',W84+'/templates.json','projects/g_agreement/manifest/assets.json',
        'common/__init__.py','common/stats.py','external/PINS.md']
    paths += [str(p.relative_to(P.ROOT)) for p in (P.ROOT/'external/mats-nla-workspace/src').rglob('*.py')]
    return {n:P.sha(P.ROOT/n) for n in sorted(paths)}


def freeze(tok, tokenizer, bank, frozen, stage):
    items=build(tok);report=verify(tok,items)
    selected,templates,w84=dependencies();donors=random_donors(items)
    bank,frozen,stage=map(Path,(bank,frozen,stage))
    bank.mkdir(parents=True,exist_ok=False)
    P.jsonl(bank/'items.DO_NOT_STAGE.jsonl',items)
    P.jsonl(bank/'labels.DO_NOT_STAGE.jsonl',[{k:x[k] for k in ('id','feature','class','domain','split','cluster','value')} for x in items])
    P.jsonl(bank/'items.input.jsonl',[{k:x[k] for k in ('id','feature','ids')}|{
        'donor_id':donors[x['id']],'pair_id':x['meta']['pair_id'],
        'target_start':x['meta']['target_start'],
        'positions':[x['meta']['pretarget_position'],x['meta']['read_position']]} for x in items])
    P.dump(bank/'templates.json',templates)
    P.dump(bank/'contexts.json',{'grammars':FRAMES,'objects':OBJECTS,'records':RECORDS,
        'span_pairs':NATURAL_PAIRS,'padding':'none','suffix':'none',
        'context_split':'even grammar indices dev; odd grammar indices test'})
    P.dump(bank/'lengths.json',report)
    P.dump(bank/'manifest.json',{'schema':'blindspot-w11-v1','experiment':'W11','section':87,
        'registration':json.loads((P.ROOT/ORIGIN).read_text()),'section87_sha256':P.sha(P.ROOT/SECTION),
        'source_files':source_hashes(),'tokenizer':str(tokenizer),'tokenizer_revision':TOKENIZER_REVISION,
        'tokenizer_sha256':TOKENIZER_SHA256,'seed':P.SEED,'features':selected,'rows':{
            f:{'n':120,'class':S.BY_ID[f].kind,'domain':'prose','clusters':12,
                'dev':60,'test':60,'values':['present','absent']} for f in selected},
        'w84_selection_receipt':w84['selection_receipt'],'w84_manifest_sha256':P.sha(P.ROOT/W84/'manifest.json'),
        'w84_templates_sha256':P.sha(P.ROOT/W84/'templates.json'),
        'labels_sha256':P.sha(bank/'labels.DO_NOT_STAGE.jsonl'),'full_items_sha256':P.sha(bank/'items.DO_NOT_STAGE.jsonl'),
        'capture_sites':[42,44],'position_order':['pretarget','target_last'],
        'random_donor_policy':'same row/context/length bin floor(native_length/16); hash ignores value; self allowed',
        'science_cap_seconds':3600,'science_allocation':'min(1.5F+360,3600); NO_FIT if forecast work exceeds available allocation',
        'setup_allowance_seconds':1500,'bootstrap_replicates':2000,'model_forwards_at_freeze':0,
        'scope':'all ten rows; no outcome or timing dependent reduction in this receipt',
        'analysis_contract':{'leak_gate':'pretarget probe at both sites in [0.48,0.52]; otherwise row NOT EVALUABLE (pipeline error)',
            'probe':'W1 fixed lambda0.001 logistic, 5 template-grouped folds on test only, train-fold standardization',
            'reader_gate':'native-site probe>=0.85 and random-donor AUROC in [0.40,0.60], signed',
            'per_feature':'Oracle<=block44 probe-0.15 and Oracle gates + row leak gate pass; NLA/J gates reported separately',
            'summary':'CONFIRMED if >=70% of Oracle-evaluable features confirm; empty denominator NOT EVALUABLE',
            'secondary':'NLA-Oracle paired 2000-cluster bootstrap CI, J-lens, agreement with section84 when available'}})
    names=['items.input.jsonl','templates.json','contexts.json','lengths.json','manifest.json']
    P.seal(bank,names,'INPUTS_FROZEN_W11_BEFORE_CAPTURE')
    for destination,files in ((frozen,names[1:]+['INPUT_SEAL.json']),(stage,names+['INPUT_SEAL.json'])):
        destination.mkdir(parents=True,exist_ok=False)
        for name in files:shutil.copyfile(bank/name,destination/name)
    P.verify(stage,'INPUT_SEAL.json')
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('tokenizer','out','freeze-out','stage-out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();tok=load_pinned_tokenizer(a.tokenizer)
    with P.logged('w11_build_freeze',extra={'model_forwards':0,'section':87}):
        report=freeze(tok,a.tokenizer,a.out,a.freeze_out,a.stage_out)
    print(json.dumps({'status':report['status'],'items':report['items'],'pairs':report['pairs']}))


if __name__=='__main__':main()
