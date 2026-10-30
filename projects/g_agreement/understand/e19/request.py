"""Create an E19 request only after the dev direction freeze is committed."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from projects.g_agreement.blindspot import protocol as P
from .freeze import load_freeze
from .inputs import load
from .run import verify_committed_freeze, CAP, SETUP, schedule, source_hashes


def create(inputs,freeze,tests,out,freeze_commit):
    inputs,freeze,tests,out=map(Path,(inputs,freeze,tests,out))
    if out.exists():raise ValueError('request already exists')
    sources=source_hashes();commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P.ROOT,text=True).strip()
    for name,digest in sources.items():
        if hashlib.sha256(subprocess.check_output(['git','show',commit+':'+name],cwd=P.ROOT)).hexdigest()!=digest:
            raise ValueError('uncommitted runtime source: '+name)
    directions=verify_committed_freeze(freeze,freeze_commit)
    data=load(inputs)
    frozen,_=load_freeze(freeze)
    if frozen['source']['e3_input_seal_sha256']!=data['provenance']['source_e3_input_seal_sha256']:raise ValueError('E3 input/freeze lineage mismatch')
    validation=json.loads(tests.read_text())
    if validation.get('status')!='PASS' or validation.get('gpu_hours')!=0:raise ValueError('passing CPU tests required')
    binding={'input_seal_sha256':P.sha(inputs/'INPUT_SEAL.json'),'freeze_seal_sha256':P.sha(freeze/'FREEZE_SEAL.json'),'freeze_commit':freeze_commit}
    registration=P.ROOT/'results/g_agreement/understand/e19/REGISTRATION.md'
    rec={'experiment':'E19','status':'LAUNCH_REQUESTED_PENDING_INTEGRATOR_ASSIGNMENT_AND_WARMED_GATE',
         'source_commit':commit,'source_files':sources,'owner':'W-internals','branch':'r/blindspot-internals',
         'registration_commit':'409690ee','registration_snapshot_sha256':P.sha(registration),
         'operational_ruling_commit':'17942898',
         'input_directory':str(inputs.resolve()),'freeze_directory':str(freeze.resolve()),**binding,
         'scope':{'reader':'Oracle lens','rows':list(directions),'items':len(data['items']),'test_items_per_row':84,'production_units':len(list(schedule(data))),
                  'alphas':[0,-1,1,-2,2,-4,4],'controls':['three equal-norm random directions','content direction on four state rows','own direction with random-donor activation']},
         'continuation_scope':'Original E15 dev-valid pairs on four structure rows; prose_sentiment NOT_APPLICABLE_NO_FROZEN_E15_PAIRS (E15 never registered one). All five asked/projection endpoints retained.',
         'memory':'One Oracle base+adapter load; inference only,16 activations/32 candidates; no generation/backpropagation',
         'model_environment':'/weights/venv-kernels','resources':{'gpu_count':1,'gpu_memory_gib_at_least':80},
         'cap_rule':'min(1.5F+360,9000) seconds continuously from first warm-up; setup1500 seconds',
         'warmed_gate':'One discarded warm-up then median of three timed full-size units per row, alpha4, both endpoints, serialization/fsync/hash included; all controls/items forecast; no subsampling if gate fails',
         'assignment_required':{'experiment':'E19','pod_id':'INTEGRATOR_MUST_FILL','gpu_count':1,'max_science_seconds':CAP,'setup_allowance_seconds':SETUP,
                                'external_hard_stop_verified':True,'hard_deadline_utc':'INTEGRATOR_MUST_FILL_TIMEZONE_AWARE','source_files':sources,**binding},
         'launch_argv':['/weights/venv-kernels/bin/python','-m','projects.g_agreement.understand.e19.run',
                        '--inputs','STAGED_E19_INPUTS','--freeze','STAGED_COMMITTED_FREEZE','--freeze-commit',freeze_commit,
                        '--assets','PINNED_ASSETS_JSON','--assignment','ASSIGNMENT_JSON','--out','NEW_E19_OUTPUT'],
         'cpu_tests_receipt':str(tests),'cpu_tests_sha256':P.sha(tests),
         'operations':'Integrator pushes and operates pod. Stage only sealed label-free E19 inputs and committed direction freeze. Preserve original E3/E4 runs and the first E19 NO_GO attempt. One relaunch under 17942898; if the warmed forecast does not fit, E19 closes INCOMPLETE with no scope cuts. Seal scores before analysis; no implicit retry.',
         'test_scoring_performed':False}
    P.dump(out,rec);return rec


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('inputs','freeze','tests','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--freeze-commit',required=True)
    a=p.parse_args();r=create(**vars(a));print(json.dumps({'status':r['status'],'source_commit':r['source_commit'],'freeze_commit':r['freeze_commit']}))

if __name__=='__main__':main()
