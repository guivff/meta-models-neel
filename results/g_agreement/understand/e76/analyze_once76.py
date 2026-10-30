"""Once-only CPU E76 regex floors on the verified complete pool; no judging calls."""
import json,time
import numpy as np
from common76 import *
from regex76 import score,validate_grid


def main():
    verify(ROOT,read(HERE/'CPU_SOURCE_SEAL.json'));verify(ROOT,read(HERE/'COMMAND_SEAL.json'))
    request=read(HERE/'LAUNCH_REQUEST.json');require(request['status']=='READY','Exact READY request required')
    pull=CACHE/'verified-pull';final=pull/'final';receipt=read(pull/'VERIFIED_PULL.json')
    require(receipt.get('issuer')=='integrator' and receipt.get('experiment')=='E76' and receipt.get('verified_complete') is True
        and receipt['output_seal_sha256']==sha(final/'OUTPUT_SEAL.json'),'Main Integrator verified complete pull required')
    output=read(final/'OUTPUT_SEAL.json');require(output['status']=='COMPLETE' and output['experiment']=='E76','Complete E76 pool required');verify(final,output)
    custody=read(final/'CUSTODY.json');a=custody['assignment']
    require(custody['request_sha256']==a['request_sha256']==sha(HERE/'LAUNCH_REQUEST.json')
        and custody['source_seal_sha256']==a['source_seal_sha256']==request['source_seal_sha256']==sha(HERE/'POD_SOURCE_SEAL.json')
        and custody['input_seal_sha256']==a['input_seal_sha256']==request['input_seal_sha256']==sha(CACHE/'pod_inputs/INPUT_SEAL.json'),'Custody pins mismatch')
    stopped=receipt.get('stage_released_epoch',receipt.get('provider_stopped_epoch'))
    require(type(stopped) in (int,float) and math.isfinite(stopped),'Actual E76 stage end required')
    require('stage_released_epoch' not in receipt or receipt.get('stage_release_verified') is True,
        'Existing-pod stage release must be verified and accounted by Main Integrator')
    require(a.get('issuer')=='integrator' and a.get('main_integrator_admitted') is True and a.get('track')=='Q'
        and a.get('gpu_count')==1 and a.get('pod_id')==receipt.get('pod_id') and 0<a['allocated_stage_seconds']<=CAP
        and a['stage_started_epoch']<=custody['completed_epoch']<=stopped<=a['absolute_deadline_epoch']
        <=min(a['stage_started_epoch']+a['allocated_stage_seconds'],a['provider_lease_deadline_epoch'],STOP),'Stage cap/provider/main custody violation')
    bank,items,selected,z=load_inputs();verify(final,read(final/'CALIBRATION_SEAL.json'))
    norms={l:np.load(final/f'REFERENCE_NORMS{l}.npy',allow_pickle=False) for l in (42,44)}
    raw={l:np.load(final/f'SELECTED_RAW{l}.npy',allow_pickle=False) for l in (42,44)}
    rebuilt,calibration=make_pools(bank,norms,raw,z);saved=read(final/'CALIBRATION.json')
    require(all(saved[k]==v for k,v in calibration.items()) and saved['sealed_before_any_native_readout'] is True,'Calibration does not reproduce')
    for (l,arm),h in rebuilt.items():require(np.array_equal(h,np.load(final/f'pool_{l}_{arm}.npy',allow_pickle=False)),'Sealed norm-matched pool does not reproduce')
    records=[json.loads(line) for reader in READERS for line in (final/f'{reader}.jsonl').read_text().splitlines()];validate_grid(records)
    expected_bank=calibration['source_bank_indices_by_pool_index']
    require(all(x['source_bank']==expected_bank[x['pool_index']] for x in records),'Source-bank covariate mismatch')
    catalog=read(HERE/'REGEX_CATALOG.json')
    # Do not load real reader outputs from any bank: only their prospective regex metadata.
    require(sha(HERE/'REGEX_CATALOG.json')==request['regex_catalog_sha256'],'Frozen regex catalog changed')
    dump(HERE/'REGEX_ANALYSIS.RUN_ONCE.json',{'experiment':'E76','started_epoch':time.time(),'output_seal_sha256':sha(final/'OUTPUT_SEAL.json')})
    out=HERE/'regex_20261027';out.mkdir(exist_ok=False)
    try:
        result=score(records,catalog);result.update(output_seal_sha256=sha(final/'OUTPUT_SEAL.json'),
            regex_catalog_sha256=sha(HERE/'REGEX_CATALOG.json'),input_seal_sha256=request['input_seal_sha256'],
            source_seal_sha256=request['source_seal_sha256'],stage_GPU_seconds=stopped-a['stage_started_epoch'],
            NLA_truncation=read(final/'NLA_TRUNCATION.json'))
        dump(out/'FLOOR_TABLE.json',result)
        lines=['# E76 per-row placebo floor','',result['caveat'],'',
            '| Bank / row | Reader | Pool | Any-value N [95% CI] | Signed S_regex [95% CI] |',
            '|---|---|---|---:|---:|']
        def fmt(v):return 'N/A' if v is None else f"{v['estimate']:.4f} [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]"
        for row in result['rows']:
            if row['regex_status']!='AVAILABLE':lines.append(f"| {row['bank']}/{row['row']} | — | unavailable | {row['reason']} | — |");continue
            for reader in READERS:
                for arm in ARMS:
                    v=row['readers'][reader][arm];lines.append(f"| {row['bank']}/{row['row']} | {reader} | {arm} | {fmt(v['N_any_value'])} | {fmt(v['S_regex'])} |")
        lines+=['','Source-bank conditional floors are in FLOOR_TABLE.json. Judged floors await separate authorisation (≤USD2); no judge was called.','']
        (out/'FLOOR_TABLE.md').write_text('\n'.join(lines))
        dump(out/'ANALYSIS_SEAL.json',{'experiment':'E76','status':'REGEX_COMPLETE_ONCE','files':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}})
        print('E76 CPU regex floor table complete; judged floors remain held.')
    except BaseException as exc:
        dump(out/'FAILURE.json',{'status':'STOP','error_type':type(exc).__name__,'guard_preserved':True});raise


if __name__=='__main__':main()
