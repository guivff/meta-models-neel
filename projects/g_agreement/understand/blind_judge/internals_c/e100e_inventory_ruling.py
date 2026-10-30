"""§226 ebafaa393: field-copy inventory only; no pairing, scorer or model call."""
import argparse
import json
import subprocess
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from .transport import ROOT
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require

MISSING='MISSING'
PAIRING_COMMIT='4b78bb97e65d6619410dc5af59662e05ea3eb471'
ROW_FIELDS={'id':'id','row':'row','split':'split','donor_id':'donor_id',
            'original_value':'source_value','target_value':'donor_value'}


def copy_inventory(labels,manifest,pairing_commit,eligible):
    """Rename literal source fields; never derive a value, intervention or proof flag."""
    rows=[{target:deepcopy(x.get(source,MISSING)) for target,source in ROW_FIELDS.items()} for x in labels] if eligible['labels'] else MISSING
    top=dict(experiment='E100e',pairing_seed=manifest.get('seed',MISSING)if eligible['manifest']else MISSING,
        reader_blocks=deepcopy(manifest.get('read_blocks',MISSING))if eligible['manifest']else MISSING,
        intervention=deepcopy(manifest.get('intervention',MISSING))if eligible['manifest']else MISSING,
        pre_gpu_pairing_committed=deepcopy(manifest.get('pre_gpu_pairing_committed',MISSING))if eligible['manifest']else MISSING,
        pairing_commit=pairing_commit if eligible['pairing_commit']else MISSING)
    missing=[k for k,v in top.items()if v==MISSING]
    if rows==MISSING:missing.append('INVENTORY.json')
    else:
        missing.extend('INVENTORY.json['+str(i)+'].'+k for i,x in enumerate(rows)for k,v in x.items()if v==MISSING)
    return rows,top,missing


def build():
    original=ROOT.parent/'outputs/e100e-inputs-v1';public=original/'inputs';labels_root=original/'cpu_only'
    label_seal=labels_root/'LABEL_SEAL.json';verify(label_seal,'24b4bb2a9082269d75c57c1e14c5e91616d03c77429c9a3b78ba72702186f2a7')
    input_seal=public/'INPUT_SEAL.json';verify(input_seal,'9b944aedc44534b58b8e6fc4a319f00bf391423f0498dfcfcc6481c41d9c5bc5')
    require(read(label_seal)['input_sha256']==sha(input_seal),'same original labels and runner input')
    native=ROOT.parent/'wt-wmech/cache/g_agreement/understand/analysis402_verified/E100e/a2/out/OUTPUT_SEAL.json'
    ns=verify(native,'7ca71f4c14a3b9ec992bedf461d936525fe925e70da5606f108d0a684ee2d0cf')
    require(ns['input_sha256']==sha(input_seal),'attempt2 original unchanged input')
    jobs=[(native.parent/n)for n in ns['files']if n.startswith('jobs/')and n.endswith('.json')and not n.endswith('STAGE_SEAL.json')]
    first=min(jobs,key=lambda p:p.stat().st_mtime_ns);cutoff=first.stat().st_mtime_ns
    path='results/g_agreement/understand/e100e/INPUT_BINDING.json'
    blob=subprocess.check_output(['git','show',PAIRING_COMMIT+':'+path],cwd=ROOT)
    bound=json.loads(blob);require(bound['label_seal_sha256']==sha(label_seal)and bound['input_sha256']==sha(input_seal),
        'pre-output committed input binding includes exact original pairing label seal')
    commit_time=subprocess.check_output(['git','show','-s','--format=%cI',PAIRING_COMMIT],cwd=ROOT,text=True).strip()
    commit_epoch=datetime.fromisoformat(commit_time).timestamp()
    sources={}
    for name,p in [('label_seal',label_seal),('labels',labels_root/'LABELS.json'),('input_seal',input_seal),
                   ('manifest',public/'MANIFEST.json'),('runner_items',public/'items.json')]:
        at=p.stat().st_mtime_ns
        sources[name]=dict(path=str(p),sha256=sha(p),observed_original_file_mtime_ns=at,
            observed_original_file_mtime_utc=datetime.fromtimestamp(at/1e9,timezone.utc).isoformat(),
            timestamp_precedes_attempt2_first_output=at<cutoff,
            hash_bound_by_pre_output_input_commit=PAIRING_COMMIT,
            input_commit_utc=datetime.fromtimestamp(commit_epoch,timezone.utc).isoformat())
    sources['pairing_commit']=dict(path=path,commit=PAIRING_COMMIT,commit_timestamp=commit_time,
        committed_blob_sha256=__import__('hashlib').sha256(blob).hexdigest(),
        commit_precedes_attempt2_first_output=int(commit_epoch*1e9)<cutoff,
        meaning='Git metadata of original input-binding commit; blob binds exact label seal24b4bb2a and input9b944aed')
    eligible=dict(labels=sources['labels']['timestamp_precedes_attempt2_first_output'],
        manifest=sources['manifest']['timestamp_precedes_attempt2_first_output'],
        pairing_commit=sources['pairing_commit']['commit_precedes_attempt2_first_output'])
    labels=read(labels_root/'LABELS.json');manifest=read(public/'MANIFEST.json')
    require(len(labels)==168 and len({x['id']for x in labels})==168,'whole original168 labels, no new sample')
    rows,top,missing=copy_inventory(labels,manifest,PAIRING_COMMIT,eligible)
    for k in ('H42.npy','H44.npy'):require(k in read(input_seal)['files'],'actual pre-output reader carrier files bound')
    dest=ROOT/'results/g_agreement/understand/e100e/inventory_ruling_cpu';dest.mkdir(exist_ok=True)
    (dest/'.gitignore').write_text('INVENTORY.json\nFIELD_PROVENANCE.PRIVATE.json\n')
    if(dest/'INVENTORY_SEAL.json').exists():
        verify(dest/'INVENTORY_SEAL.json',sha(dest/'INVENTORY_SEAL.json'))
        require(read(dest/'INVENTORY.json')==rows,'immutable original source-copy inventory');return dest
    write(dest/'INVENTORY.json',rows)
    fields={k:dict(source='labels',key=v)for k,v in ROW_FIELDS.items()}
    write(dest/'FIELD_PROVENANCE.PRIVATE.json',[dict(inventory_index=i,label_source_index=i,fields=fields)for i in range(len(labels))])
    provenance=dict(authority_commit='ebafaa393',reformatted_after_attempt2_output=True,
        new_inventory_is_not_claimed_pre_output=True,at_utc=datetime.now(timezone.utc).isoformat(),
        cutoff=dict(original_native_seal=str(native),original_native_seal_sha256=sha(native),
            earliest_retained_original_job=str(first),sha256=sha(first),mtime_ns=cutoff,
            utc=datetime.fromtimestamp(cutoff/1e9,timezone.utc).isoformat(),
            precision_note='retained rsync source mtime is whole-second precision; not claimed original nanosecond precision',
            used_for_cutoff_only_no_readout_values_consumed=True),sources=sources,
        field_mapping=dict(pairing_seed='MANIFEST.json.seed',reader_blocks='MANIFEST.json.read_blocks',
            pairing_commit='Git commit metadata of original INPUT_BINDING.json binding the exact label/input seals',
            intervention='MISSING: no intervention field in allowed pre-output manifest; condition=transplant retained separately, not translated to a formula',
            pre_gpu_pairing_committed='MISSING: no literal proof flag in allowed pre-output source; not invented from chronology',
            item_fields=fields),source_condition_literal=manifest.get('condition',MISSING),
        no_pairing_rng_or_target_computation=True,no_model_calls=True,no_analysis_or_guard=True)
    write(dest/'PROVENANCE.json',provenance)
    write(dest/'INVENTORY_SEAL.json',dict(top,status='REFORMATTED_WITH_MISSING_FIELDS'if missing else'REFORMATTED_SOURCE_COPY',
        labels_cpu_only=True,n=168,missing_required_fields=missing,
        S_estimate_eligible=False if missing else'PENDING_RQ_PROVENANCE_VERIFICATION',
        ruling_disposition='descriptive item readouts only, NO S estimate'if missing else'R-Q verifies provenance before any guard',
        provenance=provenance,files={n:sha(dest/n)for n in ['INVENTORY.json','FIELD_PROVENANCE.PRIVATE.json','PROVENANCE.json']}))
    return dest


if __name__=='__main__':
    argparse.ArgumentParser(description=__doc__).parse_args();d=build();print('E100e source-copy inventory '+sha(d/'INVENTORY_SEAL.json')+' missing='+','.join(read(d/'INVENTORY_SEAL.json')['missing_required_fields']))
