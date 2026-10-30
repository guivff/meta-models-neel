"""Optional E49 inference only: staged, label-free, frozen before E50 launch."""
from pathlib import Path
import numpy as np
import contract as C

ROWS=('pronoun_referent','chased_role','container_after_move','holder_after_handovers',
      'arith_carry','arith_compare','branch_taken','var_type_at_use','asserted_vs_hypothetical',
      'negation_scope','instruction_provenance')

def load_secondary(path,assignment):
    binding=assignment['secondary']
    if binding.get('status')=='NOT_FROZEN_AT_LAUNCH':
        if path is not None:raise ValueError('unexpected secondary input')
        if binding.get('issuer')!='integrator' or binding.get('checked_before_launch') is not True:
            raise ValueError('Integrator must check conditional bank availability before launch')
        return None
    if binding.get('status')!='FROZEN_VERIFIED' or path is None:raise ValueError('explicit E49 frozen/absent decision required')
    path=Path(path);seal=C.verify(path)
    required={'test.jsonl','test.acts44.npy','templates.json','PROVENANCE.json'}
    if (set(seal['files'])!=required or {p.name for p in path.iterdir()}!=required|{'INPUT_SEAL.json'}
            or C.sha(path/'INPUT_SEAL.json')!=binding['input_seal_sha256']):raise ValueError('exact sealed label-free E49 input required')
    provenance=C.read(path/'PROVENANCE.json')
    if (provenance.get('experiment')!='E49' or provenance.get('frozen') is not True
            or provenance.get('bank_seal_sha256')!=binding['bank_seal_sha256']
            or provenance.get('capture_output_seal_sha256')!=binding['capture_output_seal_sha256']
            or provenance.get('frozen_before_epoch',float('inf'))>assignment['provider_created_epoch']
            or provenance.get('activation_layer')!=44 or provenance.get('items_split')!='test'):
        raise ValueError('verified frozen E49 test capture required')
    test=C.rows(path/'test.jsonl');acts=np.load(path/'test.acts44.npy',allow_pickle=False);specs=C.read(path/'templates.json')
    if (set(specs)!=set(ROWS) or len(test)!=924 or len({r['id'] for r in test})!=924
            or any(set(r)!={'id','feature'} for r in test) or acts.shape!=(924,5120) or not np.isfinite(acts).all()
            or any(sum(r['feature']==row for r in test)!=84 for row in ROWS)
            or any(len(s['olens'])!=2 or any(len(p)!=2 or any(not isinstance(v,str) or not v for v in p) for p in s['olens']) for s in specs.values())):
        raise ValueError('all eleven frozen semantic tracked-state rows required')
    return test,acts,specs
