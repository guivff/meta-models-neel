"""Custody-only native binding for I-2's committed 56b31d5 E122 runner.

Reads input/contract/source metadata, never a numerical job member. Original
records remain unchanged; missing condition/token metadata comes from the exact
pinned native-only producer and its hash-bound frozen inputs, not inference.
"""
from pathlib import Path
from . import adapter as a

OPERATOR_SHA='eab10d6ec4ea0ded04f56529af572df923f099500ba8076207ebe24611b5d8b8'
SCORER_SHA='932c62afbaa4eb7f219d75292529ad27224562a9324591b06f033f09bf01c73a'
INPUT_SHA='7aa32dd148be7f4cd9b071e00057631352246875685c70028d138d6f13fc39e0'
SOURCE_SHA='e2bf8d8ccf232c46631c3f2d7804cfdc21f68939364ae0fcf64f1ce1c674e11b'


def context(entry, output, frozen, cells, defs):
    a.require(output['experiment']=='E122' and output['part']=='a' and output['status']=='COMPLETE'
              and output['operator_sha256']==OPERATOR_SHA and output['original_E105_scorer_sha256']==SCORER_SHA
              and output['input_sha256']==INPUT_SHA and output['source_sha256']==SOURCE_SHA
              and output['labels_cpu_only'] is True and output['T_S_transplants_invoked'] is False
              and output['readout_or_judging_calls']==0, 'exact I2 native-only original scorer/source')
    # Immutable producer/source bytes must be available before the first opening.
    a.require(a.sha(a.ROOT/'results/g_agreement/i2/e122_logits232.py')==OPERATOR_SHA
              and a.sha(a.ROOT/'projects/g_agreement/e101/acquisition.py')==SCORER_SHA, 'pinned native producer/scorer code')
    source=a.core.verify(entry['producer_source_seal'],SOURCE_SHA)
    a.require(OPERATOR_SHA in source['files'].values() and SCORER_SHA in source['files'].values(), 'source seal original operator/scorer closure')
    ip=Path(entry['producer_input_seal'])
    inputs=a.core.verify(ip,INPUT_SHA)
    a.require(inputs['experiment']=='E122' and inputs['part']=='a' and inputs['labels_on_pod'] is False
              and inputs['source_CONTRASTS_SEAL']==a.CONTRAST_SHA and inputs['items']==600
              and inputs['dev']==200 and inputs['test']==400 and inputs['contrasts']==4, 'exact frozen public input grid')
    a.require(inputs['files']['CONTRASTS.json']==a.sha(frozen.parent/'CONTRASTS.json'), 'original contrast bytes')
    items=a.core.unique(a.read(ip.parent/'items.json'))
    a.require(set(items)=={x['id'] for x in cells}, 'all original native IDs')
    candidates=[x['candidate_ids'][0] for x in defs]
    for cell in cells:
        item=items[cell['id']]
        a.require(item['split']==cell['split'] and item['block']==44 and item['candidate_ids']==candidates
                  and item['read_index']==len(item['ids'])-1, 'original native prefix and candidate identity')
    op=Path(entry['seal']).parent
    a.require('CONTRAST_ORDER.json' in output['files'], 'original output order member')
    order=a.read(op/'CONTRAST_ORDER.json')
    ids=[x['id'] for x in defs]
    a.require(order['contrasts']==ids and order['pair_order']==['positive','negative']
              and order['score']=='sum natural log probabilities over EVERY candidate token, no mean/no appended EOS', 'original full-sum polarity/order')
    return dict(order=ids,splits={x['id']:x['split'] for x in cells})
