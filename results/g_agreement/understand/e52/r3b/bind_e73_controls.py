"""Bind only the 19da3104 W7/W8 supplement; no J scoring or native outputs."""
from pathlib import Path
from datetime import datetime, timezone
import ast
import hashlib
import json
import subprocess
import sys
import time
import numpy as np
from e73_controls_adapter import ROOT, HERE, cpu_job, validate_units
from prepare import words_for

read, dump, sha = cpu_job.read, cpu_job.dump, cpu_job.sha
BANK = 'E73_CONTROLS'
CHANNEL = ROOT/'results/g_agreement/understand/e57/jlens'
HANDOFF_COMMIT = '1c4baecebe8b4e77f8ecb5542933ead20cc5f6aa'
AUTHORITY = '19da310478230f227e2d568d625b11ef49a04095'
ORIGINAL_SHA = 'f51d07a100807a76cb975a3351314df578911693d21a7c4e2822e557df383717'


def bind():
    started = time.time()
    assert sha(HERE/'E73_JFORECAST.json') == ORIGINAL_SHA
    target = CHANNEL/(BANK+'_INPUT_PLAN.json')
    bound = ROOT/'cache/g_agreement/understand/e73_controls/jlens/bound_capture'
    receipt = ROOT/'cache/g_agreement/understand/e52/r3b/E73_CONTROLS_DELIVERY.json'
    assert not target.exists() and not bound.exists() and not receipt.exists()
    pins = {}
    def pin(p, expected=None):
        p = Path(p).resolve(); h = sha(p)
        assert expected is None or h == expected, 'hash mismatch: '+str(p)
        pins[str(p)] = h
        return {'path':str(p), 'sha256':h, 'member':p.name}
    def seal_files(folder, seal):
        for name, meta in seal['files'].items():
            p = folder/name
            assert p.parent == folder and p.stat().st_size == meta['bytes']
            pin(p, meta['sha256'])
    hp = ROOT.parent/'wt-i2/results/g_agreement/i2/E73_CONTROL_A2_WLENS_HANDOFF.json'
    assert hp.read_bytes() == subprocess.check_output(['git','show',HANDOFF_COMMIT+':results/g_agreement/i2/E73_CONTROL_A2_WLENS_HANDOFF.json'],cwd=ROOT)
    handoff = pin(hp); d = read(hp)
    assert d['run_id'] == 'e73-controls-20261027-a2'
    assert d['status'] == 'CAPTURES_AND_PROBES_SEALED_WLENS_FORECAST_REQUIRED'
    assert d['capture_count'] == 1432 and d['reader_positions_per_reader'] == 400
    assert d['reader_outputs_created'] == 0 and d['reader_GO_issued'] is False
    assert d['scientific_inputs_changed'] is False and d['no_original_bank_replay'] is True
    census = ROOT.parent/'wt-wcensus'
    source = census/'cache/g_agreement/e73/controls_19da3104'
    manifest = census/'results/g_agreement/e73/controls_19da3104/BANK_MANIFEST.json'
    mref = pin(manifest,d['frozen_bank_manifest_sha256']); m = read(manifest)
    pin(source/'GATE_REPORT.json',d['gate_report_sha256']); gate = read(source/'GATE_REPORT.json')
    pin(source/'DERIVATION.json'); deriv = read(source/'DERIVATION.json')
    assert deriv['authority_commit'] == AUTHORITY and gate['included_states'] == ['W7','W8']
    assert gate['metrics']['W7']['test_auroc'] == 1.0
    assert gate['metrics']['W8']['test_auroc'] == 0.9641483736580676
    pin(source/'public/items.jsonl',m['items_sha256'])
    pin(source/'private/labels.jsonl',m['private_labels_sha256'])
    public_rows = [json.loads(s) for s in (source/'public/items.jsonl').read_text().splitlines()]
    private_rows = [json.loads(s) for s in (source/'private/labels.jsonl').read_text().splitlines()]
    public = {r['id']:r for r in public_rows}; private = {r['id']:r for r in private_rows}
    assert len(public_rows) == len(private_rows) == len(public) == len(private) == 1432
    assert set(public) == set(private) and {r['state'] for r in private_rows} == {'W7','W8'}
    assert all(len(r['input_ids']) == 256 for r in public_rows)
    state_path = census/'projects/g_agreement/e73/states.py'
    pin(state_path,m['code_sha256']['states.py'])
    tree = ast.parse(state_path.read_text())
    values = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STATE_VALUES' for t in n.targets))
    cap = Path(d['private_capture_directory']); probes = Path(d['private_probe_directory'])
    capref = pin(cap/'CAPTURE_SEAL.json',d['capture_seal_sha256'])
    pin(cap/'OPERATOR_SEAL.json',d['operator_seal_sha256'])
    pref = pin(probes/'PROBE_SEAL.json',d['probe_seal_sha256'])
    cs, ps = read(cap/'CAPTURE_SEAL.json'), read(probes/'PROBE_SEAL.json')
    assert cs['status'] == ps['status'] == 'COMPLETE'
    assert cs['bank_manifest_sha256'] == mref['sha256'] and cs['input_sha256'] == m['items_sha256']
    assert set(cs['files']) == {'ADMISSION.json','CAPTURE_REPORT.json','MODEL_READY.json'} | {f'capture-{i:05d}.npz' for i in range(358)}
    assert set(ps['files']) == {'PROBE_REPORT.json','W7_probe.npz','W8_probe.npz'}
    seal_files(cap,read(cap/'OPERATOR_SEAL.json')); seal_files(cap,cs); seal_files(probes,ps)
    assert ps['files'] == d['probe_files']
    admission = read(cap/'ADMISSION.json'); report = read(cap/'CAPTURE_REPORT.json')
    assert admission['reader_go'] is False and admission['input_sha256'] == m['items_sha256']
    assert report['reader_outputs'] == 0 and report['status'] == 'COMPLETE' and report['completed'] == report['total'] == 1432
    assert report['input_sha256'] == m['items_sha256']
    for name,h in admission['source_files'].items():
        blob = subprocess.check_output(['git','show',admission['runtime_commit']+':'+name],cwd=ROOT)
        assert hashlib.sha256(blob).hexdigest() == h
    blob = subprocess.check_output(['git','show',d['probe_source_commit']+':projects/g_agreement/e73/probes.py'],cwd=ROOT)
    assert hashlib.sha256(blob).hexdigest() == d['probe_source_sha256']
    pr = read(probes/'PROBE_REPORT.json')
    assert pr['capture_seals'] == [{'seal_sha256':capref['sha256']}]
    assert pr['private_labels_sha256'] == m['private_labels_sha256'] and pr['bank_manifest_sha256'] == mref['sha256']
    assert all(r['probe_pass'] for r in pr['rows']) and pr['readers'] == 'NOT_RUN'
    vectors = {}; capture_index = {}
    for name in sorted(n for n in cs['files'] if n.endswith('.npz')):
        with np.load(cap/name,allow_pickle=False) as a:
            assert set(a.files) == {'ids','block44','block42'}
            ids = a['ids'].tolist(); x = a['block44']; y = a['block42']
            assert x.shape == (len(ids),256,5120) and y.shape == (len(ids),5120)
            assert x.dtype == y.dtype == np.float16 and np.isfinite(x).all() and np.isfinite(y).all()
            for j,uid in enumerate(ids):
                assert uid in private and uid not in vectors
                vectors[uid] = (x[j,255].copy(),y[j].copy())
                capture_index[uid] = {'file':name,'row':j,'read_index':255,'first_content_index':0}
    assert set(vectors) == set(private)
    basis = read(HERE.parent/'BASIS_INPUTS_2026-10-27.json')
    pin(basis['files']['tokenizer']['path'],m['tokenizer_sha256'])
    from transformers import AutoTokenizer
    sys.path.insert(0,str(ROOT/'external/mats-nla-workspace/src'))
    from mats.readers.jlens import token_variants
    tok = AutoTokenizer.from_pretrained(Path(basis['files']['tokenizer']['path']).parent,local_files_only=True)
    records, units, order, arrays, audit, reader_ids = [], [], [], [], {}, {}
    for state,n in [('W7',400),('W8',316)]:
        ids = sorted(uid for uid,r in private.items() if r['state']==state and r['split']=='test')
        dev = sorted(uid for uid,r in private.items() if r['state']==state and r['split']=='dev')
        selected = sorted(uid for uid,r in private.items() if r['state']==state and r['reader_selected'])
        assert len(ids) == len(dev) == n and selected == ids[:200]
        assert all(sum(private[i]['label']==v for i in group)==n//2 for group in (dev,ids) for v in (0,1))
        with np.load(probes/(state+'_probe.npz'),allow_pickle=False) as a:
            assert a['test_ids'].tolist() == ids and a['reader_ids'].tolist() == selected
            assert a['test_labels'].tolist() == [private[i]['label'] for i in ids]
            for j,uid in enumerate(ids):
                assert np.array_equal(a['test_block44'][j],vectors[uid][0])
                assert np.array_equal(a['test_block42'][j],vectors[uid][1])
        phrases = [[v] for v in values[state]]
        words,removed = words_for(phrases); tokens = [token_variants(tok,w) for w in words]
        audit[state] = {'source':'verbatim frozen STATE_VALUES','source_phrases':phrases,'words':words,'shared_removed':removed,'token_ids':tokens}
        reader_ids[state] = selected
        records.extend({'id':uid,'feature':state,'split':'test','original_label':private[uid]['label'],'label':1-private[uid]['label']} for uid in ids)
        order.extend(ids); arrays.extend(vectors[uid][0] for uid in ids)
        units.append({'id':state,'source_row':state,'condition':None,'binary':True,'item_ids':ids,'value_token_ids':{i:tokens for i in ids},'descriptive_token_sets':{i:{} for i in ids}})
    validate_units(units,records,order)
    bound.mkdir(parents=True)
    np.save(bound/'acts44.npy',np.stack(arrays),allow_pickle=False)
    for name,obj in [('records.json',records),('order.json',order),('WORD_AUDIT.json',audit),('CAPTURE_INDEX.json',capture_index),('READER_IDS.json',reader_ids)]:dump(bound/name,obj)
    dump(bound/'BANK_SEAL.json',{'original_bank_sha256':mref['sha256'],'normalization':'A=0/B=1 -> A=1/B=0; all W7 400 and W8 316 tests','files':{'records.json':sha(bound/'records.json')}})
    dump(bound/'CAPTURE_SEAL.json',{'original_capture_seal_sha256':capref['sha256'],'original_probe_seal_sha256':pref['sha256'],'files':{n:sha(bound/n) for n in ('acts44.npy','order.json','WORD_AUDIT.json','CAPTURE_INDEX.json','READER_IDS.json')}})
    def ref(p):return {'path':str(p),'sha256':sha(p),'member':p.name}
    null = cpu_job.E52_CACHE/'sparse-primary/NULL_SEAL.json'; atom = null.parent/'ATOM_SEAL.json'
    for p in (null,atom,Path(__file__),HERE/'e73_controls_adapter.py',bound/'WORD_AUDIT.json'):pin(p)
    plan = {'experiment':BANK,'layer':44,'split':'test','bank_seal':ref(bound/'BANK_SEAL.json'),'capture_seal':ref(bound/'CAPTURE_SEAL.json'),'records':ref(bound/'records.json'),'order':ref(bound/'order.json'),'activations':ref(bound/'acts44.npy'),'units':units,'word_audit':audit,
        'value_sources':[{'path':p,'sha256':h} for p,h in pins.items() if not p.endswith('.npz')], 'verified_source_files':pins,
        'intake_ref':handoff,'intake_commit':HANDOFF_COMMIT,'authority_commit':AUTHORITY,'original_bank_ref':mref,'original_capture_ref':capref,'original_probe_ref':pref,
        'original_structural_forecast_sha256':ORIGINAL_SHA,'original_structural_forecast_commit':'7b04585e518011c1be6a4aa14c55cb90c97313a6','reader_ids':ref(bound/'READER_IDS.json'),
        'categories':{'W7':'content','W8':'content'},'category_authority':AUTHORITY+' explicitly names both content controls; frozen E58a content/plan REPORTED otherwise MISSED',
        'category_predictions':{'W7':{'oracle_prediction':'REPORTED','nla_prediction':'REPORTED'},'W8':{'oracle_prediction':'REPORTED','nla_prediction':'REPORTED'}},
        'BOW_AUROC':{s:gate['metrics'][s]['test_auroc'] for s in ['W7','W8']},'probe_report':ref(probes/'PROBE_REPORT.json'),'null_seal':ref(null),'atom_seal':ref(atom),
        'exclusions':[],'reader_outcomes_accessed':False,'method':'Unchanged CPU J44, frozen k16 pursuit / 200-direction null / full-vocabulary G3. W7 all400 and W8 all316 balanced tests; native first200 each. Mean A-minus-B, not probe coefficients. Separate supplement, no structural replay.',
        'commands':['python results/g_agreement/understand/e52/r3b/e73_controls_adapter.py channel','python results/g_agreement/understand/e52/r3b/e73_controls_adapter.py forecast'],
        'handoff_recorded_at':d['recorded_at'],'binding_started_at':datetime.fromtimestamp(started,timezone.utc).isoformat()}
    dump(target,plan)
    dump(receipt,{'issuer':'integrator','experiment':BANK,'status':'VERIFIED_CAPTURE_ONLY','delivered_epoch':datetime.fromisoformat(d['recorded_at']).timestamp(),
        'timestamp_note':'Conservative handoff artifact creation time; actual W-lens notification/discovery occurred Oct28 ~01:58Z. No clock reset; final receipt reports both intervals.',
        'original_delivery_path':str(hp),'original_delivery_sha256':handoff['sha256'],'bank_seal_sha256':plan['bank_seal']['sha256'],'capture_seal_sha256':plan['capture_seal']['sha256'],
        'reader_outputs_opened_at_registration':False,'reader_outputs_opened_before_forecast':False,'readers_held_until_forecast_commit':True,
        'custody_authority':'Committed I-2 handoff 1c4baece and direct user instruction plus I-2 relay: no supplemental reader run, GO held for forecast.'})
    print(json.dumps({'status':'BOUND_NO_J_SCORING','states':2,'test_positions':len(order),'capture_positions':len(vectors),'token_counts':{s:[len(t) for t in a['token_ids']] for s,a in audit.items()},'wall_seconds':time.time()-started}))


if __name__ == '__main__':bind()
