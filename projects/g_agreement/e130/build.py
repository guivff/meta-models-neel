"""CPU-only E130 packet; readout artifact copied byte-identically without interpreting text."""
from datetime import datetime,timezone
from pathlib import Path
import shutil,tarfile
from projects.g_agreement.e100.contract import read,write,sha

PARENT_SEAL='114e18fb5be7d53a2591f80262f46ce83c631384f512ea0a491968d4ad5f77af'
PRIOR_SEAL='6235fa58c1e0e003ed13998d3fc42b7e5590ac390a9e423c80b53f26ca2333ad'


def build(parent,prior,out):
    parent,prior,out=map(Path,(parent,prior,out))
    if sha(parent/'INPUT_SEAL.json')!=PARENT_SEAL or sha(prior/'INPUT_SEAL.json')!=PRIOR_SEAL:
        raise ValueError('original E85 and label-free sealed native-source inputs')
    ps,rs=read(parent/'INPUT_SEAL.json'),read(prior/'INPUT_SEAL.json')
    if sha(parent/'items.json')!=ps['files']['items.json']or sha(prior/'READOUTS.json')!=rs['files']['READOUTS.json']:
        raise ValueError('original sealed source bytes')
    items=read(parent/'items.json');dev=[x for x in items if x['split']=='dev'];test=[x for x in items if x['split']=='test']
    if len(dev)!=200 or len(test)!=400 or len({x['id']for x in items})!=600:
        raise ValueError('original E85 split200/400')
    if any(x['read_index']!=len(x['ids'])-1 or len(x['ids'])<32 for x in items):
        raise ValueError('original last-token read-site/span32')
    out.mkdir(parents=True,exist_ok=False)
    write(out/'DEV_SPANS.json',[dict(id=x['id'],ids=x['ids'][-32:])for x in dev])
    write(out/'TEST_ORDER.json',[x['id']for x in test])
    shutil.copyfile(prior/'READOUTS.json',out/'READOUTS.json')
    write(out/'MANIFEST.json',dict(experiment='E130',authority='3c051915551bc9ad1f1bd9ec53c04a894273be58',dev=200,test=400,reconstruction_rows=1000,
       conditions=['span_32','ol_readout','ol_readout_shuffled'],layer=44,variant=['li','ln'],batch=16,shuffle_seed=20261031,readout_token_cap=256,
       labels_included=False,source_E85_input_sha256=PARENT_SEAL,source_native_packet_sha256=PRIOR_SEAL,
       source_E85_native_output_sha256=rs['source_native_seal_sha256'],raw_activation_reference=False,whitener_required=False,
       model_calls_by_builder=0,readout_text_interpreted_by_builder=False))
    write(out/'INPUT_SEAL.json',dict(experiment='E130',status='SEALED_CONDITIONAL_ONLY',sealed_at_utc=datetime.now(timezone.utc).isoformat(),
       labels_included=False,files={p.name:sha(p)for p in out.iterdir()}))
    return dict(input_root=str(out.resolve()),input_sha256=sha(out/'INPUT_SEAL.json'),status='SEALED_CONDITIONAL_ONLY',model_calls=0)
