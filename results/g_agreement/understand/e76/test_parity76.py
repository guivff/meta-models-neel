"""CPU-only split parity regressions; no actual W1 generation or metric run."""
import copy,json,tempfile,types,sys,time,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import common76 as C
import worker76 as W
import parity76 as P
from score_parity76 import adjudicate


def fixture(folder):
    items=[{'id':f'{r}-{i}','feature':r} for r in P.ROWS for i in range(84)]
    (folder/'items.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in items))
    C.dump(folder/'templates.json',{r:{'olens':[['A','B'],['a','b']]} for r in P.ROWS})
    np.save(folder/'acts44.npy',np.ones((252,5120),np.float32))
    C.dump(folder/'INPUT_SEAL.json',{'original_input_seal_sha256':P.ORIGINAL_SEAL,'files':{n:C.sha(folder/n) for n in ('items.jsonl','templates.json','acts44.npy')}})
    return items


class Tests(unittest.TestCase):
    def test_label_free_generation_rejects_extra_labels(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t);items=fixture(f);pin=C.sha(f/'INPUT_SEAL.json');inputs=P.load_parity(f,pin)
            class Backend:
                def load_oracle(self):pass
                def parity_scores(self,h,pairs):return [[1.,2.] for _ in h]
            class Clock:
                def warmup(self,phase,fn):fn()
                def call(self,phase,fn,left=0):return fn()
            out=f/'out';out.mkdir();detail=P.generate(Backend(),Clock(),inputs,out)
            records=[json.loads(x) for x in (out/'PARITY_SCORES.jsonl').read_text().splitlines()]
            self.assertEqual(len(records),252);self.assertTrue(all(set(x)=={'id','feature','scores'} for x in records))
            self.assertEqual([x['id'] for x in records],[x['id'] for x in items]);self.assertFalse(detail['labels_loaded']);self.assertFalse(detail['verdict_computed'])
            # Use another clean input folder so only the injected labels trip the positive whitelist.
            other=f/'input';other.mkdir();fixture(other);(other/'labels.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'whitelist'):P.load_parity(other,C.sha(other/'INPUT_SEAL.json'))

    def test_cli_parity_does_not_need_release_or_consume_production(self):
        with tempfile.TemporaryDirectory() as t:
            cache=Path(t);inp=cache/'parity_inputs';inp.mkdir();fixture(inp);pin=C.sha(inp/'INPUT_SEAL.json')
            assets=cache/'assets.json';assets.write_text('{}');ass=cache/'assignment.json'
            a={'assets_manifest_sha256':C.sha(assets),'parity_input_seal_sha256':pin,'absolute_deadline_epoch':time.time()+7000,
               'phase_forecasts_seconds':{p:1. for p in W.PHASES},'parity_phase_forecasts_seconds':{'parity_setup':1.,'parity':1.}}
            C.dump(ass,a);(cache/'LAUNCH_REQUEST.json').write_text(json.dumps({'status':'READY','parity_input_seal_sha256':pin}))
            (cache/'POD_SOURCE_SEAL.json').write_text('{}')
            for n in ('native_nla512.py','vendor/mats/readers/olens.py','vendor/mats/readers/nla.py'):
                p=cache/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('stub')
            class Backend:
                def __init__(self,assets):self.runtime={'stub':True}
                def load_oracle(self):pass
                def parity_scores(self,h,pairs):return [[0.,1.] for _ in h]
            argv=['worker76.py','--parity-generate-only','--assignment',str(ass),'--assets',str(assets)]
            with patch.object(W,'CACHE',cache),patch.object(W,'HERE',cache),patch.object(W,'preflight',return_value={}),patch.object(W,'assignment_check',return_value=a['absolute_deadline_epoch']-180),patch.object(W,'parity_release',side_effect=AssertionError('must not request PASS before generation')),patch.dict(sys.modules,{'backend76':types.SimpleNamespace(Backend=Backend)}),patch.object(sys,'argv',argv):
                W.main()
                with self.assertRaises(FileExistsError):W.main()
            self.assertFalse((cache/'WORKER.RUN_ONCE.json').exists());self.assertFalse((cache/'out-20261027').exists())
            out=cache/'parity-generated-20261027';seal=C.read(out/'OUTPUT_SEAL.json');C.verify(out,seal)
            self.assertEqual(seal['status'],'GENERATED_UNSCORED');self.assertFalse((out/'PARITY_RESULT.json').exists())

    def test_split_release_cannot_substitute_another_generation(self):
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)
            for name in ('native_nla512.py','vendor/mats/readers/olens.py','vendor/mats/readers/nla.py'):
                p=f/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('native')
            (f/'PARITY_GENERATE.RUN_ONCE.json').write_text('{}');out=f/'parity-generated-20261027';out.mkdir()
            (out/'OUTPUT_SEAL.json').write_text('{}');(out/'PARITY_SCORES.jsonl').write_text('raw')
            C.dump(f/'LAUNCH_REQUEST.json',{'parity_input_seal_sha256':'p'*64})
            release={'issuer':'integrator','pod_id':'pod','status':'PASS','same_pod_verified':True,'native_backend_unchanged':True,
                'parity_result_sha256':'a'*64,'assets_manifest_sha256':'assets',
                'native_code_sha256':{n:C.sha(f/n) for n in ('native_nla512.py','vendor/mats/readers/olens.py','vendor/mats/readers/nla.py')},
                'parity_generation_output_seal_sha256':C.sha(out/'OUTPUT_SEAL.json'),'raw_scores_sha256':C.sha(out/'PARITY_SCORES.jsonl'),
                'parity_input_seal_sha256':'p'*64}
            C.dump(f/'PARITY_RELEASE.json',release)
            with patch.object(W,'CACHE',f),patch.object(W,'HERE',f):
                self.assertEqual(W.parity_release({'pod_id':'pod','assets_manifest_sha256':'assets'}),release)
                (out/'PARITY_SCORES.jsonl').write_text('other generation')
                with self.assertRaises(ValueError):W.parity_release({'pod_id':'pod','assets_manifest_sha256':'assets'})

    def test_Oracle_parity_wrapper_keeps_original_layer_prefix_and_orientation(self):
        import torch
        from backend76 import Backend
        class Oracle:
            def paired_logodds_templates(inner,h,layer,pairs,prefix):
                self.assertEqual(layer,44);self.assertEqual(prefix,'');self.assertEqual(tuple(h.shape),(8,5120))
                self.assertEqual(pairs,[['A','B'],['a','b']]);return torch.stack([torch.arange(8),-torch.arange(8)])
        b=Backend.__new__(Backend);b.oracle=Oracle()
        self.assertEqual(b.parity_scores(np.ones((8,5120)),[['A','B'],['a','b']]),[[float(i),-float(i)] for i in range(8)])

    def test_CPU_adjudication_original_recipe_threshold_failures_and_grid(self):
        items=[{'id':f'{r}-{i}','feature':r} for r in P.ROWS for i in range(84)]
        key={'labels':{x['id']:int(int(x['id'].rsplit('-',1)[1])>=42) for x in items},'items':items,
             'reference':{'rows':list(P.ROWS),'status':'FROZEN','reference_auc':{r:1. for r in P.ROWS}}}
        records=[{**x,'scores':[float(key['labels'][x['id']])]*2} for x in items]
        self.assertEqual(adjudicate(records,key)['status'],'PASS')
        reverse=[{**x,'scores':[-s for s in x['scores']]} for x in records]
        self.assertEqual(adjudicate(reverse,key)['status'],'FAIL')
        with self.assertRaises(ValueError):adjudicate(records[:-1],key)
        with self.assertRaises(ValueError):adjudicate(records+records[:1],key)
        for ref,verdict in ((.9799,'FAIL'),(.9801,'PASS')):
            k=copy.deepcopy(key);k['reference']['reference_auc']={r:ref for r in P.ROWS}
            self.assertEqual(adjudicate(records,k)['status'],verdict)


if __name__=='__main__':unittest.main()
