"""E97 prospective judge-copy support using existing 79f63fe0/25c32f25 rules.
Original sealed candidates, properties, IDs, private joins and rubrics stay intact.
"""
from pathlib import Path
from .e97_channel import E97Bank,channels,SHARED,ROOT
from .privacy79 import redact
from projects.g_agreement.readerbench.io import read,write,sha
from projects.g_agreement.readerbench.scoring import require
HERE=ROOT/'results/g_agreement/understand/blind_judge/e97_bank/privacy_copy'


def source_gate():
    for name,digest in read(HERE/'SOURCE_SEAL.json')['files'].items():require(sha(ROOT/name)==digest,'E97 privacy-copy source pin')


def judge_copy(records):
    flat=[dict(id=x['id'],readout=x['readout']) for x in records]
    copied,audit=redact(flat,'E97',addresses=True)
    require([x['id'] for x in copied]==[x['id'] for x in records],'same frozen opaque ID order')
    return [dict(raw,readout=copy['readout']) for raw,copy in zip(records,copied)],audit


class E97PrivacyCopyBank(E97Bank):
    def __init__(self,input_seal,input_sha):
        source_gate();super().__init__(input_seal,input_sha)
        raw=read(self.path.parent/'CANDIDATES.PRIVATE.json')
        self.copied,self.audit=judge_copy(raw);self.channels=channels(self.copied)
        self.original_candidate_sha256=sha(self.path.parent/'CANDIDATES.PRIVATE.json')

    def preflight(self):
        a=super().preflight();a.update(source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),transport_source_seal_sha256=sha(HERE.parent/'SOURCE_SEAL.json'),judge_copy_privacy_authorities=['79f63fe0','25c32f25'],redacted_records=self.audit['redacted_records'],redacted_opaque_ids=[x['id'] for x in self.audit['affected']],original_candidate_sha256=self.original_candidate_sha256)
        return a

    def run(self,receipt,key):
        require(receipt.get('judge_copy_privacy_authorities')==['79f63fe0','25c32f25'],'receipt must bind existing path/address judge-copy authority')
        source_gate();super().run(receipt,key)
        require(sha(self.path.parent/'CANDIDATES.PRIVATE.json')==self.original_candidate_sha256,'original candidate file unchanged')
        job=SHARED/'E97/judgments';path=job/'JUDGMENT_SEAL.json';seal=read(path)
        write(job/'PATH_REDACTION_AUDIT.json',self.audit)
        write(job/'JUDGE_COPY_INPUT_BINDING.json',dict(original_input_sha256=self.input_sha,original_candidate_sha256=self.original_candidate_sha256,judge_copy_source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),authorities=['79f63fe0','25c32f25']))
        seal.update(source_seal_sha256=sha(HERE/'SOURCE_SEAL.json'),transport_source_seal_sha256=sha(HERE.parent/'SOURCE_SEAL.json'),redacted_opaque_ids=[x['id'] for x in self.audit['affected']],redaction_audit_complete=True,privacy_copy_finalized=True)
        for name in ['PATH_REDACTION_AUDIT.json','JUDGE_COPY_INPUT_BINDING.json']:seal['files'][name]=sha(job/name)
        write(path,seal)
