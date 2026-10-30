"""Integrator once-only CPU judged floors after sealed terminal judgments; no API calls."""
import time
from core76 import *
from redaction76 import redact


def load_sealed_inputs():
    verify(ROOT,read(JHERE/'CODE_SEAL.json'));verify(JHERE,read(JHERE/'ANALYSIS_COMMAND_SEAL.json'))
    spec=read(JHERE/'ANALYSIS_SPEC.json');manifest=read(JHERE/'EXPORT_MANIFEST.json')
    require(sha(JHERE/'EXPORT_MANIFEST.json')==spec['export_manifest_sha256'],'Export manifest pin')
    reg=read(JHERE/'ROW_INVENTORY.json');verify(JHERE,read(JHERE/'ROW_INVENTORY_SEAL.json'))
    blind=ROOT/manifest['blind_directory'];require(sha(blind/'BLIND_SEAL.json')==manifest['blind_seal_sha256'],'Blind export pin');verify(blind,read(blind/'BLIND_SEAL.json'))
    packet=read(blind/'JUDGE_PACKET.json');require(sha(blind/'RUBRIC.txt')==RUBRIC_SHA,'Frozen rubric pin')
    key=JCACHE/'GROUPING_MAP.PRIVATE.json';require(sha(key)==manifest['CPU_grouping_map_sha256'],'Private grouping pin')
    private=read(key);require(private['CPU_only'] is True and private['judge_or_pod_access_forbidden'] is True and private['blind_seal_sha256']==sha(blind/'BLIND_SEAL.json'),'CPU private custody')
    mapping=private['pairs'];validate_export(packet,mapping,reg)
    regex_folder=HERE/'regex_20261027';require(sha(regex_folder/'ANALYSIS_SEAL.json')==REGEX_SEAL,'Exact existing complete regex floor seal')
    verify(regex_folder,read(regex_folder/'ANALYSIS_SEAL.json'));regex=read(regex_folder/'FLOOR_TABLE.json')
    require(regex['output_seal_sha256']==PRODUCTION_SEAL,'Regex and judged floors must use same sealed production')
    converted=JCACHE/'converted';cs=read(converted/'PACKET_SEAL.json');verify(converted,cs)
    require(cs['experiment']=='E76' and cs['source_seal_sha256']==sha(blind/'BLIND_SEAL.json')
        and cs['source_packet_sha256']==sha(blind/'JUDGE_PACKET.json') and cs['rubric_sha256']==RUBRIC_SHA
        and read(converted/'PACKET.json')==packet and sha(converted/'RUBRIC.txt')==RUBRIC_SHA,'Lossless original/converted custody')
    pull=JCACHE/'terminal';final=pull/'final';receipt=read(pull/'VERIFIED_PULL.json')
    require(receipt.get('issuer')=='integrator' and receipt.get('experiment')=='E76_JUDGED' and receipt.get('verified_complete') is True and receipt.get('privacy_and_budget_custody_verified') is True
        and receipt.get('n')==manifest['records'] and receipt['terminal_seal_sha256']==sha(final/'RESULT_SEAL.json') and receipt['converted_packet_seal_sha256']==sha(converted/'PACKET_SEAL.json')
        and receipt['original_blind_seal_sha256']==sha(blind/'BLIND_SEAL.json'),'Integrator verified terminal custody')
    seal=read(final/'RESULT_SEAL.json');verify(final,seal)
    require(seal['bank']=='E76' and seal['channel']=='placebo' and seal['status']=='TERMINAL_BLIND_GRID_NO_ANALYSIS'
        and seal['packet_seal_sha256']==sha(converted/'PACKET_SEAL.json'),'Exact complete terminal grid')
    require({'JUDGMENTS.json','JUDGE_COPY.json','PATH_REDACTION_AUDIT.json','START.json'}<=set(seal['files']),'Complete redaction and judgment custody')
    require(read(final/'START.json')['packet_seal_sha256']==sha(converted/'PACKET_SEAL.json'),'Terminal start binding')
    saved=read(final/'PATH_REDACTION_AUDIT.json');require(saved.get('authority')=='79f63fe0' and saved.get('address_authority') in (None,'25c32f25'),'Authorized redaction only')
    expected,audit=redact([render(x,(JHERE/'RUBRIC.txt').read_text()) for x in packet],'E76',addresses=saved.get('address_authority')=='25c32f25')
    require(saved==audit and read(final/'JUDGE_COPY.json')==expected,'Exact authorized judge-copy bytes/audit')
    terminal=read(final/'JUDGMENTS.json');require(len(terminal)==manifest['records'],'Complete expanded terminal grid')
    return reg,mapping,regex,terminal,expected,{x['id'] for x in audit['affected']},sha(final/'RESULT_SEAL.json')


def main():
    # This lock is consumed only after exact custody validates, before any category join/score.
    require(not (JHERE/'JUDGED_ANALYSIS.RUN_ONCE.json').exists(),'Preserve consumed once-only judged analysis')
    reg,mapping,regex,terminal,copied,redacted,terminal_sha=load_sealed_inputs()
    dump(JHERE/'JUDGED_ANALYSIS.RUN_ONCE.json',{'experiment':'E76','started_epoch':time.time(),'terminal_seal_sha256':terminal_sha,
        'row_inventory_sha256':sha(JHERE/'ROW_INVENTORY.json'),'code_seal_sha256':sha(JHERE/'CODE_SEAL.json')})
    out=JHERE/'analysis_once_20261028';out.mkdir(exist_ok=False)
    try:
        codes=join_terminal(terminal,copied);result=analyze(mapping,codes,reg,regex,redacted)
        result.update(terminal_seal_sha256=terminal_sha,production_output_seal_sha256=PRODUCTION_SEAL,regex_analysis_seal_sha256=REGEX_SEAL,
            row_inventory_sha256=sha(JHERE/'ROW_INVENTORY.json'),complete_regex_floor_file=str((HERE/'regex_20261027/FLOOR_TABLE.json').relative_to(ROOT)))
        dump(out/'JUDGED_FLOOR_TABLE.json',result)
        rows={(x['bank'],x['row']):x for x in result['rows']}
        lines=['# E76 judged floors beside sealed complete regex floors','',
            'Judged S uses the frozen independent pseudo-truth; it is descriptive. Regex floors retain all500 vectors per reader/pool. UNPARSEABLE is excluded and counted.','',
            '| Bank / row | Reader | Pool | Judged vectors / pairs | UNPARSEABLE | Redacted pairs | S [95% CI] | Any-value N [95% CI] | S without redacted | N without redacted | Full regex S | Full regex N |',
            '|---|---|---|---:|---:|---:|---|---|---|---|---|---|']
        def fmt(v):return 'N/A' if v is None else f"{v['estimate']:.4f} [{v['ci95'][0]:.4f}, {v['ci95'][1]:.4f}]" if v['ci95'] is not None else f"{v['estimate']:.4f} [undefined CI]"
        for rr in regex['rows']:
            for reader in READERS:
                for pool in ARMS:
                    cell=rows.get((rr['bank'],rr['row']),{}).get('readers',{}).get(reader,{}).get(pool)
                    full=rr['readers'][reader][pool] if rr['regex_status']=='AVAILABLE' else None
                    if cell:
                        a=cell['judged_full'];b=cell['judged_without_redacted']
                        values=[f"{a['n_sampled_vectors']} / {a['n_pairs']}",str(a['UNPARSEABLE']),str(cell['redacted_pairs']),fmt(a['S']),fmt(a['N_any_value']),fmt(b['S']),fmt(b['N_any_value'])]
                    else:values=['not selected','—','—','—','—','—','—']
                    lines.append('| '+' | '.join([rr['bank']+'/'+rr['row'],reader,pool]+values+[fmt(full['S_regex']) if full else 'N/A',fmt(full['N_any_value']) if full else 'N/A'])+' |')
        lines+=['','Judged-row exclusions are listed in JUDGED_FLOOR_TABLE.json and ROW_INVENTORY.json. No registered verdict is changed.','']
        (out/'JUDGED_FLOOR_TABLE.md').write_text('\n'.join(lines))
        dump(out/'ANALYSIS_SEAL.json',{'experiment':'E76_JUDGED','status':'COMPLETE_ONCE','terminal_seal_sha256':terminal_sha,
            'files':{p.name:sha(p) for p in sorted(out.iterdir()) if p.is_file()}})
        print('E76 once-only judged floors sealed; original regex floor unchanged.')
    except BaseException as exc:
        dump(out/'FAILURE.json',{'error_type':type(exc).__name__,'guard_preserved':True});raise


if __name__=='__main__':main()
