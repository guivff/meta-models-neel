import json
from pathlib import Path
import tempfile
import unittest
from .analyze_once import COUNTS, FIELDS, analyze, analyze_views, rate, run, sha, write


def fixture(k=0, topic=75):
    mapping = [{'id': f'{s}-{i}', 'stratum': s} for s, n in COUNTS.items() for i in range(n)]
    rows = []
    for m in mapping:
        r = dict(id=m['id'], **{f: False for f in FIELDS})
        if m['stratum'] != 'C' and k:
            r[m['stratum']] = True
            k -= 1
        if m['stratum'] == 'C' and topic:
            r['topic'] = True
            topic -= 1
        rows.append(r)
    return rows, mapping


class AnalysisTests(unittest.TestCase):
    def test_wilson_reference(self):
        self.assertAlmostEqual(rate([False]*392)['wilson95'][1], 3.8416/(392+3.8416))
        self.assertAlmostEqual(rate([True]*50+[False]*50)['wilson95'][0], .4038298286)

    def test_registered_boundaries(self):
        self.assertTrue(analyze(*fixture(19))['R_G1']['holds'])
        self.assertFalse(analyze(*fixture(20))['R_G1']['holds'])
        self.assertFalse(analyze(*fixture(0, 74))['R_G1']['holds'])
        self.assertFalse(analyze(*fixture(78))['R_G1']['falsifier'])
        self.assertTrue(analyze(*fixture(79))['R_G1']['falsifier'])

    def test_matching_question_only(self):
        rows, mapping = fixture()
        for r, m in zip(rows, mapping):
            for s in COUNTS:
                if s != 'C' and s != m['stratum']:
                    r[s] = True
        result = analyze(rows, mapping)
        self.assertEqual(result['R_G1']['pooled_structural']['k'], 0)
        self.assertEqual(result['R_G3']['eval_awareness']['n'], 542)

    def test_reject_bad_codes_and_ids(self):
        for mode in ('missing', 'duplicate', 'null', 'integer'):
            rows, mapping = fixture()
            if mode == 'missing': rows.pop()
            if mode == 'duplicate': rows[-1] = rows[0]
            if mode == 'null': rows[0]['topic'] = None
            if mode == 'integer': rows[0]['S1'] = 0
            with self.assertRaises(ValueError): analyze(rows, mapping)

    def test_evidence_and_terminal_sentinels(self):
        rows, mapping = fixture()
        for r in rows:
            r['evidence'] = {f: 'synthetic evidence' if r[f] else '' for f in FIELDS}
        baseline = analyze(rows, mapping)
        wrapped = [dict(id=r['id'], status='KEPT', code=r, attempts=0) for r in rows]
        self.assertEqual(analyze(wrapped, mapping), baseline)
        for i in (0, 392):
            wrapped[i] = dict(id=rows[i]['id'], status='UNPARSEABLE', code=None, attempts=2)
        result = analyze(wrapped, mapping)
        self.assertEqual(result['judgment_accounting']['UNPARSEABLE'], 2)
        self.assertTrue(result['judgment_accounting']['flag'])
        self.assertEqual(result['R_G1']['pooled_structural']['n'], 391)
        self.assertEqual(result['R_G1']['C_topic']['n'], 149)
        self.assertEqual(result['R_G1']['C_topic']['k'], 74)
        self.assertEqual(result['R_G2']['S1']['topic']['n'], 127)
        self.assertEqual(result['R_G3']['eval_awareness']['n'], 540)
        self.assertNotIn('synthetic evidence', json.dumps(result))

    def test_all_unparseable_serializes_without_nan(self):
        rows, mapping = fixture()
        rows = [dict(id=r['id'], status='UNPARSEABLE', code=None) for r in rows]
        result = analyze(rows, mapping)
        self.assertEqual(result['R_G1']['verdict'], 'NOT_EVALUABLE')
        self.assertEqual(result['judgment_accounting']['UNPARSEABLE'], 542)
        self.assertIsNone(result['R_G1']['pooled_structural']['rate'])
        json.dumps(result, allow_nan=False)

    def test_invalid_envelope_not_silently_excluded(self):
        rows, mapping = fixture()
        rows[0] = dict(id=rows[0]['id'], status='INVALID', code=None)
        with self.assertRaises(ValueError): analyze(rows, mapping)

    def test_two_views_and_unparseable_overlap(self):
        rows, mapping = fixture(1)
        ids = ['S1-0', 'S1-1', 'C-0']
        rows[1] = dict(id='S1-1', status='UNPARSEABLE', code=None)
        result = analyze_views(rows, mapping, ids)
        a, b = result['all_records'], result['excluding_path_redacted']
        self.assertEqual(a, analyze(rows, mapping))
        self.assertEqual(a['R_G1']['pooled_structural']['n'], 391)
        self.assertEqual(b['R_G1']['pooled_structural']['n'], 390)
        self.assertEqual(b['R_G1']['pooled_structural']['k'], 0)
        self.assertEqual(b['R_G1']['C_topic']['n'], 149)
        self.assertEqual(b['R_G1']['C_topic']['k'], 74)
        self.assertEqual(b['R_G2']['S1']['structural']['n'], 126)
        self.assertEqual(b['R_G3']['eval_awareness']['n'], 539)
        self.assertEqual(a['judgment_accounting']['UNPARSEABLE'], 1)
        self.assertEqual(b['judgment_accounting']['UNPARSEABLE'], 0)
        self.assertEqual(b['judgment_accounting']['total'], 539)
        for bad in ([], ids[:2], ['S1-0']*3, ['S1-0', 'C-0', 'unknown']):
            with self.assertRaises(ValueError): analyze_views(rows, mapping, bad)

    def test_seal_before_map_and_once_lock(self):
        for valid in (False, True):
            with tempfile.TemporaryDirectory() as td:
                root = Path(td)
                rows, mapping = fixture()
                rows = [dict(id=r['id'], status='KEPT', code=dict(r, evidence={f: '' for f in FIELDS}), attempts=0) for r in rows]
                rows[0] = dict(id=rows[0]['id'], status='UNPARSEABLE', code=None, attempts=2)
                j = root/'judgments.jsonl'
                j.write_text(''.join(json.dumps(r)+'\n' for r in rows))
                m = root/'map.jsonl'
                m.write_text(''.join(json.dumps(r)+'\n' for r in mapping))
                rubric = root/'rubric.json'; write(rubric, {'synthetic': True})
                redacted = root/'redacted.json'
                write(redacted, ['S1-0', 'S1-1', 'C-0'])
                js = root/'judge-seal.json'
                write(js, {'status': 'SEALED_BLIND_JUDGMENTS' if valid else 'INCOMPLETE', 'n': 542,
                           'packet_sha256': 'synthetic', 'strata_joined': False,
                           'redacted_ids_sha256': sha(redacted), 'judgments_sha256': sha(j), 'rubric_sha256': sha(rubric)})
                sp = root/'spec.json'
                write(sp, {'repo_root': str(root), 'output': str(root/'cache/out'), 'judgment_seal': str(js),
                           'redacted_ids': str(redacted), 'judgments': str(j), 'rubric': str(rubric), 'packet_sha256': 'synthetic',
                           'private_map': str(m) if valid else str(root/'MUST_NOT_OPEN'), 'private_map_sha256': sha(m)})
                write(root/'ANALYSIS_COMMAND_SEAL.json', {'files': {'spec.json': sha(sp)}})
                if valid:
                    run(sp)
                    self.assertTrue((root/'cache/out/ANALYSIS_SEAL.json').exists())
                    result = json.loads((root/'cache/out/RESULTS.json').read_text())
                    self.assertEqual(result['excluding_path_redacted']['judgment_accounting']['total'], 539)
                    self.assertIn('R_G1', result['all_records'])
                else:
                    with self.assertRaisesRegex(ValueError, 'completion seal'): run(sp)
                    self.assertTrue((root/'cache/out/INVALID.json').exists())
                with self.assertRaises(FileExistsError): run(sp)

if __name__ == '__main__':
    unittest.main()
