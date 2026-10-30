"""Verify complete E73 capture/probe intake; freeze input plan without J scoring."""
from pathlib import Path
from datetime import datetime
import json
import re
import subprocess
import sys
import numpy as np
from e73_adapter import ROOT, HERE, validate_units, cpu_job
from prepare import words_for

read, dump, sha = cpu_job.read, cpu_job.dump, cpu_job.sha
CHANNEL = ROOT / 'results/g_agreement/understand/e57/jlens'
DELIVERY = ROOT.parent / 'wt-wcensus/cache/g_agreement/e73/wlens_delivery_6f9ea0e0/E73_DELIVERY.json'
DELIVERY_SHA = '81ad85bc3fef697c3b706e92414034af42acc6f24ec27560ee05dd9c42db8820'


def bind():
    assert sha(DELIVERY) == DELIVERY_SHA
    d = read(DELIVERY)
    assert d['experiment'] == 'E73' and d['schema'] == 'e73-wlens-delivery-v1'
    assert d['included_states'] == ['W1', 'W2', 'W3', 'W4', 'W5']
    assert set(d['excluded_states']) == {'W6', 'W7', 'W8'}
    assert d['custody']['operator_attestation'] == {'native_generation_started': False, 'reader_outputs_opened': False}
    assert d['custody']['reader_release'] == 'HELD_FOR_IMMUTABLE_W_LENS_FORECAST_COMMIT_AND_I2_GO'
    refs = {}
    def collect(v):
        if isinstance(v, dict):
            if {'path', 'sha256'} <= v.keys():
                p = Path(v['path']).resolve()
                assert not any(x in p.name.lower() for x in ('readout', 'judgment', 'judgement'))
                assert str(p) not in refs or refs[str(p)] == v['sha256']
                refs[str(p)] = v['sha256']
                assert sha(p) == v['sha256'], 'Delivery file hash mismatch'
                if 'bytes' in v: assert p.stat().st_size == v['bytes']
            for child in v.values(): collect(child)
        elif isinstance(v, list):
            for child in v: collect(child)
    collect(d)
    producer_repo = ROOT.parent / 'wt-wcensus'
    for name, source in [('sampler', 'states.py'), ('capture', 'capture.py'), ('probes', 'probes.py')]:
        commit = d['producer_commits'][name]
        blob = subprocess.check_output(['git', 'show', commit+':projects/g_agreement/e73/'+source], cwd=producer_repo)
        import hashlib
        expected = read(d['inputs']['bank_manifest']['path'])['code_sha256']['states.py'] if name == 'sampler' else (
            read(d['captures'][0]['admission']['path'])['source_files']['projects/g_agreement/e73/capture.py'] if name == 'capture'
            else d['probes']['producer_source_sha256'])
        assert hashlib.sha256(blob).hexdigest() == expected
    assert d['producer_commits']['probes'] == 'ae31701edd2b1f8ec58ee17c222ada1143f37ab1'
    public = {r['id']: r for r in map(json.loads, Path(d['inputs']['items']['path']).read_text().splitlines())}
    private = {r['id']: r for r in map(json.loads, Path(d['inputs']['private_labels']['path']).read_text().splitlines())}
    pos = {r['id']: r for r in d['positions']}
    assert len(public) == len(private) == len(pos) == d['total_positions'] == 4000
    assert set(public) == set(private) == set(pos)
    for uid, p in pos.items():
        assert p['input_ids'] == public[uid]['input_ids']
        assert all(p[k] == private[uid][k] for k in ('state', 'split', 'label', 'reader_selected'))
        assert p['read_index'] == 255 and p['first_content_index'] == 0
    read_vectors = {}
    for cap in d['captures']:
        seal = read(cap['seal']['path'])
        assert set(seal['files']) == {'ADMISSION.json', 'CAPTURE_REPORT.json', 'MODEL_READY.json'} | {Path(f['path']).name for f in cap['files']}
        for f in cap['files']:
            p = Path(f['path'])
            assert seal['files'][p.name]['sha256'] == f['sha256']
            with np.load(p, allow_pickle=False) as a:
                assert set(a.files) == {'ids', 'block44', 'block42'}
                ids = a['ids'].tolist(); x = a['block44']; y = a['block42']
                assert x.shape == (len(ids),256,5120) and y.shape == (len(ids),5120)
                assert x.dtype == y.dtype == np.float16 and np.isfinite(x).all() and np.isfinite(y).all()
                for j, uid in enumerate(ids):
                    assert uid not in read_vectors and pos[uid]['capture']['row_index'] == j
                    assert Path(pos[uid]['capture']['path']) == p
                    read_vectors[uid] = (x[j,255].copy(), y[j].copy())
    assert set(read_vectors) == set(pos)
    basis = read(HERE.parent / 'BASIS_INPUTS_2026-10-27.json')
    assert d['pinned_assets']['jlens']['file_sha256'] == basis['files']['jlens']['sha256']
    assert d['inputs']['tokenizer']['sha256'] == basis['files']['tokenizer']['sha256']
    assert d['pinned_assets']['target']['revision'] == basis['model_revision']
    from transformers import AutoTokenizer
    sys.path.insert(0, str(ROOT / 'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tok = AutoTokenizer.from_pretrained(Path(basis['files']['tokenizer']['path']).parent, local_files_only=True)
    units, records, order, arrays, audit = [], [], [], [], {}
    pseal = read(d['probes']['seal']['path'])
    assert set(pseal['files']) == {'PROBE_REPORT.json'} | {s+'_probe.npz' for s in d['included_states']}
    for s in d['states']:
        state = s['state']; ids = s['test_ids']
        assert s['label_encoding'] == {'A': 0, 'B': 1}
        assert len(ids) == len(s['dev_ids']) == 400 and len(s['reader_ids']) == 200
        assert s['reader_ids'] == sorted(ids)[:200]
        path = Path(s['probe']['path'])
        assert pseal['files'][path.name]['sha256'] == s['probe']['sha256']
        with np.load(path, allow_pickle=False) as a:
            assert a['test_ids'].tolist() == ids and a['test_labels'].tolist() == s['test_labels']
            for j, uid in enumerate(ids):
                assert np.array_equal(a['test_block44'][j], read_vectors[uid][0])
                assert np.array_equal(a['test_block42'][j], read_vectors[uid][1])
                assert pos[uid]['split'] == 'test' and pos[uid]['state'] == state and pos[uid]['label'] == s['test_labels'][j]
            arrays.extend(read_vectors[i][0] for i in ids)
        phrases = [[s['A']], [s['B']]]
        words, removed = words_for(phrases); tokens = [token_variants(tok,w) for w in words]
        audit[state] = {'source': 'verbatim frozen E73 state A/B definitions', 'source_phrases': phrases,
                        'words': words, 'shared_removed': removed, 'token_ids': tokens,
                        'empty_value_set_policy': 'NOT EVALUABLE G3; unchanged primary_label handles missing readability'}
        for uid in ids:
            records.append({'id':uid,'feature':state,'split':'test','label':1-pos[uid]['label'],'original_label':pos[uid]['label']})
        order.extend(ids)
        units.append({'id':state,'source_row':state,'condition':None,'binary':True,'item_ids':ids,
                      'value_token_ids':{i:tokens for i in ids},'descriptive_token_sets':{i:{} for i in ids}})
    validate_units(units, records, order)
    bound = ROOT/'cache/g_agreement/understand/e73/jlens/bound_capture'
    bound.mkdir(parents=True,exist_ok=False)
    np.save(bound/'acts44.npy',np.stack(arrays),allow_pickle=False)
    dump(bound/'order.json',order); dump(bound/'records.json',records); dump(bound/'WORD_AUDIT.json',audit)
    dump(bound/'BANK_SEAL.json',{'original_bank_sha256':d['inputs']['bank_manifest']['sha256'],
         'normalization':'A=0/B=1 -> A=1/B=0, all400 tests/state; no sampling',
         'files':{'records.json':sha(bound/'records.json')}})
    dump(bound/'CAPTURE_SEAL.json',{'original_capture_seal_sha256':d['captures'][0]['seal']['sha256'],
         'original_probe_seal_sha256':d['probes']['seal']['sha256'],'original_delivery_sha256':DELIVERY_SHA,
         'files':{n:sha(bound/n) for n in ('acts44.npy','order.json','WORD_AUDIT.json')}})
    def ref(p): return {'path':str(p),'sha256':sha(p),'member':p.name}
    null = cpu_job.E52_CACHE/'sparse-primary/NULL_SEAL.json'
    atom = null.parent/'ATOM_SEAL.json'
    plan = {'experiment':'E73','layer':44,'split':'test','bank_seal':ref(bound/'BANK_SEAL.json'),
            'capture_seal':ref(bound/'CAPTURE_SEAL.json'),'records':ref(bound/'records.json'),
            'order':ref(bound/'order.json'),'activations':ref(bound/'acts44.npy'),'units':units,
            'word_audit':audit,'value_sources':[{'path':p,'sha256':h} for p,h in {
                str(DELIVERY):DELIVERY_SHA,str(bound/'WORD_AUDIT.json'):sha(bound/'WORD_AUDIT.json'),
                str(Path(__file__).resolve()):sha(__file__),str(HERE/'e73_adapter.py'):sha(HERE/'e73_adapter.py'),
                str(null):sha(null),str(atom):sha(atom),**{v['path']:v['sha256'] for v in d['inputs'].values()}}.items()],
            'intake_ref':ref(DELIVERY),'producer_commits':d['producer_commits'],
            'original_bank_seal_sha256':d['inputs']['bank_manifest']['sha256'],
            'original_capture_seal_sha256':d['captures'][0]['seal']['sha256'],
            'original_probe_seal_sha256':d['probes']['seal']['sha256'],
            'source_state_exclusions':d['exclusions'],'probe_gate_context':d['probe_exclusions'],
            'exclusions':[],'reader_outcomes_accessed':False,
            'method':'Unchanged E52 sparse k16 / 200-direction null and full-vocabulary G3; all400 balanced test positions per state. Native readers use frozen first200, all5 retained states forecast regardless of probe pass.',
            'null_seal':ref(null),'atom_seal':ref(atom),'verified_source_files':refs}
    target=CHANNEL/'E73_INPUT_PLAN.json';assert not target.exists();dump(target,plan)
    receipt=ROOT/'cache/g_agreement/understand/e52/r3b/E73_DELIVERY.json';assert not receipt.exists()
    dump(receipt,{'issuer':'integrator','experiment':'E73','status':'VERIFIED_CAPTURE_ONLY',
        'delivered_epoch':datetime.fromisoformat('2026-10-27T16:31:02+00:00').timestamp(),
        'intake_created_at':d['created_at_utc'],'original_delivery_path':str(DELIVERY),'original_delivery_sha256':DELIVERY_SHA,
        'bank_seal_sha256':plan['bank_seal']['sha256'],'capture_seal_sha256':plan['capture_seal']['sha256'],
        'reader_outputs_opened_at_registration':False,'reader_outputs_opened_before_forecast':False,
        'readers_held_until_forecast_commit':True,'custody_authority':'I-2 complete delivery relay 16:31:02Z plus hashed W-census custody attestation',
        'original_capture_seal_sha256':plan['original_capture_seal_sha256'],'original_probe_seal_sha256':plan['original_probe_seal_sha256']})
    print('E73 bound, no J scoring: 5 states / 2000 tests; all source files verified; A/B explicitly normalized')
    print('Frozen token counts:', {k:[len(t) for t in v['token_ids']] for k,v in audit.items()})


if __name__ == '__main__': bind()
