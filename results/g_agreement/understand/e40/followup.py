"""E40 admission for the existing §131 rubric/decomposition, after a real PASS."""
import math
from dataclasses import asdict
from pathlib import Path
from e40_common import read,sha,verify_files
from e40_sae import FIXED_CONFIG


def verify_pass(folder,request_sha):
    folder=Path(folder)
    seal=verify_files(folder)
    required={'GATE_RESULT.json','TRAINING_RESULT.json','CALIBRATION.json',
              'CALIBRATION_SEAL.json','layer44.e40.sae.pt','GATE.RUN_ONCE.json'}
    if not required<=set(seal['files'])or seal.get('status')!='PASS':
        raise ValueError('complete E40 passing output seal required')
    gate=read(folder/'GATE_RESULT.json');training=read(folder/'TRAINING_RESULT.json')
    calibration=read(folder/'CALIBRATION.json')
    calibration_seal=verify_files(folder,'CALIBRATION_SEAL.json')
    if calibration_seal.get('status')!='COMPLETE' or calibration_seal.get('before_training_step')!=1:
        raise ValueError('calibration must be sealed before training step1')
    metric=(gate.get('metrics')or{}).get('filtered')or{}
    all_tokens=(gate.get('metrics')or{}).get('all_tokens')or{}
    excluded=(gate.get('metrics')or{}).get('excluded')or{}
    if (gate.get('experiment')!='E40'or gate.get('status')!='PASS'or gate.get('request_sha256')!=request_sha
            or gate.get('sample_sha256')!='dff73a3a83b76a6de4a5a2cbf2fe909a14a6888eaa9b91eeca6df849323fc593'
            or gate.get('primary_gate')!='filtered'or gate.get('sae_k')!=128
            or gate.get('calibration_sha256')!=sha(folder/'CALIBRATION.json')
            or gate.get('sae_checkpoint_sha256')!=sha(folder/'layer44.e40.sae.pt')
            or metric.get('d_model')!=5120 or metric.get('d_sae')!=65536
            or type(metric.get('n_tokens'))is not int or not 0<metric['n_tokens']<=50000 or all_tokens.get('n_tokens')!=50000
            or metric.get('n_tokens')!=50000-excluded.get('union',-1)
            or metric.get('passed')is not True or not 0<=metric.get('fvu',math.inf)<=.25
            or type(metric.get('dead_latents'))is not int or not 0<=10*metric['dead_latents']<65536):
        raise ValueError('registered filtered E40 gate PASS required')
    if (training.get('experiment')!='E40'or training.get('synthetic')is not False
            or training.get('training_tokens')!=100000000 or training.get('optimizer_updates')!=24415
            or training.get('config')!=asdict(FIXED_CONFIG)
            or training.get('data_passes')!=1 or training.get('recaptured_training_occurrences')!=0
            or training.get('checkpoint_selection')!='final_only'
            or training.get('sae_checkpoint_sha256')!=gate['sae_checkpoint_sha256']
            or training.get('calibration_sha256')!=gate['calibration_sha256']):
        raise ValueError('completed final100M checkpoint required')
    if (calibration.get('population_tokens')!=1000000 or calibration.get('heldout_statistics_used')is not False
            or calibration.get('position_zero_included')is not False or calibration.get('d_model')!=5120
            or calibration.get('outlier_threshold_raw_norm')!=10*calibration.get('median_raw_norm',math.nan)
            or not math.isfinite(calibration.get('scale',math.nan))or calibration['scale']<=0
            or not math.isclose(calibration['scale']*calibration['mean_raw_norm_after_outlier_exclusion'],math.sqrt(5120),rel_tol=1e-12)
            or gate.get('scale')!=calibration['scale']):
        raise ValueError('unchanged training-only calibration constants required')
    if training.get('normalization',{}).get('scale')!=calibration['scale']:
        raise ValueError('same scale required for training, gate and decomposition')
    return {'experiment':'E40','gate_result_sha256':sha(folder/'GATE_RESULT.json'),
            'sae_checkpoint_sha256':gate['sae_checkpoint_sha256'],'scale':calibration['scale'],
            'metrics':metric,'sae_k':128,'rubric_and_rules':'§131 + clarification1 unchanged'}
