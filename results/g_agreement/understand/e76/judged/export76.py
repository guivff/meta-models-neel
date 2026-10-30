"""Once-only blind E76 judged-floor export. Maps stay in ignored CPU cache."""
import os,subprocess,time
from core76 import *
from redaction76 import redact,strings,PATTERNS


def load_production():
    final=CACHE/'verified-pull/final';receipt=read(CACHE/'verified-pull/VERIFIED_PULL.json')
    require(receipt.get('issuer')=='integrator' and receipt.get('experiment')=='E76' and receipt.get('verified_complete') is True
        and receipt['output_seal_sha256']==PRODUCTION_SEAL==sha(final/'OUTPUT_SEAL.json'),'Exact verified complete E76 production pull')
    s=read(final/'OUTPUT_SEAL.json');require(s['experiment']=='E76' and s['status']=='COMPLETE','Complete production');verify(final,s)
    records=[json.loads(line) for reader in READERS for line in (final/f'{reader}.jsonl').read_text().splitlines()]
    validate_grid(records);return records


def main():
    verify(ROOT,read(JHERE/'CODE_SEAL.json'));verify(JHERE,read(JHERE/'ROW_INVENTORY_SEAL.json'))
    reg=read(JHERE/'ROW_INVENTORY.json');validate_registry(reg)
    source=JCACHE/'SOURCE_BINDING.PRIVATE.json';require(sha(source)==read(JHERE/'ROW_INVENTORY_SEAL.json')['source_binding_sha256'],'Original inventory sources')
    for p,h in read(source)['files'].items():require(sha(p)==h,'Inventory source changed')
    rubric=(JHERE/'RUBRIC.txt').read_text();require(sha(JHERE/'RUBRIC.txt')==RUBRIC_SHA,'Frozen section172 rubric')
    private=JCACHE/'GROUPING_MAP.PRIVATE.json'
    require(subprocess.run(['git','check-ignore','-q',str(private)],cwd=ROOT).returncode==0,'Private map must be ignored')
    dump(JHERE/'EXPORT.RUN_ONCE.json',{'experiment':'E76','started_epoch':time.time(),'row_inventory_sha256':sha(JHERE/'ROW_INVENTORY.json'),
        'source_production_seal_sha256':PRODUCTION_SEAL,'code_seal_sha256':sha(JHERE/'CODE_SEAL.json')})
    records=load_production();packet,mapping=build_export(records,reg)
    # Format/privacy preflight only; the registered runner later makes its own sealed judge copy.
    wire=[render(x,rubric) for x in packet];copied,audit=redact(wire,'E76',addresses=True)
    require(not any(re.search(p,s) for s in strings(copied) for p in PATTERNS),'Frozen decoded privacy guard requires coordinator review')
    blind=JCACHE/'blind';blind.mkdir()
    dump(blind/'JUDGE_PACKET.json',packet);(blind/'RUBRIC.txt').write_bytes((JHERE/'RUBRIC.txt').read_bytes())
    dump(blind/'BLIND_SEAL.json',{'experiment':'E76','n':len(packet),'rubric_sha256':RUBRIC_SHA,
        'row_inventory_sha256':sha(JHERE/'ROW_INVENTORY.json'),'production_output_seal_sha256':PRODUCTION_SEAL,
        'files':{n:sha(blind/n) for n in ('JUDGE_PACKET.json','RUBRIC.txt')}})
    fd=os.open(private,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as f:f.write(json.dumps({'experiment':'E76','CPU_only':True,'judge_or_pod_access_forbidden':True,
        'pairs':mapping,'blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),'row_inventory_sha256':sha(JHERE/'ROW_INVENTORY.json')},indent=2,sort_keys=True)+'\n')
    dump(JCACHE/'CPU_SEAL.json',{'experiment':'E76','CPU_only':True,'files':{n:sha(JCACHE/n) for n in ('GROUPING_MAP.PRIVATE.json','SOURCE_BINDING.PRIVATE.json')}})
    dump(JHERE/'EXPORT_MANIFEST.json',{'experiment':'E76','status':'BLIND_EXPORT_READY','records':len(packet),'rows':len(reg['rows']),
        'families':reg['binary_families'],'n_per_row_reader_pool':reg['n_per_row_reader_pool'],'sample_seed':20261028,
        'blind_directory':str(blind.relative_to(ROOT)),'blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),
        'CPU_grouping_map':str(private.relative_to(ROOT)),'CPU_grouping_map_sha256':sha(private),'CPU_seal_sha256':sha(JCACHE/'CPU_SEAL.json'),
        'rubric_sha256':RUBRIC_SHA,'original_text_and_value_bytes_preserved':True,'field_whitelist':['id','property','values','readout'],
        'privacy_preflight':{'status':'PASS','records_requiring_authorized_redaction':audit['redacted_records'],'source_packet_changed':False},
        'production_output_seal_sha256':PRODUCTION_SEAL,'regex_analysis_seal_sha256':REGEX_SEAL,'judge_calls':0,'judged_analysis_runs':0})
    print(json.dumps({'status':'BLIND_EXPORT_READY','records':len(packet),'rows':len(reg['rows']),'n_per_cell':reg['n_per_row_reader_pool']}))


if __name__=='__main__':main()
