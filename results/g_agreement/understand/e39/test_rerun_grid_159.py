"""Execute the production orchestration on fake models, without scientific scores."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest import mock
import numpy as np
import contract as C
import worker as W
import rerun_159 as R


class Grid(unittest.TestCase):
    def test_four_run_recovery_preserves_original_full_steps_and_parity(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)/'cache';root.mkdir();out=root/'output'
            a=SimpleNamespace(out=out,assignment=root/'assignment.json',environment_manifest=root/'env.json',
                parity_inputs=root/'parity',input=root/'input',assets=root/'assets',mapping=C.HERE/'LORA_TARGETS.json',admission=root/'ADMISSION.json')
            assignment={'issuer':'integrator','experiment':'E39','pod_count':1,'slot':0,
                'runs':R.scope()['rerun_runs'],'plan_sha256':C.sha(C.HERE/'PLAN.json'),
                'target_mapping_sha256':C.sha(C.HERE/'LORA_TARGETS.json'),'source_published':True,
                'external_hardstop_verified':True,'allocated_gpu_seconds':13500,'previous_gpu_seconds':50925,
                'provider_created_epoch':time.time()-600,'deadline_epoch':time.time()+12900,
                'training_environment_sha256':'synthetic','parity_input_seal_sha256':'synthetic','input_seal_sha256':'synthetic'}
            assignment['deadline_epoch']=assignment['provider_created_epoch']+13500
            C.dump(a.assignment,assignment);C.dump(a.environment_manifest,{'synthetic':True})
            dev=[{'id':f'{row}-{i}','feature':row,'y':i%2,'cluster':str(i//14)} for row in C.ROWS for i in range(84)]
            test=[{'id':r['id'],'feature':r['feature']} for r in dev]
            specs={r:{'olens':[['a','b'],['aa','bb']]} for r in C.ROWS}
            model=SimpleNamespace(named_parameters=lambda:[])
            tok=SimpleNamespace(encode=lambda x,**kw:list(x))
            reader=SimpleNamespace(device='cuda')
            counts={'train':0,'score':0,'free':0};events=[]
            def train(*args,**kw):
                counts['train']+=1;events.append('train')
                return {'finite_loss':True,'finite_gradients':True,'frozen_parameter_grads_none':True} if kw.get('diagnostics') else .5
            def score(reader,items,acts,spec,row):
                counts['score']+=1;return [{'id':r['id'],'scores':[0.,0.]} for r in items if r['feature']==row]
            def free(reader,items,acts,row,**kw):
                counts['free']+=1;return [{'id':r['id'],'raw':'synthetic'} for r in items if r['feature']==row]
            real_dump=C.dump
            def dump(path,value):
                real_dump(path,value)
                if Path(path).name=='FORECAST.json':
                    f={**value,'forecast_sha256':C.sha(path)}
                    real_dump(a.admission,R.admit(f,assignment))
            def parity(*args,**kw):events.append('parity');real_dump(out/'PARITY_RESULT.json',{'status':'PASS','synthetic':True})
            with mock.patch.multiple(W,arm_deadline=mock.Mock(),load_base=mock.Mock(return_value=(model,tok)),
                    make_reader=mock.Mock(return_value=reader),attach_lowrank=mock.Mock(return_value=([],[])),
                    detach_lowrank=mock.Mock(),optimizer_for=mock.Mock(),train_step=mock.Mock(side_effect=train),
                    score=mock.Mock(side_effect=score),free=mock.Mock(side_effect=free),parity_gate=mock.Mock(side_effect=parity),
                    parity_inputs=mock.Mock(return_value=None),runtime_inputs=mock.Mock(return_value=(assignment,{}, {},dev,test,np.ones((1,1)),np.ones((1,1)),specs))), \
                 mock.patch.object(W.E,'verify_manifest'),mock.patch.object(W.E,'runtime_ready',return_value={'synthetic':True}), \
                 mock.patch.object(C,'assignment',side_effect=lambda a,now=None:a),mock.patch.object(C,'dump',side_effect=dump):
                W.run(a)
            self.assertEqual(counts,{'train':4*800+10,'score':4*7+2,'free':4+2})
            self.assertEqual(events[0],'parity')
            self.assertEqual(C.read(out/'RUN_RECEIPT.json')['status'],'COMPLETE_FULL_ASSIGNED_GRID')
            for row,arm in assignment['runs']:
                run=out/(row+'__'+arm);C.verify(run,'SCORE_SEAL.json')
                self.assertEqual(len(C.rows(run/'train.jsonl')),800)
                self.assertTrue((run/'adapter.800.pt').exists())
                self.assertTrue((run/'free.800.jsonl').exists())
                self.assertFalse((run/'free.400.jsonl').exists())


if __name__=='__main__':unittest.main()
