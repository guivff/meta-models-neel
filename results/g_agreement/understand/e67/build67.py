"""Build E67 wave1 once, from sealed eligible sources; does not judge or analyse."""
from datetime import datetime,timezone
from packet67 import *
from sources67 import HERE,ROOT,Ledger,load_e49,load_e54,load_d4,pending_banks


def main():
    judge=HERE/'judge_wave1';private=HERE/'integrator_wave1'
    require(not (HERE/'BUILD.wave1.RUN_ONCE.json').exists(),'Preserve frozen wave1; never re-sample')
    rubric=judge/'CLAIMS_RUBRIC.txt';schema=judge/'CLAIMS_OUTPUT_SCHEMA.json'
    require(rubric.is_file() and schema.is_file(),'Freeze claims rubric/schema before source assembly')
    ledger=Ledger();pending=pending_banks()
    pools={**load_e49(ledger),**load_e54(ledger),**load_d4(ledger)}
    packets,mapping,inventory=build_packets(pools)
    dump(HERE/'BUILD.wave1.RUN_ONCE.json',{'experiment':'E67','created_utc':datetime.now(timezone.utc).isoformat(),
        'authority_commit':'bbefdae2','rubric_sha256':sha(rubric),'schema_sha256':sha(schema),'sample_seed':SAMPLE_SEED,'donor_seed':DONOR_SEED})
    for i,packet in enumerate(packets):
        with (judge/f'packet_{i+1:02d}.jsonl').open('x') as f:
            for record in packet:f.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
    dump(judge/'JUDGE_PACKET_SEAL.json',{'files':{p.name:sha(p) for p in sorted(judge.iterdir()) if p.is_file()},
         'record_fields':['id','prompt_text','readout'],'independent_packet_contexts_required':True})
    dump(private/'PAIRING_CONDITION_MAP.PRIVATE.json',{'experiment':'E67','integrator_only':True,'judge_or_pod_access_forbidden':True,
        'wave':1,'pairs':mapping,'packet_seal_sha256':sha(judge/'JUDGE_PACKET_SEAL.json')})
    dump(private/'SAMPLE_INVENTORY.PRIVATE.json',{'experiment':'E67','strata':inventory,'sample_seed':SAMPLE_SEED,'donor_seed':DONOR_SEED,
        'numpy_version':np.__version__,
        'shuffle_streams':'SeedSequence([20261028,3]) and SeedSequence([20261028,4])',
        'assignment_stream':'SeedSequence([20261028,1])','opaque_id_stream':'SeedSequence([20261028,2])',
        'D4_balance':'99 readouts per reader;33 each arm','no_readout_content_filtering':True})
    dump(private/'SOURCE_BINDING.PRIVATE.json',{'experiment':'E67','eligible_once_analysis_seals':ledger.analyses,
        'files_sha256':ledger.files,'E56_E57':pending,'shared_pilot_readouts_opened':False,
        'original_analysis_or_model_rerun':False})
    dump(private/'INTEGRATOR_SEAL.json',{'experiment':'E67','integrator_only':True,'judge_or_pod_access_forbidden':True,
        'files':{p.name:sha(p) for p in sorted(private.iterdir()) if p.is_file()}})
    dump(HERE/'WAVE1_MANIFEST.json',{'experiment':'E67','status':'FROZEN_PACKETS_READY_FOR_INTEGRATOR',
        'authority_commit':'bbefdae2','wave':1,'CPU_only':True,'judge_calls':0,'registered_analysis_runs':0,
        'sampled_readouts':len(mapping),'judge_records':sum(map(len,packets)),'packets':2,'records_per_packet':list(map(len,packets)),
        'strata':[{'bank':x['bank'],'reader':x['reader'],'eligible':x['eligible_items'],'sampled':x['sampled_items'],
                   'truncation_cohort':x['truncation_cohort']} for x in inventory],
        'judge_directory':str(judge.relative_to(ROOT)),'judge_packet_seal_sha256':sha(judge/'JUDGE_PACKET_SEAL.json'),
        'integrator_only_directory':str(private.relative_to(ROOT)),'integrator_seal_sha256':sha(private/'INTEGRATOR_SEAL.json'),
        'E56_E57':pending,'scope_of_future_additions':'Separate sealed wave after each bank once-only analysis seals; do not change wave1.'})
    print(json.dumps({'status':'FROZEN','sampled_readouts':len(mapping),'judge_records':sum(map(len,packets)),
        'per_stratum':[(x['bank'],x['reader'],x['sampled_items']) for x in inventory],
        'judge_packet_seal_sha256':sha(judge/'JUDGE_PACKET_SEAL.json')}))


if __name__=='__main__':main()
