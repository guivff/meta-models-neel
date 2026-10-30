"""Read-only export audit: reproduces frozen selection, no judge calls or outcome scoring."""
from core76 import *
from export76 import load_production
from redaction76 import redact


def audit():
    verify(ROOT,read(JHERE/'CODE_SEAL.json'));verify(JHERE,read(JHERE/'ROW_INVENTORY_SEAL.json'))
    m=read(JHERE/'EXPORT_MANIFEST.json');reg=read(JHERE/'ROW_INVENTORY.json');blind=ROOT/m['blind_directory']
    require(sha(blind/'BLIND_SEAL.json')==m['blind_seal_sha256'],'Original blind pin');verify(blind,read(blind/'BLIND_SEAL.json'))
    verify(JCACHE,read(JCACHE/'CPU_SEAL.json'));require(sha(JCACHE/'CPU_SEAL.json')==m['CPU_seal_sha256'],'CPU map seal pin')
    require(sha(JCACHE/'GROUPING_MAP.PRIVATE.json')==m['CPU_grouping_map_sha256'],'Private map pin')
    sources=read(JCACHE/'SOURCE_BINDING.PRIVATE.json')
    for p,h in sources['files'].items():require(sha(p)==h,'Frozen bank analysis/definition changed')
    packet=read(blind/'JUDGE_PACKET.json');private=read(JCACHE/'GROUPING_MAP.PRIVATE.json')
    require(private['CPU_only'] is True and private['judge_or_pod_access_forbidden'] is True,'Private CPU custody')
    validate_export(packet,private['pairs'],reg)
    expected,mapping=build_export(load_production(),reg)
    require(packet==expected and mapping==private['pairs'],'Frozen seeds, source linkage, sampling or text changed')
    converted=JCACHE/'converted';cs=read(converted/'PACKET_SEAL.json');verify(converted,cs)
    require(cs['source_seal_sha256']==sha(blind/'BLIND_SEAL.json') and cs['source_packet_sha256']==sha(blind/'JUDGE_PACKET.json')
        and cs['rubric_sha256']==RUBRIC_SHA and read(converted/'PACKET.json')==packet,'Published converter changed field bytes')
    _,redaction=redact([render(x,(JHERE/'RUBRIC.txt').read_text()) for x in packet],'E76',addresses=True)
    require(redaction['redacted_records']==m['privacy_preflight']['records_requiring_authorized_redaction'],'Privacy preflight changed')
    folder=HERE/'regex_20261027';require(sha(folder/'ANALYSIS_SEAL.json')==REGEX_SEAL,'Original regex seal changed');verify(folder,read(folder/'ANALYSIS_SEAL.json'))
    return {'experiment':'E76_JUDGED','status':'PASS','rows':len(reg['rows']),'binary_families':reg['binary_families'],
        'n_per_row_reader_pool':reg['n_per_row_reader_pool'],'expanded_records':len(packet),'uniform_cap':len(packet)<=5000,
        'seeds_and_verbatim_records_reproduced':True,'converter_field_bytes_preserved':True,'frozen_source_analyses_verified':True,
        'private_map_only_in_ignored_cache':True,'authorized_redaction_pairs':redaction['redacted_records'],
        'production_output_seal_sha256':PRODUCTION_SEAL,'regex_analysis_seal_sha256':REGEX_SEAL,
        'blind_seal_sha256':sha(blind/'BLIND_SEAL.json'),'converted_packet_seal_sha256':sha(converted/'PACKET_SEAL.json'),
        'judgments_opened':False,'judge_calls':0,'judged_floor_analysis_runs':0}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);a=p.parse_args();result=audit()
    if a.out:dump(a.out,result)
    print(json.dumps(result))
