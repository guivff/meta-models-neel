"""CPU-only synthetic checks. No E85 outputs or model weights accessed."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('score122', HERE / 'score122.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FrozenContrasts(unittest.TestCase):
    def test_summed_not_mean_log_probability(self):
        self.assertAlmostEqual(m.score('hedged_vs_direct', [-1., -2.], [-4.]), 1.)
        self.assertAlmostEqual(m.score('ai_vs_direct', [-1.] * 4, [-2.]), -2.)

    def test_stop_is_native_special_token(self):
        stop = m.load_contract()['contrasts'][2]['positive']
        self.assertEqual(stop, {'text': '<|im_end|>', 'token_ids': [248046]})
        self.assertAlmostEqual(m.score('stop_vs_continue', [-3.], [-1.]), -2.)

    def test_formal_direction(self):
        self.assertAlmostEqual(m.score('formal_vs_informal', [-1., -2.], [-3., -4.]), 4.)

    def test_bad_inputs_fail_closed(self):
        for bad in ([], [-1.], [-1., -2., -3.], [float('nan'), -1.],
                    [float('-inf'), -1.], [1., -1.], [True, -1.], ['-1', -1.]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                m.score('hedged_vs_direct', bad, [-1.])
        with self.assertRaises(ValueError):
            m.score('new_contrast', [-1.], [-1.])

    def test_fresh_extract_import_and_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            archive = folder / 'source.tar.gz'
            with tarfile.open(archive, 'w:gz') as tar:
                for name in ('score122.py', 'CONTRASTS.json'):
                    tar.add(HERE / name, arcname=name)
            extracted = folder / 'extract'
            extracted.mkdir()
            with tarfile.open(archive) as tar:
                tar.extractall(extracted, filter='data')
            command = [sys.executable, '-c', 'import score122; assert len(score122.load_contract()["contrasts"]) == 4']
            subprocess.run(command, cwd=extracted, check=True)
            source = folder / 'input.jsonl'
            result = folder / 'output.jsonl'
            record = {'id': 'synthetic-only', 'contrast_id': 'stop_vs_continue',
                      'positive_token_logprobs': [-1.], 'negative_token_logprobs': [-2.]}
            source.write_text(json.dumps(record) + '\n')
            command = [sys.executable, str(extracted / 'score122.py'), str(source), str(result)]
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual(json.loads(result.read_text())['log_probability_difference'], 1.)
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            source.write_text((json.dumps(record) + '\n') * 2)
            self.assertNotEqual(subprocess.run(command[:-1] + [str(folder / 'bad.jsonl')], capture_output=True).returncode, 0)
            self.assertFalse((folder / 'bad.jsonl').exists())


if __name__ == '__main__':
    unittest.main()
