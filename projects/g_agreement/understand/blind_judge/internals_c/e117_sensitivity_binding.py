"""Copy-only eight-record privacy audit -> original source-ID map, no scoring."""
import hashlib
from .transport import ROOT,HERE
from .runner import CACHE
from projects.g_agreement.readerbench.io import read,write,sha,verify
from projects.g_agreement.readerbench.scoring import require


def project(joins,audit,units,original,descriptors,n=3024,affected_n=8):
    js={j['id']:j for j in joins};us={u['id']:u for u in units};affected={a['id']:a for a in audit['affected']}
    require(len(joins)==len(js)==len(units)==len(us)==n and set(js)==set(us),'full unique original source/dispatch inventory')
    require(audit['bank']=='E117' and audit['n_records']==n and audit['redacted_records']==len(affected)==len(audit['affected'])==affected_n,'exact original affected audit census')
    require(set(original)==set(affected) and set(affected)<=set(js),'no omitted/invented affected IDs')
    rows=[]
    for ident,a in sorted(affected.items()):
        j=js[ident];u=us[ident];d=descriptors[j['descriptor_ref_id']]
        require(j['part']=='main' and j['item_id']==d['source_id'] and j['row']==d['row'] and j['source_bank']==d['source_bank'],'original source item/row/family identity')
        require(hashlib.sha256(original[ident].encode()).hexdigest()==a['original_readout_sha256'] and hashlib.sha256(u['data']['readout'].encode()).hexdigest()==a['judge_readout_sha256'],'both unchanged UTF8 text hashes')
        rows.append(dict(judgment_id=ident,original_e113_item_id=j['item_id'],original_bank_item_id=d['original_source_id'],row=j['row'],alpha=j['alpha'],arm=j['arm'],native_readout_id=j['native_id'],native_text_ref=j['source_ref'],descriptor_ref_id=j['descriptor_ref_id'],original_packet_indices=d['original_packet_indices'],original_private_key_indices=d['original_key_indices'],source_bank=d['source_bank'],original_audit=a))
    return rows


def build():
    for n,h in read(HERE/'E117_SENSITIVITY_BINDING_SOURCE_SEAL.json')['files'].items():require(sha(ROOT/n)==h,'published copy-only source-map helper')
    root=CACHE/'E117';u=root/'native_units/UNIT_SEAL.json';o=root/'original_descriptor_origin/ORIGIN_SEAL.json';verify(u,sha(u));verify(o,sha(o))
    rows=project(read(u.parent/'SOURCE_POINTERS.PRIVATE.json'),read(u.parent/'PATH_REDACTION_AUDIT.json'),read(u.parent/'UNITS.json'),read(u.parent/'ORIGINAL_EVIDENCE.PRIVATE.json'),read(o.parent/'DESCRIPTORS.PRIVATE.json'))
    d=root/'privacy_sensitivity_binding';d.mkdir(exist_ok=True);d.chmod(0o700);final=d/'BINDING_SEAL.json'
    if final.exists():verify(final,sha(final));require(read(d/'SENSITIVITY_MAP.PRIVATE.json')==rows,'immutable original affected map');return d
    write(d/'SENSITIVITY_MAP.PRIVATE.json',rows)
    write(final,dict(experiment='E117',part='main',status='COMPLETE_SOURCE_ONLY_PRIVACY_SENSITIVITY_BINDING',affected=8,judgments_opened=False,scientific_analysis_run=False,labels_cpu_only=True,original_audit_sha256=sha(u.parent/'PATH_REDACTION_AUDIT.json'),source_seals=[dict(seal=str(x),sha256=sha(x)) for x in (u,o)],files={'SENSITIVITY_MAP.PRIVATE.json':sha(d/'SENSITIVITY_MAP.PRIVATE.json')}))
    return d


if __name__=='__main__':print('E117 source-only privacy binding '+sha(build()/'BINDING_SEAL.json'))
